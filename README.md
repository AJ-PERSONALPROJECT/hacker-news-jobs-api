# Hacker News Jobs API v2.0

A comprehensive, production-ready Flask API for scraping and managing Hacker News job listings with advanced features including caching, database storage, background jobs, filtering, and full API documentation.

## 🚀 Features

### Core Features
- **Web Scraping**: Scrapes job listings from Hacker News
- **Enhanced Data Extraction**: Extracts title, URL, company name, location, and posting date
- **Database Storage**: SQLite/PostgreSQL support for persistent job storage
- **Caching**: In-memory caching to reduce API calls and improve response times
- **Background Jobs**: Automatic periodic scraping using APScheduler
- **Rate Limiting**: Built-in rate limiting to prevent abuse
- **API Documentation**: Full Swagger/OpenAPI documentation at `/docs`

### Advanced Features
- **Pagination**: Support for paginated results
- **Search & Filtering**: Search by keywords, filter by company or location
- **New Jobs Tracking**: Track which jobs are new vs. previously seen
- **Health Checks**: Health check endpoint for monitoring
- **Statistics**: API statistics endpoint
- **Error Handling**: Comprehensive error handling and logging
- **CORS Support**: Cross-origin resource sharing enabled

## 📋 Requirements

- Python 3.8+
- See `requirements.txt` for all dependencies

## 🛠️ Installation

1. **Clone or download this project**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize the database:**
   ```bash
   python init_db.py
   ```
   Or the database will be created automatically on first run.

5. **Run the application:**
   ```bash
   python app.py
   ```

The API will be available at `http://localhost:5000`

## 📚 API Endpoints

### Base URL
```
http://localhost:5000
```

### Endpoints

#### `GET /`
Get API status and available endpoints.

**Response:**
```json
{
  "status": "API is Live",
  "version": "2.0",
  "endpoints": {...},
  "documentation": "/docs"
}
```

#### `GET /health`
Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "database": "healthy",
  "timestamp": "2025-01-01T00:00:00",
  "cache_age_seconds": 120
}
```

#### `GET /stats`
Get API statistics.

**Response:**
```json
{
  "total_jobs": 150,
  "new_jobs": 5,
  "oldest_job_date": "2025-01-01T00:00:00",
  "newest_job_date": "2025-01-01T12:00:00",
  "cache_enabled": true,
  "cache_age_seconds": 120
}
```

#### `GET /jobs`
Get all jobs with optional filtering and pagination.

**Query Parameters:**
- `page` (int, default: 1): Page number
- `limit` (int, default: 30, max: 100): Results per page
- `search` (string): Search query to filter jobs
- `company` (string): Filter by company name
- `location` (string): Filter by location
- `new_only` (bool, default: false): Return only new jobs
- `use_cache` (bool, default: true): Use cached results
- `use_db` (bool, default: true): Query from database instead of scraping

**Examples:**
```bash
# Get all jobs
GET /jobs

# Get jobs with pagination
GET /jobs?page=2&limit=50

# Search for Python jobs
GET /jobs?search=python

# Filter by company
GET /jobs?company=google

# Filter by location
GET /jobs?location=remote

# Get only new jobs
GET /jobs?new_only=true

