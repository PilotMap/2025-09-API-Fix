# Migration Guide: 2025 AviationWeather.gov API Changes

## Overview

This document outlines the complete migration from the legacy AviationWeather.gov API to the 2025 API version. The 2025 API introduced significant changes that require updates to the Live Sectional codebase to maintain functionality.

## Key Changes in 2025 API

### 1. Endpoint Changes

| Legacy Endpoint | 2025 Endpoint | Notes |
|----------------|---------------|-------|
| `/cgi-bin/data/metar.php` | `/api/data/metar` | New RESTful endpoint |
| `/cgi-bin/data/taf.php` | `/api/data/taf` | New RESTful endpoint |

### 2. Response Format Changes

#### Removed Fields
- `<flight_category>` - No longer provided in XML responses
- `<metar_id>` - Deprecated field
- Individual cloud properties - Replaced with `<clouds>` array

#### New Fields
- `<clouds>` - Array structure containing cloud layer information
- `<visibility>` - Structured visibility data with `<statute_mi>` sub-element
- ISO8601 timestamp format - Replaced epoch timestamps

#### Modified Fields
- Date format: Epoch timestamps → ISO8601 format (`2025-01-06T12:51:00Z`)
- Cloud data: Individual elements → Array structure

### 3. Error Handling Updates

| HTTP Code | Meaning | Handling |
|-----------|---------|----------|
| 200 | Success | Normal processing |
| 400 | Bad Request | Invalid parameters |
| 204 | No Content | Valid request, no data available |
| 429 | Rate Limited | Too many requests |
| 5xx | Server Error | Service unavailable |

## Code Changes Summary

### Files Modified

#### `metar-v4.py`
- **Lines 1192-1261**: Removed direct `flight_category` element access
- **Lines 1201-1232**: Updated cloud parsing for new array structure
- **Lines 1234-1249**: Enhanced cloud base height extraction
- **Lines 1264-1288**: Updated visibility parsing with fallback paths
- **Added**: Comprehensive error handling for missing elements

#### `config.py`
- **Lines 163-171**: Added 2025 API compatibility settings
- New configuration options for timeout, retry logic, and error handling

### New Files Created

#### `api_client.py`
- Dedicated API client for AviationWeather.gov
- Handles chunking for requests with > 300 airports
- Implements retry logic with exponential backoff
- Comprehensive error handling for all HTTP status codes

#### `flight_category_calculator.py`
- Standalone flight category calculation module
- Implements official flight category rules
- Handles both XML and dict data formats
- Provides color mapping for LED display

#### `test_metar_parsing.py`
- Comprehensive test suite for METAR parsing
- Tests flight category calculation logic
- Validates error handling scenarios
- Includes integration tests

#### `test_fixtures/`
- `metar_2025_sample.xml`: Sample METAR response in 2025 format
- `taf_2025_sample.xml`: Sample TAF response in 2025 format

## Flight Category Calculation

### Rules Implementation

The 2025 API no longer provides `<flight_category>` elements, so the system now calculates flight categories locally using the following rules:

| Category | Ceiling | Visibility | Logic |
|----------|---------|------------|-------|
| **LIFR** | < 500 ft AGL | OR | < 1 mile |
| **IFR** | 500-999 ft AGL | OR | 1-2.99 miles |
| **MVFR** | 1000-3000 ft AGL | OR | 3-5 miles |
| **VFR** | > 3000 ft AGL | AND | > 5 miles |

### Cloud Layer Processing

The new `<clouds>` array structure requires updated parsing:

```xml
<clouds>
  <cloud>
    <sky_cover>BKN</sky_cover>
    <cloud_base_ft_agl>1000</cloud_base_ft_agl>
  </cloud>
  <cloud>
    <sky_cover>OVC</sky_cover>
    <cloud_base_ft_agl>2000</cloud_base_ft_agl>
  </cloud>
</clouds>
```

The system now:
1. Iterates through all cloud layers
2. Identifies OVC, BKN, and OVX layers
3. Finds the lowest ceiling among these layers
4. Uses this for flight category calculation

### Visibility Processing

Updated visibility parsing handles the new structure:

