# Zornade Italian Parcel Downloader

**Professional QGIS plugin for accessing enriched Italian cadastral parcel data**

[![QGIS Version](https://img.shields.io/badge/QGIS-3.16+-green.svg)](https://qgis.org)
[![License](https://img.shields.io/badge/License-GPL--2.0--or--later-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-orange.svg)](metadata.txt)

## Overview

Zornade Italian Parcel Downloader is a professional-grade QGIS plugin that provides seamless access to Zornade's comprehensive Italian cadastral parcel database via RapidAPI. The plugin is designed for GIS professionals, real estate analysts, urban planners, and researchers who need accurate and enriched cadastral data for their projects.

## Key Features

### 🏗️ **Professional Data Access**
- **Comprehensive Dataset**: Access to over 10 million enriched Italian cadastral parcels
- **Rich Attributes**: 17 data fields including administrative info, demographics, and risk assessments
- **Accurate Geometries**: High-quality polygon and multipolygon geometries in EPSG:4326

### ⚡ **Performance & Reliability**
- **Intelligent Batch Processing**: Adaptive batch sizes (10-25 parcels) based on dataset size
- **Robust Error Handling**: Comprehensive error recovery and user-friendly messages
- **Rate Limiting**: Respectful API usage with automatic delays between batches
- **Progress Monitoring**: Real-time progress reporting with detailed feedback

### 🔧 **Professional Tools**
- **QGIS Integration**: Full Processing Framework integration with algorithm dialog
- **Coordinate Transformation**: Automatic CRS conversion with validation
- **Secure Credentials**: Encrypted storage of API keys with optional persistence
- **Large Dataset Support**: Optimized for processing thousands of parcels efficiently

### 🛡️ **Production Ready**
- **Extensive Validation**: Input validation and boundary checks
- **Performance Warnings**: Alerts for large areas that may impact performance
- **Detailed Logging**: Comprehensive error reporting and troubleshooting guidance
- **Cancellation Support**: User can cancel long-running operations safely

## Installation

### From QGIS Plugin Repository (Recommended)
1. Open QGIS and go to **Plugins** → **Manage and Install Plugins**
2. Search for **"Zornade Italian Parcel Downloader"**
3. Click **Install Plugin**
4. The plugin will appear in the Processing Toolbox under **Zornade API**

### Manual Installation
1. Download the latest release ZIP file
2. In QGIS, go to **Plugins** → **Manage and Install Plugins**
3. Click **Install from ZIP** and select the downloaded file
4. Enable the plugin in the **Installed** tab

## Prerequisites

### Software Requirements
- **QGIS**: Version 3.16 or higher
- **Internet Connection**: Stable connection for API access
- **Operating System**: Windows, macOS, or Linux

### API Access Requirements
- **RapidAPI Account**: Free registration at [rapidapi.com](https://rapidapi.com)
- **Service Subscription**: Active subscription to [Zornade's Italian Cadastral API](https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy)
- **API Credentials**: RapidAPI key and Bearer authorization token

## Quick Start Guide

### 1. API Setup
1. **Create RapidAPI Account**: Visit [rapidapi.com](https://rapidapi.com) and sign up
2. **Subscribe to Service**: Navigate to the [API page](https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy) and subscribe
3. **Get Credentials**:
   - Copy your **X-RapidAPI-Key** from the dashboard
   - Obtain the **Bearer token** from the API documentation
4. **Test Access**: Use the RapidAPI test console to verify your credentials work

### 2. Using the Plugin
1. **Open Processing Toolbox**: Go to **Processing** → **Toolbox**
2. **Navigate to Algorithm**: Expand **Zornade API** → **Zornade Italian Parcel Downloader**
3. **Configure Parameters**:
   - **RapidAPI Key**: Enter your API key
   - **Authorization Bearer Token**: Enter token (without 'Bearer ' prefix)
   - **Save Credentials**: Check to store securely for future use
   - **Bounding Box**: Define your area of interest in Italy
4. **Run Algorithm**: Click **Run** and monitor progress

### 3. Working with Results
- **Output Layer**: Automatically added to map with enriched attributes
- **Attribute Table**: Access detailed parcel information
- **Styling**: Apply symbology based on risk assessments or land use
- **Analysis**: Use QGIS tools for spatial analysis and reporting

## Data Structure

The plugin creates a polygon layer with the following attributes:

| Field | Type | Description |
|-------|------|-------------|
| `fid` | String | Unique parcel identifier |
| `gml_id` | String | GML ID from cadastral system |
| `administrativeunit` | String | Administrative unit code |
| `comune_name` | String | Municipality name |
| `footprint_sqm` | Double | Parcel area in square meters |
| `elevation_min` | Double | Minimum elevation (meters) |
| `elevation_max` | Double | Maximum elevation (meters) |
| `class` | String | Primary land use classification |
| `subtype` | String | Detailed land use subtype |
| `landcover` | String | Land cover type |
| `densita_abitativa` | Double | Population density |
| `eta_media` | Double | Average age of residents |
| `tasso_occupazione` | Double | Employment rate |
| `flood_risk` | String | Flood risk assessment |
| `landslide_risk` | String | Landslide risk assessment |
| `seismic_risk` | String | Seismic risk assessment |
| `buildings_count` | Integer | Number of buildings on parcel |

## Performance Guidelines

### Optimal Usage
- **Small Areas**: Start with areas under 1 km² for testing
- **Incremental Expansion**: Gradually increase area size based on performance
- **Peak Hours**: Avoid peak usage times for faster processing
- **Saved Credentials**: Use saved credentials to avoid re-entry

### Performance Expectations
| Area Size | Typical Parcels | Processing Time |
|-----------|----------------|-----------------|
| City Block | 10-50 parcels | 1-2 minutes |
| Neighborhood | 100-500 parcels | 5-15 minutes |
| Municipality | 1,000+ parcels | 20+ minutes |

### Large Dataset Tips
- **Break Into Chunks**: Process large areas in smaller sections
- **Monitor Progress**: Use the progress bar and log messages
- **Error Tolerance**: Plugin handles up to 10% errors automatically
- **Stable Connection**: Ensure stable internet for large downloads

## Troubleshooting

### Common Issues

#### Authentication Problems
**Symptoms**: 401/403 errors, "Authentication failed" messages
**Solutions**:
- Verify RapidAPI key is correct and active
- Ensure Bearer token is entered without 'Bearer ' prefix
- Check subscription status on RapidAPI dashboard
- Confirm API quota hasn't been exceeded

#### No Results Returned
**Symptoms**: "No parcels found" message
**Solutions**:
- Verify bounding box covers area within Italy
- Try smaller, more specific areas
- Check coordinate system of input extent
- Ensure area contains cadastral parcels

#### Performance Issues
**Symptoms**: Slow processing, timeouts
**Solutions**:
- Reduce bounding box size
- Check internet connection stability
- Process during off-peak hours
- Close other bandwidth-intensive applications

#### Geometry Errors
**Symptoms**: Missing or invalid geometries
**Solutions**:
- Check error messages in log for specific issues
- Verify API is returning valid geometry data
- Report persistent geometry issues to support

### Error Codes Reference

| Code | Meaning | Action |
|------|---------|--------|
| 401 | Authentication failed | Check API credentials |
| 403 | Access forbidden | Verify subscription status |
| 404 | Parcel not found | Normal - some parcels may be unavailable |
| 429 | Rate limit exceeded | Wait and retry with smaller area |
| 500 | Server error | Retry later or contact support |

## Advanced Usage

### Batch Processing
For processing multiple areas:
1. Save your credentials once
2. Use QGIS Model Builder to automate multiple downloads
3. Combine results using QGIS merge tools

### Integration with Other Tools
- **Database Import**: Export results to PostGIS, SpatiaLite, or other databases
- **Analysis Workflows**: Integrate with QGIS processing models
- **Reporting**: Use QGIS layout manager for professional reports
- **Web Services**: Publish results via QGIS Server

### Custom Styling
Example styling approaches:
- **Risk Assessment**: Color-code by flood/landslide/seismic risk
- **Land Use**: Categorize by class and subtype
- **Demographics**: Style by population density or age
- **Elevation**: Create elevation-based symbology

## Support & Community

### Getting Help
- **Documentation**: This README and plugin help text
- **Issues**: Report bugs on [GitHub Issues](https://github.com/zornade/qgis-italian-parcel-downloader/issues)
- **API Support**: Contact RapidAPI support for service issues
- **Community**: QGIS community forums for general GIS questions

### Contributing
We welcome contributions! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description
4. Follow existing code style and documentation standards

## License & Credits

### License
This plugin is licensed under the **GNU General Public License v2.0 or later (GPL-2.0-or-later)**.

### Credits
- **Developed by**: Zornade
- **Data Provider**: Zornade's enriched Italian cadastral dataset
- **API Platform**: RapidAPI
- **Built for**: QGIS Processing Framework
- **Geometry Processing**: QGIS geometry libraries
- **Concurrent Processing**: Python concurrent.futures

### Acknowledgments
- QGIS Development Team for the excellent Processing Framework
- RapidAPI for reliable API hosting
- Italian cadastral authorities for base data
- QGIS community for feedback and testing

---

**Version**: 1.0.0 | **Last Updated**: 2024 | **Maintained by**: Zornade Team
