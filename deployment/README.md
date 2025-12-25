# Deployment Guide

## Production Deployment on Ubuntu Server

### Prerequisites

- Ubuntu Server with Docker installed
- Python 3.11+
- `uv` package manager installed
- Cloudflare Tunnel configured (optional, for external access)

---

## Installation Steps

### 1. Database Setup

Start the PostgreSQL database and Adminer:

```bash
cd /home/shazzy/projects/rri_orchestrator
docker compose up -d
```

Verify containers are running:
```bash
docker ps | grep rri
```

### 2. Application Dependencies

Install Python dependencies:

```bash
uv sync
```

### 3. Environment Configuration

Copy and configure environment variables:

```bash
cp .env.example .env
nano .env
```

Required variables:
- `DATABASE_URL` - PostgreSQL connection string
- `GEMINI_API_KEY` - Google AI API key
- `OPENAI_API_KEY` - OpenAI API key
- `SECRET_KEY` - Generate with `openssl rand -hex 32`

### 4. Database Initialization

Initialize database tables:

```bash
uv run python scripts/init_db.py
```

---

## Systemd Service Setup

### Install Service

1. Copy the service file to systemd:

```bash
sudo cp deployment/rri-orchestrator.service /etc/systemd/system/
```

2. Reload systemd and enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable rri-orchestrator
sudo systemctl start rri-orchestrator
```

3. Verify the service is running:

```bash
sudo systemctl status rri-orchestrator
```

### Service Management

**Start:**
```bash
sudo systemctl start rri-orchestrator
```

**Stop:**
```bash
sudo systemctl stop rri-orchestrator
```

**Restart:**
```bash
sudo systemctl restart rri-orchestrator
```

**View logs:**
```bash
journalctl -u rri-orchestrator -f
```

**Check status:**
```bash
sudo systemctl status rri-orchestrator
```

---

## Port Configuration

Default ports:
- **Application:** 8080
- **PostgreSQL:** 5432
- **Adminer (DB UI):** 8081

To change the application port, edit `.env`:
```env
PORT=8080
```

---

## External Access (Cloudflare Tunnel)

If using Cloudflare Tunnel for external access:

1. Install cloudflared:
```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

2. Configure tunnel to point to `localhost:8080`

3. Install as service:
```bash
sudo cloudflared --config /path/to/config.yml service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

---

## Troubleshooting

### Service won't start

Check logs:
```bash
journalctl -u rri-orchestrator -n 50 --no-pager
```

Common issues:
- Database not running: `docker compose up -d`
- Port already in use: Check with `ss -tuln | grep 8080`
- Environment variables missing: Verify `.env` file

### Database connection failed

Verify PostgreSQL is running:
```bash
docker ps | grep rri_postgres
```

Check database health:
```bash
docker exec rri_postgres pg_isready -U rri_user
```

### Permission errors

Ensure the service user has access:
```bash
sudo chown -R shazzy:shazzy /home/shazzy/projects/rri_orchestrator
```

---

## Updates and Maintenance

### Update application code

```bash
cd /home/shazzy/projects/rri_orchestrator
git pull
uv sync
sudo systemctl restart rri-orchestrator
```

### Database backup

```bash
docker exec rri_postgres pg_dump -U rri_user rri_orchestrator > backup_$(date +%Y%m%d).sql
```

### Database restore

```bash
cat backup.sql | docker exec -i rri_postgres psql -U rri_user -d rri_orchestrator
```

---

## Health Checks

Verify all components are running:

```bash
# Application
curl -I http://localhost:8080

# Database
docker exec rri_postgres pg_isready -U rri_user

# Service status
sudo systemctl is-active rri-orchestrator

# Auto-start enabled
sudo systemctl is-enabled rri-orchestrator
```

---

## Uninstall

To remove the service:

```bash
sudo systemctl stop rri-orchestrator
sudo systemctl disable rri-orchestrator
sudo rm /etc/systemd/system/rri-orchestrator.service
sudo systemctl daemon-reload
```

To remove Docker containers:

```bash
cd /home/shazzy/projects/rri_orchestrator
docker compose down -v
```
