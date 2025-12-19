# Deployment Guide

This guide covers the initial setup and management of the P2P project on an Ubuntu server using systemctl and Nginx.

## Prerequisites

- Ubuntu 18.04 or later
- Python 3.8+
- Nginx installed
- Project located at: `/home/ubuntu/project1/backend_server/`

## Directory Structure

```
/home/ubuntu/project1/backend_server/
├── manage.py
├── requirements.txt
├── db.sqlite3
├── staticfiles/
├── p2p_project/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── core_app/
│   └── ...
└── deployment/
    ├── nginx_p2p.conf
    ├── p2p_project.service
    └── DEPLOYMENT_GUIDE.md
```

---

## 1. Initial Service Setup (Systemctl)

### 1.1 Copy Service File

Copy the systemd service file to the system directory:

```bash
sudo cp /home/ubuntu/project1/backend_server/deployment/p2p_project.service /etc/systemd/system/
```

### 1.2 Set Correct Permissions

```bash
sudo chmod 644 /etc/systemd/system/p2p_project.service
```

### 1.3 Reload Systemd Daemon

After adding or modifying service files, reload the systemd daemon:

```bash
sudo systemctl daemon-reload
```

### 1.4 Enable Service to Start on Boot

```bash
sudo systemctl enable p2p_project
```

### 1.5 Start the Service

```bash
sudo systemctl start p2p_project
```

### 1.6 Verify Service Status

```bash
sudo systemctl status p2p_project
```

Expected output should show the service as **active (running)**.

---

## 2. Nginx Configuration

### 2.1 Copy Nginx Configuration

Copy the Nginx configuration file to the Nginx sites-available directory:

```bash
sudo cp /home/ubuntu/project1/backend_server/deployment/nginx_p2p.conf /etc/nginx/sites-available/
```

### 2.2 Create Symbolic Link to sites-enabled

```bash
sudo ln -s /etc/nginx/sites-available/nginx_p2p.conf /etc/nginx/sites-enabled/
```

### 2.3 Test Nginx Configuration

Before reloading, always test the configuration for syntax errors:

```bash
sudo nginx -t
```

**Expected output:**
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

If there are errors, fix them in `/etc/nginx/sites-available/nginx_p2p.conf` and test again.

### 2.4 Create Static Files Directory

Ensure the staticfiles directory exists:

```bash
mkdir -p /home/ubuntu/project1/backend_server/staticfiles/
sudo chown -R www-data:www-data /home/ubuntu/project1/backend_server/
```

### 2.5 Collect Static Files (Django)

From the project directory, run:

```bash
cd /home/ubuntu/project1/backend_server/
python manage.py collectstatic --noinput
```

---

## 3. Service Management Commands

### Check Service Status

```bash
sudo systemctl status p2p_project
```

### Restart Service

```bash
sudo systemctl restart p2p_project
```

### Stop Service

```bash
sudo systemctl stop p2p_project
```

### View Service Logs

```bash
sudo journalctl -u p2p_project -f
```

View the last 50 lines:
```bash
sudo journalctl -u p2p_project -n 50
```

---

## 4. Nginx Management Commands

### Test Nginx Configuration

Always run this before reloading to catch configuration errors:

```bash
sudo nginx -t
```

### Reload Nginx (without stopping)

```bash
sudo systemctl reload nginx
```

### Restart Nginx

```bash
sudo systemctl restart nginx
```

### Check Nginx Status

```bash
sudo systemctl status nginx
```

### View Nginx Logs

Access log:
```bash
sudo tail -f /var/log/nginx/access.log
```

Error log:
```bash
sudo tail -f /var/log/nginx/error.log
```

---

## 5. Complete Restart Procedure

Follow these steps to perform a complete restart of the application:

### Step 1: Test Nginx Configuration

```bash
sudo nginx -t
```

If errors are found, fix them before proceeding.

### Step 2: Reload Nginx

```bash
sudo systemctl reload nginx
```

### Step 3: Restart the P2P Service

```bash
sudo systemctl restart p2p_project
```

### Step 4: Verify Services

```bash
sudo systemctl status nginx
sudo systemctl status p2p_project
```

Both should show **active (running)**.

---

## 6. Troubleshooting

### Service Won't Start

Check the service logs:
```bash
sudo journalctl -u p2p_project -n 100
```

**Error: exit-code 217/USER**

This indicates a user or working directory issue:

1. Verify the service file paths are correct:
```bash
sudo cat /etc/systemd/system/p2p_project.service
```

2. Check if user exists:
```bash
id ubuntu
```

3. Update service file if paths are wrong:
```bash
sudo nano /etc/systemd/system/p2p_project.service
```

Ensure these paths are correct:
- `WorkingDirectory=/home/ubuntu/project1/backend_server`
- `ExecStart=/home/ubuntu/project1/backend_server/venv/bin/daphne -b 0.0.0.0 -p 9000 p2p_project.asgi:application`

4. Reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart p2p_project
```

**Other Common Issues:**
- Port 9000 already in use: `sudo lsof -i :9000`
- Permission issues: `sudo chown -R ubuntu:www-data /home/ubuntu/project1/`
- Missing virtual environment: Create it with `python -m venv /home/ubuntu/project1/backend_server/venv`
- Missing dependencies: `source /home/ubuntu/project1/backend_server/venv/bin/activate && pip install -r requirements.txt`

### Nginx Configuration Error

Test the configuration:
```bash
sudo nginx -t
```

View the error details and fix the configuration file.

### Connection Refused

Verify the backend service is running:
```bash
sudo systemctl status p2p_project
```

Check if the service is listening on port 9000:
```bash
sudo netstat -tlnp | grep 9000
```

### Permission Denied

Ensure Nginx user has access to staticfiles:
```bash
sudo chown -R www-data:www-data /home/ubuntu/project1/backend_server/staticfiles/
sudo chmod 755 /home/ubuntu/project1/backend_server/
```

---

## 7. Quick Reference Commands

| Task | Command |
|------|---------|
| Start service | `sudo systemctl start p2p_project` |
| Stop service | `sudo systemctl stop p2p_project` |
| Restart service | `sudo systemctl restart p2p_project` |
| Service status | `sudo systemctl status p2p_project` |
| Enable on boot | `sudo systemctl enable p2p_project` |
| View logs | `sudo journalctl -u p2p_project -f` |
| Test Nginx | `sudo nginx -t` |
| Reload Nginx | `sudo systemctl reload nginx` |
| Restart Nginx | `sudo systemctl restart nginx` |
| Nginx status | `sudo systemctl status nginx` |

---

## 8. Server Information

- **Server IP**: 46.62.195.191
- **Backend Port**: 9000
- **Nginx Port**: 80
- **Project Path**: /home/ubuntu/project1/backend_server/
- **Static Files Path**: /home/ubuntu/project1/backend_server/staticfiles/

---

## Notes

- Always test Nginx configuration with `nginx -t` before reloading
- Keep backups of configuration files before making changes
- Monitor logs regularly for any issues
- Set up log rotation to prevent disk space issues
- Consider enabling HTTPS with Let's Encrypt in production
