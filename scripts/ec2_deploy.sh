#!/usr/bin/env bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "=========================================================="
echo "      DEEPTRACE PRODUCTION DEPLOYMENT ENGINE (UBUNTU)     "
echo "=========================================================="

echo ">>> [1/7] Installing system packages, Caddy, Node.js & Docker..."
sudo apt-get update -y
sudo apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
    git curl wget build-essential python3 python3-venv python3-pip \
    libgl1 libglib2.0-0 tesseract-ocr tesseract-ocr-urd \
    caddy docker.io docker-compose-v2

# Start and enable Docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu || true

# Install Node.js 20.x and PM2
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi
sudo npm install -g pm2

echo ">>> [2/7] Cloning or Updating DeepTrace Repository..."
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

echo ">>> [3/7] Launching PostgreSQL 16 & Redis containers..."
cd /home/ubuntu/DeepTrace
sudo docker compose up -d

echo "Waiting for PostgreSQL to be healthy..."
for i in {1..30}; do
    if sudo docker compose exec -T postgres pg_isready -U deeptrace -d deeptrace_db >/dev/null 2>&1; then
        echo "PostgreSQL is online and accepting connections!"
        break
    fi
    sleep 1
done

echo ">>> [4/7] Setting up Python virtual environment and Prisma..."
cd /home/ubuntu/DeepTrace
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run Prisma schema push & database seeding
echo "Running Prisma db push..."
prisma db push
echo "Running Prisma generate..."
prisma generate
echo "Seeding development database..."
python scripts/seed_dev.py

echo ">>> [5/7] Installing frontend dependencies & building Next.js production bundle..."
cd /home/ubuntu/DeepTrace/frontend
npm install
npm run build

echo ">>> [6/7] Managing PM2 processes..."
cd /home/ubuntu/DeepTrace
pm2 delete all || true
pm2 start ecosystem.config.cjs
pm2 startup systemd -u ubuntu --hp /home/ubuntu || true
if [ -f /etc/systemd/system/pm2-ubuntu.service ]; then
    sudo sed -i 's/Type=forking/Type=oneshot/g' /etc/systemd/system/pm2-ubuntu.service
    sudo sed -i 's/PIDFile=/#PIDFile=/g' /etc/systemd/system/pm2-ubuntu.service
    sudo sed -i '/^Type=oneshot/a RemainAfterExit=yes' /etc/systemd/system/pm2-ubuntu.service
    sudo systemctl daemon-reload
    sudo systemctl enable pm2-ubuntu
fi

echo ">>> [7/7] Configuring Caddy Reverse Proxy for HTTP & HTTPS..."
sudo cp /home/ubuntu/DeepTrace/Caddyfile /etc/caddy/Caddyfile
sudo systemctl enable caddy
sudo systemctl restart caddy

echo "=========================================================="
echo "   DEEPTRACE DEPLOYMENT COMPLETE & RUNNING IN BACKGROUND  "
echo "=========================================================="
pm2 status
sudo systemctl status caddy --no-pager | head -n 10
