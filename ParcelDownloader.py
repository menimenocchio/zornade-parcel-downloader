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
    QgsRectangle
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
                       "https://rapidapi.com/ageratlas/api/enriched-cadastral-parcels-for-italy to get one.")
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

        # Define output fields based on AgerAtlas API response
        fields = QgsFields()
        # Use QVariant types: 10=String, 6=Double, 2=Int
        from qgis.PyQt.QtCore import QVariant
        
        fields.append(QgsField("fid", QVariant.String))  # String
        fields.append(QgsField("gml_id", QVariant.String))  # String
        fields.append(QgsField("administrativeunit", QVariant.String))  # String
        fields.append(QgsField("comune_name", QVariant.String))  # String
        fields.append(QgsField("footprint_sqm", QVariant.Double))  # Double
        fields.append(QgsField("elevation_min", QVariant.Double))  # Double
        fields.append(QgsField("elevation_max", QVariant.Double))  # Double
        fields.append(QgsField("class", QVariant.String))  # String
        fields.append(QgsField("subtype", QVariant.String))  # String
        fields.append(QgsField("landcover", QVariant.String))  # String
        fields.append(QgsField("densita_abitativa", QVariant.Double))  # Double
        fields.append(QgsField("eta_media", QVariant.Double))  # Double
        fields.append(QgsField("tasso_occupazione", QVariant.Double))  # Double
        fields.append(QgsField("flood_risk", QVariant.String))  # String
        fields.append(QgsField("landslide_risk", QVariant.String))  # String
        fields.append(QgsField("seismic_risk", QVariant.String))  # String
        fields.append(QgsField("buildings_count", QVariant.Int))  # Integer

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT_PARCELS,
            context,
            fields,
            QgsWkbTypes.Polygon,
            QgsProject.instance().crs()
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
            "Authorization": "Bearer {}".format(auth_token)
        }

        try:
            # Step 1: Get parcel FIDs using bounding box only
            get_parcels_url = "{}/get-parcels".format(self.API_BASE_URL)
            
            # Use bbox query with correct format for the edge function
            # Edge function expects: queryType: "bbox", params: [minX, minY, maxX, maxY]
            parcels_payload = {
                "queryType": "bbox",
                "params": [
                    bbox_extent_4326.xMinimum(),  # min_x
                    bbox_extent_4326.yMinimum(),  # min_y  
                    bbox_extent_4326.xMaximum(),  # max_x
                    bbox_extent_4326.yMaximum()   # max_y
                ]
            }
            
            feedback.pushInfo(self.tr("Request payload: {}".format(str(parcels_payload))))
            feedback.pushInfo(self.tr("Requesting parcel FIDs using bbox query..."))
            parcels_response = requests.post(get_parcels_url, headers=headers, json=parcels_payload, timeout=30)
            
            feedback.pushInfo(self.tr("Response status: {}".format(parcels_response.status_code)))
            
            if parcels_response.status_code != 200:
                # Log the full error response
                response_text = parcels_response.text
                feedback.pushInfo(self.tr("Bbox query failed with status {}: {}".format(parcels_response.status_code, response_text)))
                
                raise QgsProcessingException(
                    self.tr("Bbox query failed: {} - {}. Please check that the bbox query function is available in the database.".format(
                        parcels_response.status_code, response_text
                    ))
                )
            
            parcels_data = parcels_response.json()
            feedback.pushInfo(self.tr("API Response: {}".format(str(parcels_data))))
            
            # Handle the correct API response format: {"success":true,"data":[...],"meta":{...}}
            if parcels_data.get("success") and "data" in parcels_data:
                parcel_fids = parcels_data["data"]
                total_found = len(parcel_fids)
                feedback.pushInfo(self.tr("Bbox query successful: found {} parcels".format(total_found)))
            else:
                # Log the actual response for debugging
                feedback.pushInfo(self.tr("Unexpected API response: {}".format(str(parcels_data))))
                
                # Check if it's an error response with details
                if not parcels_data.get("success"):
                    error_msg = parcels_data.get("message", "Unknown error")
                    error_details = parcels_data.get("details", "")
                    feedback.pushInfo(self.tr("API Error: {} - {}".format(error_msg, error_details)))
                
                raise QgsProcessingException(
                    self.tr("Bbox query failed or returned unexpected format. Error: {}".format(
                        parcels_data.get("message", "Unknown error")
                    ))
                )
            
            if not parcel_fids:
                feedback.pushWarning(self.tr("No parcels found in the specified bounding box"))
                return {self.OUTPUT_PARCELS: dest_id}

            # Step 2: Get detailed information for each parcel (batch processing)
            get_info_url = "{}/get-parcel-info".format(self.API_BASE_URL)
            
            feedback.setProgress(0)
            processed_count = 0
            batch_size = 50  # Download 50 parcels concurrently
            
            # Create a thread-safe lock for updating progress
            progress_lock = threading.Lock()
            
            def download_parcel_info(fid_batch_info):
                """Download info for a single parcel. Returns (fid, success, feature_data_or_error)"""
                fid, batch_index, total_in_batch = fid_batch_info
                
                try:
                    info_payload = {"fid": str(fid)}
                    info_response = requests.post(get_info_url, headers=headers, json=info_payload, timeout=15)
                    
                    if info_response.status_code == 200:
                        info_data = info_response.json()
                        
                        # Handle the get-parcel-info response format
                        if info_data.get("success") and "data" in info_data:
                            return (fid, True, info_data["data"])
                        else:
                            return (fid, False, f"Invalid response: {str(info_data)}")
                    else:
                        return (fid, False, f"HTTP {info_response.status_code}: {info_response.text}")
                        
                except Exception as e:
                    return (fid, False, f"Exception: {str(e)}")
            
            # Process parcels in batches
            total_parcels = len(parcel_fids)
            
            for batch_start in range(0, total_parcels, batch_size):
                if feedback.isCanceled():
                    break
                
                batch_end = min(batch_start + batch_size, total_parcels)
                current_batch = parcel_fids[batch_start:batch_end]
                batch_num = (batch_start // batch_size) + 1
                total_batches = (total_parcels + batch_size - 1) // batch_size
                
                feedback.pushInfo(self.tr("Processing batch {}/{}: {} parcels (FIDs: {})".format(
                    batch_num, total_batches, len(current_batch), ", ".join(map(str, current_batch))
                )))
                
                # Prepare batch with additional info for progress tracking
                batch_with_info = [(fid, i, len(current_batch)) for i, fid in enumerate(current_batch)]
                
                # Download batch concurrently
                with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
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
                            result = future.result()
                            batch_results.append(result)
                        except Exception as e:
                            fid = future_to_fid[future]
                            batch_results.append((fid, False, f"Future exception: {str(e)}"))
                
                # Process results from this batch
                for fid, success, data_or_error in batch_results:
                    if feedback.isCanceled():
                        break
                    
                    if success:
                        parcel_info = data_or_error
                        
                        # Create QGIS feature
                        feat = QgsFeature(fields)
                        
                        # Set attributes from API response
                        feat["fid"] = str(fid)
                        feat["gml_id"] = parcel_info.get("gml_id", "")
                        feat["administrativeunit"] = parcel_info.get("administrativeunit", "")
                        feat["comune_name"] = parcel_info.get("comune_name", "")
                        feat["footprint_sqm"] = parcel_info.get("footprint_sqm", 0.0)
                        feat["elevation_min"] = parcel_info.get("elevation_min", 0.0)
                        feat["elevation_max"] = parcel_info.get("elevation_max", 0.0)
                        feat["class"] = parcel_info.get("class", "")
                        feat["subtype"] = parcel_info.get("subtype", "")
                        feat["landcover"] = parcel_info.get("landcover", "")
                        feat["densita_abitativa"] = parcel_info.get("densita_abitativa", 0.0)
                        feat["eta_media"] = parcel_info.get("eta_media", 0.0)
                        feat["tasso_occupazione"] = parcel_info.get("tasso_occupazione", 0.0)
                        feat["flood_risk"] = parcel_info.get("flood_risk", "")
                        feat["landslide_risk"] = parcel_info.get("landslide_risk", "")
                        feat["seismic_risk"] = parcel_info.get("seismic_risk", "")
                        feat["buildings_count"] = parcel_info.get("buildings_count", 0)
                        
                        # Handle geometry if provided
                        geometry_processed = False
                        if "geom" in parcel_info and parcel_info["geom"]:
                            geom_data = parcel_info["geom"]
                            try:
                                if isinstance(geom_data, dict):
                                    # Handle GeoJSON format - convert to WKT first
                                    if geom_data.get("type") == "MultiPolygon":
                                        coordinates = geom_data.get("coordinates", [])
                                        if coordinates:
                                            polygons = []
                                            for polygon in coordinates:
                                                rings = []
                                                for ring in polygon:
                                                    ring_coords = ", ".join([f"{coord[0]} {coord[1]}" for coord in ring])
                                                    rings.append(f"({ring_coords})")
                                                polygons.append(f"({', '.join(rings)})")
                                            wkt = f"MULTIPOLYGON({', '.join(polygons)})"
                                            qgis_geom = QgsGeometry.fromWkt(wkt)
                                    elif geom_data.get("type") == "Polygon":
                                        coordinates = geom_data.get("coordinates", [])
                                        if coordinates:
                                            rings = []
                                            for ring in coordinates:
                                                ring_coords = ", ".join([f"{coord[0]} {coord[1]}" for coord in ring])
                                                rings.append(f"({ring_coords})")
                                            wkt = f"POLYGON({', '.join(rings)})"
                                            qgis_geom = QgsGeometry.fromWkt(wkt)
                                    else:
                                        feedback.pushWarning(self.tr("Unsupported geometry type for parcel FID {}: {}".format(fid, geom_data.get("type"))))
                                        continue
                                    
                                    if not qgis_geom.isEmpty() and qgis_geom.isGeosValid():
                                        feat.setGeometry(qgis_geom)
                                        geometry_processed = True
                                        if processed_count == 0:  # Log success for first geometry
                                            feedback.pushInfo(self.tr("Successfully parsed GeoJSON geometry as WKT"))
                                elif isinstance(geom_data, str):
                                    # Handle different string formats
                                    if len(geom_data) > 20 and all(c in '0123456789ABCDEFabcdef' for c in geom_data):
                                        # WKB hex string from PostGIS
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
                                    feedback.pushWarning(self.tr("Could not process geometry for parcel FID {}".format(fid)))
                                    continue
                                    
                            except Exception as e:
                                feedback.pushWarning(self.tr("Error processing geometry for parcel FID {}: {}".format(fid, str(e))))
                                continue
                        else:
                            feedback.pushWarning(self.tr("No geometry data for parcel FID {} - skipping".format(fid)))
                            continue

                        sink.addFeature(feat, QgsFeatureSink.Flag.FastInsert)
                        processed_count += 1
                        
                    else:
                        feedback.pushWarning(self.tr("Failed to get info for parcel FID {}: {}".format(fid, data_or_error)))
                
                # Update progress after each batch
                progress = int((batch_end) / total_parcels * 100)
                feedback.setProgress(progress)
                
                feedback.pushInfo(self.tr("Batch {}/{} completed. Successfully processed: {} parcels total".format(
                    batch_num, total_batches, processed_count
                )))
            
            feedback.pushInfo(self.tr("All batches completed. Successfully processed {} out of {} parcels".format(
                processed_count, total_parcels
            )))
            
        except requests.exceptions.RequestException as e:
            feedback.reportError(self.tr("Network error: {}".format(str(e))), fatalError=True)
            return {}
        except Exception as e:
            feedback.reportError(self.tr("Error fetching data: {}".format(str(e))), fatalError=True)
            return {}

        return {self.OUTPUT_PARCELS: dest_id}

    def _process_parcels_data(self, parcels_data, sink, fields, feedback):
        """Process API response and add features to sink."""
        # Implementation will depend on actual API response format
        pass

    def postProcessAlgorithm(self, context: QgsProcessingContext, feedback: QgsProcessingFeedback) -> dict[str, Any]:
        """
        Actions to be performed after the algorithm has finished.
        """
        return super().postProcessAlgorithm(context, feedback)