# zornade Parcel Downloader

A QGIS plugin to download Italian parcel data from the zornade RapidAPI service.

## Features

- Download parcel geometries and attributes by bounding box
- Secure API key management with optional persistence
- Automatic coordinate transformation to project CRS
- Integration with QGIS Processing Framework

## Installation

1. Copy the plugin folder to your QGIS plugins directory
2. Enable the plugin in QGIS Plugin Manager
3. Get your RapidAPI key from https://rapidapi.com/zornade/api/zornade

## Usage

1. Open Processing Toolbox
2. Navigate to "zornade API" -> "zornade Parcel Downloader"
3. Enter your RapidAPI key
4. Define a bounding box
5. Run the algorithm

## Requirements

- QGIS 3.16 or higher
- Active RapidAPI subscription to zornade service
- Internet connection

## License

GNU General Public License v2.0
