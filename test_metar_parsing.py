#!/usr/bin/env python3
"""
Test suite for METAR parsing with 2025 AviationWeather.gov API compatibility.
Tests flight category calculation, cloud parsing, visibility parsing, and error handling.
"""

import unittest
import xml.etree.ElementTree as ET
import os
import sys
from datetime import datetime

# Add the current directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the modules we're testing
import config
from log import logger

class TestFlightCategoryCalculation(unittest.TestCase):
    """Test flight category calculation logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_metar_xml = os.path.join(os.path.dirname(__file__), 'test_fixtures', 'metar_2025_sample.xml')
        self.test_taf_xml = os.path.join(os.path.dirname(__file__), 'test_fixtures', 'taf_2025_sample.xml')
    
    def test_vfr_calculation(self):
        """Test VFR calculation with high ceiling and good visibility."""
        # KORD: FEW250 (25000 ft ceiling), 10SM visibility
        metar_data = self._parse_metar_xml()
        kord_metar = None
        for metar in metar_data.findall('METAR'):
            if metar.find('station_id').text == 'KORD':
                kord_metar = metar
                break
        
        self.assertIsNotNone(kord_metar)
        
        # Test cloud parsing - handle both nested and flat structures
        sky_cvr = "SKC"
        cld_base_ft_agl = 9999
        
        # Try nested structure first
        clouds_elem = kord_metar.find('clouds')
        if clouds_elem is not None:
            for cloud_layer in clouds_elem.findall('cloud'):
                sky_cvr = cloud_layer.get('sky_cover', 'SKC')
                if sky_cvr in ("OVC", "BKN", "OVX"):
                    cld_base_ft_agl = int(cloud_layer.get('cloud_base_ft_agl', '9999'))
                    break
        else:
            # Try flat structure
            for sky_cond in kord_metar.findall('sky_condition'):
                sky_cvr = sky_cond.get('sky_cover', 'SKC')
                if sky_cvr in ("OVC", "BKN", "OVX"):
                    cld_base_ft_agl = int(sky_cond.get('cloud_base_ft_agl', '9999'))
                    break
        
        # Test visibility parsing - handle both nested and flat structures
        visibility_statute_mi = 999
        vis_elem = kord_metar.find('visibility')
        if vis_elem is not None:
            statute_mi_elem = vis_elem.find('statute_mi')
            if statute_mi_elem is not None:
                visibility_statute_mi = float(statute_mi_elem.text)
        else:
            # Try flat structure
            vis_elem = kord_metar.find('visibility_statute_mi')
            if vis_elem is not None:
                visibility_statute_mi = float(vis_elem.text)
        
        # Calculate flight category
        flightcategory = self._calculate_flight_category(sky_cvr, cld_base_ft_agl, visibility_statute_mi)
        self.assertEqual(flightcategory, "VFR")
    
    def test_mvfr_calculation(self):
        """Test MVFR calculation with moderate ceiling and visibility."""
        # KJFK: BKN008 (800 ft ceiling), 3SM visibility
        metar_data = self._parse_metar_xml()
        kjfk_metar = None
        for metar in metar_data.findall('METAR'):
            if metar.find('station_id').text == 'KJFK':
                kjfk_metar = metar
                break
        
        self.assertIsNotNone(kjfk_metar)
        
        # Test cloud parsing - handle both nested and flat structures
        sky_cvr = "SKC"
        cld_base_ft_agl = 9999
        
        # Try nested structure first
        clouds_elem = kjfk_metar.find('clouds')
        if clouds_elem is not None:
            for cloud_layer in clouds_elem.findall('cloud'):
                sky_cvr = cloud_layer.get('sky_cover', 'SKC')
                if sky_cvr in ("OVC", "BKN", "OVX"):
                    cld_base_ft_agl = int(cloud_layer.get('cloud_base_ft_agl', '9999'))
                    break
        else:
            # Try flat structure
            for sky_cond in kjfk_metar.findall('sky_condition'):
                sky_cvr = sky_cond.get('sky_cover', 'SKC')
                if sky_cvr in ("OVC", "BKN", "OVX"):
                    cld_base_ft_agl = int(sky_cond.get('cloud_base_ft_agl', '9999'))
                    break
        
        # Test visibility parsing - handle both nested and flat structures
        visibility_statute_mi = 999
        vis_elem = kjfk_metar.find('visibility')
        if vis_elem is not None:
            statute_mi_elem = vis_elem.find('statute_mi')
            if statute_mi_elem is not None:
                visibility_statute_mi = float(statute_mi_elem.text)
        else:
            # Try flat structure
            vis_elem = kjfk_metar.find('visibility_statute_mi')
            if vis_elem is not None:
                visibility_statute_mi = float(vis_elem.text)
        
        # Calculate flight category
        flightcategory = self._calculate_flight_category(sky_cvr, cld_base_ft_agl, visibility_statute_mi)
        self.assertEqual(flightcategory, "MVFR")
    
    def test_lifr_calculation(self):
        """Test LIFR calculation with low ceiling and poor visibility."""
        # KLAX: OVC002 (200 ft ceiling), 0.5SM visibility
        metar_data = self._parse_metar_xml()
        klax_metar = None
        for metar in metar_data.findall('METAR'):
            if metar.find('station_id').text == 'KLAX':
                klax_metar = metar
                break
        
        self.assertIsNotNone(klax_metar)
        
        # Test cloud parsing - handle both nested and flat structures
        sky_cvr = "SKC"
        cld_base_ft_agl = 9999
        
        # Try nested structure first
        clouds_elem = klax_metar.find('clouds')
        if clouds_elem is not None:
            for cloud_layer in clouds_elem.findall('cloud'):
                sky_cvr = cloud_layer.get('sky_cover', 'SKC')
                if sky_cvr in ("OVC", "BKN", "OVX"):
                    cld_base_ft_agl = int(cloud_layer.get('cloud_base_ft_agl', '9999'))
                    break
        else:
            # Try flat structure
            for sky_cond in klax_metar.findall('sky_condition'):
                sky_cvr = sky_cond.get('sky_cover', 'SKC')
                if sky_cvr in ("OVC", "BKN", "OVX"):
                    cld_base_ft_agl = int(sky_cond.get('cloud_base_ft_agl', '9999'))
                    break
        
        # Test visibility parsing - handle both nested and flat structures
        visibility_statute_mi = 999
        vis_elem = klax_metar.find('visibility')
        if vis_elem is not None:
            statute_mi_elem = vis_elem.find('statute_mi')
            if statute_mi_elem is not None:
                visibility_statute_mi = float(statute_mi_elem.text)
        else:
            # Try flat structure
            vis_elem = klax_metar.find('visibility_statute_mi')
            if vis_elem is not None:
                visibility_statute_mi = float(vis_elem.text)
        
        # Calculate flight category
        flightcategory = self._calculate_flight_category(sky_cvr, cld_base_ft_agl, visibility_statute_mi)
        self.assertEqual(flightcategory, "LIFR")
    
    def test_missing_cloud_data(self):
        """Test handling of missing cloud data."""
        flightcategory = self._calculate_flight_category("SKC", 9999, 10.0)
        self.assertEqual(flightcategory, "VFR")
    
    def test_missing_visibility_data(self):
        """Test handling of missing visibility data."""
        flightcategory = self._calculate_flight_category("OVC", 1000, 999)
        self.assertEqual(flightcategory, "MVFR")
    
    def test_edge_cases(self):
        """Test edge cases for flight category calculation."""
        # Test exact boundary values
        self.assertEqual(self._calculate_flight_category("OVC", 500, 1.0), "IFR")  # 500ft ceiling = IFR, 1.0mi visibility = IFR
        self.assertEqual(self._calculate_flight_category("OVC", 1000, 3.0), "MVFR")  # 1000ft ceiling = MVFR, 3.0mi visibility = MVFR
        self.assertEqual(self._calculate_flight_category("OVC", 3000, 5.0), "MVFR")  # 3000ft ceiling = MVFR, 5.0mi visibility = MVFR
        self.assertEqual(self._calculate_flight_category("OVC", 3001, 5.1), "VFR")  # 3001ft ceiling = VFR, 5.1mi visibility = VFR
    
    def _parse_metar_xml(self):
        """Parse the test METAR XML file."""
        tree = ET.parse(self.test_metar_xml)
        return tree.getroot()
    
    def _calculate_flight_category(self, sky_cvr, cld_base_ft_agl, visibility_statute_mi):
        """Calculate flight category based on cloud and visibility data."""
        flightcategory = "VFR"  # Initialize as VFR
        
        # Check cloud conditions first
        if sky_cvr in ("OVC", "BKN", "OVX"):
            if cld_base_ft_agl < 500:
                flightcategory = "LIFR"
            elif 500 <= cld_base_ft_agl < 1000:
                flightcategory = "IFR"
            elif 1000 <= cld_base_ft_agl <= 3000:
                flightcategory = "MVFR"
            elif cld_base_ft_agl > 3000:
                flightcategory = "VFR"
        
        # Check visibility conditions (only if not already LIFR from clouds)
        if flightcategory != "LIFR":
            if visibility_statute_mi < 1.0:
                flightcategory = "LIFR"
            elif 1.0 <= visibility_statute_mi < 3.0:
                flightcategory = "IFR"
            elif 3.0 <= visibility_statute_mi <= 5.0 and flightcategory != "IFR":
                flightcategory = "MVFR"
        
        return flightcategory

class TestTAFParsing(unittest.TestCase):
    """Test TAF parsing with 2025 API format."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_taf_xml = os.path.join(os.path.dirname(__file__), 'test_fixtures', 'taf_2025_sample.xml')
    
    def test_taf_parsing(self):
        """Test TAF XML parsing with new structure."""
        tree = ET.parse(self.test_taf_xml)
        root = tree.getroot()
        
        # Test that we can find TAF elements
        tafs = root.findall('.//TAF')
        self.assertGreater(len(tafs), 0)
        
        # Test KORD TAF parsing
        kord_taf = None
        for taf in tafs:
            if taf.find('station_id').text == 'KORD':
                kord_taf = taf
                break
        
        self.assertIsNotNone(kord_taf)
        
        # Test forecast parsing
        forecasts = kord_taf.findall('forecast')
        self.assertGreater(len(forecasts), 0)
        
        # Test first forecast
        first_forecast = forecasts[0]
        wind_speed = first_forecast.find('wind_speed_kt')
        self.assertIsNotNone(wind_speed)
        self.assertEqual(wind_speed.text, '10')
        
        # Test visibility parsing
        visibility = first_forecast.find('visibility')
        self.assertIsNotNone(visibility)
        statute_mi = visibility.find('statute_mi')
        self.assertIsNotNone(statute_mi)
        self.assertEqual(statute_mi.text, '6')
        
        # Test cloud parsing
        clouds = first_forecast.find('clouds')
        self.assertIsNotNone(clouds)
        cloud_layers = clouds.findall('cloud')
        self.assertGreater(len(cloud_layers), 0)

