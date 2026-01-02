# license_window.py
"""
Окно активации лицензии - ИСПРАВЛЕННАЯ ВЕРСИЯ С СОВРЕМЕННЫМ ДИЗАЙНОМ
"""

import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QProgressBar,
                             QMessageBox, QGroupBox, QTabWidget, QWidget,
                             QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from license_client import LicenseClient

class LicenseActivationThread(QThread):
    """Поток для активации лицензии"""
    
    activation_finished = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, license_client, license_key, client_name, saby_profile_url):
        super().__init__()
        self.license_client = license_client
        self.license_key = license_key
        self.client_name = client_name
        self.saby_profile_url = saby_profile_url
    
    def run(self):
        try:
            self.progress_updated.emit(30)
            result = self.license_client.activate_license(
                self.license_key, 
                self.client_name,
                self.saby_profile_url
            )
            self.progress_updated.emit(100)
            self.activation_finished.emit(result)
        except Exception as e:
            self.activation_finished.emit({"success": False, "error": str(e)})

class LicenseDialog(QDialog):
    """Диалог активации лицензии - СОВРЕМЕННАЯ ВЕРСИЯ"""
    
    def __init__(self, license_client, parent=None):
        super().__init__(parent)
        self.license_client = license_client
        self.logger = logging.getLogger(__name__)
        
        self.setWindowTitle("🎯 Активация лицензии")
        self.setFixedSize(700, 600)
        self.setStyleSheet("""
            LicenseDialog {
                background-color: #2a2c36;
                color: #f8f8f2;
            }
        """)
        
        self._setup_ui()
        self._load_current_license_info()
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title = QLabel("Активация лицензии")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #f8f8f2; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #6272a4;
                border-radius: 5px;
                background-color: #44475a;
            }
            QTabBar::tab {
                background-color: #44475a;
                color: #f8f8f2;
                padding: 8px 16px;
                border: 1px solid #6272a4;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #6272a4;
            }
            QTabBar::tab:hover {
                background-color: #7282b4;
            }
        """)
        
        # Вкладка активации
        self.activation_tab = self._create_activation_tab()
        self.tabs.addTab(self.activation_tab, "🔑 Активация")
        
        # Вкладка информации
        self.info_tab = self._create_info_tab()
        self.tabs.addTab(self.info_tab, "📊 Информация")
        
        layout.addWidget(self.tabs)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.activate_btn = QPushButton("🎯 Активировать")
        self.activate_btn.setStyleSheet(self._get_button_style())
        self.activate_btn.clicked.connect(self._activate_license)
        
        self.deactivate_btn = QPushButton("❌ Деактивировать")
        self.deactivate_btn.setStyleSheet(self._get_button_style())
        self.deactivate_btn.clicked.connect(self._deactivate_license)
        
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.setStyleSheet(self._get_button_style())
        self.close_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.activate_btn)
        button_layout.addWidget(self.deactivate_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #6272a4;
                border-radius: 5px;
                text-align: center;
                color: #f8f8f2;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #50fa7b;
            }
        """)
        layout.addWidget(self.progress_bar)
    
    def _get_button_style(self):
        return """
            QPushButton {
                background-color: #6272a4;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7282b4;
            }
            QPushButton:pressed {
                background-color: #526294;
            }
            QPushButton:disabled {
                background-color: #404352;
                color: #888888;
            }
        """
    
    def _create_activation_tab(self):
        """Создание вкладки активации"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Группа ввода данных
        input_group = QGroupBox("Данные для активации")
        input_group.setStyleSheet("""
            QGroupBox {
                color: #f8f8f2;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #6272a4;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        input_layout = QFormLayout(input_group)
        
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("Введите ваш лицензионный ключ...")
        self.license_input.setStyleSheet("""
            QLineEdit {
                background-color: #44475a;
                color: #f8f8f2;
                border: 1px solid #6272a4;
                padding: 8px;
                border-radius: 4px;
            }
        """)
        input_layout.addRow("Лицензионный ключ:", self.license_input)
        
        self.client_name_input = QLineEdit()
        self.client_name_input.setPlaceholderText("Введите ваше имя...")
        self.client_name_input.setStyleSheet(self.license_input.styleSheet())
        input_layout.addRow("Ваше имя:*", self.client_name_input)
        
        self.saby_profile_input = QLineEdit()
        self.saby_profile_input.setPlaceholderText("https://online.sbis.ru/person/... (необязательно)")
        self.saby_profile_input.setStyleSheet(self.license_input.styleSheet())
        input_layout.addRow("Профиль Saby:", self.saby_profile_input)
        
        layout.addWidget(input_group)
        
        # Группа информации об устройстве
        device_group = QGroupBox("Информация об устройстве")
        device_group.setStyleSheet(input_group.styleSheet())
        device_layout = QFormLayout(device_group)
        
        self.device_id_label = QLabel(self.license_client.hardware_id)
        self.device_id_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.device_id_label.setStyleSheet("""
            QLabel {
                background-color: #44475a;
                color: #f8f8f2;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #6272a4;
            }
        """)
        
        self.machine_name_label = QLabel(self.license_client._get_machine_name())
        self.machine_name_label.setStyleSheet(self.device_id_label.styleSheet())
        
        device_layout.addRow("ID устройства:", self.device_id_label)
        device_layout.addRow("Имя компьютера:", self.machine_name_label)
        
        layout.addWidget(device_group)
        
        # Результат активации
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(100)
        self.result_text.setStyleSheet("""
            QTextEdit {
                background-color: #44475a;
                color: #f8f8f2;
                border: 1px solid #6272a4;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.result_text)
        
        layout.addStretch()
        
        return widget
    
    def _create_info_tab(self):
        """Создание вкладки информации"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.license_info_text = QTextEdit()
        self.license_info_text.setReadOnly(True)
        self.license_info_text.setStyleSheet("""
            QTextEdit {
                background-color: #44475a;
                color: #f8f8f2;
                border: 1px solid #6272a4;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        
        layout.addWidget(QLabel("Информация о лицензии:"))
        layout.addWidget(self.license_info_text)
        
        # Кнопка обновления информации
        refresh_btn = QPushButton("🔄 Обновить информацию")
        refresh_btn.setStyleSheet(self._get_button_style())
        refresh_btn.clicked.connect(self._load_current_license_info)
        layout.addWidget(refresh_btn)
        
        return widget
    
    def _load_current_license_info(self):
        """Загрузка информации о текущей лицензии"""
        if self.license_client.is_license_active():
            info = self.license_client.get_license_info()
            if info:
                self._display_license_info(info)
            else:
                self.license_info_text.setPlainText("Не удалось загрузить информацию о лицензии")
        else:
            self.license_info_text.setPlainText("Лицензия не активирована")
    
    def _display_license_info(self, info):
        """Отображение информации о лицензии"""
        text = f"""🎯 ИНФОРМАЦИЯ О ЛИЦЕНЗИИ

🔑 Ключ: {info.get('license_key', 'N/A')}
👤 Пользователь: {info.get('client_name', 'N/A')}
🌐 IP активации: {info.get('ip_address', 'N/A')}
🔗 Профиль Saby: {info.get('saby_profile_url', 'N/A')}
📅 Создана: {info.get('created_at', 'N/A')}
⏰ Активирована: {info.get('activated_at', 'N/A')}
📆 Срок действия: {info.get('expires_at', 'N/A')}
♾️ Тип: {'Бессрочная' if info.get('is_permanent') else 'Временная'}

📊 АКТИВАЦИИ:
• Текущие: {info.get('current_activations', 0)}
• Максимум: {info.get('max_activations', 0)}

🎯 СТАТУС: {"✅ АКТИВНА" if info.get('is_active') else "❌ НЕАКТИВНА"}
"""

        self.license_info_text.setPlainText(text)
    
    def _activate_license(self):
        """Активация лицензии"""
        license_key = self.license_input.text().strip()
        client_name = self.client_name_input.text().strip()
        saby_profile_url = self.saby_profile_input.text().strip()
        
        if not license_key:
            self._show_message("Ошибка", "Введите лицензионный ключ")
            return
        
        if not client_name:
            self._show_message("Ошибка", "Введите ваше имя")
            return
        
        # Показываем прогресс
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.activate_btn.setEnabled(False)
        
        # Запускаем активацию в отдельном потоке
        self.activation_thread = LicenseActivationThread(
            self.license_client, license_key, client_name, saby_profile_url
        )
        
        self.activation_thread.activation_finished.connect(self._on_activation_finished)
        self.activation_thread.progress_updated.connect(self.progress_bar.setValue)
        
        self.activation_thread.start()
    
    def _on_activation_finished(self, result):
        """Обработка завершения активации"""
        self.progress_bar.setVisible(False)
        self.activate_btn.setEnabled(True)
        
        if result.get('success'):
            self.result_text.setPlainText(f"✅ {result.get('message', 'Лицензия активирована!')}")
            self._show_message("Успех", "✅ Лицензия успешно активирована!")
            self._load_current_license_info()
            self.accept()  # Закрываем диалог с успехом
        else:
            error_msg = result.get('error', 'Неизвестная ошибка')
            self.result_text.setPlainText(f"❌ Ошибка: {error_msg}")
            self._show_message("Ошибка", f"Не удалось активировать лицензию:\n{error_msg}")
    
    def _deactivate_license(self):
        """Деактивация лицензии"""
        reply = QMessageBox.question(
            self, 
            "Подтверждение", 
            "Вы уверены, что хотите деактивировать лицензию?\n\n"
            "После деактивации приложение перестанет работать.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.license_client.deactivate_license():
                self._show_message("Успех", "Лицензия деактивирована")
                self._load_current_license_info()
    
    def _show_message(self, title, message):
        """Показать сообщение"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2a2c36;
                color: #f8f8f2;
            }
            QMessageBox QLabel {
                color: #f8f8f2;
            }
        """)
        msg_box.exec_()