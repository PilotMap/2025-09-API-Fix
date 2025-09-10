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
import os

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
    
    # Configurable constants for robust batching
    MAX_PER_REQUEST = 380  # Safe below API cap
    REQUEST_TIMEOUT = 15
    RETRIES = 3
    INTER_BATCH_SLEEP = 0.2
    
    def __init__(self):
        """Initialize the API client with configuration."""
        self.base_url = "https://aviationweather.gov/api/data"
        self.timeout = getattr(config, 'api_timeout', self.REQUEST_TIMEOUT)
        self.retry_attempts = getattr(config, 'api_retry_attempts', self.RETRIES)
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
        
        # Normalize station IDs (uppercase, stripped, unique)
        stations = []
        for code in valid_codes:
            stations.append(code.strip().upper())
        stations = list(dict.fromkeys([s for s in stations if s]))  # preserves order, unique
        
        if not stations:
            logger.warning("No valid stations after normalization")
            return self._create_empty_response(data_type)
        
        # Handle chunking for requests with > MAX_PER_REQUEST airports
        if len(stations) > self.MAX_PER_REQUEST:
            return self._make_chunked_request(base_url, stations, data_type)
        
        # Build URL with airport codes
        airport_string = ','.join(stations)
        url = base_url + airport_string
        
        if loglevel <= 2:  # Only log if info level is enabled
            logger.info(f"Requesting {data_type} data for {len(stations)} airports")
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
        Make chunked requests for large numbers of airports with robust batching.
        
        Args:
            base_url (str): Base URL for the API endpoint
            airport_codes (list): List of airport codes
            data_type (str): Type of data being requested
            
        Returns:
            ET.Element: Combined XML root element
        """
        # Normalize station IDs (uppercase, stripped, unique)
        stations = list(set([code.strip().upper() for code in airport_codes if code and code.strip()]))
        
        if not stations:
            logger.warning("No valid stations after normalization")
            return self._create_empty_response(data_type)
        
        # Split into chunks of size <= MAX_PER_REQUEST
        chunks = []
        for i in range(0, len(stations), self.MAX_PER_REQUEST):
            chunks.append(stations[i:i + self.MAX_PER_REQUEST])
        
        # Debug logging when PILOTMAP_DEBUG_BATCH=1
        if os.getenv('PILOTMAP_DEBUG_BATCH') == '1':
            logger.info(f"Batching {len(stations)} stations into {len(chunks)} batches of max {self.MAX_PER_REQUEST}")
        
        all_xml_content = []
        
        for batch_idx, chunk in enumerate(chunks):
            airport_string = ','.join(chunk)
            url = base_url + airport_string
            
            # Make request with retry logic and exponential backoff
            for attempt in range(self.retry_attempts):
                try:
                    response = self._make_single_request(url)
                    
                    # Handle different response types
                    if response:
                        content = self._extract_xml_content(response)
                        all_xml_content.append(content)
                        
                        if os.getenv('PILOTMAP_DEBUG_BATCH') == '1':
                            # Count records in this batch
                            try:
                                batch_xml = '\n'.join(['<x>'] + content + ['</x>'])
                                batch_root = ET.fromstring(batch_xml)
                                record_count = len(batch_root.findall('.//METAR')) if data_type == 'METAR' else len(batch_root.findall('.//TAF'))
                                logger.info(f"Batch {batch_idx + 1}: {record_count} records returned")
                            except:
                                pass
                        
                        break  # Success, exit retry loop
                    
                except urllib.error.HTTPError as e:
                    if e.code == 204:  # No content
                        if os.getenv('PILOTMAP_DEBUG_BATCH') == '1':
                            logger.info(f"Batch {batch_idx + 1}: No content (204)")
                        break  # Continue to next batch
                    elif e.code in [400, 429, 500, 502, 503, 504]:
                        if attempt < self.retry_attempts - 1:
                            backoff_delay = self.retry_delay * (2 ** attempt)
                            logger.warning(f"Batch {batch_idx + 1} attempt {attempt + 1} failed with HTTP {e.code}, retrying in {backoff_delay}s...")
                            time.sleep(backoff_delay)
                        else:
                            logger.warning(f"Batch {batch_idx + 1} failed after {self.retry_attempts} attempts with HTTP {e.code}")
                            break  # Continue to next batch
                    else:
                        logger.warning(f"Batch {batch_idx + 1} failed with HTTP {e.code}")
                        break  # Continue to next batch
                        
                except (urllib.error.URLError, socket.timeout) as e:
                    if attempt < self.retry_attempts - 1:
                        backoff_delay = self.retry_delay * (2 ** attempt)
                        logger.warning(f"Batch {batch_idx + 1} attempt {attempt + 1} network error: {e}, retrying in {backoff_delay}s...")
                        time.sleep(backoff_delay)
                    else:
                        logger.warning(f"Batch {batch_idx + 1} failed after {self.retry_attempts} attempts with network error: {e}")
                        break  # Continue to next batch
                        
                except Exception as e:
                    logger.warning(f"Batch {batch_idx + 1} unexpected error: {e}")
                    break  # Continue to next batch
            
            # Inter-batch sleep to avoid rate limiting
            if batch_idx < len(chunks) - 1:  # Don't sleep after last batch
                time.sleep(self.INTER_BATCH_SLEEP)
        
        # Merge and deduplicate by observation_time
        return self._merge_and_deduplicate_xml(all_xml_content, data_type)
    
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
            # Extract XML content using robust method
            xml_lines = self._extract_xml_content(response_content)
            logger.info(f"_parse_response: Extracted {len(xml_lines)} XML lines")
            logger.info(f"_parse_response: First few lines: {xml_lines[:3] if len(xml_lines) >= 3 else xml_lines}")
            
            # Create complete XML document
            if xml_lines and xml_lines[0].strip().startswith('<?xml'):
                # Full XML response - parse directly
                xml_str = '\n'.join(xml_lines)
                logger.info(f"_parse_response: Parsing full XML response, length: {len(xml_str)}")
            else:
                # Partial XML - wrap with container
                xml_content = ['<x>'] + xml_lines + ['</x>']
                xml_str = '\n'.join(xml_content)
                logger.info(f"_parse_response: Created wrapped XML string, length: {len(xml_str)}")
            
            # Parse XML
            root = ET.fromstring(xml_str)
            logger.info(f"_parse_response: Parsed XML successfully, root: {root.tag}")
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
        logger.info(f"_extract_xml_content: Response has {len(lines)} lines")
        logger.info(f"_extract_xml_content: First 5 lines: {lines[:5]}")
        logger.info(f"_extract_xml_content: Last 5 lines: {lines[-5:]}")
        
        start = next((i for i,l in enumerate(lines) if '<data' in l), 8)
        end = next((i for i in range(len(lines)-1, -1, -1) if '</data>' in lines[i]), len(lines)-1)
        
        logger.info(f"_extract_xml_content: Found data start at line {start}, end at line {end}")
        
        result = lines[start:end+1] if start <= end else lines[8:len(lines)-1]
        logger.info(f"_extract_xml_content: Extracted {len(result)} lines")
        logger.info(f"_extract_xml_content: First few extracted lines: {result[:3] if len(result) >= 3 else result}")
        
        return result
    
    def _merge_and_deduplicate_xml(self, all_content, data_type):
        """
        Merge and deduplicate XML responses by observation_time.
        
        Args:
            all_content (list): List of XML content lines
            data_type (str): Type of data (METAR/TAF)
            
        Returns:
            ET.Element: Combined XML root element with deduplicated records
        """
        if not all_content:
            logger.warning("_merge_and_deduplicate_xml: No content provided")
            return self._create_empty_response(data_type)
        
        logger.info(f"_merge_and_deduplicate_xml: Processing {len(all_content)} content chunks")
        
        # Parse all METAR/TAF elements from collected chunks
        station_records = {}  # station_id -> (observation_time, element)
        
        for i, content in enumerate(all_content):
            try:
                logger.info(f"_merge_and_deduplicate_xml: Processing chunk {i+1}, content length: {len(content)}")
                logger.info(f"_merge_and_deduplicate_xml: First few lines of chunk {i+1}: {content[:3] if len(content) >= 3 else content}")
                
                # Create temporary XML document for parsing
                if content and content[0].strip().startswith('<?xml'):
                    # Full XML response - parse directly
                    temp_xml = '\n'.join(content)
                    logger.info(f"_merge_and_deduplicate_xml: Parsing full XML for chunk {i+1}")
                else:
                    # Partial XML - wrap with container
                    temp_xml = '\n'.join(['<x>'] + content + ['</x>'])
                    logger.info(f"_merge_and_deduplicate_xml: Created wrapped XML for chunk {i+1}")
                temp_root = ET.fromstring(temp_xml)
                
                # Find all METAR or TAF elements
                elements = temp_root.findall('.//METAR') if data_type == 'METAR' else temp_root.findall('.//TAF')
                logger.info(f"_merge_and_deduplicate_xml: Found {len(elements)} {data_type} elements in chunk {i+1}")
                
                for element in elements:
                    sid_elem = element.find('station_id')
                    station_id = (sid_elem.text.strip() if sid_elem is not None and sid_elem.text else element.get('station_id','').strip())
                    if not station_id:
                        continue
                    
                    # Get observation time for deduplication
                    if data_type == 'TAF':
                        time_elem = element.find('issue_time') or element.find('valid_time_from')
                    else:  # METAR
                        time_elem = element.find('observation_time')
                    if time_elem is not None and time_elem.text:
                        obs_time_str = time_elem.text.strip()
                        try:
                            # Parse ISO8601 timestamp for comparison
                            obs_time = datetime.fromisoformat(obs_time_str.replace('Z', '+00:00'))
                            
                            # Keep the most recent observation per station
                            if station_id not in station_records or obs_time > station_records[station_id][0]:
                                station_records[station_id] = (obs_time, element)
                        except ValueError:
                            # If timestamp parsing fails, keep the record anyway
                            if station_id not in station_records:
                                station_records[station_id] = (datetime.min, element)
                    else:
                        # No observation time, keep if we don't have this station
                        if station_id not in station_records:
                            station_records[station_id] = (datetime.min, element)
                            
            except ET.ParseError as e:
                logger.warning(f"Failed to parse XML chunk: {e}")
                continue
        
        # Reconstruct XML with deduplicated records
        if not station_records:
            logger.warning(f"_merge_and_deduplicate_xml: No station records found after processing {len(all_content)} chunks")
            return self._create_empty_response(data_type)
        
        # Create new XML structure
        root = ET.Element('x')
        data_elem = ET.SubElement(root, 'data')
        data_elem.set('num_results', str(len(station_records)))
        
        # Add deduplicated records
        for station_id, (obs_time, element) in station_records.items():
            data_elem.append(element)
        
        if os.getenv('PILOTMAP_DEBUG_BATCH') == '1':
            logger.info(f"Final result: {len(station_records)} unique stations after deduplication")
        
        if loglevel <= 2:  # Only log if info level is enabled
            logger.info(f"Successfully merged and deduplicated {data_type} responses")
        
        return root
    
    def _combine_xml_content(self, all_content, data_type):
        """
        Combine multiple XML responses into one (legacy method for backward compatibility).
        
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
