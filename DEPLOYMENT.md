# Render Deployment Guide

This guide will help you deploy the Hacker News Jobs API to Render using the zero-cost free tier.

## Prerequisites

1. A GitHub account
2. A Render account (sign up at https://render.com)
3. Your code pushed to a GitHub repository

## Deployment Steps

### Option 1: One-Click Deployment (Recommended)

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy using Render Blueprint**
   - Go to https://dashboard.render.com
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Select the repository containing this project
   - Render will automatically detect `render.yaml` and create:
     - A web service (Flask API)
     - A PostgreSQL database
   - Click "Apply" to deploy

3. **Environment Variables**
   - Render will automatically set `DATABASE_URL` when you create a PostgreSQL database
   - The database will be linked to your web service automatically
   - Optional: Adjust `CACHE_TIMEOUT` and `SCRAPE_INTERVAL` in the Render dashboard

### Option 2: Manual Deployment

1. **Create PostgreSQL Database**
   - Go to Render Dashboard → "New +" → "PostgreSQL"
   - Choose "Free" plan
   - Name it (e.g., "hacker-news-jobs-db")
   - Note the `DATABASE_URL` (you'll need it later)

2. **Create Web Service**
   - Go to Render Dashboard → "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository
   - Configure:
     - **Name**: hacker-news-jobs-api
     - **Region**: Choose closest to you
     - **Branch**: main (or your default branch)
     - **Root Directory**: (leave empty if root)
     - **Runtime**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
     - **Plan**: Free

3. **Set Environment Variables**
   - In the web service settings, go to "Environment"
   - Add these variables:
     - `DATABASE_URL`: (from PostgreSQL service - Internal Database URL)
     - `PORT`: `10000` (Render sets this automatically, but good to have)
     - `CACHE_TIMEOUT`: `300` (optional)
     - `SCRAPE_INTERVAL`: `30` (optional)
     - `FLASK_ENV`: `production`

4. **Deploy**
   - Click "Create Web Service"
   - Render will build and deploy your app
   - Wait for deployment to complete (usually 2-5 minutes)

## Post-Deployment

1. **Verify Health**
   - Visit: `https://your-app-name.onrender.com/health`
   - Should return: `{"status": "healthy", "database": "healthy", ...}`

2. **Check API Documentation**
   - Visit: `https://your-app-name.onrender.com/docs`
   - Interactive Swagger UI should be available

3. **Test Endpoints**
   ```bash
   # Health check
   curl https://your-app-name.onrender.com/health
   
   # Get jobs
   curl https://your-app-name.onrender.com/jobs
   
   # Search jobs
   curl https://your-app-name.onrender.com/jobs/search?q=python
   ```

## Free Tier Limitations

### Render Free Tier:
- **Web Services**: 
  - Spins down after 15 minutes of inactivity
  - First request after spin-down takes ~30 seconds (cold start)
  - 750 hours/month free
- **PostgreSQL Database**:
  - 1 GB storage
  - 90 days retention
  - Automatic backups

### Recommendations:
- Use a cron job or uptime monitor to ping `/health` every 10 minutes to prevent spin-down
- Consider upgrading to paid tier for production use
- Monitor database size to stay under 1 GB limit

## Troubleshooting

### Database Connection Issues
- Verify `DATABASE_URL` is set correctly
- Check that PostgreSQL service is running
- Ensure the database URL uses `postgresql://` (app.py handles `postgres://` conversion)

### App Won't Start
- Check build logs in Render dashboard
- Verify all dependencies in `requirements.txt`
- Ensure `gunicorn` is in requirements.txt (it is)

### Background Jobs Not Running
- Background scheduler starts automatically
- Check logs in Render dashboard for scheduler messages
- Verify `SCRAPE_INTERVAL` is set correctly

### Rate Limiting Issues
- Default limits: 200/day, 50/hour per IP
- Adjust in `app.py` if needed for your use case

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Server port (Render sets this automatically) |
| `DATABASE_URL` | `sqlite:///jobs.db` | Database connection string |
| `CACHE_TIMEOUT` | `300` | Cache timeout in seconds |
| `SCRAPE_INTERVAL` | `30` | Background scrape interval in minutes |
| `FLASK_ENV` | `production` | Flask environment |

## Monitoring

- **Logs**: View in Render dashboard → Your Service → Logs
- **Metrics**: Available in Render dashboard
- **Health Checks**: Use `/health` endpoint for monitoring

## Updating Your App

1. Push changes to GitHub
2. Render automatically detects and deploys updates
3. Monitor deployment in Render dashboard

## Zero-Cost Stack Summary

✅ **Web Service**: Render Free Tier  
✅ **Database**: Render PostgreSQL Free Tier  
✅ **Total Cost**: $0/month

Perfect for:
- Personal projects
- Portfolio demonstrations
- Low-traffic APIs
- Development/testing

---

**Need Help?** Check Render's documentation: https://render.com/docs

