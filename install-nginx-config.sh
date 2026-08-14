#!/bin/bash
# Install Unified Nginx Configuration for Mercai
# This script will install nginx-all-projects.conf and reload nginx

set -e

echo "=== Installing Unified Nginx Configuration ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    echo "Usage: sudo bash install-nginx-config.sh"
    exit 1
fi

# Backup current config
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo "✓ Backing up current default config..."
    cp /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.backup 2>/dev/null || true
fi

# Copy new config
echo "✓ Copying nginx-all-projects.conf..."
cp /home/tuanph/TuanPH/all_projects/nginx-all-projects.conf /etc/nginx/sites-available/

# Enable new config
echo "✓ Enabling new configuration..."
ln -sf /etc/nginx/sites-available/nginx-all-projects.conf /etc/nginx/sites-enabled/

# Remove default
echo "✓ Removing default configuration..."
rm -f /etc/nginx/sites-enabled/default

# Test nginx config
echo "✓ Testing nginx configuration..."
nginx -t

# Reload nginx
echo "✓ Reloading nginx..."
systemctl reload nginx

echo ""
echo "=== Installation Complete! ==="
echo ""
echo "Your frontend can now access Mercai API at:"
echo "  - http://localhost/mercai/api/v1/auth/login"
echo "  - http://localhost/mercai/api/v1/products"
echo "  - http://localhost/mercai/api/v1/orders"
echo "  - http://localhost/mercai/api/v1/chat"
echo ""
echo "Test with:"
echo "  curl http://localhost/mercai/health"
echo "  curl http://localhost/mercai/api/v1/products"
