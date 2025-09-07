# LiveSectional 2025 API Fix

Fixes for LiveSectional LED aviation weather display to work with updated 2025 AviationWeather.gov API.

## Problem Solved
- AviationWeather.gov API changed XML structure in 2025
- LEDs showing "INVALID" instead of flight categories
- Web interface crashes due to missing dependencies

## Key Fixes
1. **2025 API Compatibility** - Updated XML parsing in `metar-v4.py`
2. **LED Color Format** - Fixed `rpi_ws281x` color conversion in `leds.py`
3. **Web Interface** - Added error handling and dependency installation
4. **Hardware Compatibility** - Fixed LED strip initialization

## Installation
```bash
# Install LED library
sudo pip3 install rpi_ws281x

# Install web dependencies
chmod +x install_web_deps.sh
sudo ./install_web_deps.sh
```

## Usage
```bash
# Run main display
sudo python3 metar-v4.py

# Test LEDs
sudo python3 test_led_simple.py

# Web interface: http://[PI_IP]:5000
```

## Status: ✅ FULLY FUNCTIONAL