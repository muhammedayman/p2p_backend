#!/bin/bash
set -e

echo "--- Installing Coturn TURN Server ---"
sudo apt-get update
sudo apt-get install -y coturn

echo "--- Configuring /etc/turnserver.conf ---"
# Backup existing config
sudo mv /etc/turnserver.conf /etc/turnserver.conf.bak 2>/dev/null || true

# Write new config
sudo tee /etc/turnserver.conf <<EOF
listening-port=3478
tls-listening-port=5349
fingerprint
lt-cred-mech
user=myuser:SecureP2PStrongPass2025!^**
realm=p2papp
total-quota=100
stale-nonce=600
log-file=/var/log/turn.log
simple-log
external-ip=46.62.195.191
# Restrict ports to make Firewalling easier
min-port=60000
max-port=60200

echo "--- Enabling Service ---"
sudo sed -i 's/#TURNSERVER_ENABLED=1/TURNSERVER_ENABLED=1/' /etc/default/coturn

echo "--- Restarting Coturn ---"
sudo systemctl restart coturn
sudo systemctl enable coturn

echo "✅ Coturn Installed & Running!"
echo "Credentials: myuser / mypassword"
