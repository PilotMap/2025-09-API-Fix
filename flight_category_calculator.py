#!/usr/bin/env python3
"""
Flight Category Calculator for 2025 AviationWeather.gov API.
Calculates VFR/MVFR/IFR/LIFR categories from cloud and visibility data.
"""

import logging
from typing import Optional, List, Dict, Any

# Import configuration
import config
from log import logger

class FlightCategoryCalculator:
    """Calculator for determining flight categories from weather data."""
    
    def __init__(self):
        """Initialize the calculator with configuration."""
        self.log_calculation = getattr(config, 'log_flight_category_calculation', 1)
        self.force_fallback = getattr(config, 'force_fallback_calculation', 1)
    
    def calculate_flight_category(self, clouds_data: Any, visibility_data: Any) -> str:
        """
        Calculate flight category from cloud and visibility data.
        
        Args:
            clouds_data: Cloud data (XML element or dict)
            visibility_data: Visibility data (XML element or dict)
            
        Returns:
            str: Flight category (VFR, MVFR, IFR, LIFR)
        """
        try:
            # Parse cloud data
            cloud_layers = self.parse_cloud_layers(clouds_data)
            lowest_ceiling = self.get_lowest_ceiling(cloud_layers)
            
            # Parse visibility data
            visibility_mi = self.parse_visibility(visibility_data)
            
            # Calculate flight category
            flight_category = self._determine_flight_category(lowest_ceiling, visibility_mi)
            
            if self.log_calculation:
                logger.debug(f"Flight category calculation: ceiling={lowest_ceiling}ft, visibility={visibility_mi}mi -> {flight_category}")
            
            return flight_category
            
        except Exception as e:
            logger.warning(f"Error calculating flight category: {e}")
            return "VFR"  # Default to VFR on error
    
    def parse_cloud_layers(self, clouds_data: Any) -> List[Dict[str, Any]]:
        """
        Parse cloud layers from XML or dict data.
        Enhanced to handle both nested (<clouds><cloud>) and flat (<sky_condition>) structures.
        
        Args:
            clouds_data: Cloud data element
            
        Returns:
            List[Dict]: List of cloud layer dictionaries
        """
        cloud_layers = []
        
        if clouds_data is None:
            return cloud_layers
        
        try:
            # Handle XML element with findall method (nested structure)
            if hasattr(clouds_data, 'findall'):
                # Try nested clouds structure first
                for cloud_elem in clouds_data.findall('cloud'):
                    layer = {
                        'sky_cover': cloud_elem.get('sky_cover', 'SKC'),
                        'cloud_base_ft_agl': cloud_elem.get('cloud_base_ft_agl', '9999')
                    }
                    cloud_layers.append(layer)
                
                # If no nested clouds found, try flat sky_condition structure
                if not cloud_layers:
                    for sky_cond in clouds_data.findall('sky_condition'):
                        layer = {
                            'sky_cover': sky_cond.get('sky_cover', 'SKC'),
                            'cloud_base_ft_agl': sky_cond.get('cloud_base_ft_agl', '9999')
                        }
                        cloud_layers.append(layer)
            
            # Handle dict data
            elif isinstance(clouds_data, dict):
                if 'clouds' in clouds_data:
                    for cloud in clouds_data['clouds']:
                        layer = {
                            'sky_cover': cloud.get('sky_cover', 'SKC'),
                            'cloud_base_ft_agl': cloud.get('cloud_base_ft_agl', '9999')
                        }
                        cloud_layers.append(layer)
                elif 'sky_condition' in clouds_data:
                    # Handle flat structure in dict
                    sky_cond = clouds_data['sky_condition']
                    layer = {
                        'sky_cover': sky_cond.get('sky_cover', 'SKC'),
                        'cloud_base_ft_agl': sky_cond.get('cloud_base_ft_agl', '9999')
                    }
                    cloud_layers.append(layer)
            
            # Handle list data
            elif isinstance(clouds_data, list):
                for cloud in clouds_data:
                    layer = {
                        'sky_cover': cloud.get('sky_cover', 'SKC'),
                        'cloud_base_ft_agl': cloud.get('cloud_base_ft_agl', '9999')
                    }
                    cloud_layers.append(layer)
        
        except Exception as e:
            logger.warning(f"Error parsing cloud layers: {e}")
        
        return cloud_layers
    
    def parse_visibility(self, visibility_data: Any) -> float:
        """
        Parse visibility from XML or dict data.
        Enhanced to handle both nested (<visibility><statute_mi>) and flat (<visibility_statute_mi>) structures.
        
        Args:
            visibility_data: Visibility data element
            
        Returns:
            float: Visibility in statute miles
        """
        try:
            # Handle XML element
            if hasattr(visibility_data, 'get'):
                # Try nested structure first
                statute_mi = visibility_data.get('statute_mi', '999')
                if statute_mi != '999':
                    return self.normalize_visibility_value(statute_mi)
                
                # Try flat structure
                if hasattr(visibility_data, 'text') and visibility_data.text:
                    return self.normalize_visibility_value(visibility_data.text)
            
            # Handle dict data
            elif isinstance(visibility_data, dict):
                statute_mi = visibility_data.get('statute_mi', '999')
                if statute_mi != '999':
                    return self.normalize_visibility_value(statute_mi)
            
            # Handle direct value
            elif isinstance(visibility_data, (int, float, str)):
                return self.normalize_visibility_value(visibility_data)
        
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing visibility: {e}")
        
        return 999.0  # Default to unlimited visibility
    
    def normalize_visibility_value(self, visibility_str):
        """
        Normalize visibility values from various formats to float miles.
        
        Handles special cases like:
        - "10+" -> 10.0
        - "P6SM" -> 6.0 (P = Plus, SM = Statute Miles)
        - "1/2" -> 0.5
        - "1 1/2" -> 1.5
        - Regular numbers like "3.0" -> 3.0
        
        Args:
            visibility_str: String visibility value
            
        Returns:
            float: Normalized visibility in statute miles
        """
        if not visibility_str:
            return 999.0
        
        visibility_str = str(visibility_str).strip()
        
        try:
            # Handle "10+" format
            if visibility_str.endswith('+'):
                return float(visibility_str[:-1])
            
            # Handle "P6SM" format (P = Plus, SM = Statute Miles)
            if visibility_str.startswith('P') and visibility_str.endswith('SM'):
                return float(visibility_str[1:-2])
            
            # Handle fractional values like "1/2" or "1 1/2"
            if '/' in visibility_str:
                parts = visibility_str.split()
                if len(parts) == 1:
                    # Simple fraction like "1/2"
                    numerator, denominator = parts[0].split('/')
                    return float(numerator) / float(denominator)
                elif len(parts) == 2:
                    # Mixed number like "1 1/2"
                    whole_part = float(parts[0])
                    numerator, denominator = parts[1].split('/')
                    fractional_part = float(numerator) / float(denominator)
                    return whole_part + fractional_part
            
            # Handle regular numbers
            return float(visibility_str)
            
        except (ValueError, ZeroDivisionError):
            logger.warning(f"Could not parse visibility value: {visibility_str}")
            return 999.0  # Default to unlimited visibility
    
    def get_lowest_ceiling(self, cloud_layers: List[Dict[str, Any]]) -> int:
        """
        Get the lowest ceiling from cloud layers.
        
        Args:
            cloud_layers: List of cloud layer dictionaries
            
        Returns:
            int: Lowest ceiling in feet AGL
        """
        lowest_ceiling = 9999  # Default to high ceiling
        
        for layer in cloud_layers:
            sky_cover = layer.get('sky_cover', 'SKC')
            
            # Only consider OVC, BKN, and OVX layers
            if sky_cover in ('OVC', 'BKN', 'OVX'):
                try:
                    ceiling = int(layer.get('cloud_base_ft_agl', '9999'))
                    if ceiling < lowest_ceiling:
                        lowest_ceiling = ceiling
                except (ValueError, TypeError):
                    continue
        
        return lowest_ceiling
    
    def _determine_flight_category(self, ceiling_ft: int, visibility_mi: float) -> str:
        """
        Determine flight category based on ceiling and visibility.
        
        Flight Category Rules:
        - LIFR: ceiling < 500 ft OR visibility < 1 mile
        - IFR: ceiling 500-999 ft OR visibility 1-2.99 miles
        - MVFR: ceiling 1000-3000 ft OR visibility 3-5 miles
        - VFR: ceiling > 3000 ft AND visibility > 5 miles
        
        Args:
            ceiling_ft: Ceiling height in feet AGL
            visibility_mi: Visibility in statute miles
            
        Returns:
            str: Flight category
        """
        # Check for LIFR conditions
        if ceiling_ft < 500 or visibility_mi < 1.0:
            return "LIFR"
        
        # Check for IFR conditions
        if (500 <= ceiling_ft < 1000) or (1.0 <= visibility_mi < 3.0):
            return "IFR"
        
        # Check for MVFR conditions
        if (1000 <= ceiling_ft <= 3000) or (3.0 <= visibility_mi <= 5.0):
            return "MVFR"
        
        # Default to VFR
        return "VFR"
    
    def calculate_from_metar_element(self, metar_element) -> str:
        """
        Calculate flight category directly from METAR XML element.
        Enhanced to handle both nested and flat XML structures from 2025 API.
        
        Args:
            metar_element: METAR XML element
            
        Returns:
            str: Flight category
        """
        try:
            # Try to get API-provided flight category first
            flight_category_elem = metar_element.find('flight_category')
            if (flight_category_elem is not None and 
                flight_category_elem.text is not None and 
                flight_category_elem.text.strip() != '' and 
                flight_category_elem.text.strip() != 'NONE'):
                return flight_category_elem.text.strip()
            
            # Fall back to manual calculation
            # Try nested clouds structure first
            clouds_elem = metar_element.find('clouds')
            if clouds_elem is None:
                # Try flat sky_condition structure
                clouds_elem = metar_element
            
            # Try nested visibility structure first
            visibility_elem = metar_element.find('visibility')
            if visibility_elem is None:
                # Try flat visibility_statute_mi structure
                visibility_elem = metar_element.find('visibility_statute_mi')
            
            return self.calculate_flight_category(clouds_elem, visibility_elem)
        
        except Exception as e:
            logger.warning(f"Error calculating flight category from METAR element: {e}")
            return "VFR"
    
    def calculate_from_metar_xml(self, metar_element) -> str:
        """
        Calculate flight category directly from METAR XML element.
        Legacy method - use calculate_from_metar_element for enhanced functionality.
        
        Args:
            metar_element: METAR XML element
            
        Returns:
            str: Flight category
        """
        return self.calculate_from_metar_element(metar_element)
    
    def calculate_from_taf_forecast(self, forecast_element) -> str:
        """
        Calculate flight category from TAF forecast element.
        
        Args:
            forecast_element: TAF forecast XML element
            
        Returns:
            str: Flight category
        """
        try:
            # Get cloud data
            clouds_elem = forecast_element.find('clouds')
            
            # Get visibility data
            visibility_elem = forecast_element.find('visibility')
            
            return self.calculate_flight_category(clouds_elem, visibility_elem)
        
        except Exception as e:
            logger.warning(f"Error calculating flight category from TAF forecast: {e}")
            return "VFR"
    
    def get_flight_category_color(self, flight_category: str) -> tuple:
        """
        Get RGB color tuple for flight category.
        
        Args:
            flight_category: Flight category string
            
        Returns:
            tuple: RGB color tuple
        """
        color_map = {
            'VFR': getattr(config, 'color_vfr', (0, 255, 0)),
            'MVFR': getattr(config, 'color_mvfr', (0, 0, 255)),
            'IFR': getattr(config, 'color_ifr', (255, 0, 0)),
            'LIFR': getattr(config, 'color_lifr', (255, 0, 255)),
            'NONE': getattr(config, 'color_nowx', (242, 138, 37))
        }
        
        return color_map.get(flight_category, color_map['NONE'])
    
    def validate_flight_category(self, flight_category: str) -> bool:
        """
        Validate that flight category is a known value.
        
        Args:
            flight_category: Flight category string
            
        Returns:
            bool: True if valid, False otherwise
        """
        valid_categories = ['VFR', 'MVFR', 'IFR', 'LIFR', 'NONE']
        return flight_category in valid_categories

