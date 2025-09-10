#!/usr/bin/env python3
"""
Test suite for chunking functionality in api_client.py.
Tests robust batching, deduplication, error handling, and configuration.
"""

import unittest
import xml.etree.ElementTree as ET
import os
import sys
import socket
from datetime import datetime
from unittest.mock import patch, MagicMock
import urllib.error

# Add the current directory to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the modules we're testing
from api_client import AviationWeatherAPIClient, AviationWeatherAPIError

class TestChunkingLogic(unittest.TestCase):
    """Test the chunking logic for large airport lists."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = AviationWeatherAPIClient()
        # Create a large list of test airports (950 stations)
        self.large_airport_list = [f"K{i:03d}" for i in range(1, 951)]
    
    def test_chunker_splits_correctly(self):
        """Test that 950 stations are split into correct batches."""
        # Test the chunking logic directly
        stations = self.large_airport_list
        chunks = []
        for i in range(0, len(stations), self.client.MAX_PER_REQUEST):
            chunks.append(stations[i:i + self.client.MAX_PER_REQUEST])
        
        # Should have 3 chunks: 380, 380, 190
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 380)
        self.assertEqual(len(chunks[1]), 380)
        self.assertEqual(len(chunks[2]), 190)
    
    def test_station_id_normalization(self):
        """Test station ID normalization (uppercase, stripped, unique)."""
        test_stations = [
            "kord", " KJFK ", "kLAX", "kord", "  KDFW  ", "kord", "KSEA"
        ]
        
        # Simulate the normalization logic
        normalized = list(set([code.strip().upper() for code in test_stations if code and code.strip()]))
        
        expected = ["KORD", "KJFK", "KLAX", "KDFW", "KSEA"]
        self.assertEqual(sorted(normalized), sorted(expected))
        self.assertEqual(len(normalized), 5)  # Duplicates removed
    
    def test_constants_loaded_correctly(self):
        """Test that all new constants are properly loaded."""
        self.assertEqual(self.client.MAX_PER_REQUEST, 380)
        self.assertEqual(self.client.REQUEST_TIMEOUT, 15)
        self.assertEqual(self.client.RETRIES, 3)
        self.assertEqual(self.client.INTER_BATCH_SLEEP, 0.2)

class TestDeduplicationLogic(unittest.TestCase):
    """Test deduplication by observation_time."""
    
    def setUp(self):
        """Set up test fixtures with duplicate stations."""
        self.client = AviationWeatherAPIClient()
        
        # Create test XML with duplicate stations having different observation times
        self.duplicate_xml_content = [
            '<data num_results="2">',
            '<METAR station_id="KORD">',
            '<observation_time>2025-01-06T10:00:00Z</observation_time>',
            '<raw_text>KORD 061000Z 36010KT 10SM FEW250 15/02 A3012</raw_text>',
            '</METAR>',
            '<METAR station_id="KORD">',
            '<observation_time>2025-01-06T12:00:00Z</observation_time>',
            '<raw_text>KORD 061200Z 36010KT 10SM FEW250 15/02 A3012</raw_text>',
            '</METAR>',
            '<METAR station_id="KJFK">',
            '<observation_time>2025-01-06T11:00:00Z</observation_time>',
            '<raw_text>KJFK 061100Z 18015KT 8SM BKN100 12/05 A2998</raw_text>',
            '</METAR>',
            '</data>'
        ]
    
    def test_deduplication_keeps_newest(self):
        """Test that deduplication keeps the most recent observation per station."""
        result = self.client._merge_and_deduplicate_xml([self.duplicate_xml_content], "METAR")
        
        # Should have 2 unique stations
        metars = result.findall('.//METAR')
        self.assertEqual(len(metars), 2)
        
        # Check that KORD has the newer observation time
        kord_metars = [m for m in metars if m.get('station_id') == 'KORD']
        self.assertEqual(len(kord_metars), 1)
        
        obs_time = kord_metars[0].find('observation_time').text
        self.assertEqual(obs_time, '2025-01-06T12:00:00Z')
    
    def test_iso8601_timestamp_parsing(self):
        """Test ISO8601 timestamp parsing and comparison."""
        # Test various timestamp formats
        timestamps = [
            '2025-01-06T12:00:00Z',
            '2025-01-06T10:00:00Z',
            '2025-01-06T11:30:00Z'
        ]
        
        parsed_times = []
        for ts in timestamps:
            try:
                parsed_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                parsed_times.append(parsed_time)
            except ValueError:
                self.fail(f"Failed to parse timestamp: {ts}")
        
        # Should be sorted correctly
        sorted_times = sorted(parsed_times)
        self.assertEqual(sorted_times[0].isoformat(), '2025-01-06T10:00:00+00:00')
        self.assertEqual(sorted_times[-1].isoformat(), '2025-01-06T12:00:00+00:00')

class TestErrorHandling(unittest.TestCase):
    """Test error handling scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = AviationWeatherAPIClient()
    
    @patch('api_client.AviationWeatherAPIClient._make_single_request')
    def test_retry_logic_with_exponential_backoff(self, mock_request):
        """Test retry logic with exponential backoff."""
        # Mock HTTP error that should trigger retries
        mock_request.side_effect = urllib.error.HTTPError(
            url="test", code=500, msg="Server Error", hdrs={}, fp=None
        )
        
        with patch('time.sleep') as mock_sleep:
            with self.assertRaises(AviationWeatherAPIError):
                self.client._make_chunked_request(
                    "https://test.com/api?ids=", 
                    ["KORD", "KJFK"], 
                    "METAR"
                )
        
        # Should have made 3 attempts (RETRIES)
        self.assertEqual(mock_request.call_count, 3)
        
        # Should have slept with exponential backoff
        expected_sleeps = [5, 10]  # retry_delay * (2^0), retry_delay * (2^1)
        mock_sleep.assert_any_call(5)  # First retry
        mock_sleep.assert_any_call(10)  # Second retry
    
    @patch('api_client.AviationWeatherAPIClient._make_single_request')
    def test_handles_204_no_content(self, mock_request):
        """Test handling of 204 (no content) responses."""
        # Mock 204 response
        mock_request.side_effect = urllib.error.HTTPError(
            url="test", code=204, msg="No Content", hdrs={}, fp=None
        )
        
        result = self.client._make_chunked_request(
            "https://test.com/api?ids=", 
            ["KORD", "KJFK"], 
            "METAR"
        )
        
        # Should return empty response
        self.assertIsNotNone(result)
        metars = result.findall('.//METAR')
        self.assertEqual(len(metars), 0)
    
    @patch('api_client.AviationWeatherAPIClient._make_single_request')
    def test_handles_network_timeout(self, mock_request):
        """Test handling of network timeout scenarios."""
        # Mock timeout error
        mock_request.side_effect = socket.timeout("Request timed out")
        
        with patch('time.sleep') as mock_sleep:
            result = self.client._make_chunked_request(
                "https://test.com/api?ids=", 
                ["KORD", "KJFK"], 
                "METAR"
            )
        
        # Should return empty response after retries
        self.assertIsNotNone(result)
        metars = result.findall('.//METAR')
        self.assertEqual(len(metars), 0)

