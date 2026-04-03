# Production Deployment Guide

This guide covers deploying the Startup Portal application on Ubuntu using Docker, Docker Compose, and Nginx.

## Prerequisites

- Ubuntu 20.04+ server with root access
- Domain name pointing to your server's IP
- At least 2GB RAM and 20GB disk space

## Step 1: Install Docker and Docker Compose

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

## Step 2: Clone Repository

```bash
cd /opt
sudo git clone <your-repo-url> startup-portal
cd startup-portal
sudo chown -R $USER:$USER .
```

## Step 3: Configure Environment Variables

```bash
# Copy and edit production environment file
cp .env.prod .env.prod.local
nano .env.prod

# Update these critical values:
# - SECRET_KEY: Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# - ALLOWED_HOSTS: your-domain.com,www.your-domain.com
# - DB_PASSWORD: Strong database password
# - CSRF_TRUSTED_ORIGINS: https://your-domain.com,https://www.your-domain.com
# - EMAIL_* settings if using email
```

## Step 4: Configure Nginx

```bash
# Update domain in nginx config
nano nginx/conf.d/default.conf

# Replace 'your-domain.com' with your actual domain in:
# - server_name directives
# - SSL certificate paths
```

## Step 5: Initial Deployment

```bash
# Make scripts executable
chmod +x deploy.sh init-letsencrypt.sh

# Start without SSL first (for Let's Encrypt verification)
docker-compose -f docker-compose.prod.yml up -d db web

# Wait for services to be ready
sleep 15

# Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
docker-compose -f docker-compose.prod.yml exec web python manage.py seed_phases
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Create superuser
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## Step 6: Setup SSL with Let's Encrypt

```bash
# Edit init-letsencrypt.sh with your domain and email
nano init-letsencrypt.sh

# Update these variables:
# - domains=(your-domain.com www.your-domain.com)
# - email="your-email@example.com"
# - staging=0 (set to 1 for testing)

# Run SSL initialization
./init-letsencrypt.sh
```

## Step 7: Start Full Stack

```bash
# Start all services including nginx
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

## Step 8: Verify Deployment

Visit your domain:
- `https://your-domain.com` - API Swagger docs
- `https://your-domain.com/admin/` - Django admin
- `https://your-domain.com/api/users/register/` - User registration

## Maintenance Commands

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f nginx
docker-compose -f docker-compose.prod.yml logs -f db
```

### Restart Services
```bash
# Restart all
docker-compose -f docker-compose.prod.yml restart

# Restart specific service
docker-compose -f docker-compose.prod.yml restart web
```

### Update Application
```bash
# Use the deployment script
./deploy.sh

# Or manually:
git pull origin main
docker-compose -f docker-compose.prod.yml build web
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### Database Backup
```bash
# Backup
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres startup_portal > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres startup_portal < backup_file.sql
```

### Access Database
```bash
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -d startup_portal
```

### Django Shell
```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py shell
```

## Monitoring

### Check Container Health
```bash
docker-compose -f docker-compose.prod.yml ps
docker stats
```

### Check Disk Usage
```bash
df -h
docker system df
```

### Clean Up Old Images
```bash
docker system prune -a
```

## Firewall Configuration

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
sudo ufw status
```

## Security Checklist

- [ ] Changed SECRET_KEY to a strong random value
- [ ] Set DEBUG=False in production
- [ ] Updated ALLOWED_HOSTS with your domain
- [ ] Set strong DB_PASSWORD
- [ ] Configured CSRF_TRUSTED_ORIGINS
- [ ] SSL certificate installed and working
- [ ] Firewall configured (UFW)
- [ ] Regular backups scheduled
- [ ] Monitoring setup (optional: Sentry, New Relic)
- [ ] Created non-root user for deployment
- [ ] Disabled root SSH login

## Troubleshooting

### Container won't start
```bash
docker-compose -f docker-compose.prod.yml logs web
docker-compose -f docker-compose.prod.yml logs db
```

### Database connection issues
```bash
# Check if DB is running
docker-compose -f docker-compose.prod.yml exec db pg_isready -U postgres

# Check DATABASE_URL in .env.prod
```

### Static files not loading
```bash
# Recollect static files
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Check nginx logs
docker-compose -f docker-compose.prod.yml logs nginx
```

### SSL certificate issues
```bash
# Check certificate status
docker-compose -f docker-compose.prod.yml exec certbot certbot certificates

# Renew manually
docker-compose -f docker-compose.prod.yml exec certbot certbot renew
```

## Performance Optimization

### Increase Gunicorn Workers
Edit `docker-compose.prod.yml`:
```yaml
command: gunicorn startup_portal.wsgi:application --bind 0.0.0.0:8000 --workers 8 --timeout 120
```

Rule of thumb: `workers = (2 x CPU cores) + 1`

### Database Connection Pooling
Add to `settings.py`:
```python
DATABASES['default']['CONN_MAX_AGE'] = 600
```

### Enable Redis Caching (Optional)
Add Redis service to `docker-compose.prod.yml` and configure Django caching.

## Support

For issues or questions, check:
- Application logs: `docker-compose -f docker-compose.prod.yml logs`
- Django documentation: https://docs.djangoproject.com/
- Docker documentation: https://docs.docker.com/
