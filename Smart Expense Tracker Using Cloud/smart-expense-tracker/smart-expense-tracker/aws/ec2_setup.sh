#!/bin/bash
# Run on a fresh Ubuntu / Amazon Linux EC2 instance (or a VirtualBox Ubuntu VM).
# Usage: bash aws/ec2_setup.sh
set -e

if command -v apt-get >/dev/null; then
  sudo apt-get update -y && sudo apt-get install -y docker.io docker-compose-v2 git
else
  sudo yum install -y docker git && sudo systemctl enable --now docker
  sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
       -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose
fi
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER" || true

cd "$(dirname "$0")/.."
sudo docker compose up -d --build || sudo docker-compose up -d --build
echo "App running on port 5000. Open http://<public-ip>:5000"
