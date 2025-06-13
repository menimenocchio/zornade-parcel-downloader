#!/usr/bin/env python3
"""
Script to create a QGIS plugin ZIP file for installation.
"""

import os
import zipfile
import sys
from pathlib import Path

def create_plugin_zip():
    """Create a ZIP file for the QGIS plugin."""
    
    # Plugin information
    plugin_name = "zornade_parcel_downloader"
    
    # Files to include in the ZIP
    files_to_include = [
        "__init__.py",
        "zornade_parcel_downloader.py", 
        "parcel_downloader_provider.py",
        "ParcelDownloader.py",
        "rapidapi_auth.py",
        "metadata.txt",
        "README.md",
        "howto.png"  # Added the visual guide image
    ]
    
    # Optional files (include if they exist)
    optional_files = [
        "icon.png",
        "LICENSE"
    ]
    
    # Get the current directory (should be the plugin directory)
    plugin_dir = Path(__file__).parent
    
    # Create ZIP file
    zip_filename = f"{plugin_name}.zip"
    zip_path = plugin_dir / zip_filename
    
    print(f"Creating plugin ZIP: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add required files
        for filename in files_to_include:
            file_path = plugin_dir / filename
            if file_path.exists():
                # Add file to ZIP with plugin directory structure
                arcname = f"{plugin_name}/{filename}"
                zip_file.write(file_path, arcname)
                print(f"Added: {filename}")
            else:
                print(f"Warning: Required file not found: {filename}")
        
        # Add optional files if they exist
        for filename in optional_files:
            file_path = plugin_dir / filename
            if file_path.exists():
                arcname = f"{plugin_name}/{filename}"
                zip_file.write(file_path, arcname)
                print(f"Added: {filename}")
    
    print(f"\nPlugin ZIP created successfully: {zip_filename}")
    print(f"You can now install this ZIP file in QGIS via:")
    print("Plugins -> Manage and Install Plugins -> Install from ZIP")
    
    return zip_path

if __name__ == "__main__":
    create_plugin_zip()