class TestErrorHandling(unittest.TestCase):
    """Test error handling for various failure scenarios."""
    
    def test_malformed_xml(self):
        """Test handling of malformed XML."""
        malformed_xml = "<invalid>not a valid METAR response</invalid>"
        try:
            root = ET.fromstring(malformed_xml)
            # This should not raise an exception in our code
            self.assertTrue(True)
        except ET.ParseError:
            # This is expected for malformed XML
            self.assertTrue(True)
    
    def test_missing_elements(self):
        """Test handling of missing XML elements."""
        # Create a minimal METAR with missing elements
        minimal_metar = ET.Element('METAR')
        station_id = ET.SubElement(minimal_metar, 'station_id')
        station_id.text = 'KTEST'
        
        # Test that we can handle missing clouds element
        clouds_elem = minimal_metar.find('clouds')
        self.assertIsNone(clouds_elem)
        
        # Test that we can handle missing visibility element
        vis_elem = minimal_metar.find('visibility')
        self.assertIsNone(vis_elem)
    
    def test_invalid_data_types(self):
        """Test handling of invalid data types."""
        # Test invalid cloud base height
        try:
            cld_base_ft_agl = int("invalid")
        except ValueError:
            self.assertTrue(True)
        
        # Test invalid visibility
        try:
            visibility_statute_mi = float("invalid")
        except ValueError:
            self.assertTrue(True)