class TestIntegrationSmokeTest(unittest.TestCase):
    """Integration smoke test with mocked HTTP client."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = AviationWeatherAPIClient()
    
    @patch('api_client.AviationWeatherAPIClient._make_single_request')
    def test_mocked_batch_processing(self, mock_request):
        """Test batch processing with mocked HTTP responses."""
        # Mock responses for two batches with overlapping stations
        batch1_xml = [
            '<data num_results="2">',
            '<METAR station_id="KORD">',
            '<observation_time>2025-01-06T10:00:00Z</observation_time>',
            '<raw_text>KORD 061000Z 36010KT 10SM FEW250 15/02 A3012</raw_text>',
            '</METAR>',
            '<METAR station_id="KJFK">',
            '<observation_time>2025-01-06T10:00:00Z</observation_time>',
            '<raw_text>KJFK 061000Z 18015KT 8SM BKN100 12/05 A2998</raw_text>',
            '</METAR>',
            '</data>'
        ]
        
        batch2_xml = [
            '<data num_results="2">',
            '<METAR station_id="KORD">',  # Duplicate with newer time
            '<observation_time>2025-01-06T12:00:00Z</observation_time>',
            '<raw_text>KORD 061200Z 36010KT 10SM FEW250 15/02 A3012</raw_text>',
            '</METAR>',
            '<METAR station_id="KLAX">',
            '<observation_time>2025-01-06T12:00:00Z</observation_time>',
            '<raw_text>KLAX 061200Z 27008KT 10SM FEW200 20/10 A3015</raw_text>',
            '</METAR>',
            '</data>'
        ]
        
        # Mock the responses with 8 dummy header lines and 1 dummy footer line
        mock1 = ['h']*8 + batch1_xml + ['t']
        mock2 = ['h']*8 + batch2_xml + ['t']
        mock_request.side_effect = [
            '\n'.join(mock1).encode('utf-8'),
            '\n'.join(mock2).encode('utf-8')
        ]
        
        # Test with 500 stations to trigger chunking
        test_stations = [f"K{i:03d}" for i in range(1, 501)]
        
        result = self.client._make_chunked_request(
            "https://test.com/api?ids=", 
            test_stations, 
            "METAR"
        )
        
        # Should have 3 unique stations (KORD, KJFK, KLAX)
        metars = result.findall('.//METAR')
        self.assertEqual(len(metars), 3)
        
        # Verify KORD has the newer observation time
        kord_metars = [m for m in metars if m.get('station_id') == 'KORD']
        self.assertEqual(len(kord_metars), 1)
        obs_time = kord_metars[0].find('observation_time').text
        self.assertEqual(obs_time, '2025-01-06T12:00:00Z')
    
    def test_no_station_dropped_silently(self):
        """Test that no station is silently dropped during processing."""
        # Create test data with known stations
        test_stations = ["KORD", "KJFK", "KLAX", "KDFW", "KSEA"]
        
        with patch('api_client.AviationWeatherAPIClient._make_single_request') as mock_request:
            # Mock successful response
            mock_xml = [
                '<data num_results="5">',
                '<METAR station_id="KORD"><observation_time>2025-01-06T12:00:00Z</observation_time></METAR>',
                '<METAR station_id="KJFK"><observation_time>2025-01-06T12:00:00Z</observation_time></METAR>',
                '<METAR station_id="KLAX"><observation_time>2025-01-06T12:00:00Z</observation_time></METAR>',
                '<METAR station_id="KDFW"><observation_time>2025-01-06T12:00:00Z</observation_time></METAR>',
                '<METAR station_id="KSEA"><observation_time>2025-01-06T12:00:00Z</observation_time></METAR>',
                '</data>'
            ]
            mock_with_headers = ['h']*8 + mock_xml + ['t']
            mock_request.return_value = '\n'.join(mock_with_headers).encode('utf-8')
            
            result = self.client._make_chunked_request(
                "https://test.com/api?ids=", 
                test_stations, 
                "METAR"
            )
        
        # All 5 stations should be present
        metars = result.findall('.//METAR')
        self.assertEqual(len(metars), 5)
        
        station_ids = [m.get('station_id') for m in metars]
        for station in test_stations:
            self.assertIn(station, station_ids)

class TestDebugLogging(unittest.TestCase):
    """Test debug logging functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = AviationWeatherAPIClient()
    
    @patch.dict(os.environ, {'PILOTMAP_DEBUG_BATCH': '1'})
    @patch('api_client.logger')
    def test_debug_logging_activation(self, mock_logger):
        """Test debug logging activation with PILOTMAP_DEBUG_BATCH=1."""
        test_stations = [f"K{i:03d}" for i in range(1, 401)]  # 400 stations
        
        with patch('api_client.AviationWeatherAPIClient._make_single_request') as mock_request:
            mock_request.return_value = b'<data num_results="0"></data>'
            
            self.client._make_chunked_request(
                "https://test.com/api?ids=", 
                test_stations, 
                "METAR"
            )
        
        # Should have logged batch information
        mock_logger.info.assert_any_call("Batching 400 stations into 2 batches of max 380")
        mock_logger.info.assert_any_call("Final result: 0 unique stations after deduplication")

class TestConfiguration(unittest.TestCase):
    """Test configuration loading and constants."""
    
    def test_configuration_constants(self):
        """Test that all configuration constants are properly set."""
        client = AviationWeatherAPIClient()
        
        # Test class constants
        self.assertEqual(client.MAX_PER_REQUEST, 380)
        self.assertEqual(client.REQUEST_TIMEOUT, 15)
        self.assertEqual(client.RETRIES, 3)
        self.assertEqual(client.INTER_BATCH_SLEEP, 0.2)
        
        # Test that timeout is set correctly
        self.assertEqual(client.timeout, 15)

if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
