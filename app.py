import os
import logging
import re
import random
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database URL configuration with PostgreSQL support
# Fix for Render/Neon: convert postgres:// to postgresql://
database_url = os.environ.get('DATABASE_URL', 'sqlite:///jobs.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
    logger.info("Converted postgres:// to postgresql:// for SQLAlchemy compatibility")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CACHE_TIMEOUT'] = int(os.environ.get('CACHE_TIMEOUT', 300))  # 5 minutes default

# Initialize extensions
db = SQLAlchemy(app)
CORS(app)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# API Documentation
api = Api(
    app,
    version='2.0',
    title='Hacker News Jobs API',
    description='Enhanced API for scraping and managing Hacker News job listings',
    doc='/docs'
)

# Cache storage (in-memory, can be upgraded to Redis)
cache = {
    'jobs': None,
    'timestamp': None
}

# Database Models
class Job(db.Model):
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    hn_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    company = db.Column(db.String(200))
    location = db.Column(db.String(200))
    posted_date = db.Column(db.DateTime)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_new = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'hn_id': self.hn_id,
            'title': self.title,
            'url': self.url,
            'company': self.company,
            'location': self.location,
            'posted_date': self.posted_date.isoformat() if self.posted_date else None,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'is_new': self.is_new
        }

# API Models for Swagger documentation
job_model = api.model('Job', {
    'id': fields.Integer(description='Database ID'),
    'hn_id': fields.String(description='Hacker News job ID'),
    'title': fields.String(description='Job title'),
    'url': fields.String(description='Job URL'),
    'company': fields.String(description='Company name'),
    'location': fields.String(description='Job location'),
    'posted_date': fields.String(description='Posting date'),
    'scraped_at': fields.String(description='When job was scraped'),
    'is_new': fields.Boolean(description='Whether job is new')
})

# Helper Functions
def extract_company_from_title(title):
    """Extract company name from job title (e.g., 'Company Name is hiring...')"""
    patterns = [
        r'^(.+?)\s+(?:is\s+)?hiring',
        r'^(.+?)\s+-\s+',
        r'^(.+?):\s+',
    ]
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def extract_location_from_title(title):
    """Extract location from title if mentioned"""
    location_patterns = [
        r'\b(Remote|San Francisco|SF|New York|NYC|London|Berlin|Amsterdam|Toronto|Vancouver|Austin|Seattle|Boston)\b',
        r'\(([^)]+)\)',  # Location in parentheses
    ]
    for pattern in location_patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return match.group(1) if match.groups() else match.group(0)
    return None

def parse_hn_date(date_str):
    """Parse Hacker News date format"""
    try:
        # HN uses relative dates, we'll store as is for now
        # Could be enhanced with date parsing
        return datetime.utcnow()
    except:
        return datetime.utcnow()

