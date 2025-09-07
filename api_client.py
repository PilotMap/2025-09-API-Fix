#!/usr/bin/env python3
"""
API Client for AviationWeather.gov 2025 API.
Handles METAR and TAF data requests with proper error handling and retry logic.
"""

import urllib.request
import urllib.parse
import urllib.error
import socket
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import logging

# Import configuration
import config
from log import logger

# Get log level from config
loglevel = getattr(config, 'loglevel', 3)

class AviationWeatherAPIError(Exception):
    """Custom exception for API errors."""
    pass

class AviationWeatherAPIClient:
    """Client for AviationWeather.gov 2025 API."""
    
    def __init__(self):
        """Initialize the API client with configuration."""
        self.base_url = "https://aviationweather.gov/api/data"
        self.timeout = getattr(config, 'api_timeout', 30)
        self.retry_attempts = getattr(config, 'api_retry_attempts', 3)
        self.retry_delay = getattr(config, 'api_retry_delay', 5)
        self.handle_errors = getattr(config, 'handle_api_errors', 1)
        self.default_to_nowx = getattr(config, 'default_to_nowx_on_error', 1)
        
    def get_metar_data(self, airport_codes, hours=2.5):
        """
        Fetch METAR data for specified airports.
        
        Args:
            airport_codes (list): List of airport ICAO codes
            hours (float): Number of hours of data to retrieve
            
        Returns:
            ET.Element: XML root element containing METAR data
            
        Raises:
            AviationWeatherAPIError: If API request fails
        """
        url = f"{self.base_url}/metar?format=xml&hours={hours}&ids="
        return self._make_request(url, airport_codes, "METAR")
    
    def get_taf_data(self, airport_codes, hours=2.5):
        """
        Fetch TAF data for specified airports.
        
        Args:
            airport_codes (list): List of airport ICAO codes
            hours (float): Number of hours of data to retrieve
            
        Returns:
            ET.Element: XML root element containing TAF data
            
        Raises:
            AviationWeatherAPIError: If API request fails
        """
        url = f"{self.base_url}/taf?format=xml&hours={hours}&ids="
        return self._make_request(url, airport_codes, "TAF")
    
    def _make_request(self, base_url, airport_codes, data_type):
        """
        Make API request with retry logic and error handling.
        
        Args:
            base_url (str): Base URL for the API endpoint
            airport_codes (list): List of airport codes
            data_type (str): Type of data being requested (METAR/TAF)
            
        Returns:
            ET.Element: XML root element
            
        Raises:
            AviationWeatherAPIError: If all retry attempts fail
        """
        # Filter out NULL and LGND entries
        valid_codes = [code for code in airport_codes if code not in ['NULL', 'LGND']]
        
        if not valid_codes:
            logger.warning("No valid airport codes provided")
            return self._create_empty_response(data_type)
        
        # Handle chunking for requests with > 300 airports
        if len(valid_codes) > 300:
            return self._make_chunked_request(base_url, valid_codes, data_type)
        
        # Build URL with airport codes
        airport_string = ','.join(valid_codes)
        url = base_url + airport_string
        
        if loglevel <= 2:  # Only log if info level is enabled
            logger.info(f"Requesting {data_type} data for {len(valid_codes)} airports")
        if loglevel <= 1:  # Only log if debug level is enabled
            logger.debug(f"API URL: {url}")
        
        # Make request with retry logic
        for attempt in range(self.retry_attempts):
            try:
                response = self._make_single_request(url)
                return self._parse_response(response, data_type)
                
            except urllib.error.HTTPError as e:
                error_msg = self._handle_http_error(e.code, data_type)
                if e.code in [400, 204] and self.handle_errors:
                    logger.warning(f"HTTP {e.code}: {error_msg}")
                    return self._create_empty_response(data_type)
                elif attempt < self.retry_attempts - 1:
                    logger.warning(f"HTTP {e.code} on attempt {attempt + 1}, retrying...")
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise AviationWeatherAPIError(f"HTTP {e.code}: {error_msg}")
                    
            except (urllib.error.URLError, socket.timeout) as e:
                if attempt < self.retry_attempts - 1:
                    logger.warning(f"Network error on attempt {attempt + 1}: {e}, retrying...")
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise AviationWeatherAPIError(f"Network error: {e}")
                    
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise AviationWeatherAPIError(f"Unexpected error: {e}")
        
        raise AviationWeatherAPIError("All retry attempts failed")
    
    def _make_chunked_request(self, base_url, airport_codes, data_type):
        """
        Make chunked requests for large numbers of airports.
        
        Args:
            base_url (str): Base URL for the API endpoint
            airport_codes (list): List of airport codes
            data_type (str): Type of data being requested
            
        Returns:
            ET.Element: Combined XML root element
        """
        if loglevel <= 2:  # Only log if info level is enabled
            logger.info(f"Making chunked request for {len(airport_codes)} airports")
        
        all_content = []
        chunk_size = 300
        
        for i in range(0, len(airport_codes), chunk_size):
            chunk = airport_codes[i:i + chunk_size]
            airport_string = ','.join(chunk)
            url = base_url + airport_string
            
            try:
                response = self._make_single_request(url)
                content = self._extract_xml_content(response)
                all_content.extend(content)
                # Only log every 5th chunk or on errors to reduce logging overhead
                if (i // chunk_size + 1) % 5 == 0 and loglevel <= 1:
                    logger.debug(f"Processed chunk {i//chunk_size + 1}")
                
            except Exception as e:
                logger.warning(f"Error processing chunk {i//chunk_size + 1}: {e}")
                continue
        
        return self._combine_xml_content(all_content, data_type)
    
    def _make_single_request(self, url):
        """
        Make a single HTTP request.
        
        Args:
            url (str): Complete URL to request
            
        Returns:
            bytes: Response content
        """
        request = urllib.request.Request(url)
        request.add_header('User-Agent', 'LiveSectional/1.0')
        
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.read()
    
    def _parse_response(self, response_content, data_type):
        """
        Parse API response XML.
        
        Args:
            response_content (bytes): Raw response content
            data_type (str): Type of data (METAR/TAF)
            
        Returns:
            ET.Element: XML root element
        """
        try:
            # Decode response
            content_str = response_content.decode('UTF-8')
            lines = content_str.splitlines()
            
            # Extract XML content (skip first 8 lines and last line)
            xml_lines = lines[8:len(lines)-1]
            
            # Create complete XML document
            xml_content = ['<x>'] + xml_lines + ['</x>']
            xml_str = '\n'.join(xml_content)
            
            # Parse XML
            root = ET.fromstring(xml_str)
            if loglevel <= 2:  # Only log if info level is enabled
                logger.info(f"Successfully parsed {data_type} response")
            return root
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            raise AviationWeatherAPIError(f"Invalid XML response: {e}")
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            raise AviationWeatherAPIError(f"Response parsing failed: {e}")
    
    def _extract_xml_content(self, response_content):
        """
        Extract XML content from response.
        
        Args:
            response_content (bytes): Raw response content
            
        Returns:
            list: List of XML lines
        """
        content_str = response_content.decode('UTF-8')
        lines = content_str.splitlines()
        return lines[8:len(lines)-1]
    
    def _combine_xml_content(self, all_content, data_type):
        """
        Combine multiple XML responses into one.
        
        Args:
            all_content (list): List of XML content lines
            data_type (str): Type of data (METAR/TAF)
            
        Returns:
            ET.Element: Combined XML root element
        """
        # Create combined XML document
        xml_content = ['<x>'] + all_content + ['</x>']
        xml_str = '\n'.join(xml_content)
        
        try:
            root = ET.fromstring(xml_str)
            if loglevel <= 2:  # Only log if info level is enabled
                logger.info(f"Successfully combined {data_type} responses")
            return root
        except ET.ParseError as e:
            logger.error(f"XML combination error: {e}")
            raise AviationWeatherAPIError(f"Failed to combine XML responses: {e}")
    
    def _handle_http_error(self, status_code, data_type):
        """
        Handle HTTP error codes.
        
        Args:
            status_code (int): HTTP status code
            data_type (str): Type of data being requested
            
        Returns:
            str: Error message
        """
        if status_code == 400:
            return f"Invalid request parameters for {data_type}"
        elif status_code == 204:
            return f"No {data_type} data available for requested airports"
        elif status_code == 429:
            return f"Rate limit exceeded for {data_type} requests"
        elif status_code >= 500:
            return f"Server error ({status_code}) for {data_type} requests"
        else:
            return f"HTTP error {status_code} for {data_type} requests"
    
    def _create_empty_response(self, data_type):
        """
        Create empty XML response for error cases.
        
        Args:
            data_type (str): Type of data (METAR/TAF)
            
        Returns:
            ET.Element: Empty XML root element
        """
        if data_type == "METAR":
            xml_str = '<x><data num_results="0"></data></x>'
        else:  # TAF
            xml_str = '<x><data num_results="0"></data></x>'
        
        return ET.fromstring(xml_str)
    
    def test_connection(self):
        """
        Test API connection and availability.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Test with a single airport
            test_codes = ['KORD']
            self.get_metar_data(test_codes, hours=1)
            if loglevel <= 2:  # Only log if info level is enabled
                logger.info("API connection test successful")
            return True
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False

def create_api_client():
    """Create and return an API client instance."""
    return AviationWeatherAPIClient()

# Example usage
if __name__ == '__main__':
    # Test the API client
    client = create_api_client()
    
    # Test connection
    if client.test_connection():
        print("API connection test passed")
    else:
        print("API connection test failed")
    
    # Test METAR request
    try:
        airports = ['KORD', 'KJFK', 'KLAX']
        metar_data = client.get_metar_data(airports)
        print(f"Retrieved METAR data for {len(metar_data.findall('.//METAR'))} airports")
    except AviationWeatherAPIError as e:
        print(f"METAR request failed: {e}")
    
    # Test TAF request
    try:
        taf_data = client.get_taf_data(airports)
        print(f"Retrieved TAF data for {len(taf_data.findall('.//TAF'))} airports")
    except AviationWeatherAPIError as e:
        print(f"TAF request failed: {e}")