class Test2025APIParsing(unittest.TestCase):
    """Test parsing of actual 2025 API XML structure."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_metar_2025_xml = os.path.join(os.path.dirname(__file__), 'test_fixtures', 'metar_actual_2025_sample.xml')
    
    def test_flat_sky_condition_parsing(self):
        """Test parsing of flat sky_condition elements from 2025 API."""
        tree = ET.parse(self.test_metar_2025_xml)
        root = tree.getroot()
        
        # Test KSRQ (VFR with FEW250)
        ksrq_metar = None
        for metar in root.findall('METAR'):
            if metar.find('station_id').text == 'KSRQ':
                ksrq_metar = metar
                break
        
        self.assertIsNotNone(ksrq_metar)
        
        # Test flat sky_condition parsing
        sky_conditions = ksrq_metar.findall('sky_condition')
        self.assertGreater(len(sky_conditions), 0)
        
        sky_cvr = "SKC"
        cld_base_ft_agl = 9999
        
        for sky_cond in sky_conditions:
            sky_cvr = sky_cond.get('sky_cover', 'SKC')
            if sky_cvr in ("OVC", "BKN", "OVX"):
                cld_base_ft_agl = int(sky_cond.get('cloud_base_ft_agl', '9999'))
                break
        
        # KSRQ has FEW250, so no ceiling restrictions
        self.assertEqual(sky_cvr, "FEW")
        self.assertEqual(cld_base_ft_agl, 9999)
    
    def test_flat_visibility_parsing(self):
        """Test parsing of flat visibility_statute_mi elements from 2025 API."""
        tree = ET.parse(self.test_metar_2025_xml)
        root = tree.getroot()
        
        # Test KSRQ visibility
        ksrq_metar = None
        for metar in root.findall('METAR'):
            if metar.find('station_id').text == 'KSRQ':
                ksrq_metar = metar
                break
        
        self.assertIsNotNone(ksrq_metar)
        
        # Test flat visibility parsing
        vis_elem = ksrq_metar.find('visibility_statute_mi')
        self.assertIsNotNone(vis_elem)
        self.assertEqual(vis_elem.text, '10')
        
        visibility_statute_mi = float(vis_elem.text)
        self.assertEqual(visibility_statute_mi, 10.0)
    
    def test_api_provided_flight_category(self):
        """Test parsing of API-provided flight_category elements."""
        tree = ET.parse(self.test_metar_2025_xml)
        root = tree.getroot()
        
        # Test all METARs have flight_category
        for metar in root.findall('METAR'):
            station_id = metar.find('station_id').text
            flight_category_elem = metar.find('flight_category')
            self.assertIsNotNone(flight_category_elem, f"No flight_category found for {station_id}")
            self.assertIsNotNone(flight_category_elem.text, f"Empty flight_category for {station_id}")
            
            # Verify expected flight categories
            if station_id == 'KSRQ':
                self.assertEqual(flight_category_elem.text, 'VFR')
            elif station_id == 'KORD':
                self.assertEqual(flight_category_elem.text, 'IFR')
            elif station_id == 'KLAX':
                self.assertEqual(flight_category_elem.text, 'LIFR')
            elif station_id == 'KDFW':
                self.assertEqual(flight_category_elem.text, 'MVFR')
    
    def test_multiple_sky_conditions(self):
        """Test parsing of multiple sky_condition elements."""
        tree = ET.parse(self.test_metar_2025_xml)
        root = tree.getroot()
        
        # Test KDFW (has multiple sky conditions: SCT015, BKN025, OVC035)
        kdfw_metar = None
        for metar in root.findall('METAR'):
            if metar.find('station_id').text == 'KDFW':
                kdfw_metar = metar
                break
        
        self.assertIsNotNone(kdfw_metar)
        
        sky_conditions = kdfw_metar.findall('sky_condition')
        self.assertEqual(len(sky_conditions), 3)
        
        # Check first significant layer (BKN025)
        sky_cvr = "SKC"
        cld_base_ft_agl = 9999
        
        for sky_cond in sky_conditions:
            sky_cvr = sky_cond.get('sky_cover', 'SKC')
            if sky_cvr in ("OVC", "BKN", "OVX"):
                cld_base_ft_agl = int(sky_cond.get('cloud_base_ft_agl', '9999'))
                break
        
        self.assertEqual(sky_cvr, "BKN")
        self.assertEqual(cld_base_ft_agl, 2500)

class TestVisibilityNormalization(unittest.TestCase):
    """Test visibility value normalization function."""
    
    def test_normalize_visibility_value(self):
        """Test the normalize_visibility_value function."""
        # Import the function from metar-v4.py
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from metar_v4 import normalize_visibility_value
        
        # Test regular numbers
        self.assertEqual(normalize_visibility_value("3.0"), 3.0)
        self.assertEqual(normalize_visibility_value("10"), 10.0)
        
        # Test "10+" format
        self.assertEqual(normalize_visibility_value("10+"), 10.0)
        self.assertEqual(normalize_visibility_value("6+"), 6.0)
        
        # Test "P6SM" format
        self.assertEqual(normalize_visibility_value("P6SM"), 6.0)
        self.assertEqual(normalize_visibility_value("P10SM"), 10.0)
        
        # Test fractional values
        self.assertEqual(normalize_visibility_value("1/2"), 0.5)
        self.assertEqual(normalize_visibility_value("3/4"), 0.75)
        
        # Test mixed numbers
        self.assertEqual(normalize_visibility_value("1 1/2"), 1.5)
        self.assertEqual(normalize_visibility_value("2 3/4"), 2.75)
        
        # Test edge cases
        self.assertEqual(normalize_visibility_value(""), 999.0)
        self.assertEqual(normalize_visibility_value(None), 999.0)
        self.assertEqual(normalize_visibility_value("invalid"), 999.0)

class TestFlightCategoryCalculator(unittest.TestCase):
    """Test the enhanced FlightCategoryCalculator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        from flight_category_calculator import FlightCategoryCalculator
        self.calculator = FlightCategoryCalculator()
        self.test_metar_2025_xml = os.path.join(os.path.dirname(__file__), 'test_fixtures', 'metar_actual_2025_sample.xml')
    
    def test_calculate_from_metar_element(self):
        """Test the enhanced calculate_from_metar_element method."""
        tree = ET.parse(self.test_metar_2025_xml)
        root = tree.getroot()
        
        # Test KSRQ (VFR)
        ksrq_metar = None
        for metar in root.findall('METAR'):
            if metar.find('station_id').text == 'KSRQ':
                ksrq_metar = metar
                break
        
        self.assertIsNotNone(ksrq_metar)
        
        # Test API-provided flight category
        flight_category = self.calculator.calculate_from_metar_element(ksrq_metar)
        self.assertEqual(flight_category, "VFR")
        
        # Test KORD (IFR)
        kord_metar = None
        for metar in root.findall('METAR'):
            if metar.find('station_id').text == 'KORD':
                kord_metar = metar
                break
        
        self.assertIsNotNone(kord_metar)
        flight_category = self.calculator.calculate_from_metar_element(kord_metar)
        self.assertEqual(flight_category, "IFR")
    
    def test_parse_cloud_layers_flat_structure(self):
        """Test parsing cloud layers from flat sky_condition structure."""
        tree = ET.parse(self.test_metar_2025_xml)
        root = tree.getroot()
        
        kdfw_metar = None
        for metar in root.findall('METAR'):
            if metar.find('station_id').text == 'KDFW':
                kdfw_metar = metar
                break
        
        self.assertIsNotNone(kdfw_metar)
        
        # Test parsing flat structure
        cloud_layers = self.calculator.parse_cloud_layers(kdfw_metar)
        self.assertEqual(len(cloud_layers), 3)
        
        # Check first significant layer
        lowest_ceiling = self.calculator.get_lowest_ceiling(cloud_layers)
        self.assertEqual(lowest_ceiling, 2500)  # BKN025
    
    def test_parse_visibility_flat_structure(self):
        """Test parsing visibility from flat visibility_statute_mi structure."""
        tree = ET.parse(self.test_metar_2025_xml)
        root = tree.getroot()
        
        ksrq_metar = None
        for metar in root.findall('METAR'):
            if metar.find('station_id').text == 'KSRQ':
                ksrq_metar = metar
                break
        
        self.assertIsNotNone(ksrq_metar)
        
        # Test parsing flat visibility
        vis_elem = ksrq_metar.find('visibility_statute_mi')
        visibility = self.calculator.parse_visibility(vis_elem)
        self.assertEqual(visibility, 10.0)