def get_random_user_agent():
    """Generate a random User-Agent to prevent blocking"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
    ]
    return random.choice(user_agents)

def scrape_jobs(page=1, use_cache=True):
    """Scrape jobs from Hacker News with pagination support"""
    # Check cache
    if use_cache and cache['jobs'] and cache['timestamp']:
        cache_age = datetime.utcnow() - cache['timestamp']
        if cache_age.total_seconds() < app.config['CACHE_TIMEOUT']:
            logger.info("Returning cached jobs")
            return cache['jobs']
    
    url = f"https://news.ycombinator.com/jobs"
    if page > 1:
        url = f"https://news.ycombinator.com/jobs?p={page}"
    
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = []
        
        # Find all job rows
        job_rows = soup.find_all('tr', class_='athing')
        
        for item in job_rows:
            try:
                title_line = item.find('span', class_='titleline')
                if not title_line:
                    continue
                
                link = title_line.find('a')
                if not link:
                    continue
                
                title = link.text.strip()
                href = link.get('href', '')
                
                # Handle relative URLs
                if href.startswith('item?'):
                    url_full = f"https://news.ycombinator.com/{href}"
                elif href.startswith('http'):
                    url_full = href
                else:
                    url_full = f"https://news.ycombinator.com/{href}"
                
                # Extract HN ID from URL or item
                hn_id = None
                if 'id=' in href:
                    hn_id = href.split('id=')[1].split('&')[0]
                else:
                    # Try to get from data attribute
                    hn_id = item.get('id', None)
                
                # Extract additional info
                company = extract_company_from_title(title)
                location = extract_location_from_title(title)
                
                # Find the next row which contains metadata
                metadata_row = item.find_next_sibling('tr')
                posted_date = None
                if metadata_row:
                    age_elem = metadata_row.find('span', class_='age')
                    if age_elem:
                        posted_date = parse_hn_date(age_elem.get('title', ''))
                
                job_data = {
                    'hn_id': hn_id or f"unknown_{int(time.time())}",
                    'title': title,
                    'url': url_full,
                    'company': company,
                    'location': location,
                    'posted_date': posted_date
                }
                
                jobs.append(job_data)
                
            except Exception as e:
                logger.warning(f"Error parsing job item: {e}")
                continue
        
        # Update cache
        cache['jobs'] = jobs
        cache['timestamp'] = datetime.utcnow()
        
        logger.info(f"Scraped {len(jobs)} jobs from page {page}")
        return jobs
        
    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
        raise Exception(f"Failed to fetch jobs: {str(e)}")
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        raise Exception(f"Failed to parse jobs: {str(e)}")

def save_jobs_to_db(jobs_data):
    """Save scraped jobs to database, marking new ones"""
    new_count = 0
    for job_data in jobs_data:
        existing_job = Job.query.filter_by(hn_id=job_data['hn_id']).first()
        
        if existing_job:
            # Update existing job
            existing_job.title = job_data['title']
            existing_job.url = job_data['url']
            existing_job.company = job_data.get('company')
            existing_job.location = job_data.get('location')
            existing_job.posted_date = job_data.get('posted_date')
            existing_job.is_new = False
        else:
            # Create new job
            new_job = Job(
                hn_id=job_data['hn_id'],
                title=job_data['title'],
                url=job_data['url'],
                company=job_data.get('company'),
                location=job_data.get('location'),
                posted_date=job_data.get('posted_date'),
                is_new=True
            )
            db.session.add(new_job)
            new_count += 1
    
    db.session.commit()
    logger.info(f"Saved {new_count} new jobs to database")
    return new_count

def background_scrape():
    """Background job to scrape and save jobs periodically"""
    with app.app_context():
        try:
            logger.info("Running background scrape job")
            jobs = scrape_jobs(use_cache=False)
            save_jobs_to_db(jobs)
        except Exception as e:
            logger.error(f"Background scrape failed: {e}")

# API Routes
@api.route('/')
class Home(Resource):
    def get(self):
        """API status and information"""
        return {
            "status": "API is Live",
            "version": "2.0",
            "endpoints": {
                "jobs": "/jobs - Get all jobs",
                "jobs_new": "/jobs/new - Get only new jobs",
                "jobs_search": "/jobs/search?q=query - Search jobs",
                "health": "/health - Health check",
                "stats": "/stats - API statistics"
            },
            "documentation": "/docs"
        }

@api.route('/health')
class Health(Resource):
    def get(self):
        """Health check endpoint"""
        try:
            # Check database connection
            db.session.execute(db.text('SELECT 1'))
            db_status = "healthy"
        except:
            db_status = "unhealthy"
        
        return {
            "status": "healthy",
            "database": db_status,
            "timestamp": datetime.utcnow().isoformat(),
            "cache_age_seconds": (datetime.utcnow() - cache['timestamp']).total_seconds() if cache['timestamp'] else None
        }

@api.route('/stats')
class Stats(Resource):
    def get(self):
        """Get API statistics"""
        total_jobs = Job.query.count()
        new_jobs = Job.query.filter_by(is_new=True).count()
        oldest_job = Job.query.order_by(Job.scraped_at.asc()).first()
        newest_job = Job.query.order_by(Job.scraped_at.desc()).first()
        
        return {
            "total_jobs": total_jobs,
            "new_jobs": new_jobs,
            "oldest_job_date": oldest_job.scraped_at.isoformat() if oldest_job else None,
            "newest_job_date": newest_job.scraped_at.isoformat() if newest_job else None,
            "cache_enabled": cache['timestamp'] is not None,
            "cache_age_seconds": (datetime.utcnow() - cache['timestamp']).total_seconds() if cache['timestamp'] else None
        }

@api.route('/jobs')
class Jobs(Resource):
    @api.doc(params={
        'page': 'Page number (default: 1)',
        'limit': 'Number of results per page (default: 30)',
        'search': 'Search query to filter jobs',
        'company': 'Filter by company name',
        'location': 'Filter by location',
        'new_only': 'Return only new jobs (true/false)',
        'use_cache': 'Use cached results (true/false, default: true)'
    })
    @api.marshal_list_with(job_model)
    @limiter.limit("30 per minute")
    def get(self):
        """Get all jobs with optional filtering and pagination"""
        try:
            # Get query parameters
            page = int(request.args.get('page', 1))
            limit = min(int(request.args.get('limit', 30)), 100)  # Max 100 per page
            search = request.args.get('search', '').lower()
            company = request.args.get('company', '').lower()
            location = request.args.get('location', '').lower()
            new_only = request.args.get('new_only', 'false').lower() == 'true'
            use_cache = request.args.get('use_cache', 'true').lower() == 'true'
            
            # Check if we should scrape fresh data or use database
            use_db = request.args.get('use_db', 'true').lower() == 'true'
            
            if use_db:
                # Query from database
                query = Job.query
                
                if new_only:
                    query = query.filter_by(is_new=True)
                
                if search:
                    query = query.filter(Job.title.ilike(f'%{search}%'))
                
                if company:
                    query = query.filter(Job.company.ilike(f'%{company}%'))
                
                if location:
                    query = query.filter(Job.location.ilike(f'%{location}%'))
                
                # Order by newest first
                query = query.order_by(Job.scraped_at.desc())
                
                # Pagination
                total = query.count()
                jobs = query.offset((page - 1) * limit).limit(limit).all()
                
                return {
                    'jobs': [job.to_dict() for job in jobs],
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total,
                        'pages': (total + limit - 1) // limit
                    }
                }
            else:
                # Scrape fresh data
                jobs_data = scrape_jobs(page=page, use_cache=use_cache)
                
                # Apply filters
                if search:
                    jobs_data = [j for j in jobs_data if search in j['title'].lower()]
                if company:
                    jobs_data = [j for j in jobs_data if j.get('company', '').lower().find(company) != -1]
                if location:
                    jobs_data = [j for j in jobs_data if j.get('location', '').lower().find(location) != -1]
                
                # Pagination
                total = len(jobs_data)
                start = (page - 1) * limit
                end = start + limit
                jobs_data = jobs_data[start:end]
                
                return {
                    'jobs': jobs_data,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total,
                        'pages': (total + limit - 1) // limit
                    }
                }
                
        except Exception as e:
            logger.error(f"Error in /jobs: {e}")
            api.abort(500, f"Internal server error: {str(e)}")

@api.route('/jobs/new')
class NewJobs(Resource):
    @api.marshal_list_with(job_model)
    @limiter.limit("30 per minute")
    def get(self):
        """Get only new jobs that haven't been seen before"""
        try:
            jobs = Job.query.filter_by(is_new=True).order_by(Job.scraped_at.desc()).all()
            return [job.to_dict() for job in jobs]
        except Exception as e:
            logger.error(f"Error in /jobs/new: {e}")
            api.abort(500, f"Internal server error: {str(e)}")