# Get fresh scraped data (bypass database)
GET /jobs?use_db=false
```

**Response:**
```json
{
  "jobs": [
    {
      "id": 1,
      "hn_id": "12345678",
      "title": "Company Name is hiring Software Engineer",
      "url": "https://news.ycombinator.com/item?id=12345678",
      "company": "Company Name",
      "location": "Remote",
      "posted_date": "2025-01-01T00:00:00",
      "scraped_at": "2025-01-01T00:00:00",
      "is_new": true
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 30,
    "total": 150,
    "pages": 5
  }
}
```

#### `GET /jobs/new`
Get only new jobs that haven't been seen before.

**Response:**
```json
[
  {
    "id": 1,
    "hn_id": "12345678",
    "title": "New Job Title",
    ...
  }
]
```

#### `GET /jobs/search?q=query`
Search jobs by title, company, or location.

**Query Parameters:**
- `q` (string, required): Search query

**Example:**
```bash
GET /jobs/search?q=python developer
```

#### `POST /jobs/refresh`
Manually trigger a fresh scrape and save to database.

**Response:**
```json
{
  "message": "Jobs refreshed successfully",
  "total_scraped": 30,
  "new_jobs": 5
}
```

**Rate Limit:** 10 requests per hour

## 📖 API Documentation

Interactive API documentation is available at:
```
http://localhost:5000/docs
```

This provides a Swagger UI where you can:
- View all endpoints
- See request/response schemas
- Test endpoints directly
- View rate limits

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set these environment variables:

- `PORT`: Server port (default: 5000)
- `DATABASE_URL`: Database connection string (default: `sqlite:///jobs.db`)
- `CACHE_TIMEOUT`: Cache timeout in seconds (default: 300)
- `SCRAPE_INTERVAL`: Background scrape interval in minutes (default: 30)

### Database Options

**SQLite (Default):**
```env
DATABASE_URL=sqlite:///jobs.db
```

**PostgreSQL:**
```env
DATABASE_URL=postgresql://user:password@localhost/jobsdb
```

## 🔄 Background Jobs

The application automatically runs background scraping jobs at configurable intervals (default: every 30 minutes). This ensures your database stays up-to-date without manual intervention.

To disable background jobs, you can modify the scheduler setup in `app.py`.

## 🛡️ Rate Limiting

Default rate limits:
- **200 requests per day** per IP
- **50 requests per hour** per IP
- **30 requests per minute** for `/jobs` endpoints
- **10 requests per hour** for `/jobs/refresh`

These can be adjusted in `app.py` if needed.

## 📊 Database Schema

### Jobs Table
- `id`: Primary key
- `hn_id`: Hacker News job ID (unique)
- `title`: Job title
- `url`: Job URL
- `company`: Extracted company name
- `location`: Extracted location
- `posted_date`: Posting date
- `scraped_at`: When job was scraped
- `is_new`: Whether job is new

## 🚢 Deployment

### Render.com
1. Connect your repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python app.py`
4. Add environment variables in dashboard

### Heroku
1. Create `Procfile`:
   ```
   web: python app.py
   ```
2. Deploy using Heroku CLI or GitHub integration

### Docker (Example)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

## 🧪 Testing

Test the API using curl:

```bash
# Health check
curl http://localhost:5000/health

# Get all jobs
curl http://localhost:5000/jobs

# Search jobs
curl http://localhost:5000/jobs/search?q=python

# Refresh jobs
curl -X POST http://localhost:5000/jobs/refresh
```

## 📝 Logging

The application logs to stdout with the following format:
```
2025-01-01 00:00:00 - app - INFO - Scraped 30 jobs from page 1
```

Logs include:
- Scraping operations
- Database operations
- Errors and warnings
- Background job execution

## 🔧 Troubleshooting

### Database Issues
- Ensure database file permissions are correct
- For PostgreSQL, verify connection string format
- Run `python init_db.py` to recreate tables

### Scraping Issues
- Check internet connectivity
- Verify Hacker News is accessible
- Check rate limiting (may need to adjust delays)

### Cache Issues
- Cache is in-memory and resets on restart
- Adjust `CACHE_TIMEOUT` for different cache durations
- Use `use_cache=false` parameter to bypass cache

## 🎯 Future Enhancements

Potential improvements:
- Redis caching for distributed systems
- Email notifications for new jobs
- Job deduplication improvements
- More sophisticated company/location extraction
- Job categorization/tagging
- Export functionality (CSV, JSON)
- Webhook support for new jobs

## 📄 License

This project is open source and available for use.

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## 📞 Support

For issues or questions, please open an issue in the repository.

---

**Version:** 2.0  
**Last Updated:** 2025

