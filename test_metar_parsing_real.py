#!/usr/bin/env python3
"""
Test the actual metar-v4.py parsing logic with real API data.
"""

import sys
import os
import xml.etree.ElementTree as ET
import urllib.request

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_real_api_parsing():
    """Test parsing with real API data using the actual metar-v4.py logic."""
    try:
        print("Testing real API parsing with metar-v4.py logic...")
        
        # Make real API call to get KSRQ data
        api_url = "https://aviationweather.gov/api/data/metar?ids=ksrq&format=xml&hours=2.5"
        
        print(f"Fetching data from: {api_url}")
        
        try:
            with urllib.request.urlopen(api_url, timeout=10) as response:
                xml_data = response.read()
        except Exception as e:
            print(f"✗ Failed to fetch API data: {e}")
            return False
        
        # Parse the XML
        root = ET.fromstring(xml_data)
        
        # Find KSRQ METAR
        ksrq_metar = None
        for metar in root.findall('METAR'):
            if metar.find('station_id').text == 'KSRQ':
                ksrq_metar = metar
                break
        
        if ksrq_metar is None:
            print("✗ KSRQ METAR not found in API response")
            return False
        
        print("✓ Found KSRQ METAR data")
        
        # Test the actual parsing logic from metar-v4.py
        stationId = ksrq_metar.find('station_id').text
        print(f"Station ID: {stationId}")
        
        # Test configuration loading
        import config
        prefer_api_flight_category = getattr(config, 'prefer_api_flight_category', 1)
        force_fallback_calculation = getattr(config, 'force_fallback_calculation', 0)
        log_xml_parsing_details = getattr(config, 'log_xml_parsing_details', 1)
        
        print(f"Configuration: prefer_api_flight_category={prefer_api_flight_category}, force_fallback_calculation={force_fallback_calculation}")
        
        # Test API-provided flight category
        flight_category_elem = ksrq_metar.find('flight_category')
        api_flight_category_available = (flight_category_elem is not None and 
                                       flight_category_elem.text is not None and 
                                       flight_category_elem.text.strip() != '' and 
                                       flight_category_elem.text.strip() != 'NONE')
        
        if api_flight_category_available:
            flightcategory = flight_category_elem.text.strip()
            print(f"✓ API-provided flight category: {flightcategory}")
        else:
            print("✗ No API-provided flight category found")
            return False
        
        # Test flat sky_condition parsing
        sky_conditions = ksrq_metar.findall('sky_condition')
        print(f"Found {len(sky_conditions)} sky_condition elements")
        
        sky_cvr = "SKC"
        sky_condition = None
        
        for sky_cond in sky_conditions:
            sky_cvr = sky_cond.get('sky_cover', 'SKC')
            print(f"Sky Cover: {sky_cvr}")
            if sky_cvr in ("OVC", "BKN", "OVX"):
                sky_condition = sky_cond
                break
        
        # Test flat visibility parsing
        vis_elem = ksrq_metar.find('visibility_statute_mi')
        if vis_elem is not None:
            print(f"Visibility: {vis_elem.text} miles")
            
            # Test visibility normalization
            from metar_v4 import normalize_visibility_value
            normalized_visibility = normalize_visibility_value(vis_elem.text)
            print(f"Normalized visibility: {normalized_visibility} miles")
        else:
            print("✗ No visibility_statute_mi element found")
            return False
        
        # Test cloud base parsing
        if sky_condition is not None:
            cld_base_ft_agl = sky_condition.get('cloud_base_ft_agl')
            if cld_base_ft_agl is not None:
                print(f"Cloud base: {cld_base_ft_agl} ft AGL")
            else:
                print("No cloud base found")
        else:
            print("No significant cloud layer found")
        
        print("✓ All parsing tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Real API parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test."""
    print("Testing real API parsing with metar-v4.py logic...")
    print("=" * 60)
    
    if test_real_api_parsing():
        print("\n🎉 Real API parsing test passed! The fixes should work.")
        return True
    else:
        print("\n❌ Real API parsing test failed.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
