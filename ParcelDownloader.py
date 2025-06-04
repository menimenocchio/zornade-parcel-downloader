# -*- coding: utf-8 -*-
"""
/***************************************************************************
 zornade Parcel Downloader
                                 A QGIS plugin
 Downloads parcel data from the zornade API and loads it into QGIS.
                              -------------------
        begin                : 2023-10-10
        git sha              : $Format:%H$
        copyright            : (C) 2023 by Your Name
        email                : your.email@example.com
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
    This algorithm fetches parcel data from the zornade RapidAPI service
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
    API_BASE_URL = "https://zornade.p.rapidapi.com"
    SETTINGS_GROUP = "ZornadeParcelDownloader"
    SETTINGS_API_KEY = "rapidApiKey"

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
        return self.tr("zornade Parcel Downloader")

    def group(self):
        """
        Returns the name of the group this algorithm belongs to.
        """
        return self.tr("zornade API")

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
            "Downloads parcel data from the zornade API based on bounding box.\n\n"
            "You need a RapidAPI key to use this service. Enter your API key in the 'RapidAPI Key' field below. "
            "You can optionally save it for future use by checking 'Save API key for future sessions'.\n\n"
            "To get your API key:\n"
            "1. Visit https://rapidapi.com/zornade/api/zornade\n"
            "2. Subscribe to the service\n"
            "3. Copy your API key from the dashboard\n\n"
            "Your API key will be stored securely in QGIS settings if you choose to save it."
        )

    def helpUrl(self):
        # Optional: return a URL to a more detailed help page
        return "https://github.com/your-repo/zornade-parcel-downloader/blob/main/README.md"

    def __init__(self):
        super().__init__()

    def initAlgorithm(self, config: Optional[dict[str, Any]] = None):
        """
        Defines the inputs and outputs of the algorithm.
        """
        # --- API Key Management ---
        settings = QSettings()
        saved_api_key = settings.value(f"{self.SETTINGS_GROUP}/{self.SETTINGS_API_KEY}", "")
        
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
        
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SAVE_API_KEY,
                self.tr("Save API key for future sessions (uncheck to remove saved key)"),
                defaultValue=bool(saved_api_key)
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
                       "https://rapidapi.com/zornade/api/zornade to get one.")
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
        # Get API key from parameters
        api_key = self.parameterAsString(parameters, self.API_KEY, context).strip()
        save_api_key = self.parameterAsBool(parameters, self.SAVE_API_KEY, context)
        
        # Handle API key saving/updating/removing
        settings = QSettings()
        current_saved = settings.value(f"{self.SETTINGS_GROUP}/{self.SETTINGS_API_KEY}", "")
        
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
            if current_saved:
                settings.remove(f"{self.SETTINGS_GROUP}/{self.SETTINGS_API_KEY}")
                feedback.pushInfo(self.tr("Saved API key removed. Current key will only be used for this session."))

        bbox_extent = self.parameterAsExtent(parameters, self.BBOX, context)
        
        # Handle coordinate transformation
        source_crs = bbox_extent.crs() if bbox_extent.crs().isValid() else QgsProject.instance().crs()
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        
        if source_crs != target_crs:
            transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
            bbox_extent_4326 = transform.transformBoundingBox(bbox_extent)
            feedback.pushInfo(self.tr("Transformed bounding box from {} to EPSG:4326".format(source_crs.authid())))
        else:
            bbox_extent_4326 = bbox_extent

        # Define output fields based on expected API response
        fields = QgsFields()
        fields.append(QgsField("parcel_id", 2))  # String (QVariant::String = 2)
        fields.append(QgsField("area", 6))  # Double (QVariant::Double = 6)
        fields.append(QgsField("municipality", 2))  # String
        fields.append(QgsField("sheet", 2))  # String
        fields.append(QgsField("parcel_num", 2))  # String

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

        # Prepare API headers
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "zornade.p.rapidapi.com"
        }

        # Convert bbox to API format
        bbox_str = "{},{},{},{}".format(
            bbox_extent_4326.xMinimum(),
            bbox_extent_4326.yMinimum(),
            bbox_extent_4326.xMaximum(),
            bbox_extent_4326.yMaximum()
        )
        feedback.pushInfo(self.tr("Fetching parcels for BBOX: {}".format(bbox_str)))

        try:
            # TODO: Replace with actual API call
            # get_parcels_url = f"{self.API_BASE_URL}/get-parcels"
            # params = {"bbox": bbox_str, "input_epsg": 4326, "output_epsg": 4326}
            # response = requests.get(get_parcels_url, headers=headers, params=params, timeout=30)
            # 
            # if response.status_code == 200:
            #     parcels_data = response.json()
            #     self._process_parcels_data(parcels_data, sink, fields, feedback)
            # else:
            #     raise QgsProcessingException("API Error: {} - {}".format(response.status_code, response.text))
            
            # Placeholder for development
            feedback.pushInfo("API call implementation pending. Plugin structure is ready.")
            
            # Create a dummy feature to test the plugin
            feat = QgsFeature(fields)
            feat["parcel_id"] = "TEST_001"
            feat["area"] = 1000.0
            feat["municipality"] = "Test Municipality"
            feat["sheet"] = "001"
            feat["parcel_num"] = "123"
            
            # Create a simple test geometry
            test_rect = QgsRectangle(
                bbox_extent_4326.xMinimum(), 
                bbox_extent_4326.yMinimum(), 
                bbox_extent_4326.xMinimum() + 0.001, 
                bbox_extent_4326.yMinimum() + 0.001
            )
            feat.setGeometry(QgsGeometry.fromRect(test_rect))
            
            sink.addFeature(feat, QgsFeatureSink.Flag.FastInsert)
            feedback.pushInfo("Added test feature to verify plugin functionality.")
            
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