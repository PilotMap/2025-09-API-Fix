#!/usr/bin/env python3
"""
Simple LED test script to verify LED strip is working
"""

import time
import sys
import os

# Add current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from leds import LedStrip, Color
    print("✅ Successfully imported LED modules")
except ImportError as e:
    print(f"❌ Failed to import LED modules: {e}")
    sys.exit(1)

def test_led_strip():
    """Test basic LED strip functionality"""
    print("🔧 Initializing LED strip...")
    
    try:
        # Initialize LED strip with 5 LEDs for testing
        strip = LedStrip(5)
        print(f"✅ LED strip initialized with {strip.number} LEDs")
    except Exception as e:
        print(f"❌ Failed to initialize LED strip: {e}")
        return False
    
    print("🎨 Testing colors...")
    
    # Test colors
    colors = [
        (255, 0, 0, "Red"),
        (0, 255, 0, "Green"), 
        (0, 0, 255, "Blue"),
        (255, 255, 0, "Yellow"),
        (255, 0, 255, "Magenta")
    ]
    
    for i, (r, g, b, name) in enumerate(colors):
        print(f"  Setting LED {i} to {name} ({r}, {g}, {b})")
        strip.set_pixel_color(i, Color(r, g, b))
    
    print("💡 Showing pixels...")
    try:
        strip.show_pixels()
        print("✅ Pixels displayed successfully")
    except Exception as e:
        print(f"❌ Failed to show pixels: {e}")
        return False
    
    print("⏱️  Waiting 3 seconds...")
    time.sleep(3)
    
    print("🔴 Testing all LEDs red...")
    for i in range(strip.number):
        strip.set_pixel_color(i, Color(255, 0, 0))
    strip.show_pixels()
    time.sleep(2)
    
    print("🟢 Testing all LEDs green...")
    for i in range(strip.number):
        strip.set_pixel_color(i, Color(0, 255, 0))
    strip.show_pixels()
    time.sleep(2)
    
    print("🔵 Testing all LEDs blue...")
    for i in range(strip.number):
        strip.set_pixel_color(i, Color(0, 0, 255))
    strip.show_pixels()
    time.sleep(2)
    
    print("⚫ Turning off all LEDs...")
    for i in range(strip.number):
        strip.set_pixel_color(i, Color(0, 0, 0))
    strip.show_pixels()
    
    print("✅ LED test completed successfully!")
    return True

if __name__ == "__main__":
    print("🚀 Starting LED strip test...")
    success = test_led_strip()
    if success:
        print("🎉 LED strip test PASSED!")
    else:
        print("💥 LED strip test FAILED!")
        sys.exit(1)
