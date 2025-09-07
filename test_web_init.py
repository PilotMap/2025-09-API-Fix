#!/usr/bin/env python3
"""
Test script to check if web app initialization works
"""

import sys
import os

print("Testing web app initialization...")

try:
    print("1. Testing imports...")
    import config
    print("   ✓ config imported")
    
    from leds import LedStrip, Color
    print("   ✓ leds imported")
    
    print("2. Testing LED strip initialization...")
    strip = LedStrip(config.LED_COUNT)
    print(f"   ✓ LED strip initialized with {strip.number} LEDs")
    
    print("3. Testing Flask imports...")
    from flask import Flask
    print("   ✓ Flask imported")
    
    print("4. Testing Flask app creation...")
    app = Flask(__name__)
    print("   ✓ Flask app created")
    
    print("5. Testing other web dependencies...")
    import folium
    print("   ✓ folium imported")
    
    print("\n✅ All web app components initialized successfully!")
    print("The web interface should work if services are running properly.")
    
except Exception as e:
    print(f"\n❌ Error during initialization: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
