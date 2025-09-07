#!/usr/bin/env python3
"""
Debug script to see what's actually in the API response.
"""

import urllib.request
import xml.etree.ElementTree as ET

def debug_api_response():
    """Debug the API response to see what data we're getting."""
    try:
        print("Fetching API data...")
        
        # Make real API call to get KSRQ data
        api_url = "https://aviationweather.gov/api/data/metar?ids=ksrq&format=xml&hours=2.5"
        
        with urllib.request.urlopen(api_url, timeout=10) as response:
            xml_data = response.read()
        
        print(f"Response length: {len(xml_data)} bytes")
        print("Raw XML response:")
        print("-" * 50)
        print(xml_data.decode('utf-8')[:1000])  # First 1000 characters
        print("-" * 50)
        
        # Parse the XML
        root = ET.fromstring(xml_data)
        
        print(f"Root tag: {root.tag}")
        print(f"Root attributes: {root.attrib}")
        
        # Check for data element
        data_elem = root.find('data')
        if data_elem is not None:
            num_results = data_elem.get('num_results', 'unknown')
            print(f"Number of results: {num_results}")
            
            # List all METAR elements
            metars = data_elem.findall('METAR')
            print(f"Found {len(metars)} METAR elements")
            
            for i, metar in enumerate(metars):
                station_id = metar.find('station_id')
                if station_id is not None:
                    print(f"  METAR {i+1}: {station_id.text}")
                else:
                    print(f"  METAR {i+1}: No station_id found")
        else:
            print("No data element found")
            
        # Check for errors
        errors_elem = root.find('errors')
        if errors_elem is not None and errors_elem.text:
            print(f"Errors: {errors_elem.text}")
        
        # Check for warnings
        warnings_elem = root.find('warnings')
        if warnings_elem is not None and warnings_elem.text:
            print(f"Warnings: {warnings_elem.text}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_api_response()