@api.route('/jobs/search')
class SearchJobs(Resource):
    @api.doc(params={'q': 'Search query'})
    @api.marshal_list_with(job_model)
    @limiter.limit("30 per minute")
    def get(self):
        """Search jobs by title, company, or location"""
        try:
            query = request.args.get('q', '').lower()
            if not query:
                api.abort(400, "Search query parameter 'q' is required")
            
            jobs = Job.query.filter(
                db.or_(
                    Job.title.ilike(f'%{query}%'),
                    Job.company.ilike(f'%{query}%'),
                    Job.location.ilike(f'%{query}%')
                )
            ).order_by(Job.scraped_at.desc()).limit(50).all()
            
            return [job.to_dict() for job in jobs]
        except Exception as e:
            logger.error(f"Error in /jobs/search: {e}")
            api.abort(500, f"Internal server error: {str(e)}")

@api.route('/jobs/refresh')
class RefreshJobs(Resource):
    @limiter.limit("10 per hour")
    def post(self):
        """Manually trigger a fresh scrape and save to database"""
        try:
            jobs = scrape_jobs(use_cache=False)
            new_count = save_jobs_to_db(jobs)
            return {
                "message": "Jobs refreshed successfully",
                "total_scraped": len(jobs),
                "new_jobs": new_count
            }
        except Exception as e:
            logger.error(f"Error in /jobs/refresh: {e}")
            api.abort(500, f"Failed to refresh jobs: {str(e)}")

