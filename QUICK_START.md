# Quick Start - Production Deployment

## 1. Server Setup (5 minutes)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes
```

## 2. Configure Application (3 minutes)

```bash
# Edit production environment
nano .env.prod

# REQUIRED CHANGES:
# 1. SECRET_KEY - Generate new: python3 -c "import secrets; print(secrets.token_urlsafe(50))"
# 2. ALLOWED_HOSTS=your-domain.com,www.your-domain.com
# 3. DB_PASSWORD=your-strong-password
# 4. CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Update nginx domain
nano nginx/conf.d/default.conf
# Replace all instances of 'your-domain.com' with your actual domain
```

## 3. Deploy (2 minutes)

```bash
# Make scripts executable
chmod +x deploy.sh init-letsencrypt.sh

# Initial deployment
docker-compose -f docker-compose.prod.yml up -d db web
sleep 15

# Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
docker-compose -f docker-compose.prod.yml exec web python manage.py seed_phases
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Create admin user
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## 4. Setup SSL (5 minutes)

```bash
# Edit SSL script
nano init-letsencrypt.sh
# Update: domains=(your-domain.com www.your-domain.com)
# Update: email="your-email@example.com"

# Run SSL setup
./init-letsencrypt.sh
```

## 5. Start Everything

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Done! 🎉

Your application is now running at:
- https://your-domain.com
- https://your-domain.com/admin/

## Common Commands

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart
docker-compose -f docker-compose.prod.yml restart

# Update app
./deploy.sh

# Backup database
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres startup_portal > backup.sql
```

## Troubleshooting

**Can't connect to database:**
```bash
docker-compose -f docker-compose.prod.yml logs db
docker-compose -f docker-compose.prod.yml exec db pg_isready -U postgres
```

**Static files not loading:**
```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
docker-compose -f docker-compose.prod.yml restart nginx
```

**SSL issues:**
```bash
docker-compose -f docker-compose.prod.yml logs certbot
docker-compose -f docker-compose.prod.yml exec certbot certbot certificates
```

For detailed documentation, see DEPLOYMENT.md
