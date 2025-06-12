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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsApplication

from .parcel_downloader_provider import ParcelDownloaderProvider


class ZornadeParcelDownloader:
    """QGIS Plugin Implementation for Zornade Italian Parcel Downloader."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'ZornadeParcelDownloader_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Zornade Italian Parcel Downloader')

        # Initialize processing provider
        self.provider = None

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('ZornadeParcelDownloader', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar."""

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        
        # Single main action with submenu functionality
        self.add_action(
            icon_path,
            text=self.tr(u'Zornade Italian Parcel Downloader'),
            callback=self.show_main_menu,
            status_tip=self.tr(u'Access Zornade Italian cadastral parcel downloader'),
            whats_this=self.tr(u'Download enriched Italian cadastral parcel data from Zornade\'s comprehensive dataset'),
            parent=self.iface.mainWindow())

        # Initialize processing provider
        self.initProcessing()

    def initProcessing(self):
        """Create the Processing provider"""
        self.provider = ParcelDownloaderProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr(u'&Zornade Italian Parcel Downloader'),
                action)
            self.iface.removeToolBarIcon(action)

        # Remove processing provider
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)

    def run(self):
        """Run method that opens the Processing algorithm."""
        from qgis import processing
        
        try:
            processing.execAlgorithmDialog('zornadeapi:ZornadeParcelDownloader')
        except Exception as e:
            # Fallback: try to open processing toolbox via menu
            try:
                from qgis.utils import iface
                from qgis.PyQt.QtWidgets import QApplication
                
                # Try to find and trigger the processing menu action
                main_window = iface.mainWindow()
                menubar = main_window.menuBar()
                
                # Look for Processing menu
                for action in menubar.actions():
                    if 'processing' in action.text().lower() or 'toolbox' in action.text().lower():
                        # Find the toolbox action in the submenu
                        if action.menu():
                            for sub_action in action.menu().actions():
                                if 'toolbox' in sub_action.text().lower():
                                    sub_action.trigger()
                                    return
                        break
                
                # If menu approach fails, show a message
                from qgis.PyQt.QtWidgets import QMessageBox
                QMessageBox.information(
                    iface.mainWindow(),
                    "Zornade Italian Parcel Downloader",
                    "Please open the Processing Toolbox manually:\n"
                    "Processing → Toolbox\n\n"
                    "Then navigate to: Zornade API → Zornade Parcel Downloader"
                )
                
            except Exception as e2:
                # Final fallback message
                from qgis.PyQt.QtWidgets import QMessageBox
                QMessageBox.information(
                    iface.mainWindow(),
                    "Zornade Italian Parcel Downloader",
                    "Please open the Processing Toolbox manually:\n"
                    "Processing → Toolbox\n\n"
                    "Then navigate to: Zornade API → Zornade Parcel Downloader"
                )

    def show_main_menu(self):
        """Show main menu with options."""
        from qgis.PyQt.QtWidgets import QMenu, QAction
        from qgis.PyQt.QtGui import QIcon
        
        menu = QMenu(self.iface.mainWindow())
        
        # Download parcels action
        download_action = QAction("Download Italian Parcels", menu)
        download_action.setIcon(QIcon(":/images/themes/default/algorithms/mAlgorithmVectorize.svg"))
        download_action.triggered.connect(self.run)
        menu.addAction(download_action)
        
        # Separator
        menu.addSeparator()
        
        # Manage credentials action
        credentials_action = QAction("Manage API Credentials", menu)
        credentials_action.setIcon(QIcon(":/images/themes/default/mActionOptions.svg"))
        credentials_action.triggered.connect(self.manage_credentials)
        menu.addAction(credentials_action)
        
        # Show menu at cursor position
        menu.exec_(self.iface.mainWindow().cursor().pos())

    def manage_credentials(self):
        """Show enhanced credential management dialog."""
        try:
            from .rapidapi_auth import SmartAuthDialog
            
            auth_dialog = SmartAuthDialog(self.iface.mainWindow())
            auth_dialog.exec_()
                
        except Exception as e:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Error",
                f"Could not access credential management: {str(e)}"
            )
