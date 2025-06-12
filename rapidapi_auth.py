# -*- coding: utf-8 -*-
"""
RapidAPI Authentication Module for Zornade Italian Parcel Downloader
Minimal, functional credential management with enhanced Qt UI.
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
    QScrollArea, QWidget, QTextEdit
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
    """Enhanced Qt credential management dialog with improved visibility."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Credentials Setup")
        self.setFixedSize(650, 750)
        self.setModal(True)
        
        self.credentials = None
        self.authenticator = RapidAPIAuthenticator()
        
        self.setup_ui()
        self.load_existing_credentials()
        
    def setup_ui(self):
        """Setup enhanced Qt UI with better visibility."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QFrame.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(25)
        
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
        """Create enhanced title section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box)
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a90e2, stop:1 #357abd);
                border: 2px solid #2c5aa0;
                border-radius: 8px;
            }
        """)
        frame.setFixedHeight(100)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(8)
        
        title = QLabel("Zornade API Credentials")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: white; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Configure your RapidAPI credentials for Italian cadastral data access")
        subtitle_font = QFont()
        subtitle_font.setPointSize(11)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 220); background: transparent;")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        frame.setLayout(layout)
        
        return frame
        
    def create_status_section(self) -> QGroupBox:
        """Create enhanced status section."""
        group = QGroupBox("Current Status")
        group_font = QFont()
        group_font.setPointSize(14)
        group_font.setBold(True)
        group.setFont(group_font)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                margin-top: 15px;
                padding-top: 20px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #2c3e50;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 25, 20, 20)
        
        self.status_label = QLabel("Loading status...")
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(80)
        status_font = QFont()
        status_font.setPointSize(11)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 20px;
                border: 2px solid #ddd;
                border-radius: 8px;
                background-color: #f8f9fa;
                color: #495057;
                line-height: 1.5;
            }
        """)
        
        layout.addWidget(self.status_label)
        group.setLayout(layout)
        
        return group
        
    def create_guide_section(self) -> QGroupBox:
        """Create enhanced setup guide section."""
        group = QGroupBox("Quick Setup Guide")
        group_font = QFont()
        group_font.setPointSize(14)
        group_font.setBold(True)
        group.setFont(group_font)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                margin-top: 15px;
                padding-top: 20px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #2c3e50;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 25, 20, 20)
        layout.setSpacing(15)
        
        # Enhanced step display using native Qt
        steps_frame = QFrame()
        steps_layout = QVBoxLayout()
        steps_layout.setSpacing(12)
        
        steps = [
            "1. Click 'Open API Page' below to visit the Zornade service",
            "2. Sign up or log in to your RapidAPI account",
            "3. Subscribe to a plan (free options available)",
            "4. Copy your API credentials and enter them below"
        ]
        
        for i, step in enumerate(steps):
            step_frame = QFrame()
            step_frame.setStyleSheet("""
                QFrame {
                    background-color: #e3f2fd;
                    border-left: 4px solid #2196f3;
                    border-radius: 6px;
                    padding: 2px;
                }
            """)
            
            step_layout = QHBoxLayout()
            step_layout.setContentsMargins(15, 12, 15, 12)
            
            # Step number
            step_num = QLabel(f"{i+1}")
            step_num.setStyleSheet("""
                QLabel {
                    background-color: #2196f3;
                    color: white;
                    border-radius: 15px;
                    font-weight: bold;
                    font-size: 12px;
                    min-width: 30px;
                    max-width: 30px;
                    min-height: 30px;
                    max-height: 30px;
                }
            """)
            step_num.setAlignment(Qt.AlignCenter)
            
            # Step text
            step_text = QLabel(step.split('. ', 1)[1])  # Remove number from text
            step_text.setWordWrap(True)
            step_font = QFont()
            step_font.setPointSize(11)
            step_text.setFont(step_font)
            step_text.setStyleSheet("""
                QLabel {
                    color: #0d47a1;
                    background: transparent;
                }
            """)
            
            step_layout.addWidget(step_num)
            step_layout.addWidget(step_text, 1)
            step_frame.setLayout(step_layout)
            steps_layout.addWidget(step_frame)
        
        steps_frame.setLayout(steps_layout)
        layout.addWidget(steps_frame)
        
        # Enhanced API page button
        self.api_btn = QPushButton("🌐 Open API Page")
        self.api_btn.setMinimumHeight(50)
        self.api_btn.setMinimumWidth(200)
        api_font = QFont()
        api_font.setPointSize(13)
        api_font.setBold(True)
        self.api_btn.setFont(api_font)
        self.api_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
        """)
        self.api_btn.clicked.connect(self.open_api_page)
        layout.addWidget(self.api_btn, 0, Qt.AlignCenter)
        
        group.setLayout(layout)
        return group
        
    def create_credentials_form(self) -> QGroupBox:
        """Create enhanced credentials form."""
        group = QGroupBox("Enter Your Credentials")
        group_font = QFont()
        group_font.setPointSize(14)
        group_font.setBold(True)
        group.setFont(group_font)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                margin-top: 15px;
                padding-top: 20px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #2c3e50;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 25, 20, 20)
        layout.setSpacing(25)
        
        # API Key section
        api_frame = QFrame()
        api_layout = QVBoxLayout()
        api_layout.setSpacing(10)
        
        api_label = QLabel("🔐 RapidAPI Key:")
        api_label_font = QFont()
        api_label_font.setPointSize(12)
        api_label_font.setBold(True)
        api_label.setFont(api_label_font)
        api_label.setStyleSheet("color: #2c3e50; margin-bottom: 5px;")
        
        api_help = QLabel("Get this from your RapidAPI dashboard → 'My Apps' section")
        api_help_font = QFont()
        api_help_font.setPointSize(10)
        api_help.setFont(api_help_font)
        api_help.setStyleSheet("color: #6c757d; margin-bottom: 8px;")
        api_help.setWordWrap(True)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your X-RapidAPI-Key (e.g., 1234567890abcdef...)")
        self.api_key_input.setMinimumHeight(45)
        input_font = QFont()
        input_font.setPointSize(11)
        self.api_key_input.setFont(input_font)
        self.api_key_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                font-size: 11px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
            QLineEdit:hover {
                border-color: #80bdff;
            }
        """)
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.textChanged.connect(self.on_input_changed)
        
        self.show_api_key = QCheckBox("Show API Key")
        checkbox_font = QFont()
        checkbox_font.setPointSize(10)
        self.show_api_key.setFont(checkbox_font)
        self.show_api_key.setStyleSheet("""
            QCheckBox {
                color: #6c757d;
                margin-top: 8px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.show_api_key.toggled.connect(self.toggle_api_key_visibility)
        
        api_layout.addWidget(api_label)
        api_layout.addWidget(api_help)
        api_layout.addWidget(self.api_key_input)
        api_layout.addWidget(self.show_api_key)
        api_frame.setLayout(api_layout)
        
        # Bearer Token section
        bearer_frame = QFrame()
        bearer_layout = QVBoxLayout()
        bearer_layout.setSpacing(10)
        
        bearer_label = QLabel("🎫 Bearer Token:")
        bearer_label_font = QFont()
        bearer_label_font.setPointSize(12)
        bearer_label_font.setBold(True)
        bearer_label.setFont(bearer_label_font)
        bearer_label.setStyleSheet("color: #2c3e50; margin-bottom: 5px;")
        
        bearer_help = QLabel("Get this from the API page → 'Test' tab → Copy token after 'Bearer '")
        bearer_help_font = QFont()
        bearer_help_font.setPointSize(10)
        bearer_help.setFont(bearer_help_font)
        bearer_help.setStyleSheet("color: #6c757d; margin-bottom: 8px;")
        bearer_help.setWordWrap(True)
        
        self.bearer_input = QLineEdit()
        self.bearer_input.setPlaceholderText("Enter bearer token (without 'Bearer ' prefix)")
        self.bearer_input.setMinimumHeight(45)
        self.bearer_input.setFont(input_font)
        self.bearer_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                font-size: 11px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
            QLineEdit:hover {
                border-color: #80bdff;
            }
        """)
        self.bearer_input.setEchoMode(QLineEdit.Password)
        self.bearer_input.textChanged.connect(self.on_input_changed)
        
        self.show_bearer = QCheckBox("Show Bearer Token")
        self.show_bearer.setFont(checkbox_font)
        self.show_bearer.setStyleSheet("""
            QCheckBox {
                color: #6c757d;
                margin-top: 8px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
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
        """Create enhanced validation results section."""
        group = QGroupBox("Validation Results")
        group_font = QFont()
        group_font.setPointSize(14)
        group_font.setBold(True)
        group.setFont(group_font)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                margin-top: 15px;
                padding-top: 20px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #2c3e50;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 25, 20, 20)
        layout.setSpacing(15)
        
        self.validation_label = QLabel("Enter both credentials above and click 'Test' to verify")
        self.validation_label.setWordWrap(True)
        self.validation_label.setMinimumHeight(70)
        validation_font = QFont()
        validation_font.setPointSize(11)
        self.validation_label.setFont(validation_font)
        self.validation_label.setStyleSheet("""
            QLabel {
                padding: 18px;
                border: 2px solid #ddd;
                border-radius: 8px;
                background-color: #f8f9fa;
                color: #6c757d;
                line-height: 1.4;
            }
        """)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                text-align: center;
                background-color: #f8f9fa;
                font-size: 11px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 6px;
            }
        """)
        
        layout.addWidget(self.validation_label)
        layout.addWidget(self.progress_bar)
        group.setLayout(layout)
        
        return group
        
    def create_action_buttons(self) -> QFrame:
        """Create enhanced action buttons."""
        frame = QFrame()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 15, 0, 15)
        layout.setSpacing(20)
        
        button_font = QFont()
        button_font.setPointSize(12)
        button_font.setBold(True)
        
        self.test_btn = QPushButton("🧪 Test Credentials")
        self.test_btn.setEnabled(False)
        self.test_btn.setMinimumHeight(50)
        self.test_btn.setMinimumWidth(160)
        self.test_btn.setFont(button_font)
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                border: none;
                padding: 15px 25px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
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
        
        self.save_btn = QPushButton("💾 Save & Use")
        self.save_btn.setEnabled(False)
        self.save_btn.setMinimumHeight(50)
        self.save_btn.setMinimumWidth(140)
        self.save_btn.setFont(button_font)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 15px 25px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
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
        
        self.clear_btn = QPushButton("🗑️ Clear Saved")
        self.clear_btn.setMinimumHeight(50)
        self.clear_btn.setMinimumWidth(130)
        self.clear_btn.setFont(button_font)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 15px 25px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
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
        """Create enhanced help section using native Qt."""
        group = QGroupBox("Common Issues")
        group_font = QFont()
        group_font.setPointSize(14)
        group_font.setBold(True)
        group.setFont(group_font)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                margin-top: 15px;
                padding-top: 20px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #2c3e50;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 25, 20, 20)
        layout.setSpacing(12)
        
        issues = [
            ("401 Error:", "Wrong API key or bearer token - double-check both"),
            ("403 Error:", "No active subscription - visit API page and subscribe"),
            ("Connection Error:", "Check your internet connection"),
            ("Rate Limited:", "You're hitting API limits (normal for valid credentials)")
        ]
        
        for error_type, description in issues:
            issue_frame = QFrame()
            issue_layout = QHBoxLayout()
            issue_layout.setContentsMargins(15, 12, 15, 12)
            issue_layout.setSpacing(15)
            
            error_label = QLabel(error_type)
            error_font = QFont()
            error_font.setPointSize(11)
            error_font.setBold(True)
            error_label.setFont(error_font)
            error_label.setStyleSheet("color: #dc3545; min-width: 120px;")
            
            desc_label = QLabel(description)
            desc_font = QFont()
            desc_font.setPointSize(11)
            desc_label.setFont(desc_font)
            desc_label.setStyleSheet("color: #495057;")
            desc_label.setWordWrap(True)
            
            issue_layout.addWidget(error_label)
            issue_layout.addWidget(desc_label, 1)
            issue_frame.setLayout(issue_layout)
            issue_frame.setStyleSheet("""
                QFrame {
                    background-color: #fff3cd;
                    border: 2px solid #ffeaa7;
                    border-radius: 6px;
                }
            """)
            
            layout.addWidget(issue_frame)
        
        group.setLayout(layout)
        return group
        
    def create_bottom_buttons(self) -> QHBoxLayout:
        """Create enhanced bottom dialog buttons."""
        layout = QHBoxLayout()
        layout.setContentsMargins(25, 20, 25, 25)
        layout.setSpacing(20)
        
        button_font = QFont()
        button_font.setPointSize(12)
        button_font.setBold(True)
        
        close_btn = QPushButton("❌ Cancel")
        close_btn.setMinimumHeight(45)
        close_btn.setMinimumWidth(100)
        close_btn.setFont(button_font)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        close_btn.clicked.connect(self.reject)
        
        self.use_btn = QPushButton("✅ Use These Credentials")
        self.use_btn.setEnabled(False)
        self.use_btn.setMinimumHeight(45)
        self.use_btn.setMinimumWidth(180)
        self.use_btn.setFont(button_font)
        self.use_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
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
        """Load existing credentials with enhanced display."""
        saved_creds = self.authenticator.get_saved_credentials()
        
        if saved_creds:
            masked_key = f"{saved_creds['rapidapi_key'][:8]}...{saved_creds['rapidapi_key'][-4:]}"
            
            status_text = (
                f"✅ Found saved credentials: {masked_key}\n"
                f"Last validated: {saved_creds.get('last_validated', 'Unknown')}\n"
                f"Status: {'🟢 Working' if saved_creds.get('is_working', True) else '🔴 Issues detected'}"
            )
            
            self.status_label.setText(status_text)
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 20px;
                    border: 2px solid #c3e6cb;
                    border-radius: 8px;
                    background-color: #d4edda;
                    color: #155724;
                    line-height: 1.5;
                    font-weight: bold;
                }
            """)
            
            self.api_key_input.setText(saved_creds['rapidapi_key'])
            self.bearer_input.setText(saved_creds['bearer_token'])
            self.use_btn.setEnabled(True)
            self.clear_btn.setEnabled(True)
        else:
            status_text = (
                "⚠️ No saved credentials found\n"
                "Please follow the setup guide below to get started"
            )
            
            self.status_label.setText(status_text)
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 20px;
                    border: 2px solid #ffeaa7;
                    border-radius: 8px;
                    background-color: #fff3cd;
                    color: #856404;
                    line-height: 1.5;
                    font-weight: bold;
                }
            """)
            self.clear_btn.setEnabled(False)

    def open_api_page(self):
        """Open API page in browser."""
        QDesktopServices.openUrl(QUrl("https://rapidapi.com/abigdatacompany-abigdatacompany-default/api/enriched-cadastral-parcels-for-italy"))

    def on_input_changed(self):
        """Handle input changes with enhanced validation feedback."""
        has_both = bool(self.api_key_input.text().strip() and self.bearer_input.text().strip())
        self.test_btn.setEnabled(has_both)
        
        api_key = self.api_key_input.text().strip()
        bearer_token = self.bearer_input.text().strip()
        
        if api_key and len(api_key) < 20:
            self.validation_label.setText("⚠️ API key seems too short (should be 30+ characters)")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 18px;
                    border: 2px solid #ffeaa7;
                    border-radius: 8px;
                    background-color: #fff3cd;
                    color: #856404;
                    line-height: 1.4;
                    font-weight: bold;
                }
            """)
        elif bearer_token and len(bearer_token) < 10:
            self.validation_label.setText("⚠️ Bearer token seems too short")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 18px;
                    border: 2px solid #ffeaa7;
                    border-radius: 8px;
                    background-color: #fff3cd;
                    color: #856404;
                    line-height: 1.4;
                    font-weight: bold;
                }
            """)
        elif has_both:
            self.validation_label.setText("✅ Both credentials entered - click 'Test' to verify")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 18px;
                    border: 2px solid #bee5eb;
                    border-radius: 8px;
                    background-color: #d1ecf1;
                    color: #0c5460;
                    line-height: 1.4;
                    font-weight: bold;
                }
            """)
        else:
            self.validation_label.setText("Enter both credentials above and click 'Test' to verify")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 18px;
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    background-color: #f8f9fa;
                    color: #6c757d;
                    line-height: 1.4;
                }
            """)

    def toggle_api_key_visibility(self, checked):
        """Toggle API key visibility."""
        self.api_key_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        
    def toggle_bearer_visibility(self, checked):
        """Toggle bearer token visibility."""
        self.bearer_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    def test_credentials(self):
        """Test credentials with enhanced UI feedback."""
        api_key = self.api_key_input.text().strip()
        bearer_token = self.bearer_input.text().strip()
        
        if not api_key or not bearer_token:
            self.validation_label.setText("❌ Please enter both credentials")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.test_btn.setText("🔄 Testing...")
        self.test_btn.setEnabled(False)
        
        QApplication.processEvents()
        
        is_valid, message = self.authenticator.validate_credentials(api_key, bearer_token)
        
        self.progress_bar.setVisible(False)
        self.test_btn.setText("🧪 Test Credentials")
        self.test_btn.setEnabled(True)
        
        if is_valid:
            self.validation_label.setText(f"✅ {message} - Credentials are working!")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 18px;
                    border: 2px solid #c3e6cb;
                    border-radius: 8px;
                    background-color: #d4edda;
                    color: #155724;
                    line-height: 1.4;
                    font-weight: bold;
                }
            """)
            self.save_btn.setEnabled(True)
            self.use_btn.setEnabled(True)
        else:
            self.validation_label.setText(f"❌ {message}")
            self.validation_label.setStyleSheet("""
                QLabel {
                    padding: 18px;
                    border: 2px solid #f5c6cb;
                    border-radius: 8px;
                    background-color: #f8d7da;
                    color: #721c24;
                    line-height: 1.4;
                    font-weight: bold;
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
            QMessageBox.information(self, "Success", "✅ Credentials saved successfully!\nYou can now use the plugin.")
            self.load_existing_credentials()
            self.accept_credentials()
        else:
            QMessageBox.critical(self, "Error", "❌ Failed to save credentials. Please try again.")

    def clear_credentials(self):
        """Clear saved credentials with confirmation."""
        reply = QMessageBox.question(
            self, "Clear Credentials", 
            "Are you sure you want to clear all saved credentials?\nYou'll need to enter them again next time.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.authenticator.clear_credentials():
                QMessageBox.information(self, "Cleared", "✅ Credentials cleared successfully.")
                self.api_key_input.clear()
                self.bearer_input.clear()
                self.validation_label.setText("Enter both credentials above and click 'Test' to verify")
                self.validation_label.setStyleSheet("""
                    QLabel {
                        padding: 18px;
                        border: 2px solid #ddd;
                        border-radius: 8px;
                        background-color: #f8f9fa;
                        color: #6c757d;
                        line-height: 1.4;
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
