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
from .rapidapi_auth import RapidAPIAuthenticator, SmartAuthDialog


class ParcelDownloaderAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm fetches enriched Italian cadastral parcel data from 
    Zornade's comprehensive dataset via RapidAPI service and loads it into QGIS.
    """

    # --- Parameter definition ---
    # Input parameters (credentials removed - handled by credential manager)
    BBOX = "BBOX"

    # Output parameters
    OUTPUT_PARCELS = "OUTPUT_PARCELS"

    # --- API Configuration ---
    API_BASE_URL = "https://enriched-cadastral-parcels-for-italy.p.rapidapi.com/functions/v1"

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
            "Downloads enriched Italian cadastral parcel data from Zornade's comprehensive dataset via RapidAPI.\n\n"
            "This algorithm provides access to detailed cadastral information including geometries, administrative data, "
            "risk assessments (flood, landslide, seismic), land cover classification, demographic statistics, and elevation data.\n\n"
            "Setup:\n"
            "• Use 'Manage API Credentials' from the plugin menu to configure your RapidAPI access\n"
            "• Visit https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy\n"
            "• Subscribe to Zornade's Italian Cadastral Parcels service\n"
            "• Enter your credentials using the credential manager\n\n"
            "Usage:\n"
            "• Define a bounding box covering your area of interest in Italy\n"
            "• The algorithm will automatically use your saved credentials\n"
            "• Download parcels in batches with automatic coordinate transformation\n\n"
            "Output:\n"
            "A polygon layer with 57 enriched attributes including risk assessments, demographics, and land use data."
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
        # Check credential status for UI feedback
        authenticator = RapidAPIAuthenticator()
        saved_creds = authenticator.get_saved_credentials()
        
        if saved_creds:
            masked_key = f"{saved_creds['rapidapi_key'][:8]}...{saved_creds['rapidapi_key'][-4:]}"
            credential_status = f"Using saved credentials: {masked_key}"
        else:
            credential_status = "No credentials configured - use 'Manage API Credentials' from plugin menu"

        # Add informational parameter showing credential status
        self.addParameter(
            QgsProcessingParameterString(
                "CREDENTIAL_INFO",
                self.tr(f"Credential Status: {credential_status}"),
                defaultValue="",
                optional=True,
                multiLine=False
            )
        )

        # --- Bounding Box ---
        self.addParameter(
            QgsProcessingParameterExtent(
                self.BBOX,
                self.tr("Bounding Box (area of interest in Italy)"),
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
        # Check if credentials are available
        authenticator = RapidAPIAuthenticator()
        saved_creds = authenticator.get_saved_credentials()
        
        if not saved_creds:
            raise QgsProcessingException(
                self.tr("No API credentials found.\n\n"
                       "Please configure your credentials first:\n"
                       "1. Go to the plugin menu and select 'Manage API Credentials'\n"
                       "2. Enter your RapidAPI key and bearer token\n"
                       "3. Test and save your credentials\n"
                       "4. Run this algorithm again\n\n"
                       "Need credentials? Visit: https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy")
            )

        # Validate bounding box
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
        # Get credentials from credential manager
        feedback.pushInfo(self.tr("🔧 Loading saved credentials..."))
        
        authenticator = RapidAPIAuthenticator()
        saved_creds = authenticator.get_saved_credentials()
        
        if not saved_creds:
            # This should not happen due to checkParameterValues, but just in case
            raise QgsProcessingException(
                self.tr("No credentials available. Please use 'Manage API Credentials' from the plugin menu.")
            )
        
        api_key = saved_creds['rapidapi_key']
        auth_token = saved_creds['bearer_token']
        
        feedback.pushInfo(self.tr("✅ Using saved credentials"))
        if saved_creds.get('subscription_plan'):
            feedback.pushInfo(self.tr("📋 Subscription: {}".format(saved_creds['subscription_plan'])))
        
        # Warn if credentials had issues previously
        if not saved_creds.get('is_working', True):
            feedback.pushWarning(self.tr("⚠️ Previously detected issues with credentials. They will be retested during processing."))

        # Clean up auth token - remove "Bearer " prefix if present
        if auth_token.lower().startswith('bearer '):
            auth_token = auth_token[7:]

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

        # Define output fields
        fields = QgsFields()
        from qgis.PyQt.QtCore import QVariant
        
        # Core identification fields
        fields.append(QgsField("fid", QVariant.String))
        fields.append(QgsField("gml_id", QVariant.String))
        fields.append(QgsField("label", QVariant.String))
        
        # Administrative and geographic data
        fields.append(QgsField("administrativeunit", QVariant.String))
        fields.append(QgsField("municipality_name", QVariant.String))
        fields.append(QgsField("region_name", QVariant.String))
        fields.append(QgsField("province_name", QVariant.String))
        fields.append(QgsField("province_code", QVariant.String))
        fields.append(QgsField("postal_code", QVariant.String))
        
        # Physical characteristics
        fields.append(QgsField("footprint_sqm", QVariant.Double))
        fields.append(QgsField("elevation_min", QVariant.Double))
        fields.append(QgsField("elevation_max", QVariant.Double))
        fields.append(QgsField("ruggedness_index", QVariant.Double))
        fields.append(QgsField("number_of_points", QVariant.Int))
        
        # Land use and classification
        fields.append(QgsField("class", QVariant.String))
        fields.append(QgsField("subtype", QVariant.String))
        fields.append(QgsField("landcover", QVariant.String))
        fields.append(QgsField("buildings_count", QVariant.Int))
        
        # Census and demographics
        fields.append(QgsField("census_section_id", QVariant.String))
        fields.append(QgsField("section_type_code", QVariant.String))
        fields.append(QgsField("estimated_population", QVariant.Int))
        fields.append(QgsField("average_age", QVariant.Double))
        fields.append(QgsField("average_family_size", QVariant.Double))
        fields.append(QgsField("masculinity_rate", QVariant.Double))
        fields.append(QgsField("single_person_rate", QVariant.Double))
        fields.append(QgsField("large_families_rate", QVariant.Double))
        fields.append(QgsField("elderly_rate", QVariant.Double))
        
        # Housing and employment
        fields.append(QgsField("housing_density", QVariant.Double))
        fields.append(QgsField("average_building_occupancy", QVariant.Double))
        fields.append(QgsField("employment_rate", QVariant.Double))
        fields.append(QgsField("female_employment_rate", QVariant.Double))
        fields.append(QgsField("employment_gender_gap", QVariant.Double))
        
        # Education and social indicators
        fields.append(QgsField("higher_education_rate", QVariant.Double))
        fields.append(QgsField("low_education_rate", QVariant.Double))
        fields.append(QgsField("foreign_population_rate", QVariant.Double))
        fields.append(QgsField("labor_integration_rate", QVariant.Double))
        fields.append(QgsField("non_eu_foreigners_rate", QVariant.Double))
        fields.append(QgsField("young_foreigners_rate", QVariant.Double))
        
        # Economic and development indices
        fields.append(QgsField("structural_dependency_index", QVariant.Double))
        fields.append(QgsField("population_turnover_index", QVariant.Double))
        fields.append(QgsField("real_estate_potential_index", QVariant.Double))
        fields.append(QgsField("redevelopment_opportunity_index", QVariant.Double))
        fields.append(QgsField("economic_resilience_index", QVariant.Double))
        fields.append(QgsField("social_cohesion_index", QVariant.Double))
        
        # Risk assessments
        fields.append(QgsField("flood_risk", QVariant.String))
        fields.append(QgsField("landslide_risk", QVariant.String))
        fields.append(QgsField("coastalerosion_risk", QVariant.String))
        fields.append(QgsField("seismic_risk", QVariant.String))
        
        # Address information
        fields.append(QgsField("primary_street_address", QVariant.String))
        fields.append(QgsField("address_numbers", QVariant.String))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT_PARCELS,
            context,
            fields,
            QgsWkbTypes.Polygon,
            target_crs
        )

        if sink is None:
            raise QgsProcessingException(
                self.invalidSinkError(parameters, self.OUTPUT_PARCELS)
            )

        # Prepare API headers
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "enriched-cadastral-parcels-for-italy.p.rapidapi.com",
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(auth_token),
            "User-Agent": "Zornade-QGIS-Plugin/1.5.0"
        }

        try:
            # Test credentials with first API call
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
            
            # Handle credential-related errors and update status
            if parcels_response.status_code == 401:
                # Update credential status
                authenticator.update_credential_status(False)
                raise QgsProcessingException(
                    self.tr("Authentication failed. Your saved credentials appear to be invalid.\n"
                           "Please update them using 'Manage API Credentials' from the plugin menu.")
                )
            elif parcels_response.status_code == 403:
                # Update credential status
                authenticator.update_credential_status(False)
                raise QgsProcessingException(
                    self.tr("Access forbidden. Please verify your subscription is active.\n"
                           "Visit: https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy")
                )
            elif parcels_response.status_code == 429:
                # Credentials are valid, just rate limited
                feedback.pushWarning(self.tr("Rate limit exceeded. Please wait and try again with a smaller area."))
                raise QgsProcessingException(
                    self.tr("Rate limit exceeded. Please wait a moment and try again with a smaller area.")
                )
            elif parcels_response.status_code != 200:
                response_text = parcels_response.text[:500]
                raise QgsProcessingException(
                    self.tr("API request failed with status {}: {}".format(
                        parcels_response.status_code, response_text
                    ))
                )
            
            # If we get here, credentials are working - update status
            authenticator.update_credential_status(True)
            
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
                    # Fix: Ensure proper JSON payload construction
                    info_payload = {"fid": str(fid)}
                    
                    # Debug: Log the payload format for first request
                    if batch_index == 0:
                        feedback.pushInfo(self.tr("Debug: Request payload format: {}".format(info_payload)))
                    
                    info_response = requests.post(
                        get_info_url, 
                        headers=headers, 
                        json=info_payload,  # Use json parameter for proper serialization
                        timeout=20
                    )
                    
                    if info_response.status_code == 200:
                        try:
                            info_data = info_response.json()
                            if info_data.get("success") and "data" in info_data:
                                return (fid, True, info_data["data"])
                            else:
                                error_msg = info_data.get("message", "Invalid response format")
                                return (fid, False, f"API Error: {error_msg}")
                        except ValueError as e:
                            return (fid, False, f"Invalid JSON response: {str(e)}")
                    elif info_response.status_code == 404:
                        return (fid, False, f"Parcel not found")
                    elif info_response.status_code == 429:
                        return (fid, False, f"Rate limited")
                    elif info_response.status_code == 500:
                        # Log more details for 500 errors
                        try:
                            error_details = info_response.text[:200]
                            return (fid, False, f"Server error (500): {error_details}")
                        except:
                            return (fid, False, f"Server error (500): Unknown server issue")
                    else:
                        try:
                            error_text = info_response.text[:200]
                            return (fid, False, f"HTTP {info_response.status_code}: {error_text}")
                        except:
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
                            
                            # Core identification
                            feat["fid"] = str(fid)
                            feat["gml_id"] = str(parcel_info.get("gml_id", "")) 
                            feat["label"] = str(parcel_info.get("label", ""))
                            
                            # Administrative data
                            feat["administrativeunit"] = str(parcel_info.get("administrativeunit", ""))
                            feat["municipality_name"] = str(parcel_info.get("municipality_name", ""))
                            feat["region_name"] = str(parcel_info.get("region_name", ""))
                            feat["province_name"] = str(parcel_info.get("province_name", ""))
                            feat["province_code"] = str(parcel_info.get("province_code", ""))
                            feat["postal_code"] = str(parcel_info.get("postal_code", ""))

                            # Physical characteristics - safe numeric conversion
                            feat["footprint_sqm"] = float(parcel_info.get("footprint_sqm", 0.0)) if parcel_info.get("footprint_sqm") is not None else 0.0
                            feat["elevation_min"] = float(parcel_info.get("elevation_min", 0.0)) if parcel_info.get("elevation_min") is not None else 0.0
                            feat["elevation_max"] = float(parcel_info.get("elevation_max", 0.0)) if parcel_info.get("elevation_max") is not None else 0.0
                            feat["ruggedness_index"] = float(parcel_info.get("ruggedness_index", 0.0)) if parcel_info.get("ruggedness_index") is not None else 0.0
                            feat["number_of_points"] = int(parcel_info.get("number_of_points", 0)) if parcel_info.get("number_of_points") is not None else 0
                            
                            # Land use and classification
                            feat["class"] = str(parcel_info.get("class", ""))
                            feat["subtype"] = str(parcel_info.get("subtype", ""))
                            feat["landcover"] = str(parcel_info.get("landcover", ""))
                            feat["buildings_count"] = int(parcel_info.get("buildings_count", 0)) if parcel_info.get("buildings_count") is not None else 0
                            
                            # Census and demographics
                            feat["estimated_population"] = int(parcel_info.get("estimated_population", 0)) if parcel_info.get("estimated_population") is not None else 0
                            feat["average_age"] = float(parcel_info.get("average_age", 0.0)) if parcel_info.get("average_age") is not None else 0.0
                            feat["average_family_size"] = float(parcel_info.get("average_family_size", 0.0)) if parcel_info.get("average_family_size") is not None else 0.0
                            feat["masculinity_rate"] = float(parcel_info.get("masculinity_rate", 0.0)) if parcel_info.get("masculinity_rate") is not None else 0.0
                            feat["single_person_rate"] = float(parcel_info.get("single_person_rate", 0.0)) if parcel_info.get("single_person_rate") is not None else 0.0
                            feat["large_families_rate"] = float(parcel_info.get("large_families_rate", 0.0)) if parcel_info.get("large_families_rate") is not None else 0.0
                            feat["elderly_rate"] = float(parcel_info.get("elderly_rate", 0.0)) if parcel_info.get("elderly_rate") is not None else 0.0
                            
                            # Housing and employment
                            feat["housing_density"] = float(parcel_info.get("housing_density", 0.0)) if parcel_info.get("housing_density") is not None else 0.0
                            feat["average_building_occupancy"] = float(parcel_info.get("average_building_occupancy", 0.0)) if parcel_info.get("average_building_occupancy") is not None else 0.0
                            feat["employment_rate"] = float(parcel_info.get("employment_rate", 0.0)) if parcel_info.get("employment_rate") is not None else 0.0
                            feat["female_employment_rate"] = float(parcel_info.get("female_employment_rate", 0.0)) if parcel_info.get("female_employment_rate") is not None else 0.0
                            feat["employment_gender_gap"] = float(parcel_info.get("employment_gender_gap", 0.0)) if parcel_info.get("employment_gender_gap") is not None else 0.0
                            
                            # Education and social indicators
                            feat["higher_education_rate"] = float(parcel_info.get("higher_education_rate", 0.0)) if parcel_info.get("higher_education_rate") is not None else 0.0
                            feat["low_education_rate"] = float(parcel_info.get("low_education_rate", 0.0)) if parcel_info.get("low_education_rate") is not None else 0.0
                            feat["foreign_population_rate"] = float(parcel_info.get("foreign_population_rate", 0.0)) if parcel_info.get("foreign_population_rate") is not None else 0.0
                            feat["labor_integration_rate"] = float(parcel_info.get("labor_integration_rate", 0.0)) if parcel_info.get("labor_integration_rate") is not None else 0.0
                            feat["non_eu_foreigners_rate"] = float(parcel_info.get("non_eu_foreigners_rate", 0.0)) if parcel_info.get("non_eu_foreigners_rate") is not None else 0.0
                            feat["young_foreigners_rate"] = float(parcel_info.get("young_foreigners_rate", 0.0)) if parcel_info.get("young_foreigners_rate") is not None else 0.0
                            
                            # Economic and development indices
                            feat["structural_dependency_index"] = float(parcel_info.get("structural_dependency_index", 0.0)) if parcel_info.get("structural_dependency_index") is not None else 0.0
                            feat["population_turnover_index"] = float(parcel_info.get("population_turnover_index", 0.0)) if parcel_info.get("population_turnover_index") is not None else 0.0
                            feat["real_estate_potential_index"] = float(parcel_info.get("real_estate_potential_index", 0.0)) if parcel_info.get("real_estate_potential_index") is not None else 0.0
                            feat["redevelopment_opportunity_index"] = float(parcel_info.get("redevelopment_opportunity_index", 0.0)) if parcel_info.get("redevelopment_opportunity_index") is not None else 0.0
                            feat["economic_resilience_index"] = float(parcel_info.get("economic_resilience_index", 0.0)) if parcel_info.get("economic_resilience_index") is not None else 0.0
                            feat["social_cohesion_index"] = float(parcel_info.get("social_cohesion_index", 0.0)) if parcel_info.get("social_cohesion_index") is not None else 0.0
                            
                            # Risk assessments
                            feat["flood_risk"] = str(parcel_info.get("flood_risk", ""))
                            feat["landslide_risk"] = str(parcel_info.get("landslide_risk", ""))
                            feat["coastalerosion_risk"] = str(parcel_info.get("coastalerosion_risk", ""))
                            feat["seismic_risk"] = str(parcel_info.get("seismic_risk", ""))
                            
                            # Address information
                            feat["primary_street_address"] = str(parcel_info.get("primary_street_address", ""))
                            feat["address_numbers"] = str(parcel_info.get("address_numbers", ""))

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
        """Create a categorized renderer based on land use classification with enhanced styling."""
        
        # Enhanced color scheme for different land use types
        land_use_colors = {
            # Residential categories
            'residential': QColor(255, 230, 153),    # Light yellow
            'housing': QColor(255, 204, 128),        # Light orange  
            'urban': QColor(255, 179, 102),          # Orange
            'dwelling': QColor(255, 255, 179),       # Very light yellow
            'apartment': QColor(255, 218, 128),      # Pale orange
            
            # Commercial/Business
            'commercial': QColor(204, 153, 255),     # Light purple
            'business': QColor(179, 128, 255),       # Medium purple
            'retail': QColor(153, 102, 204),         # Purple
            'office': QColor(218, 179, 255),         # Very light purple
            'shop': QColor(191, 153, 230),           # Light lavender
            
            # Industrial
            'industrial': QColor(153, 102, 204),     # Purple
            'factory': QColor(128, 77, 179),         # Dark purple
            'warehouse': QColor(102, 51, 153),       # Very dark purple
            'manufacturing': QColor(140, 90, 190),   # Medium dark purple
            
            # Agricultural/Rural
            'agricultural': QColor(153, 255, 153),   # Light green
            'farmland': QColor(102, 204, 102),       # Green
            'crops': QColor(76, 153, 76),            # Dark green
            'farm': QColor(128, 230, 128),           # Bright light green
            'rural': QColor(102, 179, 102),          # Medium green
            'vineyard': QColor(153, 204, 102),       # Yellow-green
            'orchard': QColor(128, 204, 128),        # Light-medium green
            
            # Natural/Forest
            'forest': QColor(34, 139, 34),           # Forest green
            'woodland': QColor(0, 128, 0),           # Dark green
            'natural': QColor(107, 142, 35),         # Olive
            'park': QColor(124, 252, 0),             # Lawn green
            'green': QColor(50, 205, 50),            # Lime green
            
            # Water features
            'water': QColor(173, 216, 230),          # Light blue
            'wetland': QColor(135, 206, 235),        # Sky blue
            'river': QColor(100, 149, 237),          # Cornflower blue
            'lake': QColor(70, 130, 180),            # Steel blue
            
            # Infrastructure/Transport
            'transport': QColor(128, 128, 128),      # Gray
            'infrastructure': QColor(105, 105, 105), # Dim gray
            'utilities': QColor(169, 169, 169),      # Dark gray  
            'road': QColor(64, 64, 64),              # Very dark gray
            'railway': QColor(96, 96, 96),           # Dark gray
            'airport': QColor(192, 192, 192),        # Light gray
            
            # Special use
            'recreational': QColor(255, 182, 193),   # Light pink
            'sport': QColor(255, 160, 122),          # Light salmon
            'public': QColor(255, 140, 105),         # Salmon
            'institutional': QColor(255, 218, 185),  # Peach
            'educational': QColor(255, 239, 213),    # Papaya whip
            'healthcare': QColor(255, 228, 225),     # Misty rose
            'religious': QColor(230, 230, 250),      # Lavender
            'cemetery': QColor(139, 69, 19),         # Saddle brown
            'military': QColor(85, 107, 47),         # Dark olive green
            
            # Mixed/Other
            'mixed': QColor(221, 160, 221),          # Plum
            'unknown': QColor(211, 211, 211),        # Light gray
            'other': QColor(192, 192, 192),          # Silver
            'vacant': QColor(245, 245, 220),         # Beige
            'undeveloped': QColor(250, 240, 230)     # Linen
        }
        
        categories = []
        
        # Get unique land use values from the layer
        unique_classes = set()
        for feature in layer.getFeatures():
            land_class = str(feature['class']).lower().strip()
            if land_class and land_class != 'null':
                unique_classes.add(land_class)
        
        feedback.pushInfo(self.tr("Found {} unique land use classes".format(len(unique_classes))))
        
        # Create categories for each land use type with intelligent color matching
        for land_class in sorted(unique_classes):
            if not land_class or land_class == 'null':
                continue
                
            # Find best color match using keyword matching
            fill_color = land_use_colors.get('other')  # Default fallback
            
            # Try exact match first
            if land_class in land_use_colors:
                fill_color = land_use_colors[land_class]
            else:
                # Try partial matches with scoring
                best_score = 0
                for keyword, color in land_use_colors.items():
                    if keyword in land_class or land_class in keyword:
                        # Score based on length of match
                        score = len(keyword) if keyword in land_class else len(land_class)
                        if score > best_score:
                            best_score = score
                            fill_color = color
            
            # Create symbol with enhanced styling
            symbol = QgsFillSymbol.createSimple({
                'color': fill_color.name(),
                'color_border': QColor(64, 64, 64).name(),  # Dark gray border
                'style': 'solid',
                'style_border': 'solid',
                'width_border': '0.4',
                'opacity': '0.75'
            })
            
            # Create category with formatted label
            category = QgsRendererCategory(
                land_class,
                symbol,
                self._format_class_label(land_class)
            )
            categories.append(category)
        
        # Create "No Data" category with distinctive pattern
        no_data_symbol = QgsFillSymbol.createSimple({
            'color': QColor(240, 240, 240).name(),  # Very light gray
            'color_border': QColor(128, 128, 128).name(),
            'style': 'dense6',  # Hatched pattern
            'style_border': 'dash',
            'width_border': '0.3',
            'opacity': '0.4'
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
        
        feedback.pushInfo(self.tr("Applied enhanced categorized symbology with {} categories".format(len(categories))))

    def _apply_parcel_labels(self, layer: QgsVectorLayer, feedback: QgsProcessingFeedback):
        """Apply comprehensive labels showing key parcel information."""
        
        # Create label settings
        label_settings = QgsPalLayerSettings()
        
        # Enhanced label expression showing multiple key fields
        label_settings.fieldName = '''
        CASE 
            WHEN "municipality_name" IS NOT NULL AND "municipality_name" != '' THEN
                CASE
                    WHEN "class" IS NOT NULL AND "class" != '' THEN
                        "fid" || '\n' || "municipality_name" || '\n' || "class"
                    ELSE
                        "fid" || '\n' || "municipality_name"
                END
            WHEN "class" IS NOT NULL AND "class" != '' THEN
                "fid" || '\n' || "class"
            ELSE
                "fid"
        END
        '''
        label_settings.isExpression = True
        
        # Enhanced text formatting
        text_format = QgsTextFormat()
        text_format.setFont(layer.labelsFont())
        text_format.setSize(7)  # Slightly smaller for multi-line labels
        text_format.setColor(QColor(20, 20, 20))  # Very dark gray (more readable than pure black)
        
        # Enhanced text buffer with better contrast
        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.setSize(1.2)
        buffer_settings.setColor(QColor(255, 255, 255, 220))  # Semi-transparent white
        buffer_settings.setOpacity(0.9)
        text_format.setBuffer(buffer_settings)
        
        label_settings.setFormat(text_format)
        
        # Improved label placement
        label_settings.placement = QgsPalLayerSettings.OverPoint
        label_settings.centroidWhole = True
        label_settings.centroidInside = True
        
        # Scale visibility optimized for detailed parcels
        label_settings.scaleVisibility = True
        label_settings.minimumScale = 250     # Show when very zoomed in
        label_settings.maximumScale = 25000   # Hide when zoomed out
        
        # Enhanced priority and obstacle handling
        label_settings.priority = 6
        label_settings.obstacle = True
        label_settings.obstacleFactor = 0.3
        label_settings.displayAll = False  # Allow label competition for cleaner display
        
        # Apply labeling
        labeling = QgsVectorLayerSimpleLabeling(label_settings)
        layer.setLabeling(labeling)
        layer.setLabelsEnabled(True)
        
        feedback.pushInfo(self.tr("Applied comprehensive parcel labels (visible at scales 1:250 to 1:25,000)"))

    def _format_class_label(self, class_name: str) -> str:
        """Format class name for display in legend."""
        return class_name.replace('_', ' ').title()

    def postProcessAlgorithm(self, context: QgsProcessingContext, feedback: QgsProcessingFeedback) -> dict[str, Any]:
        """
        Actions to be performed after the algorithm has finished.
        """
        return super().postProcessAlgorithm(context, feedback)