def create_flight_category_calculator():
    """Create and return a flight category calculator instance."""
    return FlightCategoryCalculator()

# Example usage and testing
if __name__ == '__main__':
    # Create calculator
    calculator = create_flight_category_calculator()
    
    # Test cases
    test_cases = [
        # (ceiling_ft, visibility_mi, expected_category)
        (25000, 10.0, "VFR"),
        (1000, 3.0, "MVFR"),
        (800, 2.0, "IFR"),
        (200, 0.5, "LIFR"),
        (9999, 1.0, "LIFR"),
        (500, 1.0, "IFR"),
        (3000, 5.0, "MVFR"),
        (3001, 5.1, "VFR")
    ]
    
    print("Testing flight category calculations:")
    print("-" * 50)
    
    for ceiling, visibility, expected in test_cases:
        result = calculator._determine_flight_category(ceiling, visibility)
        status = "✓" if result == expected else "✗"
        print(f"{status} Ceiling: {ceiling:5d}ft, Visibility: {visibility:4.1f}mi -> {result:4s} (expected {expected})")
    
    print("\nTesting cloud layer parsing:")
    print("-" * 50)
    
    # Test cloud layer parsing
    test_clouds = [
        {'sky_cover': 'FEW', 'cloud_base_ft_agl': '25000'},
        {'sky_cover': 'BKN', 'cloud_base_ft_agl': '1000'},
        {'sky_cover': 'OVC', 'cloud_base_ft_agl': '500'}
    ]
    
    cloud_layers = calculator.parse_cloud_layers(test_clouds)
    lowest_ceiling = calculator.get_lowest_ceiling(cloud_layers)
    print(f"Cloud layers: {len(cloud_layers)}")
    print(f"Lowest ceiling: {lowest_ceiling}ft")
    
    # Test visibility parsing
    test_visibility = {'statute_mi': '3.0'}
    visibility = calculator.parse_visibility(test_visibility)
    print(f"Visibility: {visibility}mi")
    
    # Test full calculation
    flight_category = calculator.calculate_flight_category(test_clouds, test_visibility)
    print(f"Calculated flight category: {flight_category}")
    
    # Test color mapping
    color = calculator.get_flight_category_color(flight_category)
    print(f"Flight category color: {color}")
