#!/usr/bin/env python3
"""
Basic test script that doesn't rely on metar_v4 imports.
"""

import urllib.request
import xml.etree.ElementTree as ET

def test_api_response():
    """Test what we get from the API."""
    try:
        print("Testing API response...")
        
        # Make real API call to get KSRQ data
        api_url = "https://aviationweather.gov/api/data/metar?ids=ksrq&format=xml&hours=2.5"
        
        with urllib.request.urlopen(api_url, timeout=10) as response:
            xml_data = response.read()
        
        print(f"✓ Got {len(xml_data)} bytes from API")
        
        # Parse the XML
        root = ET.fromstring(xml_data)
        
        # Check for data element
        data_elem = root.find('data')
        if data_elem is None:
            print("✗ No data element found")
            return False
        
        num_results = data_elem.get('num_results', '0')
        print(f"✓ Found {num_results} results")
        
        # List all METAR elements
        metars = data_elem.findall('METAR')
        print(f"✓ Found {len(metars)} METAR elements")
        
        for i, metar in enumerate(metars):
            station_id = metar.find('station_id')
            if station_id is not None:
                print(f"  Station {i+1}: {station_id.text}")
                
                # Check for flight category
                flight_category = metar.find('flight_category')
                if flight_category is not None:
                    print(f"    Flight Category: {flight_category.text}")
                else:
                    print(f"    No flight category found")
                
                # Check for visibility
                vis_elem = metar.find('visibility_statute_mi')
                if vis_elem is not None:
                    print(f"    Visibility: {vis_elem.text} miles")
                else:
                    print(f"    No visibility_statute_mi found")
                
                # Check for sky conditions
                sky_conditions = metar.findall('sky_condition')
                print(f"    Sky conditions: {len(sky_conditions)}")
                for j, sky_cond in enumerate(sky_conditions):
                    sky_cover = sky_cond.get('sky_cover', 'unknown')
                    cloud_base = sky_cond.get('cloud_base_ft_agl', 'unknown')
                    print(f"      {j+1}: {sky_cover} at {cloud_base} ft")
            else:
                print(f"  METAR {i+1}: No station_id found")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_visibility_normalization():
    """Test visibility normalization without importing metar_v4."""
    try:
        print("\nTesting visibility normalization...")
        
        def normalize_visibility_value(visibility_str):
            """Simple visibility normalization function."""
            if not visibility_str:
                return 999.0
            
            visibility_str = str(visibility_str).strip()
            
            try:
                # Handle "10+" format
                if visibility_str.endswith('+'):
                    return float(visibility_str[:-1])
                
                # Handle "P6SM" format
                if visibility_str.startswith('P') and visibility_str.endswith('SM'):
                    return float(visibility_str[1:-2])
                
                # Handle fractional values
                if '/' in visibility_str:
                    parts = visibility_str.split()
                    if len(parts) == 1:
                        numerator, denominator = parts[0].split('/')
                        return float(numerator) / float(denominator)
                    elif len(parts) == 2:
                        whole_part = float(parts[0])
                        numerator, denominator = parts[1].split('/')
                        fractional_part = float(numerator) / float(denominator)
                        return whole_part + fractional_part
                
                # Handle regular numbers
                return float(visibility_str)
                
            except (ValueError, ZeroDivisionError):
                return 999.0
        
        # Test cases
        test_cases = [
            ("10", 10.0),
            ("10+", 10.0),
            ("P6SM", 6.0),
            ("1/2", 0.5),
            ("1 1/2", 1.5),
            ("", 999.0),
            ("invalid", 999.0)
        ]
        
        for input_val, expected in test_cases:
            result = normalize_visibility_value(input_val)
            if result == expected:
                print(f"  ✓ '{input_val}' -> {result}")
            else:
                print(f"  ✗ '{input_val}' -> {result} (expected {expected})")
                return False
        
        print("✓ Visibility normalization tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Visibility normalization test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Running basic compatibility tests...")
    print("=" * 50)
    
    tests = [
        test_api_response,
        test_visibility_normalization
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
        print("🎉 All basic tests passed!")
        return True
    else:
        print("❌ Some tests failed.")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
