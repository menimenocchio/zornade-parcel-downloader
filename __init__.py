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

def classFactory(iface):
    """Load ZornadeParcelDownloader class from file zornade_parcel_downloader.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .zornade_parcel_downloader import ZornadeParcelDownloader
    return ZornadeParcelDownloader(iface)
