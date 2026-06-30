# Deployment Guide

## Ubuntu / Linux Production Setup

### 1. System Prerequisites

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3.11-dev \
    libopencv-dev ffmpeg git curl build-essential

# Optional: NVIDIA CUDA (for GPU acceleration)
# Follow https://docs.nvidia.com/cuda/cuda-installation-guide-linux/
```

### 2. Application Setup

```bash
# Clone / copy project
git clone <your-repo> /opt/yolo11-detection
cd /opt/yolo11-detection/streamlit_app

# Create virtual environment
python3.11 -m venv /opt/yolo11-venv
source /opt/yolo11-venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install GPU support (optional, requires CUDA)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 3. Environment Configuration

```bash
cat > /opt/yolo11-detection/streamlit_app/.env << 'EOF'
ADMIN_PASSWORD=change-this-strong-password
ADMIN_EMAIL=admin@yourdomain.com
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com
SECRET_KEY=your-64-char-random-secret
EOF

chmod 600 /opt/yolo11-detection/streamlit_app/.env
```

### 4. Systemd Service

```ini
# /etc/systemd/system/yolo11-detection.service
[Unit]
Description=YOLO11 Detection Platform
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/yolo11-detection/streamlit_app
Environment=PATH=/opt/yolo11-venv/bin
ExecStart=/opt/yolo11-venv/bin/streamlit run app.py \
    --server.port 5000 \
    --server.address 127.0.0.1 \
    --server.headless true \
    --browser.gatherUsageStats false
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable yolo11-detection
sudo systemctl start yolo11-detection
sudo systemctl status yolo11-detection
```

### 5. Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/yolo11-detection
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    client_max_body_size 600M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/yolo11-detection /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## Windows Production Setup

### 1. Prerequisites

- Python 3.11 from [python.org](https://www.python.org/downloads/)
- Optional: CUDA Toolkit from [nvidia.com](https://developer.nvidia.com/cuda-downloads)
- Nginx for Windows (optional) or IIS with ARR

### 2. Application Setup (PowerShell)

```powershell
# Create virtual environment
cd C:\yolo11-detection\streamlit_app
python -m venv venv
.\venv\Scripts\Activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# GPU support (optional)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 3. Environment File

Create `C:\yolo11-detection\streamlit_app\.env`:
```
ADMIN_PASSWORD=strong-password
ADMIN_EMAIL=admin@company.com
SECRET_KEY=your-random-secret-64-chars
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com
```

### 4. Windows Service (NSSM)

```powershell
# Download NSSM from https://nssm.cc/
nssm install "YOLO11Detection" "C:\yolo11-detection\streamlit_app\venv\Scripts\streamlit.exe"
nssm set "YOLO11Detection" AppParameters "run app.py --server.port 5000 --server.headless true"
nssm set "YOLO11Detection" AppDirectory "C:\yolo11-detection\streamlit_app"
nssm set "YOLO11Detection" Start SERVICE_AUTO_START
nssm start "YOLO11Detection"
```

---

## Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx libglib2.0-0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["streamlit", "run", "app.py", \
     "--server.port=5000", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
    environment:
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI}
      - SECRET_KEY=${SECRET_KEY}
    restart: unless-stopped
```

```bash
docker-compose up -d
```

---

## Security Hardening

1. **Change default admin password** immediately after first login
2. **Use HTTPS** in production (Nginx + Let's Encrypt)
3. **Restrict file upload size** in Nginx (`client_max_body_size`)
4. **Firewall**: only expose 80/443 externally, keep 5000 internal
5. **Rotate SECRET_KEY** if you suspect compromise (invalidates sessions)
6. **Database backups**: download via Admin Panel → Database tab
7. **Google OAuth**: restrict to your domain in Google Console
8. **Disable public registration** in Admin → System Settings if needed

---

## Performance Tuning

### GPU Acceleration

Select "cuda" as the device in Settings or detection pages. Requires:
- NVIDIA GPU with CUDA 11.8+
- `torch` installed with CUDA support
- Proper CUDA drivers

### Model Selection

- Use `yolo11n` for real-time applications (30+ FPS on modern CPU)
- Use `yolo11m/l` for batch processing where accuracy matters
- First run downloads the model weights (~6-136 MB)

### Video Processing

- Increase **frame skip** (2-5) for faster processing with minor accuracy loss
- For RTSP streams, reduce resolution at the camera source

### Memory

- Each loaded YOLO model uses ~200MB–1GB RAM (CPU) or VRAM (GPU)
- Use "Clear Model Cache" in Settings to free memory
- Old files auto-clean via Settings page (files > 24h old)
