# Daphne Service Troubleshooting Guide

## Issue
The p2p_project.service fails to start with status 1/FAILURE.

## Root Causes

The most common reasons daphne exits with status 1:
1. **Pending database migrations** - New models/fields haven't been applied to the database
2. **Import errors** - Missing packages or syntax errors in code
3. **Missing dependencies** - Required Python packages not installed
4. **Configuration errors** - Invalid Django settings

## Solution Steps

### Step 1: Check for Pending Migrations

```bash
cd /home/ubuntu/deploy/apps/donikkah

# Activate virtual environment
source donikkahenv/bin/activate

# Check migration status
python manage.py showmigrations

# Apply pending migrations
python manage.py migrate
```

Expected output:
```
Running migrations:
  Applying core_app.0002_authenticationcode... OK
```

### Step 2: Check for Import/Syntax Errors

```bash
# Try to import and run the ASGI app directly to see the actual error
python -c "from p2p_project.asgi import application; print('ASGI app loaded successfully')"
```

If there's an error, you'll see the full traceback.

### Step 3: Verify Dependencies are Installed

```bash
# Check if required packages are installed
pip list | grep -E "daphne|channels|django|djangorestframework"

# If any are missing, install them
pip install -r requirements.txt
```

### Step 4: Test Daphne Directly

```bash
# Run daphne directly to see the actual error
daphne -b 0.0.0.0 -p 9000 p2p_project.asgi:application
```

This will show you the exact error message instead of just "exit-code 1".

### Step 5: Collect Static Files (if needed)

```bash
python manage.py collectstatic --noinput
```

### Step 6: Restart Service After Fixes

```bash
# Reload systemd
sudo systemctl daemon-reload

# Restart the service
sudo systemctl restart p2p_project.service

# Check status
sudo systemctl status p2p_project.service

# View logs
journalctl -u p2p_project.service -n 50 -f
```

## Detailed Debugging

### Check Service Logs
```bash
journalctl -u p2p_project.service -n 100 --no-pager
```

### Check Python Virtual Environment
```bash
which python
which daphne
daphne --version
```

### Manually Run Django Check
```bash
python manage.py check
```

This will report any Django configuration issues.

## Common Errors and Fixes

### "No module named 'core_app'"
```bash
# Make sure core_app is in INSTALLED_APPS in settings.py
# Then verify the app structure:
ls -la core_app/__init__.py
```

### "no such table" error
```bash
# Run migrations
python manage.py migrate
```

### "ModuleNotFoundError: No module named 'daphne'"
```bash
# Install daphne
pip install daphne
```

### Import errors in models.py
Check if `secrets` module is available (Python 3.6+) and if `json` is imported correctly.

## After Fixing - Restart Service

```bash
# Stop the service
sudo systemctl stop p2p_project.service

# Check it's stopped
sudo systemctl status p2p_project.service

# Start it again
sudo systemctl start p2p_project.service

# Monitor logs
sudo journalctl -u p2p_project.service -f
```

## Verify Service is Running

```bash
# Check if service is active
sudo systemctl is-active p2p_project.service

# Check if port 9000 is listening
netstat -tlnp | grep 9000
# or
ss -tlnp | grep 9000

# Test the endpoint
curl -X GET http://localhost:9000/api/status/
```

## Environment Variables

If the service file uses environment variables, make sure they're set correctly:

```bash
# Check service file
cat /etc/systemd/system/p2p_project.service

# Set environment variables if needed in the service file
# Example:
# Environment="DEBUG=False"
# Environment="DATABASE_URL=sqlite:///db.sqlite3"
```

## Quick Fix Summary

1. SSH into server
2. Navigate to project: `cd /home/ubuntu/deploy/apps/donikkah`
3. Activate venv: `source donikkahenv/bin/activate`
4. Run migrations: `python manage.py migrate`
5. Test daphne: `daphne -b 0.0.0.0 -p 9000 p2p_project.asgi:application`
6. If successful, restart service: `sudo systemctl restart p2p_project.service`
7. Verify: `sudo systemctl status p2p_project.service`

## Need More Help?

Run all checks at once:
```bash
set -e
cd /home/ubuntu/deploy/apps/donikkah
source donikkahenv/bin/activate
echo "=== Django Check ==="
python manage.py check
echo "=== Pending Migrations ==="
python manage.py showmigrations --plan | grep '\[ \]'
echo "=== Running Migrations ==="
python manage.py migrate
echo "=== Testing Daphne Import ==="
python -c "from p2p_project.asgi import application; print('SUCCESS: ASGI app loaded')"
echo "=== All tests passed ==="
```
