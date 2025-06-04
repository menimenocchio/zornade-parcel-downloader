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
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider
from .ParcelDownloader import ParcelDownloaderAlgorithm


class ParcelDownloaderProvider(QgsProcessingProvider):
    """Processing Provider for zornade Parcel Downloader algorithms."""

    def __init__(self):
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """Unload provider."""
        pass

    def loadAlgorithms(self):
        """Load all algorithms belonging to this provider."""
        self.addAlgorithm(ParcelDownloaderAlgorithm())

    def id(self):
        """Return the unique provider id."""
        return 'zornadeapi'

    def name(self):
        """Return the provider name."""
        return 'Zornade API'

    def longName(self):
        """Return the full provider name."""
        return 'Zornade Parcel Downloader'

    def icon(self):
        """Return the provider icon."""
        return QIcon(os.path.join(os.path.dirname(__file__), 'icon.png'))