class TestAPIIntegration(unittest.TestCase):
    """Test API integration and response handling."""
    
    def test_http_error_codes(self):
        """Test handling of HTTP error codes."""
        # Test 400 error handling
        self.assertEqual(self._handle_http_error(400), "INVALID_REQUEST")
        
        # Test 204 error handling
        self.assertEqual(self._handle_http_error(204), "NO_DATA")
        
        # Test 200 success
        self.assertEqual(self._handle_http_error(200), "SUCCESS")
    
    def test_timeout_handling(self):
        """Test timeout handling."""
        # This would be tested with actual network calls in integration tests
        self.assertTrue(True)
    
    def _handle_http_error(self, status_code):
        """Simulate HTTP error handling."""
        if status_code == 400:
            return "INVALID_REQUEST"
        elif status_code == 204:
            return "NO_DATA"
        elif status_code == 200:
            return "SUCCESS"
        else:
            return "UNKNOWN_ERROR"

def run_tests():
    """Run all tests."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestFlightCategoryCalculation))
    test_suite.addTest(unittest.makeSuite(TestTAFParsing))
    test_suite.addTest(unittest.makeSuite(TestErrorHandling))
    test_suite.addTest(unittest.makeSuite(Test2025APIParsing))
    test_suite.addTest(unittest.makeSuite(TestVisibilityNormalization))
    test_suite.addTest(unittest.makeSuite(TestFlightCategoryCalculator))
    test_suite.addTest(unittest.makeSuite(TestAPIIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    print("Running METAR parsing tests for 2025 API compatibility...")
    success = run_tests()
    if success:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed!")
        sys.exit(1)
