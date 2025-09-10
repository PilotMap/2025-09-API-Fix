# LiveSectional 2025 API Compatibility Update

Comprehensive fixes for LiveSectional LED aviation weather display to work with the updated 2025 AviationWeather.gov API structure.

## Problem Solved

The 2025 AviationWeather.gov API introduced significant changes to the XML response structure, causing several issues:

- **Airports showing as "INVALID"** - The parsing code expected nested XML elements (`<clouds><cloud>`, `<visibility><statute_mi>`) but the API now returns flat elements (`<sky_condition>`, `<visibility_statute_mi>`)
- **Flight category calculation failures** - Manual flight category calculation was failing due to parsing issues
- **Configuration forcing fallback** - `force_fallback_calculation = 1` was preventing use of API-provided flight categories
- **Missing visibility normalization** - Special visibility formats like "10+", "P6SM", and fractional values weren't handled

## Key Changes

### 1. Enhanced XML Parsing (`metar-v4.py`)
- **Dual Structure Support**: Handles both nested (`<clouds><cloud>`) and flat (`<sky_condition>`) XML structures
- **Improved Visibility Parsing**: Supports flat `<visibility_statute_mi>` elements and nested structures
- **Visibility Normalization**: Added `normalize_visibility_value()` function to handle special formats:
  - `"10+"` → `10.0` miles
  - `"P6SM"` → `6.0` miles (P = Plus, SM = Statute Miles)
  - `"1/2"` → `0.5` miles
  - `"1 1/2"` → `1.5` miles
- **API Flight Category Priority**: Uses API-provided flight categories when available
- **Enhanced Error Handling**: Comprehensive logging and fallback mechanisms

### 2. Flight Category Calculator (`flight_category_calculator.py`)
- **Enhanced `parse_cloud_layers()`**: Supports both XML structures
- **Enhanced `parse_visibility()`**: Handles flat and nested visibility elements
- **New `calculate_from_metar_element()`**: Unified method for both XML structures
- **Visibility Normalization**: Integrated normalization function
- **Robust Error Handling**: Graceful degradation on parsing failures

### 3. Configuration Updates (`config.py`)
- **`force_fallback_calculation`**: Changed default from `1` to `0` to allow API-provided categories
- **`prefer_api_flight_category`**: New setting (default `1`) to control API category usage
- **`log_xml_parsing_details`**: New setting (default `1`) for detailed parsing logs

### 4. Comprehensive Testing (`test_metar_parsing.py`)
- **2025 API Structure Tests**: Tests for flat XML parsing
- **Visibility Normalization Tests**: Tests for all special visibility formats
- **Flight Category Calculator Tests**: Tests for enhanced calculator methods
- **Integration Tests**: End-to-end parsing and calculation tests

## XML Structure Differences

### Expected Structure (Legacy)
```xml
<METAR>
  <clouds>
    <cloud sky_cover="BKN" cloud_base_ft_agl="1000"/>
  </clouds>
  <visibility>
    <statute_mi>3</statute_mi>
  </visibility>
  <flight_category>MVFR</flight_category>
</METAR>
```

### Actual 2025 API Structure
```xml
<METAR>
  <sky_condition sky_cover="BKN" cloud_base_ft_agl="1000"/>
  <visibility_statute_mi>3</visibility_statute_mi>
  <flight_category>MVFR</flight_category>
</METAR>
```

## Configuration Options

### New Settings in `config.py`:

```python
# 2025 API Compatibility Settings
force_fallback_calculation = 0  # Allow API-provided flight categories (was 1)
prefer_api_flight_category = 1  # Use API-provided flight categories when available
log_xml_parsing_details = 1     # Enable detailed XML parsing logs
```

### When to Use Fallback Calculation:
- Set `force_fallback_calculation = 1` if you want to always use manual calculation
- Set `prefer_api_flight_category = 0` if you want to ignore API-provided categories
- Enable `log_xml_parsing_details = 1` for debugging parsing issues

## Troubleshooting

### Airports Showing as "INVALID"
1. **Enable Debug Logging**: Set `log_xml_parsing_details = 1` in `config.py`
2. **Check Logs**: Look for parsing errors in `logfile.log`
3. **Verify API Response**: Ensure the API is returning valid XML
4. **Test Parsing**: Run `python3 test_metar_parsing.py` to verify parsing works

### Flight Categories Not Updating
1. **Check Configuration**: Verify `force_fallback_calculation = 0` and `prefer_api_flight_category = 1`
2. **Check API Response**: Ensure `<flight_category>` elements are present in XML
3. **Enable Logging**: Set `log_flight_category_calculation = 1` for detailed logs

### Visibility Parsing Issues
1. **Check Format**: Verify visibility values are in expected format
2. **Test Normalization**: Run visibility normalization tests
3. **Check Logs**: Look for visibility parsing errors

## Installation

```bash
# Install LED library
sudo pip3 install rpi_ws281x

# Install web dependencies
chmod +x install_web_deps.sh
sudo ./install_web_deps.sh

# Run tests to verify functionality
python3 test_metar_parsing.py
```

## Usage

```bash
# Run main display
sudo python3 metar-v4.py

# Test LEDs
sudo python3 test_led_simple.py

# Web interface: http://[PI_IP]:5000
```

## Testing

The update includes comprehensive tests for all new functionality:

```bash
# Run all tests
python3 test_metar_parsing.py

# Test specific functionality
python3 -m unittest test_metar_parsing.Test2025APIParsing
python3 -m unittest test_metar_parsing.TestVisibilityNormalization
python3 -m unittest test_metar_parsing.TestFlightCategoryCalculator
```

## Status: ✅ FULLY FUNCTIONAL

The LiveSectional system now fully supports the 2025 AviationWeather.gov API with:
- ✅ Correct parsing of flat XML structure
- ✅ API-provided flight category support
- ✅ Enhanced visibility normalization
- ✅ Comprehensive error handling
- ✅ Backward compatibility with legacy XML
- ✅ Extensive test coverage