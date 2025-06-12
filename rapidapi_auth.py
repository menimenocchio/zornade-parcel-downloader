# -*- coding: utf-8 -*-
"""
RapidAPI Authentication Module for Zornade Italian Parcel Downloader
Minimal, functional credential management with native Qt styling.
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
    QScrollArea, QWidget
)
from qgis.PyQt.QtGui import QDesktopServices, QFont
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
    """Native Qt credential management dialog with proper QGIS styling."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Credentials Setup")
        self.setFixedSize(600, 700)
        self.setModal(True)
        
        self.credentials = None
        self.authenticator = RapidAPIAuthenticator()
        
        self.setup_ui()
        self.load_existing_credentials()
        
    def setup_ui(self):
        """Setup native Qt UI with proper spacing and styling."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QFrame.NoFrame)
        # Fix: Use correct Qt constants
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(25, 25, 25, 25)
        content_layout.setSpacing(20)
        
        # Title section
        title_frame = self.create_title_section()
        content_layout.addWidget(title_frame)
        
        # Status section
        self.status_group = self.create_status_section()
        content_layout.addWidget(self.status_group)
        
        # Setup guide section
        guide_group = self.create_guide_section()
        content_layout.addWidget(guide_group)
        
        # Credentials form section
        form_group = self.create_credentials_form()
        content_layout.addWidget(form_group)
        
        # Validation section
        validation_group = self.create_validation_section()
        content_layout.addWidget(validation_group)
        
        # Action buttons
        action_frame = self.create_action_buttons()
        content_layout.addWidget(action_frame)
        
        # Help section
        help_group = self.create_help_section()
        content_layout.addWidget(help_group)
        
        content_layout.addStretch()
        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)
        
        main_layout.addWidget(scroll_area)
        
        # Bottom buttons
        bottom_buttons = self.create_bottom_buttons()
        main_layout.addLayout(bottom_buttons)
        
        self.setLayout(main_layout)
        
    def create_title_section(self) -> QFrame:
        """Create title section with native Qt styling."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box)
        frame.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a90e2, stop:1 #357abd);
                border: 1px solid #2c5aa0;
                border-radius: 6px;
            }
        """)
        frame.setFixedHeight(80)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(5)
        
        title = QLabel("Zornade API Credentials")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: white; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Configure your RapidAPI credentials for Italian cadastral data access")
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 200); background: transparent;")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        frame.setLayout(layout)
        
        return frame
        
    def create_status_section(self) -> QGroupBox:
        """Create status section with native Qt styling."""
        group = QGroupBox("Current Status")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 15)
        
        self.status_label = QLabel("Loading status...")
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(60)
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: #f8f9fa;
                color: #495057;
            }
        """)
        
        layout.addWidget(self.status_label)
        group.setLayout(layout)
        
        return group
        
    def create_guide_section(self) -> QGroupBox:
        """Create setup guide section."""
        group = QGroupBox("Quick Setup Guide")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(15)
        
        # Step labels with proper spacing
        steps = [
            "1. Click 'Open API Page' below to visit the Zornade service",
            "2. Sign up or log in to your RapidAPI account",
            "3. Subscribe to a plan (free options available)",
            "4. Copy your API credentials and enter them below"
        ]
        
        for step in steps:
            step_label = QLabel(step)
            step_label.setWordWrap(True)
            step_label.setStyleSheet("""
                QLabel {
                    padding: 8px 12px;
                    background-color: #e3f2fd;
                    border-left: 4px solid #2196f3;
                    color: #0d47a1;
                }
            """)
            layout.addWidget(step_label)
        
        # API page button
        self.api_btn = QPushButton("Open API Page")
        self.api_btn.setMinimumHeight(40)
        self.api_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
        """)
        self.api_btn.clicked.connect(self.open_api_page)
        layout.addWidget(self.api_btn)
        
        group.setLayout(layout)
        return group
        
    def create_credentials_form(self) -> QGroupBox:
        """Create credentials form with proper spacing."""
        group = QGroupBox("Enter Your Credentials")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(20)
        
        # API Key section
        api_frame = QFrame()
        api_layout = QVBoxLayout()
        api_layout.setSpacing(8)
        
        api_label = QLabel("RapidAPI Key:")
        api_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 12px;")
        
        api_help = QLabel("Get this from your RapidAPI dashboard → 'My Apps' section")
        api_help.setStyleSheet("color: #6c757d; font-size: 11px; margin-bottom: 5px;")
        api_help.setWordWrap(True)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your X-RapidAPI-Key (e.g., 1234567890abcdef...)")
        self.api_key_input.setMinimumHeight(35)
        self.api_key_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                font-size: 13px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
        """)
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.textChanged.connect(self.on_input_changed)
        
        self.show_api_key = QCheckBox("Show API Key")
        self.show_api_key.setStyleSheet("color: #6c757d; margin-top: 5px;")
        self.show_api_key.toggled.connect(self.toggle_api_key_visibility)
        
        api_layout.addWidget(api_label)
        api_layout.addWidget(api_help)
        api_layout.addWidget(self.api_key_input)
        api_layout.addWidget(self.show_api_key)
        api_frame.setLayout(api_layout)
        
        # Bearer Token section
        bearer_frame = QFrame()
        bearer_layout = QVBoxLayout()
        bearer_layout.setSpacing(8)
        
        bearer_label = QLabel("Bearer Token:")
        bearer_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 12px;")
        
        bearer_help = QLabel("Get this from the API page → 'Test' tab → Copy token after 'Bearer '")
        bearer_help.setStyleSheet("color: #6c757d; font-size: 11px; margin-bottom: 5px;")
        bearer_help.setWordWrap(True)
        
        self.bearer_input = QLineEdit()
        self.bearer_input.setPlaceholderText("Enter bearer token (without 'Bearer ' prefix)")
        self.bearer_input.setMinimumHeight(35)
        self.bearer_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                font-size: 13px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
        """)
        self.bearer_input.setEchoMode(QLineEdit.Password)
        self.bearer_input.textChanged.connect(self.on_input_changed)
        
        self.show_bearer = QCheckBox("Show Bearer Token")
        self.show_bearer.setStyleSheet("color: #6c757d; margin-top: 5px;")
        self.show_bearer.toggled.connect(self.toggle_bearer_visibility)
        
        bearer_layout.addWidget(bearer_label)
        bearer_layout.addWidget(bearer_help)
        bearer_layout.addWidget(self.bearer_input)
        bearer_layout.addWidget(self.show_bearer)
        bearer_frame.setLayout(bearer_layout)
        
        layout.addWidget(api_frame)
        layout.addWidget(bearer_frame)
        group.setLayout(layout)
        
        return group
        
    def create_validation_section(self) -> QGroupBox:
        """Create validation results section."""
        group = QGroupBox("Validation Results")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(10)
        
        self.validation_label = QLabel("Enter both credentials above and click 'Test' to verify")
        self.validation_label.setWordWrap(True)
        self.validation_label.setMinimumHeight(50)
        self.validation_label.setStyleSheet("""
            QLabel {
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: #f8f9fa;
                color: #6c757d;
            }
        """)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                text-align: center;
                background-color: #f8f9fa;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 4px;
            }
        """)
        
        layout.addWidget(self.validation_label)
        layout.addWidget(self.progress_bar)
        group.setLayout(layout)
        
        return group
        
    def create_action_buttons(self) -> QFrame:
        """Create action buttons with proper spacing."""
        frame = QFrame()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(15)
        
        self.test_btn = QPushButton("Test Credentials")
        self.test_btn.setEnabled(False)
        self.test_btn.setMinimumHeight(40)
        self.test_btn.setMinimumWidth(130)
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover:enabled {
                background-color: #e0a800;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
            }
        """)
        self.test_btn.clicked.connect(self.test_credentials)
        
        self.save_btn = QPushButton("Save & Use")
        self.save_btn.setEnabled(False)
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setMinimumWidth(120)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover:enabled {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
            }
        """)
        self.save_btn.clicked.connect(self.save_and_use)
        
        self.clear_btn = QPushButton("Clear Saved")
        self.clear_btn.setMinimumHeight(40)
        self.clear_btn.setMinimumWidth(110)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_credentials)
        
        layout.addWidget(self.test_btn)
        layout.addWidget(self.save_btn)
        layout.addStretch()
        layout.addWidget(self.clear_btn)
        
        frame.setLayout(layout)
        return frame
        
    def create_help_section(self) -> QGroupBox:
        """Create help section with native Qt elements."""
        group = QGroupBox("Common Issues")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(8)
        
        issues = [
            ("401 Error:", "Wrong API key or bearer token - double-check both"),
            ("403 Error:", "No active subscription - visit API page and subscribe"),
            ("Connection Error:", "Check your internet connection"),
            ("Rate Limited:", "You're hitting API limits (normal for valid credentials)")
        ]
        
        for error_type, description in issues:
            issue_frame = QFrame()
            issue_layout = QHBoxLayout()
            issue_layout.setContentsMargins(10, 8, 10, 8)
            issue_layout.setSpacing(10)
            
            error_label = QLabel(error_type)
            error_label.setStyleSheet("font-weight: bold; color: #dc3545; min-width: 100px;")
            
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #495057;")
            desc_label.setWordWrap(True)
            
            issue_layout.addWidget(error_label)
            issue_layout.addWidget(desc_label, 1)
            issue_frame.setLayout(issue_layout)
            issue_frame.setStyleSheet("""
                QFrame {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                }
            """)
            
            layout.addWidget(issue_frame)
        
        group.setLayout(layout)
        return group
        
    def create_bottom_buttons(self) -> QHBoxLayout:
        """Create bottom dialog buttons."""
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(15)
        
        close_btn = QPushButton("Cancel")
        close_btn.setMinimumHeight(35)
        close_btn.setMinimumWidth(80)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        close_btn.clicked.connect(self.reject)
        
        self.use_btn = QPushButton("Use These Credentials")
        self.use_btn.setEnabled(False)
        self.use_btn.setMinimumHeight(35)
        self.use_btn.setMinimumWidth(150)
        self.use_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
            }
        """)
        self.use_btn.clicked.connect(self.accept_credentials)
        
        layout.addStretch()
        layout.addWidget(close_btn)
        layout.addWidget(self.use_btn)
        
        return layout

    def load_existing_credentials(self):
        """Load existing credentials with native Qt display."""
        saved_creds = self.authenticator.get_saved_credentials()
        
        if saved_creds:
            masked_key = f"{saved_creds['rapidapi_key'][:8]}...{saved_creds['rapidapi_key'][-4:]}"
            
            self.status_label.setText(
                f"Found saved credentials: {masked_key}\n"
                f"Last validated: {saved_creds.get('last_validated', 'Unknown')}\n"
                f"Status: {'Working' if saved_creds.get('is_working', True) else 'Issues detected'}"
            )
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 15px;
                    border: 1px solid #c3e6cb;
                    border-radius: 6px;
                    background-color: #d4edda;
                    color: #155724;
                }
            """)
            
            self.api_key_input.setText(saved_creds['rapidapi_key'])
            self.bearer_input.setText(saved_creds['bearer_token'])
            self.use_btn.setEnabled(True)
            self.clear_btn.setEnabled(True)
        else:
            self.status_label.setText(
                "No saved credentials found\n"
                "Please follow the setup guide below to get started"
            )
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 15px;
                    border: 1px solid #ffeaa7;
                    border-radius: 6px;
                    background-color: #fff3cd;
                    color: #856404;
                }
            """)
            self.clear_btn.setEnabled(False)

    def open_api_page(self):
        """Open API page in browser."""
        QDesktopServices.openUrl(QUrl("https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy"))

    def on_input_changed(self):
        """Handle input changes with validation feedback."""
        has_both = bool(self.api_key_input.text().strip() and self.bearer_input.text().strip())
        self.test_btn.setEnabled(has_both)
        
        api_key = self.api_key_input.text().strip()
        bearer_token = self.bearer_input.text().strip()
        
        if api_key and len(api_key) < 20:
            self.validation_label.setText("API key seems too short (should be 30+ characters)")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 12px;
                    border: 1px solid #ffeaa7;
                    border-radius: 6px;
                    background-color: #fff3cd;
                    color: #856404;
                }
            """)
        elif bearer_token and len(bearer_token) < 10:
            self.validation_label.setText("Bearer token seems too short")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 12px;
                    border: 1px solid #ffeaa7;
                    border-radius: 6px;
                    background-color: #fff3cd;
                    color: #856404;
                }
            """)
        elif has_both:
            self.validation_label.setText("Both credentials entered - click 'Test' to verify")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 12px;
                    border: 1px solid #bee5eb;
                    border-radius: 6px;
                    background-color: #d1ecf1;
                    color: #0c5460;
                }
            """)
        else:
            self.validation_label.setText("Enter both credentials above and click 'Test' to verify")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    background-color: #f8f9fa;
                    color: #6c757d;
                }
            """)

    def toggle_api_key_visibility(self, checked):
        """Toggle API key visibility."""
        self.api_key_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        
    def toggle_bearer_visibility(self, checked):
        """Toggle bearer token visibility."""
        self.bearer_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    def test_credentials(self):
        """Test credentials with proper UI feedback."""
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
            self.validation_label.setText(f"{message} - Credentials are working!")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 12px;
                    border: 1px solid #c3e6cb;
                    border-radius: 6px;
                    background-color: #d4edda;
                    color: #155724;
                }
            """)
            self.save_btn.setEnabled(True)
            self.use_btn.setEnabled(True)
        else:
            self.validation_label.setText(message)
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 12px;
                    border: 1px solid #f5c6cb;
                    border-radius: 6px;
                    background-color: #f8d7da;
                    color: #721c24;
                }
            """)
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
                self.validation_label.setStyleSheet("""
                    QLabel {
                        padding: 12px;
                        border: 1px solid #ddd;
                        border-radius: 6px;
                        background-color: #f8f9fa;
                        color: #6c757d;
                    }
                """)
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