# Initialize database
def init_db():
    """Initialize database tables - ensures tables exist"""
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database initialized - all tables created/verified")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

# Setup background scheduler
def setup_scheduler():
    """Setup background job scheduler - works in production with gunicorn"""
    scheduler = BackgroundScheduler(daemon=True)
    # Scrape every 30 minutes (configurable via SCRAPE_INTERVAL env var)
    scrape_interval = int(os.environ.get('SCRAPE_INTERVAL', 30))
    scheduler.add_job(
        func=background_scrape,
        trigger=IntervalTrigger(minutes=scrape_interval),
        id='scrape_jobs',
        name='Scrape Hacker News Jobs',
        replace_existing=True,
        max_instances=1  # Prevent overlapping jobs
    )
    scheduler.start()
    logger.info(f"Background scheduler started (interval: {scrape_interval} minutes)")
    return scheduler

# Global scheduler instance
scheduler = None
_app_initialized = False

def run_initial_scrape():
    """Helper function to run initial scrape"""
    try:
        logger.info("Running initial scrape...")
        jobs = scrape_jobs(use_cache=False)
        save_jobs_to_db(jobs)
    except Exception as e:
        logger.warning(f"Initial scrape failed: {e}")

def initialize_app():
    """Initialize database and scheduler - called on app startup"""
    global scheduler, _app_initialized
    
    if _app_initialized:
        return
    
    try:
        # Initialize database
        init_db()
        
        # Setup scheduler if not already running
        if scheduler is None or (hasattr(scheduler, 'running') and not scheduler.running):
            scheduler = setup_scheduler()
            
            # Schedule initial scrape after a short delay (non-blocking)
            try:
                logger.info("Scheduling initial scrape in background...")
                scheduler.add_job(
                    func=run_initial_scrape,
                    trigger='date',
                    run_date=datetime.utcnow() + timedelta(seconds=10),
                    id='initial_scrape',
                    replace_existing=True
                )
            except Exception as e:
                logger.warning(f"Initial scrape scheduling failed: {e}")
        
        _app_initialized = True
        logger.info("Application initialized successfully")
    except Exception as e:
        logger.error(f"App initialization error: {e}")

# Initialize on app import (works with gunicorn)
# This will run when gunicorn imports the app module
try:
    with app.app_context():
        initialize_app()
except Exception as e:
    logger.warning(f"Initialization at import time failed (will retry on first request): {e}")

# For direct execution (development)
if __name__ == "__main__":
    # Initialize database
    init_db()
    
    # Setup background scheduler
    scheduler = setup_scheduler()
    
    try:
        # Run initial scrape
        logger.info("Running initial scrape...")
        jobs = scrape_jobs(use_cache=False)
        save_jobs_to_db(jobs)
    except Exception as e:
        logger.warning(f"Initial scrape failed: {e}")
    
    # Start Flask app
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
