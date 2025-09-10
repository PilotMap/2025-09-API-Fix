#!/usr/bin/env python3
"""
Simple test script to verify the 2025 API compatibility fixes.
"""

import sys
import os
import xml.etree.ElementTree as ET

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_normalize_visibility():
    """Test the normalize_visibility_value function."""
    try:
        # Import the function from metar-v4.py
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Try to import the function
        try:
            from metar_v4 import normalize_visibility_value
        except ImportError:
            # If direct import fails, try importing the module first
            import metar_v4
            normalize_visibility_value = metar_v4.normalize_visibility_value
        
        print("Testing visibility normalization...")
        
        # Test regular numbers
        assert normalize_visibility_value("3.0") == 3.0
        assert normalize_visibility_value("10") == 10.0
        
        # Test "10+" format
        assert normalize_visibility_value("10+") == 10.0
        assert normalize_visibility_value("6+") == 6.0
        
        # Test "P6SM" format
        assert normalize_visibility_value("P6SM") == 6.0
        assert normalize_visibility_value("P10SM") == 10.0
        
        # Test fractional values
        assert normalize_visibility_value("1/2") == 0.5
        assert normalize_visibility_value("3/4") == 0.75
        
        # Test mixed numbers
        assert normalize_visibility_value("1 1/2") == 1.5
        assert normalize_visibility_value("2 3/4") == 2.75
        
        # Test edge cases
        assert normalize_visibility_value("") == 999.0
        assert normalize_visibility_value(None) == 999.0
        assert normalize_visibility_value("invalid") == 999.0
        
        print("✓ Visibility normalization tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Visibility normalization test failed: {e}")
        return False

def test_flight_category_calculator():
    """Test the FlightCategoryCalculator class."""
    try:
        from flight_category_calculator import FlightCategoryCalculator
        
        print("Testing FlightCategoryCalculator...")
        
        calculator = FlightCategoryCalculator()
        
        # Test visibility normalization
        assert calculator.normalize_visibility_value("10+") == 10.0
        assert calculator.normalize_visibility_value("P6SM") == 6.0
        assert calculator.normalize_visibility_value("1/2") == 0.5
        
        # Test flight category calculation
        assert calculator._determine_flight_category(25000, 10.0) == "VFR"
        assert calculator._determine_flight_category(1000, 3.0) == "MVFR"
        assert calculator._determine_flight_category(800, 2.0) == "IFR"
        assert calculator._determine_flight_category(200, 0.5) == "LIFR"
        
        print("✓ FlightCategoryCalculator tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ FlightCategoryCalculator test failed: {e}")
        return False

def test_xml_parsing():
    """Test XML parsing with real API call."""
    try:
        print("Testing XML parsing with real API call...")
        
        import urllib.request
        import urllib.parse
        
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
        
        # Test KSRQ parsing
        ksrq_metar = None
        for metar in root.findall('METAR'):
            if metar.find('station_id').text == 'KSRQ':
                ksrq_metar = metar
                break
        
        if ksrq_metar is not None:
            print("✓ Found KSRQ METAR data")
            
            # Test flat sky_condition parsing
            sky_conditions = ksrq_metar.findall('sky_condition')
            print(f"Found {len(sky_conditions)} sky_condition elements")
            
            # Test flat visibility parsing
            vis_elem = ksrq_metar.find('visibility_statute_mi')
            if vis_elem is not None:
                print(f"Visibility: {vis_elem.text} miles")
            else:
                print("No visibility_statute_mi element found")
            
            # Test API-provided flight category
            flight_category_elem = ksrq_metar.find('flight_category')
            if flight_category_elem is not None:
                print(f"API Flight Category: {flight_category_elem.text}")
            else:
                print("No flight_category element found")
            
            # Test the enhanced parsing logic
            from flight_category_calculator import FlightCategoryCalculator
            calculator = FlightCategoryCalculator()
            
            # Test parsing cloud layers
            cloud_layers = calculator.parse_cloud_layers(ksrq_metar)
            print(f"Parsed {len(cloud_layers)} cloud layers")
            
            # Test parsing visibility
            if vis_elem is not None:
                visibility = calculator.parse_visibility(vis_elem)
                print(f"Parsed visibility: {visibility} miles")
            
            # Test full calculation
            flight_category = calculator.calculate_from_metar_element(ksrq_metar)
            print(f"Calculated flight category: {flight_category}")
            
            print("✓ 2025 API XML parsing tests passed!")
        else:
            print("✗ KSRQ METAR not found in API response")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ XML parsing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Running simple compatibility tests...")
    print("=" * 50)
    
    tests = [
        test_normalize_visibility,
        test_flight_category_calculator,
        test_xml_parsing
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The 2025 API compatibility fixes are working.")
        return True
    else:
        print("❌ Some tests failed. Check the errors above.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
