# -*- coding: utf-8 -*-
"""
RapidAPI Authentication Module for Zornade Italian Parcel Downloader
Minimal, functional credential management.
"""

import base64
import json
from typing import Optional, Dict, Tuple
from datetime import datetime

from qgis.PyQt.QtCore import QObject, QSettings, Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QMessageBox, QApplication, QGroupBox, QCheckBox,
    QProgressBar, QFormLayout, QSpacerItem, QSizePolicy
)
from qgis.PyQt.QtGui import QDesktopServices
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
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success'):
                        count = len(data.get('data', []))
                        return True, f"Valid! Found {count} test parcels"
                    else:
                        return False, f"API Error: {data.get('message', 'Unknown error')}"
                except:
                    return False, "Invalid response from API"
            elif response.status_code == 401:
                return False, "Invalid credentials"
            elif response.status_code == 403:
                return False, "Access forbidden - check subscription"
            elif response.status_code == 429:
                return False, "Rate limited (credentials may be valid)"
            else:
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
    """Minimal, functional credential management dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Credentials")
        self.setFixedSize(450, 400)
        self.setModal(True)
        
        self.credentials = None
        self.authenticator = RapidAPIAuthenticator()
        
        self.setup_ui()
        self.load_existing_credentials()
        
    def setup_ui(self):
        """Setup minimal UI."""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Zornade API Credentials")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Status
        self.status_label = QLabel("Loading...")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 4px;")
        layout.addWidget(self.status_label)
        
        # Credentials form
        form_group = QGroupBox("Enter Credentials")
        form_layout = QFormLayout()
        
        # API Key
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Your X-RapidAPI-Key")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.textChanged.connect(self.on_input_changed)
        
        self.show_api_key = QCheckBox("Show")
        self.show_api_key.toggled.connect(lambda checked: 
            self.api_key_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        
        api_layout = QHBoxLayout()
        api_layout.addWidget(self.api_key_input)
        api_layout.addWidget(self.show_api_key)
        form_layout.addRow("API Key:", api_layout)
        
        # Bearer Token
        self.bearer_input = QLineEdit()
        self.bearer_input.setPlaceholderText("Bearer token (without 'Bearer ' prefix)")
        self.bearer_input.setEchoMode(QLineEdit.Password)
        self.bearer_input.textChanged.connect(self.on_input_changed)
        
        self.show_bearer = QCheckBox("Show")
        self.show_bearer.toggled.connect(lambda checked: 
            self.bearer_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        
        bearer_layout = QHBoxLayout()
        bearer_layout.addWidget(self.bearer_input)
        bearer_layout.addWidget(self.show_bearer)
        form_layout.addRow("Bearer Token:", bearer_layout)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Validation result
        self.validation_label = QLabel("Enter credentials and test them")
        self.validation_label.setWordWrap(True)
        self.validation_label.setStyleSheet("padding: 8px; background-color: #f8f8f8; border-radius: 4px;")
        layout.addWidget(self.validation_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("Test")
        self.test_btn.setEnabled(False)
        self.test_btn.clicked.connect(self.test_credentials)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_credentials)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_credentials)
        
        action_layout.addWidget(self.test_btn)
        action_layout.addWidget(self.save_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.clear_btn)
        layout.addLayout(action_layout)
        
        # Links
        links_layout = QHBoxLayout()
        
        dashboard_btn = QPushButton("RapidAPI Dashboard")
        dashboard_btn.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://rapidapi.com/developer/dashboard")))
        
        api_btn = QPushButton("Zornade API Page")
        api_btn.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy")))
        
        links_layout.addWidget(dashboard_btn)
        links_layout.addWidget(api_btn)
        layout.addLayout(links_layout)
        
        layout.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        
        self.use_btn = QPushButton("Use Credentials")
        self.use_btn.setEnabled(False)
        self.use_btn.clicked.connect(self.accept_credentials)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(close_btn)
        bottom_layout.addWidget(self.use_btn)
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
        
    def load_existing_credentials(self):
        """Load existing credentials."""
        saved_creds = self.authenticator.get_saved_credentials()
        
        if saved_creds:
            masked_key = f"{saved_creds['rapidapi_key'][:8]}...{saved_creds['rapidapi_key'][-4:]}"
            self.status_label.setText(f"Found saved credentials: {masked_key}")
            self.status_label.setStyleSheet("padding: 10px; background-color: #e8f5e8; border-radius: 4px; color: #2d5016;")
            
            self.api_key_input.setText(saved_creds['rapidapi_key'])
            self.bearer_input.setText(saved_creds['bearer_token'])
            self.use_btn.setEnabled(True)
        else:
            self.status_label.setText("No saved credentials found")
            self.status_label.setStyleSheet("padding: 10px; background-color: #fff3cd; border-radius: 4px; color: #856404;")
    
    def on_input_changed(self):
        """Handle input changes."""
        has_both = bool(self.api_key_input.text().strip() and self.bearer_input.text().strip())
        self.test_btn.setEnabled(has_both)
    
    def test_credentials(self):
        """Test credentials."""
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
        self.test_btn.setText("Test")
        self.test_btn.setEnabled(True)
        
        if is_valid:
            self.validation_label.setText(f"✓ {message}")
            self.validation_label.setStyleSheet("padding: 8px; background-color: #e8f5e8; border-radius: 4px; color: #2d5016;")
            self.save_btn.setEnabled(True)
        else:
            self.validation_label.setText(f"✗ {message}")
            self.validation_label.setStyleSheet("padding: 8px; background-color: #f8d7da; border-radius: 4px; color: #721c24;")
            self.save_btn.setEnabled(False)
    
    def save_credentials(self):
        """Save credentials."""
        api_key = self.api_key_input.text().strip()
        bearer_token = self.bearer_input.text().strip()
        
        credentials = {
            'rapidapi_key': api_key,
            'bearer_token': bearer_token,
            'subscription_plan': 'Manual Entry'
        }
        
        if self.authenticator.save_credentials(credentials):
            QMessageBox.information(self, "Success", "Credentials saved successfully!")
            self.load_existing_credentials()
            self.use_btn.setEnabled(True)
        else:
            QMessageBox.critical(self, "Error", "Failed to save credentials")
    
    def clear_credentials(self):
        """Clear saved credentials."""
        reply = QMessageBox.question(self, "Clear Credentials", 
                                   "Clear all saved credentials?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.authenticator.clear_credentials():
                QMessageBox.information(self, "Cleared", "Credentials cleared")
                self.api_key_input.clear()
                self.bearer_input.clear()
                self.validation_label.setText("Enter credentials and test them")
                self.validation_label.setStyleSheet("padding: 8px; background-color: #f8f8f8; border-radius: 4px;")
                self.save_btn.setEnabled(False)
                self.use_btn.setEnabled(False)
                self.load_existing_credentials()
    
    def accept_credentials(self):
        """Accept with current credentials."""
        api_key = self.api_key_input.text().strip()
        bearer_token = self.bearer_input.text().strip()
        
        if not api_key or not bearer_token:
            QMessageBox.warning(self, "Missing Credentials", "Please enter both credentials")
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
