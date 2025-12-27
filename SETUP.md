# Quick Setup Guide

## Step 1: Install Python Dependencies

Open PowerShell in this folder and run:

```powershell
python -m pip install -r requirements.txt
```

If `python` doesn't work, try:
```powershell
py -m pip install -r requirements.txt
```

## Step 2: Create .env File (Already Done!)

The `.env` file has been created from `.env.example`. You can edit it if needed.

## Step 3: Initialize Database (Optional)

The database will be created automatically on first run, but you can initialize it manually:

```powershell
python init_db.py
```

Or:
```powershell
py init_db.py
```

## Step 4: Run the Application

```powershell
python app.py
```

Or:
```powershell
py app.py
```

## Troubleshooting

### Python Not Found Error

If you see "Python was not found", you have a few options:

1. **Install Python from python.org**: Download from https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation

2. **Use Windows Store Python**: The Windows Store version should work, but you may need to:
   - Open Settings > Apps > Advanced app settings > App execution aliases
   - Disable the Python aliases that redirect to Microsoft Store
   - Then install Python properly from python.org

3. **Use `py` launcher**: Try using `py` instead of `python`:
   ```powershell
   py app.py
   ```

### Creating .env File (PowerShell)

If you need to create the .env file manually:

```powershell
# Copy from example
Copy-Item .env.example .env

# Or create new file
New-Item -Path .env -ItemType File
```

### Verify Python Installation

Check if Python is installed:
```powershell
where.exe python
where.exe py
python --version
py --version
```

## Next Steps

Once the app is running:
- Visit `http://localhost:5000` for the API
- Visit `http://localhost:5000/docs` for interactive API documentation
- Visit `http://localhost:5000/health` to check API health

