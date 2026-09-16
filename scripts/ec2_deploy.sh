#!/usr/bin/env bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=========================================================="
echo "      DEEPTRACE PRODUCTION DEPLOYMENT ENGINE (UBUNTU)     "
echo "=========================================================="

echo ">>> [1/8] Updating package lists and upgrading base packages..."
sudo apt-get update -y
sudo apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
    git curl wget build-essential python3.12 python3.12-venv python3-pip \
    libgl1 libglib2.0-0 tesseract-ocr tesseract-ocr-urd debian-keyring debian-archive-keyring apt-transport-https

echo ">>> [2/8] Installing Caddy Web Server..."
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg --yes
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update -y
sudo apt-get install -y caddy

echo ">>> [3/8] Installing Node.js 20.x LTS & PM2 process manager..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi
sudo npm install -g pm2

echo ">>> [4/8] Installing Docker Engine & Docker Compose Plugin..."
if ! command -v docker &> /dev/null; then
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker ubuntu
    sudo systemctl enable docker
    sudo systemctl start docker
fi

echo ">>> [5/8] Cloning / Pulling DeepTrace Codebase..."
cd /home/ubuntu
if [ -d "DeepTrace/.git" ]; then
    cd DeepTrace
    git fetch origin main
    git reset --hard origin/main
else
    rm -rf DeepTrace
    git clone https://github.com/samjanjua6/DeepTrace.git
    cd DeepTrace
fi

# Ensure .env exists
if [ ! -f ".env" ]; then
    cp .env.example .env
fi

echo ">>> [6/8] Starting PostgreSQL 16 & Redis via Docker Compose..."
sudo docker compose up -d

echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if sudo docker compose exec -T postgres pg_isready -U deeptrace -d deeptrace_db >/dev/null 2>&1; then
        echo "PostgreSQL is online and accepting connections!"
        break
    fi
    sleep 1
done

echo ">>> [7/8] Setting up Python 3.12 environment, Prisma, and database seed..."
cd /home/ubuntu/DeepTrace
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run Prisma schema push & database seeding
prisma db push
python scripts/seed_dev.py

echo ">>> [8/8] Building Frontend & Starting Daemons..."
cd /home/ubuntu/DeepTrace/frontend
npm install
npm run build

cd /home/ubuntu/DeepTrace
pm2 delete all || true
pm2 start "source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000" --name "deeptrace-api"
cd /home/ubuntu/DeepTrace/frontend
pm2 start "npm run start -- -p 3000" --name "deeptrace-web"
pm2 save
sudo env PATH=$PATH:/usr/bin /usr/lib/node_modules/pm2/bin/pm2-startup install -u ubuntu --hp /home/ubuntu || true

echo ">>> Configuring Caddy Reverse Proxy & HTTPS..."
sudo tee /etc/caddy/Caddyfile > /dev/null << 'EOF'
:80 {
    # Direct API and OpenAPI documentation routes to FastAPI
    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }
    handle /docs* {
        reverse_proxy 127.0.0.1:8000
    }
    handle /redoc* {
        reverse_proxy 127.0.0.1:8000
    }
    handle /openapi.json {
        reverse_proxy 127.0.0.1:8000
    }

    # Everything else served by Next.js Frontend
    handle {
        reverse_proxy 127.0.0.1:3000
    }
}
EOF

sudo systemctl enable caddy
sudo systemctl restart caddy

echo "=========================================================="
echo "   DEEPTRACE DEPLOYMENT COMPLETE & RUNNING IN BACKGROUND  "
echo "=========================================================="
pm2 status
sudo systemctl status caddy --no-pager | head -n 10