```xml
<visibility>
  <statute_mi>3.0</statute_mi>
</visibility>
```

The system includes fallback logic for:
- Missing visibility elements
- Invalid visibility values
- Different visibility units

## Configuration Updates

### New Settings Added

```python
# 2025 API Compatibility Settings
api_timeout = 30                    # Request timeout in seconds
api_retry_attempts = 3             # Number of retry attempts
api_retry_delay = 5                # Delay between retries in seconds
force_fallback_calculation = 1     # Always use local calculation
log_flight_category_calculation = 1 # Enable calculation logging
handle_api_errors = 1              # Enable enhanced error handling
default_to_nowx_on_error = 1       # Default to no weather on error
api_version = '2025'               # Track API version
```

## Testing Strategy

### Test Coverage

1. **Flight Category Calculation Tests**
   - VFR, MVFR, IFR, LIFR scenarios
   - Edge cases and boundary values
   - Missing data handling

2. **API Integration Tests**
   - HTTP error code handling
   - Timeout scenarios
   - Retry logic validation

3. **XML Parsing Tests**
   - New 2025 API format
   - Legacy format fallback
   - Malformed data handling

4. **Error Handling Tests**
   - Network failures
   - Invalid responses
   - Missing elements

### Running Tests

```bash
# Run all tests
python3 test_metar_parsing.py

# Run specific test categories
python3 -m unittest TestFlightCategoryCalculation
python3 -m unittest TestAPIIntegration
```

## Migration Steps

### 1. Backup Current System
```bash
# Backup current configuration
cp config.py config.py.backup
cp metar-v4.py metar-v4.py.backup
```

### 2. Update Dependencies
```bash
# Install any new dependencies
pip3 install -r requirements.txt
```

### 3. Deploy New Code
```bash
# Deploy updated files
# (Files are already updated in this migration)
```

### 4. Test Configuration
```bash
# Test API connectivity
python3 api_client.py

# Run test suite
python3 test_metar_parsing.py
```

### 5. Monitor and Validate
- Check logs for flight category calculation messages
- Verify LED colors match expected flight categories
- Monitor for any error messages or warnings

## Troubleshooting

### Common Issues

#### 1. All Airports Showing "INVALID"
- **Cause**: Missing `<flight_category>` element in 2025 API
- **Solution**: Ensure `force_fallback_calculation = 1` in config.py

#### 2. Cloud Data Not Parsing
- **Cause**: New `<clouds>` array structure not handled
- **Solution**: Verify updated cloud parsing logic is active

#### 3. Visibility Issues
- **Cause**: New visibility structure not recognized
- **Solution**: Check visibility parsing fallback logic

#### 4. API Timeout Errors
- **Cause**: Network issues or API rate limiting
- **Solution**: Adjust `api_timeout` and `api_retry_attempts` settings

### Debug Mode

Enable detailed logging by setting:
```python
loglevel = 2  # Debug level
log_flight_category_calculation = 1
```

### Performance Considerations

- **Chunking**: Requests with > 300 airports are automatically chunked
- **Caching**: Consider implementing response caching for better performance
- **Rate Limiting**: Monitor API usage to avoid rate limits

## Rollback Procedure

If issues occur, rollback to the previous version:

```bash
# Restore backup files
cp config.py.backup config.py
cp metar-v4.py.backup metar-v4.py

# Restart the service
sudo systemctl restart metar-v4.service
```

## Future Considerations

### API Evolution
- Monitor for additional API changes
- Consider implementing API version detection
- Plan for potential future deprecations

### Performance Optimization
- Implement response caching
- Optimize chunking strategy
- Consider async processing for large requests

### Monitoring
- Add API health checks
- Implement alerting for API failures
- Track calculation accuracy metrics

## Support and Resources

### Documentation
- [AviationWeather.gov API Documentation](https://aviationweather.gov/api)
- [Live Sectional GitHub Repository](https://github.com/markyharris/livesectional)

### Community
- Live Sectional Forum
- GitHub Issues
- Aviation Weather Community

---

**Migration completed on**: 2025-01-06  
**API Version**: 2025  
**Code Version**: metar-v4.py (2025 API compatible)
