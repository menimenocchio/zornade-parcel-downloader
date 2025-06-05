# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Zornade Italian Parcel Downloader
                                 A QGIS plugin
 Downloads enriched Italian cadastral parcel data from Zornade's dataset via RapidAPI.
                              -------------------
        begin                : 2024-01-01
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Zornade
        email                : info@zornade.com
 ***************************************************************************/
"""

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import os
from typing import Any, Optional
import concurrent.futures
import threading

from qgis.PyQt.QtCore import QCoreApplication, QSettings
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsFeatureSink,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterString,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsRectangle,
    QgsVectorLayer,
    QgsSymbol,
    QgsRendererCategory,
    QgsCategorizedSymbolRenderer,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsSimpleFillSymbolLayer,
    QgsSimpleLineSymbolLayer,
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsVectorLayerSimpleLabeling,
    QgsMapLayer
)
import requests # Required for API calls


class ParcelDownloaderAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm fetches enriched Italian cadastral parcel data from 
    Zornade's comprehensive dataset via RapidAPI service and loads it into QGIS.
    """

    # --- Parameter definition ---
    # Input parameters
    BBOX = "BBOX"
    API_KEY = "API_KEY"
    AUTH_TOKEN = "AUTH_TOKEN"
    SAVE_API_KEY = "SAVE_API_KEY"

    # Output parameters
    OUTPUT_PARCELS = "OUTPUT_PARCELS"

    # --- API Configuration ---
    API_BASE_URL = "https://enriched-cadastral-parcels-for-italy.p.rapidapi.com/functions/v1"
    SETTINGS_GROUP = "ZornadeParcelDownloader"
    SETTINGS_API_KEY = "rapidApiKey"
    SETTINGS_AUTH_TOKEN = "authToken"

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return ParcelDownloaderAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm.
        """
        return "ZornadeParcelDownloader"

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr("Zornade Italian Parcel Downloader")

    def group(self):
        """
        Returns the name of the group this algorithm belongs to.
        """
        return self.tr("Zornade API")

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to.
        """
        return "zornadeapi"

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm.
        """
        return self.tr(
            "Downloads enriched Italian cadastral parcel data from Zornade's comprehensive dataset via RapidAPI based on bounding box query.\n\n"
            "This algorithm provides access to detailed cadastral information including geometries, administrative data, "
            "risk assessments (flood, landslide, seismic), land cover classification, demographic statistics, and elevation data.\n\n"
            "Requirements:\n"
            "• RapidAPI account with active subscription to Zornade's service\n"
            "• RapidAPI key from your dashboard\n"
            "• Authorization Bearer Token from the API documentation\n\n"
            "Setup Instructions:\n"
            "1. Visit https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy\n"
            "2. Subscribe to Zornade's Italian Cadastral Parcels service\n"
            "3. Copy your x-rapidapi-key from the RapidAPI dashboard\n"
            "4. Obtain the Bearer token from the API documentation or test console\n\n"
            "Usage:\n"
            "• Enter your RapidAPI key and authorization token (without 'Bearer ' prefix)\n"
            "• Define a bounding box covering your area of interest in Italy\n"
            "• Choose whether to save credentials securely for future sessions\n"
            "• The algorithm will automatically transform coordinates and download parcels in batches\n\n"
            "Output:\n"
            "A polygon layer with enriched attributes including risk assessments, demographics, and land use data."
        )

    def helpUrl(self):
        """Return URL to detailed documentation."""
        return "https://github.com/zornade/qgis-italian-parcel-downloader/blob/main/README.md"

    def __init__(self):
        super().__init__()

    def initAlgorithm(self, config: Optional[dict[str, Any]] = None):
        """
        Defines the inputs and outputs of the algorithm.
        """
        # --- API Key Management ---
        settings = QSettings()
        saved_api_key = settings.value(f"{self.SETTINGS_GROUP}/{self.SETTINGS_API_KEY}", "")
        saved_auth_token = settings.value(f"{self.SETTINGS_GROUP}/{self.SETTINGS_AUTH_TOKEN}", "")
        
        if saved_api_key:
            api_key_hint = f"Current saved key: {saved_api_key[:8]}...{saved_api_key[-4:]} (masked for security)"
        else:
            api_key_hint = "No API key currently saved"
        
        self.addParameter(
            QgsProcessingParameterString(
                self.API_KEY,
                self.tr("RapidAPI Key ({})".format(api_key_hint)),
                defaultValue=saved_api_key,
                optional=False,
                multiLine=False
            )
        )
        
        if saved_auth_token:
            auth_token_hint = f"Current saved token: {saved_auth_token[:20]}... (masked for security)"
        else:
            auth_token_hint = "No auth token currently saved"
        
        self.addParameter(
            QgsProcessingParameterString(
                self.AUTH_TOKEN,
                self.tr("Authorization Bearer Token - enter token only, no 'Bearer ' prefix ({})".format(auth_token_hint)),
                defaultValue=saved_auth_token,
                optional=False,
                multiLine=False
            )
        )
        
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SAVE_API_KEY,
                self.tr("Save credentials for future sessions (uncheck to remove saved credentials)"),
                defaultValue=bool(saved_api_key and saved_auth_token)
            )
        )

        # --- Bounding Box ---
        self.addParameter(
            QgsProcessingParameterExtent(
                self.BBOX,
                self.tr("Bounding Box (will be converted to EPSG:4326 for API)"),
                optional=False
            )
        )

        # --- Output Layer ---
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_PARCELS, self.tr("Downloaded Parcels")
            )
        )

    def checkParameterValues(self, parameters: dict[str, Any], context: QgsProcessingContext) -> bool:
        """
        Validate parameters before processing.
        """
        api_key = self.parameterAsString(parameters, self.API_KEY, context)
        if not api_key or not api_key.strip():
            raise QgsProcessingException(
                self.tr("RapidAPI Key is required. Please enter your API key or visit "
                       "https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy to get one.")
            )

        auth_token = self.parameterAsString(parameters, self.AUTH_TOKEN, context)
        if not auth_token or not auth_token.strip():
            raise QgsProcessingException(
                self.tr("Authorization Bearer Token is required. Please check the API documentation for how to obtain this token.")
            )

        bbox = self.parameterAsExtent(parameters, self.BBOX, context)
        if bbox.isNull() or bbox.isEmpty():
            raise QgsProcessingException(self.tr("Bounding Box is required."))

        return super().checkParameterValues(parameters, context)

    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict[str, Any]:
        """
        Main processing logic.
        """
        # Get credentials from parameters
        api_key = self.parameterAsString(parameters, self.API_KEY, context).strip()
        auth_token = self.parameterAsString(parameters, self.AUTH_TOKEN, context).strip()
        
        # Clean up auth token - remove "Bearer " prefix if user included it
        if auth_token.lower().startswith('bearer '):
            auth_token = auth_token[7:]  # Remove "Bearer " prefix
        
        save_api_key = self.parameterAsBool(parameters, self.SAVE_API_KEY, context)
        
        # Handle credential saving/updating/removing
        settings = QSettings()
        current_saved_api = settings.value(f"{self.SETTINGS_GROUP}/{self.SETTINGS_API_KEY}", "")
        current_saved_token = settings.value(f"{self.SETTINGS_GROUP}/{self.SETTINGS_AUTH_TOKEN}", "")
        
        if save_api_key:
            if current_saved_api != api_key or current_saved_token != auth_token:
                settings.setValue(f"{self.SETTINGS_GROUP}/{self.SETTINGS_API_KEY}", api_key)
                settings.setValue(f"{self.SETTINGS_GROUP}/{self.SETTINGS_AUTH_TOKEN}", auth_token)
                if current_saved_api and current_saved_token:
                    feedback.pushInfo(self.tr("Credentials updated and saved for future sessions."))
                else:
                    feedback.pushInfo(self.tr("Credentials saved for future sessions."))
            else:
                feedback.pushInfo(self.tr("Using saved credentials."))
        else:
            if current_saved_api or current_saved_token:
                settings.remove(f"{self.SETTINGS_GROUP}/{self.SETTINGS_API_KEY}")
                settings.remove(f"{self.SETTINGS_GROUP}/{self.SETTINGS_AUTH_TOKEN}")
                feedback.pushInfo(self.tr("Saved credentials removed. Current credentials will only be used for this session."))

        bbox_extent = self.parameterAsExtent(parameters, self.BBOX, context)
        bbox_crs = self.parameterAsExtentCrs(parameters, self.BBOX, context)
        
        # Handle coordinate transformation
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        
        if bbox_crs != target_crs:
            transform = QgsCoordinateTransform(bbox_crs, target_crs, QgsProject.instance())
            bbox_extent_4326 = transform.transformBoundingBox(bbox_extent)
            feedback.pushInfo(self.tr("Transformed bounding box from {} to EPSG:4326".format(bbox_crs.authid())))
        else:
            bbox_extent_4326 = bbox_extent

        # Validate bounding box size for performance
        bbox_area = bbox_extent_4326.area()
        if bbox_area > 1.0:  # Roughly 100km x 100km at equator
            feedback.pushWarning(self.tr(
                "Large bounding box detected (area: {:.4f} sq degrees). "
                "This may result in many parcels and slow processing. "
                "Consider using a smaller area for better performance."
            ).format(bbox_area))

        # Define output fields based on zornade API response
        fields = QgsFields()
        from qgis.PyQt.QtCore import QVariant
        
        fields.append(QgsField("fid", QVariant.String))
        fields.append(QgsField("gml_id", QVariant.String))
        fields.append(QgsField("administrativeunit", QVariant.String))
        fields.append(QgsField("comune_name", QVariant.String))
        fields.append(QgsField("footprint_sqm", QVariant.Double))
        fields.append(QgsField("elevation_min", QVariant.Double))
        fields.append(QgsField("elevation_max", QVariant.Double))
        fields.append(QgsField("class", QVariant.String))
        fields.append(QgsField("subtype", QVariant.String))
        fields.append(QgsField("landcover", QVariant.String))
        fields.append(QgsField("densita_abitativa", QVariant.Double))
        fields.append(QgsField("eta_media", QVariant.Double))
        fields.append(QgsField("tasso_occupazione", QVariant.Double))
        fields.append(QgsField("flood_risk", QVariant.String))
        fields.append(QgsField("landslide_risk", QVariant.String))
        fields.append(QgsField("seismic_risk", QVariant.String))
        fields.append(QgsField("buildings_count", QVariant.Int))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT_PARCELS,
            context,
            fields,
            QgsWkbTypes.Polygon,
            target_crs  # Use EPSG:4326 for output
        )

        if sink is None:
            raise QgsProcessingException(
                self.invalidSinkError(parameters, self.OUTPUT_PARCELS)
            )

        # Prepare API headers with both RapidAPI key and Authorization token
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "enriched-cadastral-parcels-for-italy.p.rapidapi.com",
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(auth_token),
            "User-Agent": "Zornade-QGIS-Plugin/1.0.0"
        }

        try:
            # Step 1: Get parcel FIDs using bounding box only
            get_parcels_url = "{}/get-parcels".format(self.API_BASE_URL)
            
            parcels_payload = {
                "queryType": "bbox",
                "params": [
                    bbox_extent_4326.xMinimum(),
                    bbox_extent_4326.yMinimum(),
                    bbox_extent_4326.xMaximum(),
                    bbox_extent_4326.yMaximum()
                ]
            }
            
            feedback.pushInfo(self.tr("Requesting parcels within bounding box..."))
            feedback.pushInfo(self.tr("Bounding box: [{:.6f}, {:.6f}, {:.6f}, {:.6f}]".format(
                bbox_extent_4326.xMinimum(), bbox_extent_4326.yMinimum(),
                bbox_extent_4326.xMaximum(), bbox_extent_4326.yMaximum()
            )))
            
            parcels_response = requests.post(get_parcels_url, headers=headers, json=parcels_payload, timeout=30)
            
            if parcels_response.status_code == 401:
                raise QgsProcessingException(
                    self.tr("Authentication failed. Please check your RapidAPI key and authorization token. "
                           "Ensure you have an active subscription to the service.")
                )
            elif parcels_response.status_code == 403:
                raise QgsProcessingException(
                    self.tr("Access forbidden. Please verify your subscription is active and you have "
                           "permission to access this API endpoint.")
                )
            elif parcels_response.status_code == 429:
                raise QgsProcessingException(
                    self.tr("Rate limit exceeded. Please wait a moment and try again with a smaller area.")
                )
            elif parcels_response.status_code != 200:
                response_text = parcels_response.text[:500]  # Limit error message length
                raise QgsProcessingException(
                    self.tr("API request failed with status {}: {}".format(
                        parcels_response.status_code, response_text
                    ))
                )
            
            try:
                parcels_data = parcels_response.json()
            except ValueError as e:
                raise QgsProcessingException(
                    self.tr("Invalid JSON response from API. Please try again later.")
                )
            
            # Handle the correct API response format
            if parcels_data.get("success") and "data" in parcels_data:
                parcel_fids = parcels_data["data"]
                total_found = len(parcel_fids)
                feedback.pushInfo(self.tr("Found {} parcels in the specified area".format(total_found)))
                
                # Warn for large datasets
                if total_found > 1000:
                    feedback.pushWarning(self.tr(
                        "Large number of parcels found ({}). Processing may take several minutes. "
                        "Consider using a smaller bounding box for faster results."
                    ).format(total_found))
                elif total_found > 100:
                    feedback.pushInfo(self.tr(
                        "Processing {} parcels. This may take a few minutes."
                    ).format(total_found))
            else:
                error_msg = parcels_data.get("message", "Unknown error")
                error_details = parcels_data.get("details", "")
                if error_details:
                    error_msg += f" Details: {error_details}"
                raise QgsProcessingException(
                    self.tr("API error: {}".format(error_msg))
                )
            
            if not parcel_fids:
                feedback.pushInfo(self.tr("No parcels found in the specified bounding box. "
                                        "Try expanding the search area or verify the coordinates are within Italy."))
                return {self.OUTPUT_PARCELS: dest_id}

            # Step 2: Get detailed information for each parcel (batch processing)
            get_info_url = "{}/get-parcel-info".format(self.API_BASE_URL)
            
            feedback.setProgress(0)
            processed_count = 0
            error_count = 0
            max_errors = min(50, len(parcel_fids) // 10)  # Allow up to 10% errors or 50 max
            
            # Adaptive batch size based on total count
            if total_found <= 50:
                batch_size = 10
            elif total_found <= 200:
                batch_size = 20
            else:
                batch_size = 25  # Conservative for large datasets
            
            feedback.pushInfo(self.tr("Processing {} parcels in batches of {}".format(total_found, batch_size)))
            
            def download_parcel_info(fid_batch_info):
                """Download info for a single parcel. Returns (fid, success, feature_data_or_error)"""
                fid, batch_index, total_in_batch = fid_batch_info
                
                try:
                    info_payload = {"fid": str(fid)}
                    info_response = requests.post(get_info_url, headers=headers, json=info_payload, timeout=20)
                    
                    if info_response.status_code == 200:
                        try:
                            info_data = info_response.json()
                            if info_data.get("success") and "data" in info_data:
                                return (fid, True, info_data["data"])
                            else:
                                return (fid, False, f"Invalid response format")
                        except ValueError:
                            return (fid, False, f"Invalid JSON response")
                    elif info_response.status_code == 404:
                        return (fid, False, f"Parcel not found")
                    elif info_response.status_code == 429:
                        return (fid, False, f"Rate limited")
                    else:
                        return (fid, False, f"HTTP {info_response.status_code}")
                        
                except requests.exceptions.Timeout:
                    return (fid, False, f"Request timeout")
                except requests.exceptions.ConnectionError:
                    return (fid, False, f"Connection error")
                except Exception as e:
                    return (fid, False, f"Exception: {str(e)[:100]}")
            
            # Process parcels in batches
            total_parcels = len(parcel_fids)
            
            for batch_start in range(0, total_parcels, batch_size):
                if feedback.isCanceled():
                    feedback.pushInfo(self.tr("Processing cancelled by user"))
                    break
                
                # Check error threshold
                if error_count > max_errors:
                    feedback.reportError(self.tr(
                        "Too many errors encountered ({}). Stopping processing. "
                        "Please check your connection and API credentials."
                    ).format(error_count), fatalError=True)
                    break
                
                batch_end = min(batch_start + batch_size, total_parcels)
                current_batch = parcel_fids[batch_start:batch_end]
                batch_num = (batch_start // batch_size) + 1
                total_batches = (total_parcels + batch_size - 1) // batch_size
                
                feedback.pushInfo(self.tr("Processing batch {}/{} ({} parcels)".format(
                    batch_num, total_batches, len(current_batch)
                )))
                
                # Prepare batch with additional info for progress tracking
                batch_with_info = [(fid, i, len(current_batch)) for i, fid in enumerate(current_batch)]
                
                # Download batch concurrently with controlled thread pool
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(batch_size, 15)) as executor:
                    future_to_fid = {
                        executor.submit(download_parcel_info, fid_info): fid_info[0] 
                        for fid_info in batch_with_info
                    }
                    
                    batch_results = []
                    for future in concurrent.futures.as_completed(future_to_fid):
                        if feedback.isCanceled():
                            # Cancel remaining futures
                            for f in future_to_fid:
                                f.cancel()
                            break
                            
                        try:
                            result = future.result(timeout=25)  # Timeout for individual results
                            batch_results.append(result)
                        except concurrent.futures.TimeoutError:
                            fid = future_to_fid[future]
                            batch_results.append((fid, False, "Processing timeout"))
                        except Exception as e:
                            fid = future_to_fid[future]
                            batch_results.append((fid, False, f"Future error: {str(e)[:100]}"))
                
                # Process results from this batch
                batch_processed = 0
                batch_errors = 0
                
                for fid, success, data_or_error in batch_results:
                    if feedback.isCanceled():
                        break
                    
                    if success:
                        parcel_info = data_or_error
                        
                        try:
                            # Create QGIS feature
                            feat = QgsFeature(fields)
                            
                            # Set attributes with safe type conversion
                            feat["fid"] = str(fid)
                            feat["gml_id"] = str(parcel_info.get("gml_id", ""))
                            feat["administrativeunit"] = str(parcel_info.get("administrativeunit", ""))
                            feat["comune_name"] = str(parcel_info.get("comune_name", ""))
                            
                            # Safely convert numeric fields
                            feat["footprint_sqm"] = float(parcel_info.get("footprint_sqm", 0.0)) if parcel_info.get("footprint_sqm") is not None else 0.0
                            feat["elevation_min"] = float(parcel_info.get("elevation_min", 0.0)) if parcel_info.get("elevation_min") is not None else 0.0
                            feat["elevation_max"] = float(parcel_info.get("elevation_max", 0.0)) if parcel_info.get("elevation_max") is not None else 0.0
                            feat["densita_abitativa"] = float(parcel_info.get("densita_abitativa", 0.0)) if parcel_info.get("densita_abitativa") is not None else 0.0
                            feat["eta_media"] = float(parcel_info.get("eta_media", 0.0)) if parcel_info.get("eta_media") is not None else 0.0
                            feat["tasso_occupazione"] = float(parcel_info.get("tasso_occupazione", 0.0)) if parcel_info.get("tasso_occupazione") is not None else 0.0
                            feat["buildings_count"] = int(parcel_info.get("buildings_count", 0)) if parcel_info.get("buildings_count") is not None else 0
                            
                            feat["class"] = str(parcel_info.get("class", ""))
                            feat["subtype"] = str(parcel_info.get("subtype", ""))
                            feat["landcover"] = str(parcel_info.get("landcover", ""))
                            feat["flood_risk"] = str(parcel_info.get("flood_risk", ""))
                            feat["landslide_risk"] = str(parcel_info.get("landslide_risk", ""))
                            feat["seismic_risk"] = str(parcel_info.get("seismic_risk", ""))
                            
                            # Handle geometry processing with improved error handling
                            geometry_processed = False
                            if "geom" in parcel_info and parcel_info["geom"]:
                                geom_data = parcel_info["geom"]
                                try:
                                    if isinstance(geom_data, dict) and geom_data.get("type") in ["Polygon", "MultiPolygon"]:
                                        # Handle GeoJSON format - convert to WKT
                                        coordinates = geom_data.get("coordinates", [])
                                        if coordinates:
                                            if geom_data.get("type") == "MultiPolygon":
                                                polygons = []
                                                for polygon in coordinates:
                                                    rings = []
                                                    for ring in polygon:
                                                        if len(ring) >= 4:  # Valid ring needs at least 4 points
                                                            ring_coords = ", ".join([f"{coord[0]} {coord[1]}" for coord in ring])
                                                            rings.append(f"({ring_coords})")
                                                    if rings:
                                                        polygons.append(f"({', '.join(rings)})")
                                                if polygons:
                                                    wkt = f"MULTIPOLYGON({', '.join(polygons)})"
                                                    qgis_geom = QgsGeometry.fromWkt(wkt)
                                            else:  # Polygon
                                                rings = []
                                                for ring in coordinates:
                                                    if len(ring) >= 4:
                                                        ring_coords = ", ".join([f"{coord[0]} {coord[1]}" for coord in ring])
                                                        rings.append(f"({ring_coords})")
                                                if rings:
                                                    wkt = f"POLYGON({', '.join(rings)})"
                                                    qgis_geom = QgsGeometry.fromWkt(wkt)
                                            
                                            if 'qgis_geom' in locals() and not qgis_geom.isEmpty() and qgis_geom.isGeosValid():
                                                feat.setGeometry(qgis_geom)
                                                geometry_processed = True
                                                if processed_count == 0:
                                                    feedback.pushInfo(self.tr("Successfully parsing GeoJSON geometries"))
                                    
                                    elif isinstance(geom_data, str):
                                        # Handle WKB hex string
                                        if len(geom_data) > 20 and all(c in '0123456789ABCDEFabcdef' for c in geom_data):
                                            wkb_bytes = bytes.fromhex(geom_data)
                                            qgis_geom = QgsGeometry()
                                            qgis_geom.fromWkb(wkb_bytes)
                                            
                                            if not qgis_geom.isEmpty() and qgis_geom.isGeosValid():
                                                feat.setGeometry(qgis_geom)
                                                geometry_processed = True
                                        else:
                                            # Try as WKT format
                                            qgis_geom = QgsGeometry.fromWkt(geom_data)
                                            if not qgis_geom.isEmpty():
                                                feat.setGeometry(qgis_geom)
                                                geometry_processed = True
                                    
                                    if not geometry_processed:
                                        error_count += 1
                                        batch_errors += 1
                                        if batch_errors <= 3:  # Only log first few errors per batch
                                            feedback.pushWarning(self.tr("Could not process geometry for parcel FID {}".format(fid)))
                                        continue
                                        
                                except Exception as e:
                                    error_count += 1
                                    batch_errors += 1
                                    if batch_errors <= 3:
                                        feedback.pushWarning(self.tr("Geometry error for parcel FID {}: {}".format(fid, str(e)[:100])))
                                    continue
                            else:
                                error_count += 1
                                batch_errors += 1
                                if batch_errors <= 3:
                                    feedback.pushWarning(self.tr("No geometry data for parcel FID {}".format(fid)))
                                continue

                            # Add feature to output
                            sink.addFeature(feat, QgsFeatureSink.Flag.FastInsert)
                            processed_count += 1
                            batch_processed += 1
                            
                        except Exception as e:
                            error_count += 1
                            batch_errors += 1
                            if batch_errors <= 3:
                                feedback.pushWarning(self.tr("Error creating feature for FID {}: {}".format(fid, str(e)[:100])))
                        
                    else:
                        error_count += 1
                        batch_errors += 1
                        if batch_errors <= 3:
                            feedback.pushWarning(self.tr("Failed to get info for parcel FID {}: {}".format(fid, data_or_error)))
                
                # Update progress after each batch
                progress = int((batch_end) / total_parcels * 100)
                feedback.setProgress(progress)
                
                feedback.pushInfo(self.tr("Batch {}/{} completed: {} processed, {} errors. Total: {} parcels".format(
                    batch_num, total_batches, batch_processed, batch_errors, processed_count
                )))
                
                # Add small delay between batches to be respectful to API
                if batch_num < total_batches and not feedback.isCanceled():
                    import time
                    time.sleep(0.5)
            
            # Final summary
            feedback.pushInfo(self.tr("Processing completed! Successfully processed {} out of {} parcels".format(
                processed_count, total_parcels
            )))
            
            if error_count > 0:
                feedback.pushWarning(self.tr("Encountered {} errors during processing. Check the log for details.".format(error_count)))
            
            if processed_count == 0:
                feedback.pushWarning(self.tr("No parcels were successfully processed. Please check your API credentials and try a different area."))
            
        except requests.exceptions.ConnectionError:
            feedback.reportError(self.tr("Network connection error. Please check your internet connection and try again."), fatalError=True)
            return {}
        except requests.exceptions.Timeout:
            feedback.reportError(self.tr("Request timeout. The API may be slow or unavailable. Try again later or use a smaller area."), fatalError=True)
            return {}
        except requests.exceptions.RequestException as e:
            feedback.reportError(self.tr("Network error: {}".format(str(e))), fatalError=True)
            return {}
        except Exception as e:
            feedback.reportError(self.tr("Unexpected error: {}. Please report this issue.".format(str(e))), fatalError=True)
            return {}

        # Store the result for styling
        result = {self.OUTPUT_PARCELS: dest_id}
        
        # Apply styling and labels if we processed any parcels
        if processed_count > 0:
            try:
                self._apply_beautiful_styling(dest_id, context, feedback)
            except Exception as e:
                feedback.pushWarning(self.tr("Could not apply styling: {}".format(str(e))))

        return result

    def _apply_beautiful_styling(self, layer_id: str, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        """Apply beautiful symbology and labels to the parcel layer."""
        
        # Get the layer from the context
        layer = context.getMapLayer(layer_id)
        if not layer or not isinstance(layer, QgsVectorLayer):
            feedback.pushWarning(self.tr("Could not access layer for styling"))
            return
        
        feedback.pushInfo(self.tr("Applying beautiful symbology and labels..."))
        
        # Create land use based categorized renderer
        self._create_land_use_renderer(layer, feedback)
        
        # Apply labels
        self._apply_parcel_labels(layer, feedback)
        
        # Set layer properties
        layer.setOpacity(0.8)  # Slight transparency
        
        feedback.pushInfo(self.tr("Styling applied successfully!"))

    def _create_land_use_renderer(self, layer: QgsVectorLayer, feedback: QgsProcessingFeedback):
        """Create a categorized renderer based on land use classification."""
        
        # Define color scheme for different land use types
        land_use_colors = {
            # Residential
            'residential': QColor(255, 230, 153),  # Light yellow
            'housing': QColor(255, 204, 128),      # Light orange
            'urban': QColor(255, 179, 102),        # Orange
            
            # Commercial/Industrial
            'commercial': QColor(204, 153, 255),   # Light purple
            'industrial': QColor(153, 102, 204),   # Purple
            'business': QColor(128, 77, 179),      # Dark purple
            
            # Agricultural
            'agricultural': QColor(153, 255, 153), # Light green
            'farmland': QColor(102, 204, 102),     # Green
            'crops': QColor(76, 153, 76),          # Dark green
            
            # Natural/Forest
            'forest': QColor(0, 128, 0),           # Dark green
            'woodland': QColor(34, 139, 34),       # Forest green
            'natural': QColor(107, 142, 35),       # Olive
            
            # Water
            'water': QColor(173, 216, 230),        # Light blue
            'wetland': QColor(135, 206, 235),      # Sky blue
            
            # Infrastructure
            'transport': QColor(128, 128, 128),    # Gray
            'infrastructure': QColor(105, 105, 105), # Dim gray
            'utilities': QColor(169, 169, 169),    # Dark gray
            
            # Special/Other
            'recreational': QColor(255, 182, 193), # Light pink
            'public': QColor(255, 160, 122),       # Light salmon
            'cemetery': QColor(139, 69, 19),       # Saddle brown
            'unknown': QColor(211, 211, 211),      # Light gray
            'other': QColor(192, 192, 192)         # Silver
        }
        
        # Risk assessment overlay colors (for stroke)
        risk_stroke_colors = {
            'high': QColor(255, 0, 0),      # Red
            'medium': QColor(255, 165, 0),  # Orange  
            'low': QColor(0, 255, 0),       # Green
            'none': QColor(128, 128, 128),  # Gray
            'unknown': QColor(64, 64, 64)   # Dark gray
        }
        
        categories = []
        
        # Get unique land use values from the layer
        unique_classes = set()
        for feature in layer.getFeatures():
            land_class = str(feature['class']).lower().strip()
            if land_class:
                unique_classes.add(land_class)
        
        feedback.pushInfo(self.tr("Found {} unique land use classes".format(len(unique_classes))))
        
        # Create categories for each land use type
        for land_class in sorted(unique_classes):
            if not land_class or land_class == 'null':
                continue
                
            # Determine color based on land use keywords
            fill_color = land_use_colors.get('other')  # Default
            
            # Match land use to color scheme
            for keyword, color in land_use_colors.items():
                if keyword in land_class:
                    fill_color = color
                    break
            
            # Create symbol with semi-transparent fill and contrasting stroke
            symbol = QgsFillSymbol.createSimple({
                'color': fill_color.name(),
                'color_border': QColor(64, 64, 64).name(),  # Dark gray border
                'style': 'solid',
                'style_border': 'solid',
                'width_border': '0.3',
                'opacity': '0.7'
            })
            
            # Create category
            category = QgsRendererCategory(
                land_class,
                symbol,
                self._format_class_label(land_class)
            )
            categories.append(category)
        
        # Create "No Data" category
        no_data_symbol = QgsFillSymbol.createSimple({
            'color': QColor(211, 211, 211).name(),  # Light gray
            'color_border': QColor(128, 128, 128).name(),
            'style': 'dense6',  # Hatched pattern
            'style_border': 'solid',
            'width_border': '0.2',
            'opacity': '0.5'
        })
        
        no_data_category = QgsRendererCategory(
            '',  # Empty value
            no_data_symbol,
            'No Classification Data'
        )
        categories.append(no_data_category)
        
        # Create and apply the renderer
        renderer = QgsCategorizedSymbolRenderer('class', categories)
        layer.setRenderer(renderer)
        
        feedback.pushInfo(self.tr("Applied categorized symbology with {} categories".format(len(categories))))

    def _format_class_label(self, class_name: str) -> str:
        """Format class name for display in legend."""
        # Capitalize first letter of each word and replace underscores
        formatted = class_name.replace('_', ' ').title()
        return formatted

    def _apply_parcel_labels(self, layer: QgsVectorLayer, feedback: QgsProcessingFeedback):
        """Apply informative labels to parcels."""
        
        # Create label settings
        label_settings = QgsPalLayerSettings()
        
        # Set label expression - show FID and land use class
        label_settings.fieldName = '''
        CASE 
            WHEN "class" IS NOT NULL AND "class" != '' THEN
                "fid" || '\n' || "class"
            ELSE
                "fid"
        END
        '''
        label_settings.isExpression = True
        
        # Text formatting
        text_format = QgsTextFormat()
        text_format.setFont(layer.labelsFont())
        text_format.setSize(8)
        text_format.setColor(QColor(0, 0, 0))  # Black text
        
        # Add text buffer (halo effect)
        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.setSize(1)
        buffer_settings.setColor(QColor(255, 255, 255, 200))  # Semi-transparent white
        text_format.setBuffer(buffer_settings)
        
        label_settings.setFormat(text_format)
        
        # Label placement
        label_settings.placement = QgsPalLayerSettings.AroundPoint
        label_settings.centroidWhole = True
        label_settings.centroidInside = True
        
        # Only show labels at certain scale ranges (avoid clutter)
        label_settings.scaleVisibility = True
        label_settings.minimumScale = 500    # Show when zoomed in closer than 1:500
        label_settings.maximumScale = 50000  # Hide when zoomed out beyond 1:50,000
        
        # Priority and obstacles
        label_settings.priority = 5
        label_settings.obstacle = True
        label_settings.obstacleFactor = 0.5
        
        # Apply labeling
        labeling = QgsVectorLayerSimpleLabeling(label_settings)
        layer.setLabeling(labeling)
        layer.setLabelsEnabled(True)
        
        feedback.pushInfo(self.tr("Applied intelligent parcel labels (visible at scales 1:500 to 1:50,000)"))

    def postProcessAlgorithm(self, context: QgsProcessingContext, feedback: QgsProcessingFeedback) -> dict[str, Any]:
        """
        Actions to be performed after the algorithm has finished.
        """
        return super().postProcessAlgorithm(context, feedback)