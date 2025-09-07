#!/bin/bash
echo "Installing web interface dependencies..."

# Try installing in the virtual environment first
echo "Attempting to install in virtual environment..."
sudo /home/pi/livesectional/bin/pip install flask folium requests logzero arrow wget

# If that fails, install system-wide
if [ $? -ne 0 ]; then
    echo "Virtual environment install failed, trying system-wide..."
    sudo pip3 install flask folium requests logzero arrow wget
fi

echo "Installation complete!"
echo "Restarting web services..."

# Restart the app service
sudo systemctl restart app
sudo systemctl restart nginx

echo "Services restarted. Check status with:"
echo "sudo systemctl status app"
echo "sudo systemctl status nginx"
