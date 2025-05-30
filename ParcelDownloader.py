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

from qgis.PyQt.QtCore import QCoreApplication
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
    QgsProcessingParameterAuthConfig,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsSettings,
    QgsApplication,
    QgsAuthMethodConfig
)
from qgis import processing
import requests # Required for API calls


class ParcelDownloaderAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm fetches parcel data from the Ageratlas RapidAPI service
    and loads it into QGIS.
    """

    # --- Parameter definition ---
    # Input parameters
    BBOX = "BBOX"
    API_KEY = "API_KEY"
    SAVE_API_KEY = "SAVE_API_KEY"

    # Output parameters
    OUTPUT_PARCELS = "OUTPUT_PARCELS"

    # --- API Configuration ---
    API_BASE_URL = "https://ageratlas.p.rapidapi.com"
    SETTINGS_GROUP = "AgeratlasParcelDownloader"
    SETTINGS_API_KEY = "rapidApiKey"


    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("Processing", string)

    def name(self) -> str:
        """
        Returns the algorithm name, used for identifying the algorithm.
        """
        return "ageratlasparceldownloader"

    def displayName(self) -> str:
        """
        Returns the translated algorithm name.
        """
        return self.tr("Ageratlas Parcel Downloader")

    def group(self) -> str:
        """
        Returns the name of the group this algorithm belongs to.
        """
        return self.tr("Ageratlas API")

    def groupId(self) -> str:
        """
        Returns the unique ID of the group this algorithm belongs to.
        """
        return "ageratlasapi"

    def shortHelpString(self) -> str:
        """
        Returns a localised short helper string for the algorithm.
        """
        return self.tr(
            "Downloads parcel data from the Ageratlas API based on municipality or bounding box.\n\n"
            "You need a RapidAPI key to use this service. Enter your API key in the 'RapidAPI Key' field below. "
            "You can optionally save it for future use by checking 'Save API key for future sessions'.\n\n"
            "To get your API key:\n"
            "1. Visit https://rapidapi.com/ageratlas/api/ageratlas\n"
            "2. Subscribe to the service\n"
            "3. Copy your API key from the dashboard\n\n"
            "Your API key will be stored securely in QGIS settings if you choose to save it."
        )

    def helpUrl(self) -> str:
        # Optional: return a URL to a more detailed help page
        return "https://github.com/your-repo/ageratlas-parcel-downloader/blob/main/README.md" # Replace with your repo

    def createInstance(self):
        return ParcelDownloaderAlgorithm()

    def __init__(self):
        super().__init__()

    def initAlgorithm(self, config: Optional[dict[str, Any]] = None):
        """
        Defines the inputs and outputs of the algorithm.
        """
        # --- API Key Management ---
        # Get saved API key if exists
        settings = QgsSettings()
        saved_api_key = settings.value(f"{self.SETTINGS_GROUP}/{self.SETTINGS_API_KEY}", "")
        
        # Show a hint about current saved API key status
        if saved_api_key:
            api_key_hint = f"Current saved key: {saved_api_key[:8]}...{saved_api_key[-4:]} (masked for security)"
        else:
            api_key_hint = "No API key currently saved"
        
        self.addParameter(
            QgsProcessingParameterString(
                self.API_KEY,
                self.tr(f"RapidAPI Key ({api_key_hint})"),
                defaultValue=saved_api_key,
                optional=False,
                multiLine=False
            )
        )
        
        # Add parameter to save API key
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SAVE_API_KEY,
                self.tr("Save API key for future sessions (uncheck to remove saved key)"),
                defaultValue=bool(saved_api_key)  # Default to True if key already saved
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
        # Check API key
        api_key = self.parameterAsString(parameters, self.API_KEY, context)
        if not api_key or not api_key.strip():
            raise QgsProcessingException(
                self.tr("RapidAPI Key is required. Please enter your API key or visit "
                       "https://rapidapi.com/ageratlas/api/ageratlas to get one.")
            )

        # Check bounding box
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
        # Get API key from parameters
        api_key = self.parameterAsString(parameters, self.API_KEY, context).strip()
        save_api_key = self.parameterAsBool(parameters, self.SAVE_API_KEY, context)
        
        settings = QgsSettings()
        current_saved = settings.value(f"{self.SETTINGS_GROUP}/{self.SETTINGS_API_KEY}", "")
        
        # Handle API key saving/updating/removing
        if save_api_key:
            if current_saved != api_key:
                settings.setValue(f"{self.SETTINGS_GROUP}/{self.SETTINGS_API_KEY}", api_key)
                if current_saved:
                    feedback.pushInfo(self.tr("API key updated and saved for future sessions."))
                else:
                    feedback.pushInfo(self.tr("API key saved for future sessions."))
            else:
                feedback.pushInfo(self.tr("Using saved API key."))
        else:
            # User unchecked save option - remove saved key
            if current_saved:
                settings.remove(f"{self.SETTINGS_GROUP}/{self.SETTINGS_API_KEY}")
                feedback.pushInfo(self.tr("Saved API key removed. Current key will only be used for this session."))

        if not api_key:
            feedback.reportError(self.tr("API Key is required. Please enter your RapidAPI key."), fatalError=True)
            return {}

        bbox_extent = self.parameterAsExtent(parameters, self.BBOX, context)
        
        # Handle coordinate transformation if needed
        from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform
        source_crs = bbox_extent.crs() if bbox_extent.crs().isValid() else QgsProject.instance().crs()
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        
        if source_crs != target_crs:
            transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
            bbox_extent_4326 = transform.transformBoundingBox(bbox_extent)
            feedback.pushInfo(self.tr(f"Transformed bounding box from {source_crs.authid()} to EPSG:4326"))
        else:
            bbox_extent_4326 = bbox_extent

        # Define output fields
        # These should match the fields returned by the 'get-parcel-info' endpoint
        # Example fields - adjust based on actual API response
        fields = QgsFields()
        fields.append(QgsField("parcel_id", 2)) # String for ID
        fields.append(QgsField("area", 6)) # Double for area
        fields.append(QgsField("municipality", 2)) # String
        fields.append(QgsField("sheet", 2)) # String
        fields.append(QgsField("parcel_num", 2)) # String
        # Add other relevant fields from the API response

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT_PARCELS,
            context,
            fields,
            QgsWkbTypes.Polygon, # Assuming parcels are polygons
            QgsProject.instance().crs() # Output in project CRS
        )

        if sink is None:
            raise QgsProcessingException(
                self.invalidSinkError(parameters, self.OUTPUT_PARCELS)
            )

        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "ageratlas.p.rapidapi.com"
        }

        parcels_data = []

        # Fetch parcel data using bounding box
        feedback.pushInfo(self.tr(f"Fetching parcels for BBOX: {bbox_extent_4326.toString()}"))
        
        # Convert bbox to string format expected by API
        bbox_str = f"{bbox_extent_4326.xMinimum()},{bbox_extent_4326.yMinimum()},{bbox_extent_4326.xMaximum()},{bbox_extent_4326.yMaximum()}"
        
        # TODO: Implement API call for get-parcels by BBOX
        # get_parcels_url = f"{self.API_BASE_URL}/get-parcels"
        # params = {"bbox": bbox_str, "input_epsg": 4326, "output_epsg": 4326}
        # response = requests.get(get_parcels_url, headers=headers, params=params)
        # if response.status_code == 200:
        #     parcels_geojson = response.json()
        #     # Process parcels_geojson
        # else:
        #     feedback.reportError(f"Error fetching parcels: {response.status_code} - {response.text}", fatalError=True)
        #     return {}
        
        feedback.pushInfo("API call for 'get-parcels' by BBOX not yet implemented.")
        feedback.pushInfo(f"Would query API with bbox: {bbox_str}")

        # Placeholder data for development
        parcels_data = [
            {"id": "1", "geometry": {"type": "Polygon", "coordinates": [[[0,0],[0,1],[1,1],[1,0],[0,0]]]}},
            {"id": "2", "geometry": {"type": "Polygon", "coordinates": [[[1,1],[1,2],[2,2],[2,1],[1,1]]]}}
        ]

        # Step 2: For each parcel ID, fetch detailed info (get-parcel-info endpoint)
        # This might be inefficient if get-parcels already returns all info.
        # Adjust logic based on what get-parcels returns.
        # If get-parcels returns full info including geometry, this step might be combined or skipped.

        total_parcels = len(parcels_data)
        feedback.setProgress(0)

        for i, parcel_geom_data in enumerate(parcels_data):
            if feedback.isCanceled():
                break

            parcel_id = parcel_geom_data.get("id") # Or however the ID is structured
            # Assuming parcel_geom_data contains GeoJSON-like geometry
            # geojson_geometry = parcel_geom_data.get("geometry")

            # feedback.pushInfo(self.tr(f"Fetching details for parcel ID: {parcel_id}"))
            # TODO: Implement API call for get-parcel-info
            # get_info_url = f"{self.API_BASE_URL}/get-parcel-info"
            # params_info = {"id": parcel_id} # Or however the ID is passed
            # response_info = requests.get(get_info_url, headers=headers, params=params_info)
            # parcel_attributes = {}
            # if response_info.status_code == 200:
            #     parcel_attributes = response_info.json() # Assuming JSON response with attributes
            # else:
            #     feedback.reportError(f"Error fetching info for parcel {parcel_id}: {response_info.status_code} - {response_info.text}")
            #     continue # Skip this parcel or handle error differently

            # Create QGIS Feature
            feat = QgsFeature(fields)

            # Set geometry
            # if geojson_geometry:
            #     qgis_geometry = QgsGeometry.fromGeoJson(str(geojson_geometry)) # Ensure geojson_geometry is a valid JSON string
            #     # Transform geometry if it's in EPSG:4326 and output CRS is different
            #     source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            #     dest_crs = sink.crs()
            #     if source_crs != dest_crs:
            #         transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
            #         qgis_geometry.transform(transform)
            #     feat.setGeometry(qgis_geometry)

            # Set attributes (example, adapt to actual API response)
            # feat["parcel_id"] = parcel_id
            # feat["area"] = parcel_attributes.get("area_sqm")
            # feat["municipality"] = parcel_attributes.get("municipality_name")
            # feat["sheet"] = parcel_attributes.get("sheet_number")
            # feat["parcel_num"] = parcel_attributes.get("parcel_identifier")
            # ... set other attributes

            # Placeholder attributes if API call is not implemented
            feat["parcel_id"] = parcel_id
            feat["municipality"] = "N/A from BBOX"

            # Add feature to sink
            sink.addFeature(feat, QgsFeatureSink.Flag.FastInsert)
            feedback.setProgress(int((i + 1) / total_parcels * 100))


        if feedback.isCanceled():
            return {}

        return {self.OUTPUT_PARCELS: dest_id}

    def postProcessAlgorithm(self, context: QgsProcessingContext, feedback: QgsProcessingFeedback) -> dict[str, Any]:
        """
        Actions to be performed after the algorithm has finished.
        """
        # Example: Add the output layer to the map
        # output_layer_id = self.parameterAsOutputLayer(parameters, self.OUTPUT_PARCELS, context)
        # if output_layer_id:
        #    QgsProject.instance().addMapLayer(QgsProcessingUtils.mapLayerFromString(output_layer_id, context))
        return super().postProcessAlgorithm(context, feedback)
