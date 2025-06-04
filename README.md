# Zornade Italian Parcel Downloader

A QGIS plugin to download enriched Italian cadastral parcel data from Zornade's comprehensive dataset via RapidAPI.

## Overview

This plugin provides seamless access to Zornade's enriched Italian cadastral parcel database, offering detailed geometric and attribute information for cadastral parcels across Italy. The data includes administrative boundaries, risk assessments, land cover classification, demographic information, and elevation statistics.

## Features

- **Comprehensive Data**: Access to enriched cadastral parcels with geometry, administrative info, and risk assessments
- **Bounding Box Queries**: Download parcels within any specified geographic area
- **Batch Processing**: Efficient concurrent downloads (10 parcels per batch) for improved performance
- **Secure Credentials**: Safe storage of API credentials with optional persistence
- **Coordinate Transformation**: Automatic transformation from any CRS to EPSG:4326
- **Processing Integration**: Full integration with QGIS Processing Framework
- **Rich Attributes**: Including flood risk, landslide risk, seismic risk, land cover, demographics, and building statistics
- **Error Handling**: Comprehensive error handling with detailed user feedback

## Installation

### From QGIS Plugin Repository (Recommended)
1. Open QGIS
2. Go to `Plugins` → `Manage and Install Plugins`
3. Search for "Zornade Italian Parcel Downloader"
4. Click `Install Plugin`

### Manual Installation
1. Download the plugin ZIP file
2. Open QGIS
3. Go to `Plugins` → `Manage and Install Plugins`
4. Click `Install from ZIP`
5. Select the downloaded ZIP file

## Requirements

- **QGIS**: Version 3.16 or higher
- **Internet Connection**: Required for API access
- **RapidAPI Account**: Active subscription to Zornade's service
- **Python Dependencies**: `requests` library (automatically available in QGIS)

## API Access Setup

1. **Create RapidAPI Account**: Visit [RapidAPI](https://rapidapi.com)
2. **Subscribe to Service**: Go to [Zornade's Italian Cadastral API](https://rapidapi.com/ageratlas/api/enriched-cadastral-parcels-for-italy)
3. **Get Credentials**: 
   - Copy your RapidAPI key from the dashboard
   - Obtain the Bearer authorization token from the API documentation
4. **Test Access**: Use the RapidAPI test console to verify your credentials

## Usage

### Processing Framework Method (Recommended)
1. Open the **Processing Toolbox** (`Processing` → `Toolbox`)
2. Navigate to **Zornade API** → **Zornade Parcel Downloader**
3. Configure parameters:
   - **RapidAPI Key**: Enter your RapidAPI key
   - **Authorization Bearer Token**: Enter the token (without 'Bearer ' prefix)
   - **Save Credentials**: Check to store credentials securely for future use
   - **Bounding Box**: Define the area of interest
4. Click **Run**

### Plugin Menu Method
1. Click the Zornade plugin icon in the toolbar
2. This will open the Processing algorithm dialog
3. Follow the same configuration steps as above

## Output Data Structure

The plugin creates a polygon layer with the following attributes:

| Field | Type | Description |
|-------|------|-------------|
| fid | String | Unique parcel identifier |
| gml_id | String | GML identifier from cadastral system |
| administrativeunit | String | Administrative unit code |
| comune_name | String | Municipality name |
| footprint_sqm | Double | Parcel area in square meters |
| elevation_min | Double | Minimum elevation (meters) |
| elevation_max | Double | Maximum elevation (meters) |
| class | String | Land use classification |
| subtype | String | Land use subtype |
| landcover | String | Land cover type |
| densita_abitativa | Double | Population density |
| eta_media | Double | Average age of residents |
| tasso_occupazione | Double | Employment rate |
| flood_risk | String | Flood risk assessment |
| landslide_risk | String | Landslide risk assessment |
| seismic_risk | String | Seismic risk assessment |
| buildings_count | Integer | Number of buildings on parcel |

## Troubleshooting

### Common Issues

**Authentication Errors**
- Verify your RapidAPI key is correct
- Ensure you have an active subscription
- Check that the Bearer token is entered without the 'Bearer ' prefix

**No Parcels Found**
- Verify the bounding box covers an area in Italy
- Try a smaller bounding box area
- Check that the coordinate system is correct

**Network Timeouts**
- Check your internet connection
- Try processing smaller areas
- Reduce batch size if experiencing frequent timeouts

**Geometry Errors**
- The plugin automatically handles different geometry formats
- Parcels without valid geometry are skipped with warnings
- Check the log for specific geometry processing messages

### Performance Tips

- Use smaller bounding boxes for faster processing
- The plugin processes 10 parcels concurrently by default
- Saved credentials eliminate the need to re-enter API keys
- Progress is shown in the QGIS message bar and processing dialog

## Support

- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/zornade/qgis-italian-parcel-downloader/issues)
- **Documentation**: Visit the [plugin homepage](https://rapidapi.com/ageratlas/api/enriched-cadastral-parcels-for-italy)
- **API Support**: Contact RapidAPI support for API-related issues

## License

This plugin is licensed under the GNU General Public License v2.0 or later (GPL-2.0-or-later).

## Credits

- **Developed by**: Zornade
- **Data Provider**: Zornade's enriched Italian cadastral dataset
- **API Platform**: RapidAPI
- **Built for**: QGIS Processing Framework

## Changelog

### Version 1.0.0
- Initial release
- Download Italian cadastral parcels by bounding box query
- Integration with QGIS Processing Framework
- Secure API credential management with persistent storage
- Batch processing with concurrent downloads
- Automatic coordinate transformation
- Support for polygon and multipolygon geometries
- Comprehensive error handling and user feedback
- Rich attribute data including risk assessments and demographics
