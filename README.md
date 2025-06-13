# Zornade Italian Parcel Downloader

**Professional QGIS plugin for accessing enriched Italian cadastral parcel data**

[![QGIS Version](https://img.shields.io/badge/QGIS-3.16+-green.svg)](https://qgis.org)
[![License](https://img.shields.io/badge/License-GPL--2.0--or--later-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.5.0-orange.svg)](metadata.txt)

## Overview

Zornade Italian Parcel Downloader is a professional-grade QGIS plugin that provides seamless access to Zornade's comprehensive Italian cadastral parcel database via RapidAPI. The plugin is designed for GIS professionals, real estate analysts, urban planners, and researchers who need accurate and enriched cadastral data for their projects.

## Key Features

### 🏗️ **Professional Data Access**
- **Comprehensive Dataset**: Access to over 10 million enriched Italian cadastral parcels
- **Rich Attributes**: 57 data fields including administrative info, demographics, and risk assessments
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

### 1. API Setup with Visual Guide

![Credential Setup Guide](howto.png)

Follow these steps to get your API credentials:

1. **Create RapidAPI Account**: Visit [rapidapi.com](https://rapidapi.com) and sign up
2. **Subscribe to Service**: Navigate to the [Zornade API page](https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy) and subscribe to a plan
3. **Get Your Credentials** (see visual guide above):
   - **Step 1**: Click on any endpoint (like "get-parcels") to open the test interface
   - **Step 2**: Look at the "Code Examples" section on the right side
   - **Find RapidAPI Key**: In the cURL example, copy the value after `'X-RapidAPI-Key: '` (without quotes)
   - **Find Bearer Token**: In the cURL example, copy the value after `'Authorization: Bearer '` (just the token, not "Bearer ")

### 2. Plugin Configuration
1. **Open Plugin Menu**: Click the Zornade plugin icon in the toolbar
2. **Manage Credentials**: Select "Manage API Credentials" from the dropdown
3. **Enter Credentials**:
   - Paste your **RapidAPI Key** in the first field
   - Paste your **Bearer Token** in the second field (without "Bearer " prefix)
4. **Test & Save**: Click "Test Credentials" to verify, then "Save & Use"

### 3. Download Parcels
1. **Open Processing**: Click the plugin icon → "Download Italian Parcels"
2. **Set Area**: Define your bounding box area of interest in Italy
3. **Run**: Click "Run" - the plugin will use your saved credentials automatically
4. **Results**: The enriched parcel layer will be added to your map with automatic styling

## Credential Setup - Detailed Instructions

### Finding Your RapidAPI Key
1. Go to your [RapidAPI Dashboard](https://rapidapi.com/developer/dashboard)
2. Navigate to "My Apps" section
3. Copy the "X-RapidAPI-Key" value (starts with letters/numbers, about 50 characters)

### Finding Your Bearer Token
1. Visit the [Zornade API page](https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy)
2. Click on any endpoint (e.g., "get-parcels") 
3. Look at the "Code Examples" section on the right
4. In the cURL example, find the line: `'Authorization: Bearer TOKEN_HERE'`
5. Copy only the token part (after "Bearer ", usually starts with "eyJ")

### Common Setup Issues
- **Wrong format**: Make sure to copy only the token value, not "Bearer " prefix
- **Incomplete key**: RapidAPI keys are usually 50+ characters long
- **Subscription required**: Free tier may have limited access
- **Case sensitivity**: Copy credentials exactly as shown

## Data Structure

The plugin creates a polygon layer with comprehensive enriched attributes covering 57 data fields:

### Core Identification & Administrative
| Field | Type | Description |
|-------|------|-------------|
| `fid` | String | Unique parcel identifier |
| `gml_id` | String | GML ID from cadastral system |
| `label` | String | Parcel label/name |
| `administrativeunit` | String | Administrative unit code |
| `municipality_name` | String | Municipality name |
| `region_name` | String | Region name |
| `province_name` | String | Province name |
| `province_code` | String | Province code |
| `postal_code` | String | Postal code |

### Physical Characteristics & Geography
| Field | Type | Description |
|-------|------|-------------|
| `footprint_sqm` | Double | Parcel area in square meters |
| `elevation_min` | Double | Minimum elevation (meters) |
| `elevation_max` | Double | Maximum elevation (meters) |
| `ruggedness_index` | Double | Terrain ruggedness measure |
| `number_of_points` | Integer | Number of geometry points |

### Land Use & Classification
| Field | Type | Description |
|-------|------|-------------|
| `class` | String | Primary land use classification |
| `subtype` | String | Detailed land use subtype |
| `landcover` | String | Land cover type classification |
| `buildings_count` | Integer | Number of buildings on parcel |

### Demographics & Population
| Field | Type | Description |
|-------|------|-------------|
| `census_section_id` | String | Census section identifier |
| `section_type_code` | String | Census section type code |
| `estimated_population` | Integer | Estimated population count |
| `average_age` | Double | Average age of residents |
| `average_family_size` | Double | Average family size |
| `masculinity_rate` | Double | Male to female ratio |
| `single_person_rate` | Double | Single person household rate |
| `large_families_rate` | Double | Large family household rate |
| `elderly_rate` | Double | Elderly population percentage |

### Housing & Employment
| Field | Type | Description |
|-------|------|-------------|
| `housing_density` | Double | Housing units per area |
| `average_building_occupancy` | Double | Average building occupancy rate |
| `employment_rate` | Double | Employment rate percentage |
| `female_employment_rate` | Double | Female employment rate |
| `employment_gender_gap` | Double | Employment gender gap measure |

### Education & Social Indicators
| Field | Type | Description |
|-------|------|-------------|
| `higher_education_rate` | Double | Higher education attainment rate |
| `low_education_rate` | Double | Low education level rate |
| `foreign_population_rate` | Double | Foreign population percentage |
| `labor_integration_rate` | Double | Labor market integration rate |
| `non_eu_foreigners_rate` | Double | Non-EU foreign population rate |
| `young_foreigners_rate` | Double | Young foreign population rate |

### Economic & Development Indices
| Field | Type | Description |
|-------|------|-------------|
| `structural_dependency_index` | Double | Economic dependency measure |
| `population_turnover_index` | Double | Population mobility indicator |
| `real_estate_potential_index` | Double | Real estate investment potential |
| `redevelopment_opportunity_index` | Double | Redevelopment opportunity score |
| `economic_resilience_index` | Double | Economic resilience measure |
| `social_cohesion_index` | Double | Social cohesion indicator |

### Risk Assessments
| Field | Type | Description |
|-------|------|-------------|
| `flood_risk` | String | Flood risk level assessment |
| `landslide_risk` | String | Landslide risk level assessment |
| `coastalerosion_risk` | String | Coastal erosion risk assessment |
| `seismic_risk` | String | Seismic risk level assessment |

### Address & Location
| Field | Type | Description |
|-------|------|-------------|
| `primary_street_address` | String | Primary street address |
| `address_numbers` | String | Address numbers |

## Advanced Analysis Capabilities

### Risk Assessment Analysis
- **Multi-hazard Assessment**: Combine flood, landslide, coastal erosion, and seismic risk data
- **Risk Mapping**: Create comprehensive risk maps for disaster preparedness
- **Vulnerability Analysis**: Identify high-risk areas for targeted intervention

### Demographic Analysis
- **Population Dynamics**: Analyze age distribution, family structure, and migration patterns
- **Social Indicators**: Study education levels, employment patterns, and social cohesion
- **Integration Metrics**: Assess foreign population integration and labor market participation

### Economic Analysis
- **Real Estate Potential**: Evaluate investment opportunities using economic indices
- **Development Planning**: Use redevelopment indices for urban planning decisions
- **Economic Resilience**: Assess economic stability and growth potential

### Urban Planning Applications
- **Land Use Optimization**: Analyze current land use patterns and plan future development
- **Infrastructure Planning**: Use housing density and building counts for infrastructure needs
- **Environmental Planning**: Integrate elevation, ruggedness, and land cover data

## Advanced Usage

### Multi-Criteria Analysis Examples

#### Real Estate Investment Analysis
```python
# Example QGIS expression for investment scoring
("real_estate_potential_index" * 0.4) + 
("economic_resilience_index" * 0.3) + 
(CASE WHEN "flood_risk" = 'low' THEN 20 
      WHEN "flood_risk" = 'medium' THEN 10 
      ELSE 0 END * 0.3)
```

#### Social Vulnerability Assessment
```python
# Social vulnerability composite score
("elderly_rate" * 0.25) + 
("low_education_rate" * 0.25) + 
("foreign_population_rate" * 0.25) + 
(100 - "employment_rate") * 0.25
```

#### Climate Risk Evaluation
```python
# Multi-hazard risk score
(CASE WHEN "flood_risk" = 'high' THEN 3
      WHEN "flood_risk" = 'medium' THEN 2
      WHEN "flood_risk" = 'low' THEN 1
      ELSE 0 END) +
(CASE WHEN "landslide_risk" = 'high' THEN 3
      WHEN "landslide_risk" = 'medium' THEN 2
      WHEN "landslide_risk" = 'low' THEN 1
      ELSE 0 END) +
(CASE WHEN "seismic_risk" = 'high' THEN 3
      WHEN "seismic_risk" = 'medium' THEN 2
      WHEN "seismic_risk" = 'low' THEN 1
      ELSE 0 END)
```

### Professional Styling Examples

#### Risk-Based Symbology
Create categorized styling based on combined risk assessments with color gradients from green (low risk) to red (high risk).

#### Demographic Heat Maps
Use graduated symbology for population density, age distribution, or education levels to identify demographic patterns.

#### Economic Opportunity Mapping
Combine real estate potential and economic resilience indices to create opportunity heat maps for investment planning.

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

**Version**: 1.5.0 | **Last Updated**: 2025 | **Maintained by**: Zornade Team
