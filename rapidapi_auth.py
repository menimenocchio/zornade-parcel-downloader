# -*- coding: utf-8 -*-
"""
RapidAPI Authentication Module for Zornade Italian Parcel Downloader
Native QGIS/Qt integration with dark mode support.
"""

import base64
import json
from typing import Optional, Dict, Tuple
from datetime import datetime

from qgis.PyQt.QtCore import QObject, QSettings, Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QMessageBox, QApplication, QGroupBox, QCheckBox,
    QProgressBar, QFormLayout, QSpacerItem, QSizePolicy, QFrame,
    QScrollArea, QWidget, QTextEdit, QDialogButtonBox, QGridLayout
)
from qgis.PyQt.QtGui import QDesktopServices, QFont, QPalette
from qgis.PyQt.QtCore import QUrl
import requests


class RapidAPIAuthenticator(QObject):
    """Simple credential storage and validation."""
    
    SETTINGS_GROUP = "ZornadeParcelDownloader"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings()
        
    def get_saved_credentials(self) -> Optional[Dict[str, str]]:
        """Retrieve saved credentials."""
        try:
            encrypted_key = self.settings.value(f"{self.SETTINGS_GROUP}/rapidapi_key_enc")
            encrypted_token = self.settings.value(f"{self.SETTINGS_GROUP}/bearer_token_enc")
            
            if not encrypted_key or not encrypted_token:
                return None
                
            decrypted_key = self._decrypt(encrypted_key)
            decrypted_token = self._decrypt(encrypted_token)
            
            if not decrypted_key or not decrypted_token:
                return None
                
            return {
                'rapidapi_key': decrypted_key,
                'bearer_token': decrypted_token,
                'subscription_plan': self.settings.value(f"{self.SETTINGS_GROUP}/subscription_plan", "Saved"),
                'auto_retrieved': True,
                'last_validated': self.settings.value(f"{self.SETTINGS_GROUP}/last_validated", ""),
                'is_working': self.settings.value(f"{self.SETTINGS_GROUP}/is_working", True, type=bool)
            }
            
        except Exception:
            return None
    
    def save_credentials(self, credentials: Dict[str, str]) -> bool:
        """Save credentials securely."""
        try:
            if not credentials.get('rapidapi_key') or not credentials.get('bearer_token'):
                return False
                
            encrypted_key = self._encrypt(credentials['rapidapi_key'])
            encrypted_token = self._encrypt(credentials['bearer_token'])
            
            if not encrypted_key or not encrypted_token:
                return False
            
            self.settings.setValue(f"{self.SETTINGS_GROUP}/rapidapi_key_enc", encrypted_key)
            self.settings.setValue(f"{self.SETTINGS_GROUP}/bearer_token_enc", encrypted_token)
            self.settings.setValue(f"{self.SETTINGS_GROUP}/subscription_plan", credentials.get('subscription_plan', 'Manual'))
            self.settings.setValue(f"{self.SETTINGS_GROUP}/last_validated", datetime.now().strftime("%Y-%m-%d %H:%M"))
            self.settings.setValue(f"{self.SETTINGS_GROUP}/is_working", True)
            
            return True
            
        except Exception:
            return False
    
    def clear_credentials(self) -> bool:
        """Clear all saved credentials."""
        try:
            keys = ['rapidapi_key_enc', 'bearer_token_enc', 'subscription_plan', 'last_validated', 'is_working']
            for key in keys:
                self.settings.remove(f"{self.SETTINGS_GROUP}/{key}")
            return True
        except Exception:
            return False
    
    def update_credential_status(self, is_working: bool, validation_details: Dict = None):
        """Update credential working status based on API responses."""
        try:
            # Update the working status
            self.settings.setValue(f"{self.SETTINGS_GROUP}/is_working", is_working)
            self.settings.setValue(f"{self.SETTINGS_GROUP}/last_validated", datetime.now().strftime("%Y-%m-%d %H:%M"))
            
            # Optionally store additional validation details
            if validation_details:
                self.settings.setValue(f"{self.SETTINGS_GROUP}/last_status_code", validation_details.get('status_code', 0))
                self.settings.setValue(f"{self.SETTINGS_GROUP}/last_response_time", validation_details.get('response_time', 0.0))
            
            # Sync settings to ensure they're saved
            self.settings.sync()
            
        except Exception as e:
            print(f"Error updating credential status: {e}")
    
    def validate_credentials(self, api_key: str, bearer_token: str) -> Tuple[bool, str]:
        """Validate credentials with API call."""
        if not api_key or not bearer_token:
            return False, "Both API key and bearer token are required"
            
        try:
            headers = {
                "X-RapidAPI-Key": api_key.strip(),
                "X-RapidAPI-Host": "enriched-cadastral-parcels-for-italy.p.rapidapi.com",
                "Authorization": f"Bearer {bearer_token.strip()}",
                "Content-Type": "application/json"
            }
            
            test_payload = {
                "queryType": "bbox", 
                "params": [11.0, 45.0, 11.005, 45.005]
            }
            
            response = requests.post(
                "https://enriched-cadastral-parcels-for-italy.p.rapidapi.com/functions/v1/get-parcels",
                headers=headers,
                json=test_payload,
                timeout=15
            )
            
            # Create validation details
            validation_details = {
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0.0
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success'):
                        count = len(data.get('data', []))
                        # Update status to working
                        self.update_credential_status(True, validation_details)
                        return True, f"Valid! Found {count} test parcels"
                    else:
                        # Update status to not working
                        self.update_credential_status(False, validation_details)
                        return False, f"API Error: {data.get('message', 'Unknown error')}"
                except:
                    self.update_credential_status(False, validation_details)
                    return False, "Invalid response from API"
            elif response.status_code == 401:
                self.update_credential_status(False, validation_details)
                return False, "Invalid credentials"
            elif response.status_code == 403:
                self.update_credential_status(False, validation_details)
                return False, "Access forbidden - check subscription"
            elif response.status_code == 429:
                # Rate limited but credentials might be valid
                self.update_credential_status(True, validation_details)
                return False, "Rate limited (credentials may be valid)"
            else:
                self.update_credential_status(False, validation_details)
                return False, f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Request timeout"
        except requests.exceptions.ConnectionError:
            return False, "Connection error"
        except Exception as e:
            return False, f"Error: {str(e)[:50]}"
    
    def _encrypt(self, text: str) -> str:
        """Simple encryption."""
        try:
            encoded = base64.b64encode(text.encode('utf-8')).decode('ascii')
            return f"ZRN_{encoded}_END"
        except:
            return ""
    
    def _decrypt(self, encrypted_text: str) -> str:
        """Simple decryption."""
        try:
            if encrypted_text.startswith("ZRN_") and encrypted_text.endswith("_END"):
                encoded = encrypted_text[4:-4]
                return base64.b64decode(encoded.encode('ascii')).decode('utf-8')
            return ""
        except:
            return ""


class SmartAuthDialog(QDialog):
    """Native QGIS-style credential management dialog with dark mode support."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Credentials Setup")
        self.resize(550, 600)
        self.setModal(True)
        
        self.credentials = None
        self.authenticator = RapidAPIAuthenticator()
        
        self.setup_ui()
        self.load_existing_credentials()
        
    def setup_ui(self):
        """Setup native QGIS UI with minimal customization."""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Title label
        title_label = QLabel("Zornade API Credentials")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Status section
        self.status_group = self.create_status_section()
        layout.addWidget(self.status_group)
        
        # Setup guide section
        guide_group = self.create_guide_section()
        layout.addWidget(guide_group)
        
        # Credentials form
        form_group = self.create_credentials_form()
        layout.addWidget(form_group)
        
        # Validation section
        validation_group = self.create_validation_section()
        layout.addWidget(validation_group)
        
        # Help section
        help_group = self.create_help_section()
        layout.addWidget(help_group)
        
        layout.addStretch()
        
        # Standard dialog buttons
        button_box = QDialogButtonBox()
        
        # Test button
        self.test_btn = QPushButton("Test Credentials")
        self.test_btn.setEnabled(False)
        button_box.addButton(self.test_btn, QDialogButtonBox.ActionRole)
        
        # Save button
        self.save_btn = QPushButton("Save & Use")
        self.save_btn.setEnabled(False)
        button_box.addButton(self.save_btn, QDialogButtonBox.ActionRole)
        
        # Clear button
        self.clear_btn = QPushButton("Clear Saved")
        button_box.addButton(self.clear_btn, QDialogButtonBox.ResetRole)
        
        # Standard buttons
        button_box.addButton(QDialogButtonBox.Cancel)
        self.use_btn = button_box.addButton("Use Credentials", QDialogButtonBox.AcceptRole)
        self.use_btn.setEnabled(False)
        
        # Connect signals
        self.test_btn.clicked.connect(self.test_credentials)
        self.save_btn.clicked.connect(self.save_and_use)
        self.clear_btn.clicked.connect(self.clear_credentials)
        button_box.accepted.connect(self.accept_credentials)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        self.setLayout(layout)
        
    def create_status_section(self) -> QGroupBox:
        """Create native status section."""
        group = QGroupBox("Current Status")
        layout = QVBoxLayout()
        
        self.status_label = QLabel("Loading status...")
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(50)
        # Use system frame style for native appearance
        self.status_label.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.status_label.setMargin(8)
        
        layout.addWidget(self.status_label)
        group.setLayout(layout)
        return group
        
    def create_guide_section(self) -> QGroupBox:
        """Create native setup guide section."""
        group = QGroupBox("Setup Guide")
        layout = QVBoxLayout()
        
        # Instructions using native QLabel
        instructions = QLabel("""<b>Quick Setup Steps:</b><br>
1. Click 'Open API Page' below to visit the Zornade service<br>
2. Sign up or log in to your RapidAPI account<br>
3. Subscribe to a plan (free options available)<br>
4. Copy your API credentials and enter them below""")
        instructions.setWordWrap(True)
        instructions.setMargin(8)
        layout.addWidget(instructions)
        
        # API page button - using native button style
        self.api_btn = QPushButton("Open API Page")
        self.api_btn.clicked.connect(self.open_api_page)
        layout.addWidget(self.api_btn)
        
        group.setLayout(layout)
        return group
        
    def create_credentials_form(self) -> QGroupBox:
        """Create native credentials form."""
        group = QGroupBox("Enter Your Credentials")
        layout = QFormLayout()
        layout.setVerticalSpacing(8)
        
        # API Key section
        api_key_layout = QVBoxLayout()
        
        api_help = QLabel("Get this from your RapidAPI dashboard → 'My Apps' section")
        api_help.setStyleSheet("color: gray; font-size: 10pt;")
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your X-RapidAPI-Key")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.textChanged.connect(self.on_input_changed)
        
        self.show_api_key = QCheckBox("Show API Key")
        self.show_api_key.toggled.connect(self.toggle_api_key_visibility)
        
        api_key_layout.addWidget(api_help)
        api_key_layout.addWidget(self.api_key_input)
        api_key_layout.addWidget(self.show_api_key)
        
        layout.addRow("RapidAPI Key:", api_key_layout)
        
        # Bearer Token section
        bearer_layout = QVBoxLayout()
        
        bearer_help = QLabel("Get this from the API page → 'Test' tab → Copy token after 'Bearer '")
        bearer_help.setStyleSheet("color: gray; font-size: 10pt;")
        
        self.bearer_input = QLineEdit()
        self.bearer_input.setPlaceholderText("Enter bearer token (without 'Bearer ' prefix)")
        self.bearer_input.setEchoMode(QLineEdit.Password)
        self.bearer_input.textChanged.connect(self.on_input_changed)
        
        self.show_bearer = QCheckBox("Show Bearer Token")
        self.show_bearer.toggled.connect(self.toggle_bearer_visibility)
        
        bearer_layout.addWidget(bearer_help)
        bearer_layout.addWidget(self.bearer_input)
        bearer_layout.addWidget(self.show_bearer)
        
        layout.addRow("Bearer Token:", bearer_layout)
        
        group.setLayout(layout)
        return group
        
    def create_validation_section(self) -> QGroupBox:
        """Create native validation results section."""
        group = QGroupBox("Validation Results")
        layout = QVBoxLayout()
        
        self.validation_label = QLabel("Enter both credentials above and click 'Test' to verify")
        self.validation_label.setWordWrap(True)
        self.validation_label.setMinimumHeight(40)
        # Use system frame style
        self.validation_label.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.validation_label.setMargin(8)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        layout.addWidget(self.validation_label)
        layout.addWidget(self.progress_bar)
        group.setLayout(layout)
        return group
        
    def create_help_section(self) -> QGroupBox:
        """Create native help section."""
        group = QGroupBox("Common Issues")
        layout = QVBoxLayout()
        
        # Use native grid layout for issues
        grid = QGridLayout()
        
        issues = [
            ("401 Error:", "Wrong API key or bearer token"),
            ("403 Error:", "No active subscription"),
            ("Connection Error:", "Check internet connection"),
            ("Rate Limited:", "API limits (credentials may be valid)")
        ]
        
        for i, (error_type, description) in enumerate(issues):
            error_label = QLabel(error_type)
            error_label.setStyleSheet("font-weight: bold;")
            
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            
            grid.addWidget(error_label, i, 0)
            grid.addWidget(desc_label, i, 1)
        
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        group.setLayout(layout)
        return group

    def load_existing_credentials(self):
        """Load existing credentials with native display."""
        saved_creds = self.authenticator.get_saved_credentials()
        
        if saved_creds:
            masked_key = f"{saved_creds['rapidapi_key'][:8]}...{saved_creds['rapidapi_key'][-4:]}"
            
            status_text = (
                f"Found saved credentials: {masked_key}\n"
                f"Last validated: {saved_creds.get('last_validated', 'Unknown')}\n"
                f"Status: {'Working' if saved_creds.get('is_working', True) else 'Issues detected'}"
            )
            
            self.status_label.setText(status_text)
            # Use system colors for success
            palette = self.status_label.palette()
            palette.setColor(QPalette.WindowText, palette.color(QPalette.Dark))
            self.status_label.setPalette(palette)
            
            self.api_key_input.setText(saved_creds['rapidapi_key'])
            self.bearer_input.setText(saved_creds['bearer_token'])
            self.use_btn.setEnabled(True)
            self.clear_btn.setEnabled(True)
        else:
            self.status_label.setText("No saved credentials found\nPlease follow the setup guide below to get started")
            self.clear_btn.setEnabled(False)

    def open_api_page(self):
        """Open API page in browser."""
        QDesktopServices.openUrl(QUrl("https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy"))

    def on_input_changed(self):
        """Handle input changes."""
        has_both = bool(self.api_key_input.text().strip() and self.bearer_input.text().strip())
        self.test_btn.setEnabled(has_both)
        
        api_key = self.api_key_input.text().strip()
        bearer_token = self.bearer_input.text().strip()
        
        if api_key and len(api_key) < 20:
            self.validation_label.setText("API key seems too short (should be 30+ characters)")
        elif bearer_token and len(bearer_token) < 10:
            self.validation_label.setText("Bearer token seems too short")
        elif has_both:
            self.validation_label.setText("Both credentials entered - click 'Test' to verify")
        else:
            self.validation_label.setText("Enter both credentials above and click 'Test' to verify")

    def toggle_api_key_visibility(self, checked):
        """Toggle API key visibility."""
        self.api_key_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        
    def toggle_bearer_visibility(self, checked):
        """Toggle bearer token visibility."""
        self.bearer_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    def test_credentials(self):
        """Test credentials with native UI feedback."""
        api_key = self.api_key_input.text().strip()
        bearer_token = self.bearer_input.text().strip()
        
        if not api_key or not bearer_token:
            self.validation_label.setText("Please enter both credentials")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.test_btn.setText("Testing...")
        self.test_btn.setEnabled(False)
        
        QApplication.processEvents()
        
        is_valid, message = self.authenticator.validate_credentials(api_key, bearer_token)
        
        self.progress_bar.setVisible(False)
        self.test_btn.setText("Test Credentials")
        self.test_btn.setEnabled(True)
        
        if is_valid:
            self.validation_label.setText(f"✓ {message} - Credentials are working!")
            # Use system palette for success color
            palette = self.validation_label.palette()
            palette.setColor(QPalette.WindowText, palette.color(QPalette.Dark))
            self.validation_label.setPalette(palette)
            self.save_btn.setEnabled(True)
            self.use_btn.setEnabled(True)
        else:
            self.validation_label.setText(f"✗ {message}")
            # Use system palette for error color
            palette = self.validation_label.palette()
            palette.setColor(QPalette.WindowText, palette.color(QPalette.BrightText))
            self.validation_label.setPalette(palette)
            self.save_btn.setEnabled(False)

    def save_and_use(self):
        """Save credentials and use them."""
        api_key = self.api_key_input.text().strip()
        bearer_token = self.bearer_input.text().strip()
        
        credentials = {
            'rapidapi_key': api_key,
            'bearer_token': bearer_token,
            'subscription_plan': 'Manual Entry'
        }
        
        if self.authenticator.save_credentials(credentials):
            QMessageBox.information(self, "Success", "Credentials saved successfully!\nYou can now use the plugin.")
            self.load_existing_credentials()
            self.accept_credentials()
        else:
            QMessageBox.critical(self, "Error", "Failed to save credentials. Please try again.")

    def clear_credentials(self):
        """Clear saved credentials with confirmation."""
        reply = QMessageBox.question(
            self, "Clear Credentials", 
            "Are you sure you want to clear all saved credentials?\nYou'll need to enter them again next time.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.authenticator.clear_credentials():
                QMessageBox.information(self, "Cleared", "Credentials cleared successfully.")
                self.api_key_input.clear()
                self.bearer_input.clear()
                self.validation_label.setText("Enter both credentials above and click 'Test' to verify")
                # Reset to default system palette
                self.validation_label.setPalette(self.palette())
                self.save_btn.setEnabled(False)
                self.use_btn.setEnabled(False)
                self.load_existing_credentials()

    def accept_credentials(self):
        """Accept with current credentials."""
        api_key = self.api_key_input.text().strip()
        bearer_token = self.bearer_input.text().strip()
        
        if not api_key or not bearer_token:
            QMessageBox.warning(self, "Missing Credentials", "Please enter both credentials before continuing.")
            return
        
        self.credentials = {
            'rapidapi_key': api_key,
            'bearer_token': bearer_token,
            'subscription_plan': 'Manual Entry',
            'auto_retrieved': True
        }
        
        self.accept()

    def get_credentials(self) -> Optional[Dict[str, str]]:
        """Get credentials."""
        return self.credentials


# Backward compatibility aliases
BrowserAuthDialog = SmartAuthDialog
CredentialExtractionDialog = SmartAuthDialog
