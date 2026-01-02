"""
Главное окно приложения Saby Helper - ОБНОВЛЕННАЯ ВЕРСИЯ С БАЗОВЫМИ МЕХАНИЗМАМИ И ПЛАТЕЖНЫМИ ТЕРМИНАЛАМИ
"""

import os
import logging
import sys
import requests
import platform
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QFileDialog, 
                             QTextEdit, QProgressBar, QGroupBox, QTabWidget, 
                             QMessageBox, QFrame, QStatusBar, QApplication,
                             QStackedWidget, QListWidget, QListWidgetItem,
                             QFormLayout, QDialog, QDateEdit, QCheckBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QToolButton, QRadioButton, QButtonGroup, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QTimer, QUrl
from PyQt5.QtGui import QFont, QColor, QDesktopServices, QIcon

from analyzer import ErrorAnalyzer
from report_generator import ReportGenerator
from pdf_generator import PDFReportGenerator
from license_client import LicenseClient
from license_window import LicenseDialog
from config import DEPARTMENTS, MONTHS, CURRENT_YEAR, APP_VERSION, CONTACT_INFO
from update_manager import UpdateManager, UpdateChecker
from log_analyzer import SupportLogAnalyzer
from marking_analyzer import MarkingLogAnalyzer
from basic_mechanisms_analyzer import BasicMechanismsAnalyzer
from payment_terminal_analyzer import PaymentTerminalAnalyzer
from modules.settings_manager import SettingsManager
from modules.log_downloader import LogDownloader

# Импортируем модули с компонентами
from ui_components.dialogs import OperationsHelpDialog, UpdateDialog
from ui_components.threads import (AnalysisThread, ServerCheckThread, LogAnalysisThread, 
                                   MarkingAnalysisThread, BasicMechanismsThread, PaymentTerminalThread)
from ui_components.pages import (create_home_page, create_error_analyzer_page, 
                               create_log_analyzer_page, create_settings_page,
                               create_log_download_page)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class MainWindow(QMainWindow):
    """Главное окно приложения Saby Helper - ОБНОВЛЕННАЯ ВЕРСИЯ"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.current_file = None
        self.analysis_result = None
        self.current_log_archive = None
        self.current_log_analysis_result = None
        self.current_marking_archive = None
        self.current_marking_analysis_result = None
        self.current_basic_archive = None
        self.current_basic_analysis_result = None
        
        # Инициализация менеджера настроек
        self.settings_manager = SettingsManager()
        
        # Инициализация клиента лицензий
        self.license_client = LicenseClient("http://155.212.171.112:5000")
        
        # Инициализация менеджера обновлений
        self.update_manager = UpdateManager()
        self.update_manager.license_client = self.license_client
        
        self._setup_ui()
        self._create_status_bar()
        
        # Загружаем настройки автообновления
        self._load_settings()
        
        # Таймер для проверки сервера каждые 10 минут
        self.server_check_timer = QTimer()
        self.server_check_timer.timeout.connect(self._check_server_status)
        self.server_check_timer.start(600000)
        
        # Проверка лицензии при запуске
        self._check_license_on_startup()
        
        # Первоначальная проверка сервера
        self._check_server_status()
        
        # Запуск проверки обновлений (с учетом настроек)
        QTimer.singleShot(3000, self._check_for_updates_silent)
        
        self.logger.info("Главное окно Saby Helper инициализировано")
    
    def _setup_ui(self):
        """Настройка современного пользовательского интерфейса"""
        self.setWindowTitle(f"Saby Helper v{APP_VERSION}")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 700)
        
        # Устанавливаем иконку приложения
        self._set_window_icon()
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Создаем навигационную панель слева
        self.nav_panel = self._create_navigation_panel()
        main_layout.addWidget(self.nav_panel)
        
        # Создаем стек виджетов для контента
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, 1)
        
        # Добавляем страницы в правильном порядке
        self.home_page = create_home_page(self)
        self.error_analyzer_page = create_error_analyzer_page(self)
        self.log_analyzer_page = create_log_analyzer_page(self)
        self.log_download_page = create_log_download_page(self)
        self.settings_page = create_settings_page(self)
        
        self.content_stack.addWidget(self.home_page)               # 0: Главная
        self.content_stack.addWidget(self.error_analyzer_page)     # 1: Аналитика ошибок
        self.content_stack.addWidget(self.log_analyzer_page)       # 2: Анализ логов
        self.content_stack.addWidget(self.log_download_page)       # 3: Выгрузка логов
        self.content_stack.addWidget(self.settings_page)           # 4: Настройки
        
        # Показываем домашнюю страницу
        self.content_stack.setCurrentWidget(self.home_page)
    
    def _set_window_icon(self):
        """Установка иконки окна"""
        try:
            from PyQt5.QtGui import QPixmap, QPainter
            from PyQt5.QtCore import QSize
            
            icon_path = Path(__file__).parent / "icon.ico"
            if icon_path.exists():
                absolute_path = str(icon_path.resolve())
                app_icon = QIcon(absolute_path)
                self.setWindowIcon(app_icon)
                self.logger.info(f"Иконка окна установлена: {absolute_path}")
                
                # Для Windows устанавливаем AppUserModelID для корректного отображения в панели задач
                if sys.platform == "win32":
                    try:
                        import ctypes
                        myappid = u'SabyHelper.App.1.5.3'
                        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                        self.logger.info(f"Установлен AppUserModelID для Windows: {myappid}")
                    except Exception as win_e:
                        self.logger.warning(f"Не удалось установить Windows AppUserModelID: {win_e}")
            else:
                self.logger.warning(f"Файл иконки не найден: {icon_path}")
                # Создаем простую иконку
                pixmap = QPixmap(64, 64)
                pixmap.fill(Qt.transparent)
                
                painter = QPainter(pixmap)
                painter.setPen(QColor(98, 114, 164))
                painter.setBrush(QColor(98, 114, 164))
                painter.drawEllipse(0, 0, 64, 64)
                
                painter.setPen(QColor(248, 248, 242))
                painter.setFont(QFont("Arial", 24))
                painter.drawText(pixmap.rect(), Qt.AlignCenter, "SH")
                painter.end()
                
                app_icon = QIcon(pixmap)
                self.setWindowIcon(app_icon)
                self.logger.info("Создана простая иконка для окна")
        except Exception as e:
            self.logger.error(f"Ошибка установки иконки окна: {e}")
    
    def _create_navigation_panel(self):
        """Создание навигационной панели"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMinimumWidth(280)
        panel.setMaximumWidth(320)
        panel.setStyleSheet("""
            QFrame {
                background-color: #2a2c36;
                border-right: 1px solid #404352;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                color: #f8f8f2;
                font-size: 14px;
                outline: none;
            }
            QListWidget::item {
                padding: 15px 20px;
                border-bottom: 1px solid #404352;
                height: 25px;
            }
            QListWidget::item:selected {
                background-color: #6272a4;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #404352;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Заголовок приложения
        title_widget = QWidget()
        title_widget.setFixedHeight(100)
        title_widget.setStyleSheet("background-color: #1e1f29;")
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(10, 15, 10, 15)
        
        app_title = QLabel("Saby Helper")
        app_title.setAlignment(Qt.AlignCenter)
        app_title.setStyleSheet("""
            QLabel {
                color: #f8f8f2;
                font-size: 22px;
                font-weight: bold;
                padding: 5px;
                margin: 0px;
            }
        """)
        
        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #6272a4; font-size: 12px; margin: 0px;")
        
        title_layout.addWidget(app_title)
        title_layout.addWidget(version_label)
        
        layout.addWidget(title_widget)
        
        # Навигационный список с правильным порядком
        self.nav_list = QListWidget()
        self.nav_list.addItems(["🏠 Главная", "📊 Аналитика ошибок", "📝 Анализ логов", "📥 Выгрузка логов", "⚙️ Настройки"])
        self.nav_list.currentRowChanged.connect(self._on_navigation_changed)
        
        layout.addWidget(self.nav_list)
        
        # Дополнительные кнопки в навигации
        nav_buttons_widget = QWidget()
        nav_buttons_widget.setStyleSheet("background-color: #1e1f29; padding: 10px;")
        nav_buttons_layout = QVBoxLayout(nav_buttons_widget)
        
        update_btn = QPushButton("🔄 Проверить обновления")
        update_btn.setStyleSheet(self._get_nav_button_style())
        update_btn.clicked.connect(self._show_update_dialog)
        
        exit_btn = QPushButton("🚪 Выход")
        exit_btn.setStyleSheet(self._get_nav_button_style())
        exit_btn.clicked.connect(self.close)
        
        nav_buttons_layout.addWidget(update_btn)
        nav_buttons_layout.addWidget(exit_btn)
        
        layout.addWidget(nav_buttons_widget)
        
        # Информация о лицензии внизу
        license_widget = QWidget()
        license_widget.setStyleSheet("background-color: #1e1f29; padding: 15px;")
        license_layout = QVBoxLayout(license_widget)
        
        self.server_status_nav = QLabel("Сервер: Проверка...")
        self.server_status_nav.setStyleSheet("color: #ffb86c; font-size: 11px;")
        self.server_status_nav.setWordWrap(True)
        
        license_layout.addWidget(self.server_status_nav)
        
        sabik_btn = QPushButton("💝 Отправить сабик")
        sabik_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff79c6;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 5px;
                font-size: 11px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #ff92d0;
            }
        """)
        sabik_btn.clicked.connect(self._send_sabik)
        
        license_layout.addWidget(sabik_btn)
        
        layout.addWidget(license_widget)
        
        return panel

    def _load_settings(self):
        """Загрузка настроек приложения"""
        auto_update_enabled = self.settings_manager.get_auto_update_enabled()
        self.auto_update_check.setChecked(auto_update_enabled)
        
        last_check = self.settings_manager.get_last_update_check()
        if last_check:
            self.last_update_check_label.setText(f"Дата последней проверки: {last_check}")
    
    def _on_auto_update_changed(self, state):
        """Обработчик изменения настройки автообновления"""
        enabled = state == Qt.Checked
        self.settings_manager.set_auto_update_enabled(enabled)
        self.logger.info(f"Автообновление {'включено' if enabled else 'выключено'}")
    
    def _download_logs(self):
        """Выгрузка диагностических логов"""
        incident_number = self.incident_input.text().strip()
        
        if not incident_number:
            self._show_silent_message("Ошибка", "Введите номер диагностической карты")
            return
        
        if not incident_number.isdigit():
            self._show_silent_message("Ошибка", "Номер диагностической карты должен содержать только цифры!")
            return
        
        # Используем модуль LogDownloader
        success = LogDownloader.download_logs(incident_number, self)
        
        if success:
            self.ready_status.setText(f"Ссылка для скачивания открыта (инцидент {incident_number})")
            QTimer.singleShot(3000, lambda: self.ready_status.setText("Готов"))
        else:
            self.ready_status.setText("Ошибка открытия ссылки")

    # ===== ОБРАБОТЧИКИ СИГНАЛОВ =====
    def _on_navigation_changed(self, index):
        """Обработка изменения навигации"""
        self.content_stack.setCurrentIndex(index)
    
    def _switch_to_page(self, page_index):
        """Переключение на указанную страницу"""
        self.nav_list.setCurrentRow(page_index)
        self.content_stack.setCurrentIndex(page_index)

    # ===== ДИАЛОГИ =====
    def _show_operations_help_dialog(self):
        """Показать диалог помощи по операциям"""
        dialog = OperationsHelpDialog(self)
        dialog.resize(500, 350)
        
        main_window_rect = self.frameGeometry()
        dialog_rect = dialog.frameGeometry()
        dialog.move(main_window_rect.center() - dialog_rect.center())
        
        dialog.exec_()

    def _show_update_dialog(self):
        """Показать диалог обновлений"""
        try:
            dialog = UpdateDialog(self.update_manager, self)
            dialog.resize(500, 300)
            
            main_window_rect = self.frameGeometry()
            dialog_rect = dialog.frameGeometry()
            dialog.move(main_window_rect.center() - dialog_rect.center())
            
            dialog.exec_()
        except Exception as e:
            self.logger.error(f"Ошибка показа диалога обновлений: {e}")
            self._show_silent_message("Ошибка", f"Не удалось открыть окно обновлений: {str(e)}")

    def _show_silent_message(self, title, message):
        """Бесшумное сообщение"""
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

    # ===== УТИЛИТИ =====
    def _send_sabik(self):
        """Открыть страницу для отправки сабика"""
        QDesktopServices.openUrl(QUrl("https://online.sbis.ru/person/5602d216-cf53-45db-9f92-8530f395305c"))
        
        self.ready_status.setText("💝 Спасибо за поддержку!")
        QTimer.singleShot(3000, lambda: self.ready_status.setText("Готов"))

    def closeEvent(self, event):
        """Обработка закрытия приложения"""
        self.logger.info("Приложение Saby Helper закрывается")
        event.accept()

    # ===== СИСТЕМА ОБНОВЛЕНИЙ =====
    def _check_for_updates_silent(self):
        """Тихая проверка обновлений при запуске"""
        try:
            if hasattr(self, 'update_manager'):
                self.logger.info("Запуск тихой проверки обновлений при запуске")
                
                # Проверяем настройку автообновления
                auto_update_enabled = self.settings_manager.get_auto_update_enabled()
                
                if auto_update_enabled:
                    self.logger.info("Автообновление включено, запускаем автоматическую проверку")
                    
                    def check_callback(success, update_info):
                        if success and update_info:
                            self.logger.info(f"Обновление найдено: {update_info['latest_version']}")
                            
                            # Проверяем, является ли обновление обязательным
                            if update_info.get('force_update'):
                                self.logger.info("ОБЯЗАТЕЛЬНОЕ обновление, запускаем автоматическую установку")
                                self._perform_auto_update(update_info)
                            else:
                                self.logger.info("Обычное обновление, показываем диалог")
                                try:
                                    from ui_components.dialogs import UpdateDialog
                                    dialog = UpdateDialog(self.update_manager, self)
                                    dialog.set_update_info(update_info)
                                    dialog.exec_()
                                except Exception as e:
                                    self.logger.error(f"❌ Ошибка показа диалога обновлений: {e}")
                        else:
                            self.logger.info("✅ Автоматическая проверка: обновлений нет")
                    
                    # Запускаем асинхронную проверку
                    self.update_manager.check_for_updates_async(check_callback)
                else:
                    self.logger.info("Автообновление выключено, проверку не выполняем")
                    
        except Exception as e:
            self.logger.error(f"Ошибка тихой проверки обновлений: {e}")

    def _perform_auto_update(self, update_info):
        """Выполнение автоматического обновления"""
        try:
            self.logger.info(f"🚀 Запуск автоматического обновления до версии {update_info['latest_version']}")
            
            # Обновляем дату последней проверки
            self.settings_manager.set_last_update_check(datetime.now().strftime("%Y-%m-%d %H:%M"))
            
            # Запускаем загрузку и установку обновления
            self.update_manager.download_and_install_update(update_info, self)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка автоматического обновления: {e}")

    # ===== ЛИЦЕНЗИЯ =====
    def _check_license_on_startup(self):
        """Проверка лицензии при запуске"""
        self._update_license_display()
    
        # Проверяем наличие license_client
        if not hasattr(self, 'license_client') or self.license_client is None:
            self._show_silent_message(
                "Ошибка лицензии", 
                "Клиент лицензий не инициализирован.\n\nПожалуйста, перезапустите приложение."
            )
            self._enable_application(False)
            return
    
        if not self.license_client.is_license_active():
            self._show_license_dialog(required=True)
        else:
            try:
                validation = self.license_client.validate_license()
                if not validation.get('valid'):
                    self._show_silent_message(
                        "Проблема с лицензией", 
                        f"Лицензия недействительна:\n{validation.get('error')}\n\nПожалуйста, активируйте лицензию заново.\n\nДля помощи: {CONTACT_INFO}"
                    )
                    self._show_license_dialog(required=True)
                else:
                    self._enable_application(True)
            except Exception as e:
                self.logger.error(f"Ошибка проверки лицензии: {e}")
                self._show_silent_message(
                    "Ошибка проверки лицензии", 
                    f"Не удалось проверить лицензию:\n{str(e)}\n\nПожалуйста, активируйте лицензию заново."
                )
                self._show_license_dialog(required=True)
    
    def _update_license_display(self):
        """Обновление отображения статуса лицензии"""
        # Проверяем наличие license_client
        if not hasattr(self, 'license_client') or self.license_client is None:
            self.license_status_home.setText("❌ Лицензия не инициализирована")
            self.license_status_home.setStyleSheet("color: #ff5555; font-size: 14px;")
            self.license_info_home.setText("Ошибка инициализации клиента лицензий")
            return
    
        try:
            license_active = self.license_client.is_license_active()
        except Exception as e:
            self.logger.error(f"Ошибка проверки активности лицензии: {e}")
            license_active = False
    
        status_text = "✅ Активна" if license_active else "❌ Не активирована"
        status_color = "#50fa7b" if license_active else "#ff5555"
    
        self.license_status_home.setText(status_text)
        self.license_status_home.setStyleSheet(f"color: {status_color}; font-size: 14px;")
    
        if license_active:
            try:
                info = self.license_client.get_license_info()
                if info and isinstance(info, dict):
                    client_name = info.get('client_name', 'Не указан')
                    display_name = client_name.replace("Клиент", "Пользователь").replace("клиент", "пользователь")
                    expires_at = info.get('expires_at', 'Не указан')
                    if expires_at and isinstance(expires_at, str) and len(expires_at) >= 10:
                        expires_at = expires_at[:10]
                    else:
                        expires_at = 'Бессрочная'
                    
                    self.license_info_home.setText(f"Пользователь: {display_name}\nСрок: {expires_at}")
                else:
                    self.license_info_home.setText("✅ Лицензия активна (детали недоступны)")
            except Exception as e:
                self.logger.error(f"Ошибка получения информации о лицензии: {e}")
                self.license_info_home.setText("✅ Лицензия активна (ошибка получения деталей)")
        else:
            self.license_info_home.setText("Для работы приложения требуется активация")
    
    def _enable_application(self, enabled):
        """Включение/выключение функциональности приложения"""
        for i in range(1, self.nav_list.count()):
            item = self.nav_list.item(i)
            if enabled:
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            else:
                item.setFlags(Qt.NoItemFlags)
        
        if hasattr(self, 'load_file_btn'):
            self.load_file_btn.setEnabled(enabled)
        if hasattr(self, 'department_combo'):
            self.department_combo.setEnabled(enabled)
        if hasattr(self, 'month_combo'):
            self.month_combo.setEnabled(enabled)
        if hasattr(self, 'analyze_btn'):
            self.analyze_btn.setEnabled(enabled and self.current_file is not None)
        if hasattr(self, 'export_btn'):
            self.export_btn.setEnabled(enabled and self.analysis_result is not None)
    
    def _show_license_dialog(self, required=False):
        """Показать диалог активации лицензии"""
        try:
            dialog = LicenseDialog(self.license_client, self)
            
            if required:
                dialog.setWindowTitle("🎯 Активация лицензии (Обязательно)")
                dialog.setWindowModality(Qt.ApplicationModal)
            
            main_window_rect = self.frameGeometry()
            dialog_rect = dialog.frameGeometry()
            dialog.move(main_window_rect.center() - dialog_rect.center())
            
            def on_license_activated():
                self._update_license_display()
                self._enable_application(True)
                self._show_silent_message("Успех", "✅ Лицензия успешно активирована!")
            
            def on_license_rejected():
                if required:
                    self._show_silent_message(
                        "Лицензия не активирована",
                        f"Без активированной лицензии приложение не может работать.\n\nДля активации обратитесь к администратору:\n{CONTACT_INFO}"
                    )
                    self._enable_application(False)
            
            dialog.accepted.connect(on_license_activated)
            dialog.rejected.connect(on_license_rejected)
            
            dialog.show()
            
        except Exception as e:
            self.logger.error(f"Ошибка показа диалога лицензии: {e}")
            self._show_silent_message("Ошибка", f"Не удалось открыть окно активации лицензии: {str(e)}")

    # ===== СЕРВЕРЫ =====
    def _check_server_status(self):
        """Проверка статуса сервера лицензий"""
        try:
            session = requests.Session()
            session.trust_env = False
            
            response = session.get("http://155.212.171.112:5000/health", timeout=5)
            
            if response.status_code == 200:
                self.server_status_nav.setText("Сервер: ✅ Онлайн")
                self.server_status_nav.setStyleSheet("color: #50fa7b; font-size: 11px;")
            else:
                self.server_status_nav.setText("Сервер: ⚠️ Проблемы")
                self.server_status_nav.setStyleSheet("color: #ffb86c; font-size: 11px;")
                
        except Exception as e:
            self.server_status_nav.setText("Сервер: ❌ Оффлайн")
            self.server_status_nav.setStyleSheet("color: #ff5555; font-size: 11px;")
    
    def _check_servers_manual(self):
        """Ручная проверка серверов"""
        self.ready_status.setText("Проверка серверов...")
        
        self.server_check_thread = ServerCheckThread()
        self.server_check_thread.check_finished.connect(self._on_server_check_finished)
        self.server_check_thread.start()
    
    def _on_server_check_finished(self, results):
        """Обработка завершения проверки серверов"""
        status_text = "🌐 Статус серверов:\n\n"
        
        if 'saby' in results:
            saby_result = results['saby']
            status_text += f"• Saby Online: {saby_result['status']}"
            if 'response_time' in saby_result:
                status_text += f" ({saby_result['response_time']:.2f} сек)\n"
            else:
                status_text += f"\n   Ошибка: {saby_result.get('error', 'Неизвестно')}\n"
        
        if 'update_server' in results:
            update_result = results['update_server']
            status_text += f"• Сервер обновлений: {update_result['status']}"
            if 'response_time' in update_result:
                status_text += f" ({update_result['response_time']:.2f} сек)\n"
            else:
                status_text += f"\n   Ошибка: {update_result.get('error', 'Неизвестно')}\n"
        
        if 'license_server' in results:
            license_result = results['license_server']
            status_text += f"• Сервер лицензий: {license_result['status']}"
            if 'response_time' in license_result:
                status_text += f" ({license_result['response_time']:.2f} сек)\n"
            else:
                status_text += f"\n   Ошибка: {license_result.get('error', 'Неизвестно')}\n"
        
        self.server_status_home.setText(status_text)
        self.ready_status.setText("Готов")

    # ===== СТИЛИ =====
    def _get_button_style(self):
        return """
            QPushButton {
                background-color: #6272a4;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 5px;
                font-size: 14px;
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
    
    def _get_nav_button_style(self):
        return """
            QPushButton {
                background-color: #44475a;
                color: #f8f8f2;
                border: 1px solid #6272a4;
                padding: 10px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #6272a4;
            }
            QPushButton:pressed {
                background-color: #526294;
            }
        """
    
    def _get_tool_button_style(self):
        return """
            QPushButton {
                background-color: #44475a;
                color: #f8f8f2;
                border: 2px solid #6272a4;
                padding: 15px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #6272a4;
                border-color: #7282b4;
            }
            QPushButton:pressed {
                background-color: #526294;
            }
        """

    def _create_status_bar(self):
        """Создание статусной строки"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        version_label = QLabel(f"v{APP_VERSION}")
        status_bar.addPermanentWidget(version_label)
        
        author_label = QLabel(f"by Aleksey Pankratov | {CONTACT_INFO}")
        author_label.setStyleSheet("color: #6272a4;")
        status_bar.addPermanentWidget(author_label)
        
        self.ready_status = QLabel("Готов")
        status_bar.addWidget(self.ready_status)

    # ===== АНАЛИЗ ОШИБОК =====
    def _load_file(self):
        """Загрузка файла Excel"""
        if not self.license_client.is_license_active():
            self._show_silent_message(
                "Лицензия не активирована",
                "Для загрузки файлов необходимо активировать лицензию."
            )
            self._show_license_dialog()
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл отчета",
            "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        
        if file_path:
            self.current_file = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.analyze_btn.setEnabled(True)
            self.ready_status.setText(f"Загружен: {os.path.basename(file_path)}")
            self.logger.info(f"Файл загружен: {file_path}")
    
    def _start_analysis(self):
        """Запуск анализа ошибок"""
        if not self.license_client.is_license_active():
            self._show_silent_message(
                "Лицензия не активирована",
                "Для выполнения анализа необходимо активировать лицензию."
            )
            self._show_license_dialog()
            return
        
        if not self.current_file:
            self._show_silent_message("Ошибка", "Сначала выберите файл для анализа")
            return
        
        validation = self.license_client.validate_license()
        if not validation.get('valid'):
            self._show_silent_message(
                "Проблема с лицензией",
                f"Не удалось проверить лицензию:\n{validation.get('error')}\n\nПожалуйста, активируйте лицензию заново."
            )
            self._show_license_dialog()
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.analyze_btn.setEnabled(False)
        self.ready_status.setText("Выполняется анализ...")
        
        from ui_components.threads import AnalysisThread
        self.analysis_thread = AnalysisThread(
            self.current_file,
            self.department_combo.currentText(),
            self.month_combo.currentText()
        )
        
        self.analysis_thread.analysis_finished.connect(self._on_analysis_finished)
        self.analysis_thread.analysis_error.connect(self._on_analysis_error)
        self.analysis_thread.progress_updated.connect(self.progress_bar.setValue)
        
        self.analysis_thread.start()
    
    def _on_analysis_finished(self, result):
        """Обработка завершения анализа ошибок"""
        self.analysis_result = result
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.ready_status.setText("Анализ завершен")
        
        self._generate_reports(result)
        
        tabs = self.error_analyzer_page.findChild(QTabWidget)
        if tabs:
            tabs.setCurrentIndex(1)
        
        self.logger.info("Анализ успешно завершен")
    
    def _on_analysis_error(self, error_message):
        """Обработка ошибки анализа"""
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.ready_status.setText("Ошибка анализа")
        
        self._show_silent_message(
            "Ошибка анализа",
            f"Произошла ошибка при анализе файла:\n\n{error_message}"
        )
        
        self.logger.error(f"Ошибка анализа: {error_message}")
    
    def _generate_reports(self, analysis_data):
        """Генерация текстовых отчетов"""
        try:
            report_generator = ReportGenerator(
                analysis_data, 
                self.month_combo.currentText(), 
                CURRENT_YEAR
            )
            text_report = report_generator.generate_text_report()
            self.text_report.setPlainText(text_report)
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации отчетов: {e}")
            self._show_silent_message("Ошибка", f"Ошибка при генерации отчетов: {e}")
    
    def _export_to_pdf(self):
        """Экспорт отчета в PDF"""
        if not self.license_client.is_license_active():
            self._show_silent_message(
                "Лицензия не активирована",
                "Для экспорта отчетов необходимо активировать лицензию."
            )
            self._show_license_dialog()
            return
        
        if not self.analysis_result:
            self._show_silent_message("Ошибка", "Сначала выполните анализ")
            return
        
        try:
            validation = self.license_client.validate_license()
            if not validation.get('valid'):
                self._show_silent_message(
                    "Проблема с лицензией",
                    f"Не удалось проверить лицензию:\n{validation.get('error')}\n\nЭкспорт недоступен."
                )
                return
            
            pdf_generator = PDFReportGenerator(
                self.analysis_result,
                self.month_combo.currentText(),
                CURRENT_YEAR,
                self.department_combo.currentText()
            )
            
            file_path = pdf_generator.generate_pdf(self)
            
            if file_path:
                self._show_silent_message(
                    "Экспорт завершен",
                    f"✅ PDF отчет успешно сохранен:\n{file_path}"
                )
                
                self.logger.info(f"PDF отчет сохранен: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Ошибка экспорта в PDF: {e}")
            self._show_silent_message(
                "Ошибка экспорта",
                f"Не удалось экспортировать отчет в PDF:\n{str(e)}"
            )

    # ===== АНАЛИЗ ЛОГОВ ПОДДЕРЖКИ =====
    def _start_log_analysis(self):
        """Запуск анализа логов поддержки"""
        if not hasattr(self, 'current_log_archive') or not self.current_log_archive:
            self._show_silent_message("Ошибка", "Сначала выберите архив логов")
            return
    
        method_index = self.analysis_method_combo.currentIndex()
        analysis_method = "general" if method_index == 0 else "receipt" if method_index == 1 else "payment_terminal"
        analysis_date = self.analysis_date_edit.date().toString("yyyy-MM-dd")
        include_warnings = self.include_warnings_check.isChecked()
    
        self.log_analysis_progress.setVisible(True)
        self.log_analysis_progress.setValue(0)
        self.analyze_logs_btn.setEnabled(False)
        self.ready_status.setText("Выполняется анализ логов...")
    
        if analysis_method == "payment_terminal":
            # Используем поток для анализа платежных терминалов
            from ui_components.threads import PaymentTerminalThread
            self.log_analysis_thread = PaymentTerminalThread(
                self.current_log_archive,
                analysis_date
            )
        else:
            # Используем стандартный поток для анализа логов
            from ui_components.threads import LogAnalysisThread
            self.log_analysis_thread = LogAnalysisThread(
                self.current_log_archive,
                analysis_method,
                analysis_date,
                include_warnings
            )
    
        self.log_analysis_thread.analysis_finished.connect(self._on_log_analysis_finished)
        self.log_analysis_thread.analysis_error.connect(self._on_log_analysis_error)
        self.log_analysis_thread.progress_updated.connect(self.log_analysis_progress.setValue)
    
        self.log_analysis_thread.start()

    def _on_log_analysis_finished(self, result):
        """Обработка завершения анализа логов поддержки"""
        self.log_analysis_progress.setVisible(False)
        self.analyze_logs_btn.setEnabled(True)
        self.export_logs_btn.setEnabled(True)
        self.ready_status.setText("Анализ логов завершен")
        
        self.current_log_analysis_result = result
        
        method_index = self.analysis_method_combo.currentIndex()
        
        if method_index == 0:  # Общий анализ
            self._display_general_analysis_result(result)
        elif method_index == 1:  # Считать операции
            self._display_receipt_analysis_result(result)
        elif method_index == 2:  # Платежный терминал
            self._display_payment_terminal_result(result)

    def _display_general_analysis_result(self, result):
        """Отображение результата общего анализа"""
        self.log_analysis_result_text.setVisible(True)
        self.operations_table.setVisible(False)
        self.payment_terminal_table.setVisible(False)
        self.operations_summary_label.setVisible(False)
        self.operations_help_btn.setVisible(False)
        
        self.log_analysis_result_text.setPlainText(result['formatted_text'])

    def _display_receipt_analysis_result(self, result):
        """Отображение результата анализа операций"""
        self.log_analysis_result_text.setVisible(False)
        self.operations_table.setVisible(True)
        self.payment_terminal_table.setVisible(False)
        self.operations_summary_label.setVisible(True)
        self.operations_help_btn.setVisible(True)
    
        operations = result['structured_data']['operations']
        total_count = result['structured_data']['total_count']
    
        # Устанавливаем количество колонок
        self.operations_table.setRowCount(len(operations))
        self.operations_table.setColumnCount(8)
        self.operations_table.setHorizontalHeaderLabels([
            "Время", "Статус печати", "Сумма", "Тип чека", 
            "№ операции", "Тип операции", "Способ оплаты", "РНМ"
        ])
    
        for row, operation in enumerate(operations):
            self.operations_table.setItem(row, 0, QTableWidgetItem(operation.time))
            self.operations_table.setItem(row, 1, QTableWidgetItem(operation.print_status))
            self.operations_table.setItem(row, 2, QTableWidgetItem(operation.amount))
            self.operations_table.setItem(row, 3, QTableWidgetItem(operation.fiscal_type))
            self.operations_table.setItem(row, 4, QTableWidgetItem(operation.sale_number))
            self.operations_table.setItem(row, 5, QTableWidgetItem(operation.operation_type))
            self.operations_table.setItem(row, 6, QTableWidgetItem(operation.payment_method))
            self.operations_table.setItem(row, 7, QTableWidgetItem(operation.rnm))
    
        header = self.operations_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Время
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Статус печати
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Сумма
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Тип чека
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # № операции
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Тип операции
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Способ оплаты
        header.setSectionResizeMode(7, QHeaderView.Stretch)           # РНМ
    
        # Статистика по типам операций
        sale_count = len([op for op in operations if "Продажа:" in op.sale_number])
        return_count = len([op for op in operations if "Возврат:" in op.sale_number])
        unknown_count = len([op for op in operations if "не определен" in op.sale_number])
    
        stats_text = f"Количество операций: {total_count} (Продажи: {sale_count}, Возвраты: {return_count}"
        if unknown_count > 0:
            stats_text += f", Не определено: {unknown_count}"
        stats_text += ")"
    
        self.operations_summary_label.setText(stats_text)

    def _display_payment_terminal_result(self, result):
        """Отображение результата анализа платежных терминалов"""
        self.log_analysis_result_text.setVisible(True)
        self.operations_table.setVisible(False)
        self.payment_terminal_table.setVisible(False)
        self.operations_summary_label.setVisible(False)
        self.operations_help_btn.setVisible(False)
        
        self.log_analysis_result_text.setPlainText(result['formatted_text'])
        
        # Если есть транзакции INPAS, показываем их в таблице
        if 'inpas_transactions' in result and result['inpas_transactions']:
            self.payment_terminal_table.setVisible(True)
            transactions = result['inpas_transactions']
            
            self.payment_terminal_table.setRowCount(len(transactions))
            self.payment_terminal_table.setColumnCount(8)
            self.payment_terminal_table.setHorizontalHeaderLabels([
                "Дата и время", "Сумма", "Терминал", "Статус", 
                "Банк", "Тип карты", "Код авторизации", "RRN"
            ])
            
            for row, txn in enumerate(transactions):
                self.payment_terminal_table.setItem(row, 0, QTableWidgetItem(txn.timestamp))
                self.payment_terminal_table.setItem(row, 1, QTableWidgetItem(txn.amount))
                self.payment_terminal_table.setItem(row, 2, QTableWidgetItem(txn.terminal))
                self.payment_terminal_table.setItem(row, 3, QTableWidgetItem(txn.status))
                self.payment_terminal_table.setItem(row, 4, QTableWidgetItem(txn.bank))
                self.payment_terminal_table.setItem(row, 5, QTableWidgetItem(txn.card_type))
                self.payment_terminal_table.setItem(row, 6, QTableWidgetItem(txn.auth_code))
                self.payment_terminal_table.setItem(row, 7, QTableWidgetItem(txn.rrn))
            
            header = self.payment_terminal_table.horizontalHeader()
            for i in range(8):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

    def _on_log_analysis_error(self, error_message):
        """Обработка ошибки анализа логов поддержки"""
        self.log_analysis_progress.setVisible(False)
        self.analyze_logs_btn.setEnabled(True)
        self.export_logs_btn.setEnabled(False)
        self.ready_status.setText("Ошибка анализа логов")
    
        self._show_silent_message("Ошибка анализа", error_message)
        self.log_analysis_result_text.setPlainText(f"❌ Ошибка: {error_message}")

    def _export_log_analysis(self):
        """Экспорт результатов анализа логов поддержки в TXT"""
        if not hasattr(self, 'current_log_analysis_result'):
            self._show_silent_message("Ошибка", "Нет результатов для экспорта")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            method_index = self.analysis_method_combo.currentIndex()
            
            if method_index == 2:  # Платежный терминал
                default_name = f"анализ_платежных_терминалов_{timestamp}.txt"
            else:
                default_name = f"анализ_логов_{timestamp}.txt"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить результаты анализа",
                default_name,
                "Text Files (*.txt);;All Files (*)"
            )
            
            if not file_path:
                return
            
            if not file_path.lower().endswith('.txt'):
                file_path += '.txt'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("=== АНАЛИЗ ЛОГОВ SABY HELPER ===\n\n")
                f.write(f"Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Метод анализа: {self.analysis_method_combo.currentText()}\n")
                f.write(f"Дата логов: {self.analysis_date_edit.date().toString('yyyy-MM-dd')}\n")
                f.write("\n" + "="*50 + "\n\n")
                f.write(self.current_log_analysis_result['formatted_text'])
            
            self._show_silent_message(
                "Экспорт завершен", 
                f"✅ Результаты анализа успешно экспортированы:\n{file_path}"
            )
            self.ready_status.setText(f"Экспортировано: {os.path.basename(file_path)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка экспорта логов: {e}")
            self._show_silent_message(
                "Ошибка экспорта", 
                f"Не удалось экспортировать результаты:\n{str(e)}"
            )

    def _clear_log_analysis(self):
        """Очистка результатов анализа логов поддержки"""
        self.log_analysis_result_text.clear()
        self.operations_table.setRowCount(0)
        self.payment_terminal_table.setRowCount(0)
        self.operations_summary_label.clear()
        if hasattr(self, 'current_log_archive'):
            del self.current_log_archive
        if hasattr(self, 'current_log_analysis_result'):
            del self.current_log_analysis_result
        self.selected_archive_label.setText("Архив не выбран")
        self.analyze_logs_btn.setEnabled(False)
        self.export_logs_btn.setEnabled(False)
        
        self.log_analysis_result_text.setVisible(True)
        self.operations_table.setVisible(False)
        self.payment_terminal_table.setVisible(False)
        self.operations_summary_label.setVisible(False)
        self.operations_help_btn.setVisible(False)

    # ===== АНАЛИЗ МАРКИРОВКИ =====
    def _start_marking_analysis(self):
        """Запуск анализа маркировки"""
        if not hasattr(self, 'current_marking_archive') or not self.current_marking_archive:
            self._show_silent_message("Ошибка", "Сначала выберите архив логов маркировки")
            return

        method_index = self.marking_method_combo.currentIndex()
        analysis_date = self.marking_date_edit.date().toString("yyyy-MM-dd")
        use_devices = self.devices_radio.isChecked()
        
        self.marking_progress_bar.setVisible(True)
        self.marking_progress_bar.setValue(0)
        self.analyze_marking_btn.setEnabled(False)
        self.ready_status.setText("Выполняется анализ маркировки...")
        
        from ui_components.threads import MarkingAnalysisThread
        self.marking_analysis_thread = MarkingAnalysisThread(
            self.current_marking_archive,
            method_index,
            analysis_date,
            use_devices
        )
        
        self.marking_analysis_thread.analysis_finished.connect(self._on_marking_analysis_finished)
        self.marking_analysis_thread.analysis_error.connect(self._on_marking_analysis_error)
        self.marking_analysis_thread.progress_updated.connect(self.marking_progress_bar.setValue)
        
        self.marking_analysis_thread.start()

    def _on_marking_analysis_finished(self, result):
        """Обработка завершения анализа маркировки"""
        self.marking_progress_bar.setVisible(False)
        self.analyze_marking_btn.setEnabled(True)
        self.export_marking_btn.setEnabled(True)
        self.ready_status.setText("Анализ маркировки завершен")
        
        self.current_marking_analysis_result = result
        
        # Отображаем результаты в зависимости от метода
        self._display_marking_analysis_result(result)

    def _display_marking_analysis_result(self, result):
        """Отображение результатов анализа маркировки"""
        method_index = result['method_index']
        
        # Очищаем предыдущие результаты
        self.marking_result_text.clear()
        self.marking_table.clear()
        self.marking_table.setRowCount(0)
        
        # Устанавливаем заголовки таблицы в зависимости от метода
        if method_index == 0:  # Считать все сканирования
            self.marking_table.setColumnCount(2)
            self.marking_table.setHorizontalHeaderLabels(["Время сканирования", "Результат"])
            self._display_scans_result(result)
        elif method_index == 1:  # Информация по КМ
            self.marking_table.setColumnCount(9)
            self.marking_table.setHorizontalHeaderLabels([
                "Время", "КМ", "Статус", "Продажа", "Продано", "Всего", 
                "Срок годности", "Владелец", "Прослеживаемость"
            ])
            self._display_marking_info_result(result)
        elif method_index == 2:  # Подключение ЛМ ЧЗ
            self.marking_table.setColumnCount(2)
            self.marking_table.setHorizontalHeaderLabels(["Время", "Сообщение"])
            self._display_connection_issues_result(result)
        elif method_index == 3:  # Логин и пароль ЛМ ЧЗ
            self._display_login_password_result(result)
            return  # Для этого метода оставляем текстовое представление
        elif method_index == 4:  # Проверка вскрытия
            self.marking_table.setColumnCount(5)
            self.marking_table.setHorizontalHeaderLabels([
                "Время лога", "КМ", "Литраж", "Срок годности", "Дата вскрытия"
            ])
            self._display_opening_check_result(result)

    def _display_scans_result(self, result):
        """Отображение результатов сканирований - ТОЛЬКО ТАБЛИЦА"""
        scans = result['results']
        
        # Только табличное представление
        self.marking_result_text.setVisible(False)
        self.marking_table.setVisible(True)
        
        if scans:
            self.marking_table.setRowCount(len(scans))
            
            for row, scan in enumerate(scans):
                self.marking_table.setItem(row, 0, QTableWidgetItem(scan.timestamp))
                self.marking_table.setItem(row, 1, QTableWidgetItem(scan.result))
            
            # Настройка заголовков таблицы
            header = self.marking_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
        else:
            self.marking_table.setRowCount(1)
            self.marking_table.setItem(0, 0, QTableWidgetItem("Нет данных"))
            self.marking_table.setItem(0, 1, QTableWidgetItem("Сканирований не найдено"))

    def _display_marking_info_result(self, result):
        """Отображение информации по КМ - ТОЛЬКО ТАБЛИЦА"""
        marking_info = result['results']
        
        # Только табличное представление
        self.marking_result_text.setVisible(False)
        self.marking_table.setVisible(True)
        
        if marking_info:
            self.marking_table.setRowCount(len(marking_info))
            
            for row, info in enumerate(marking_info):
                items = info.to_table_row()
                for col, value in enumerate(items):
                    self.marking_table.setItem(row, col, QTableWidgetItem(value))
            
            # Настройка заголовков таблицы
            header = self.marking_table.horizontalHeader()
            for i in range(9):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)  # КМ растягиваем
        else:
            self.marking_table.setRowCount(1)
            self.marking_table.setItem(0, 0, QTableWidgetItem("Нет данных"))
            self.marking_table.setItem(0, 1, QTableWidgetItem("Информации по КМ не найдено"))

    def _display_connection_issues_result(self, result):
        """Отображение проблем подключения - ТОЛЬКО ТАБЛИЦА"""
        issues = result['results']
        
        # Только табличное представление
        self.marking_result_text.setVisible(False)
        self.marking_table.setVisible(True)
        
        if issues:
            self.marking_table.setRowCount(len(issues))
            
            for row, issue in enumerate(issues):
                self.marking_table.setItem(row, 0, QTableWidgetItem(issue.timestamp))
                self.marking_table.setItem(row, 1, QTableWidgetItem(issue.message))
            
            header = self.marking_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
        else:
            self.marking_table.setRowCount(1)
            self.marking_table.setItem(0, 0, QTableWidgetItem("Нет данных"))
            self.marking_table.setItem(0, 1, QTableWidgetItem("Проблем подключения не найдено"))

    def _display_login_password_result(self, result):
        """Отображение логинов и паролей - ТОЛЬКО ТЕКСТ"""
        logins = result['results']
        
        # Только текстовое представление для этого метода
        self.marking_table.setVisible(False)
        self.marking_result_text.setVisible(True)
        
        if logins:
            self.marking_result_text.setPlainText(result['formatted_text'])
        else:
            self.marking_result_text.setPlainText("Данных авторизации не найдено")

    def _display_opening_check_result(self, result):
        """Отображение проверки вскрытия - ТОЛЬКО ТАБЛИЦА"""
        openings = result['results']
        
        # Только табличное представление
        self.marking_result_text.setVisible(False)
        self.marking_table.setVisible(True)
        
        if openings:
            self.marking_table.setRowCount(len(openings))
            
            for row, opening in enumerate(openings):
                items = opening.to_table_row()
                for col, value in enumerate(items):
                    self.marking_table.setItem(row, col, QTableWidgetItem(value))
            
            header = self.marking_table.horizontalHeader()
            for i in range(5):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)  # КМ растягиваем
        else:
            self.marking_table.setRowCount(1)
            self.marking_table.setItem(0, 0, QTableWidgetItem("Нет данных"))
            self.marking_table.setItem(0, 1, QTableWidgetItem("Данных вскрытия не найдено"))

    def _on_marking_analysis_error(self, error_message):
        """Обработка ошибки анализа маркировки"""
        self.marking_progress_bar.setVisible(False)
        self.analyze_marking_btn.setEnabled(True)
        self.export_marking_btn.setEnabled(False)
        self.ready_status.setText("Ошибка анализа маркировки")
        
        self._show_silent_message("Ошибка анализа", error_message)
        self.marking_result_text.setVisible(True)
        self.marking_result_text.setPlainText(f"❌ Ошибка: {error_message}")
        self.marking_table.setVisible(False)

    def _export_marking_analysis(self):
        """Экспорт результатов анализа маркировки"""
        if not hasattr(self, 'current_marking_analysis_result'):
            self._show_silent_message("Ошибка", "Нет результатов для экспорта")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"анализ_маркировки_{timestamp}.txt"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить результаты анализа маркировки",
                default_name,
                "Text Files (*.txt);;All Files (*)"
            )
            
            if not file_path:
                return
            
            if not file_path.lower().endswith('.txt'):
                file_path += '.txt'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("=== АНАЛИЗ МАРКИРОВКИ SABY HELPER ===\n\n")
                f.write(f"Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Метод анализа: {self.marking_method_combo.currentText()}\n")
                f.write(f"Принцип работы: {'Devices' if self.devices_radio.isChecked() else 'Console'}\n")
                f.write("\n" + "="*50 + "\n\n")
                f.write(self.current_marking_analysis_result['formatted_text'])
            
            self._show_silent_message(
                "Экспорт завершен", 
                f"✅ Результаты анализа маркировки успешно экспортированы:\n{file_path}"
            )
            self.ready_status.setText(f"Экспортировано: {os.path.basename(file_path)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка экспорта маркировки: {e}")
            self._show_silent_message(
                "Ошибка экспорта", 
                f"Не удалось экспортировать результаты:\n{str(e)}"
            )

    def _show_original_marking_logs(self):
        """Показать оригинальные логи маркировки"""
        if not hasattr(self, 'current_marking_archive'):
            self._show_silent_message("Ошибка", "Сначала выберите архив логов маркировки")
            return
        
        try:
            from marking_analyzer import MarkingLogAnalyzer
            analyzer = MarkingLogAnalyzer()
            
            temp_dir = analyzer.extract_archive(self.current_marking_archive)
            if not temp_dir:
                self._show_silent_message("Ошибка", "Не удалось распаковать архив")
                return
            
            log_dir = analyzer.find_logs_directory(self.marking_date_edit.date().toString("yyyy-MM-dd"))
            if not log_dir:
                self._show_silent_message("Ошибка", "Логов за выбранную дату не найдено")
                return
            
            original_logs = analyzer.get_original_logs(log_dir)
            
            # Создаем диалог для показа логов
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QTextEdit
            dialog = QDialog(self)
            dialog.setWindowTitle("📄 Оригинальные логи маркировки")
            dialog.setGeometry(100, 100, 1000, 700)
            
            layout = QVBoxLayout(dialog)
            tabs = QTabWidget()
            
            for log_file, content in original_logs.items():
                text_edit = QTextEdit()
                text_edit.setPlainText(content)
                text_edit.setReadOnly(True)
                tabs.addTab(text_edit, log_file)
            
            layout.addWidget(tabs)
            dialog.exec_()
            
            analyzer.cleanup()
            
        except Exception as e:
            self.logger.error(f"Ошибка показа оригинальных логов: {e}")
            self._show_silent_message("Ошибка", f"Не удалось показать оригинальные логи:\n{str(e)}")

    def _clear_marking_analysis(self):
        """Очистка результатов анализа маркировки"""
        self.marking_result_text.clear()
        self.marking_table.setRowCount(0)
        if hasattr(self, 'current_marking_archive'):
            del self.current_marking_archive
        if hasattr(self, 'current_marking_analysis_result'):
            del self.current_marking_analysis_result
        self.selected_marking_archive_label.setText("Архив маркировки не выбран")
        self.analyze_marking_btn.setEnabled(False)
        self.export_marking_btn.setEnabled(False)
        self.show_original_logs_btn.setEnabled(False)
        self.marking_result_text.setVisible(False)
        self.marking_table.setVisible(True)

    # ===== АНАЛИЗ БАЗОВЫХ МЕХАНИЗМОВ =====
    def _start_basic_analysis(self):
        """Запуск анализа базовых механизмов"""
        if not hasattr(self, 'current_basic_archive') or not self.current_basic_archive:
            self._show_silent_message("Ошибка", "Сначала выберите архив логов")
            return
        
        analysis_date = self.basic_date_edit.date().toString("yyyy-MM-dd")
        use_custom_patterns = self.use_custom_patterns_check.isChecked()
        custom_patterns = self.custom_patterns_input.text().strip()
        
        self.basic_progress_bar.setVisible(True)
        self.basic_progress_bar.setValue(0)
        self.analyze_basic_btn.setEnabled(False)
        self.ready_status.setText("Выполняется анализ журналов ОС...")
        
        from ui_components.threads import BasicMechanismsThread
        self.basic_analysis_thread = BasicMechanismsThread(
            self.current_basic_archive,
            analysis_date,
            use_custom_patterns,
            custom_patterns
        )
        
        self.basic_analysis_thread.analysis_finished.connect(self._on_basic_analysis_finished)
        self.basic_analysis_thread.analysis_error.connect(self._on_basic_analysis_error)
        self.basic_analysis_thread.progress_updated.connect(self.basic_progress_bar.setValue)
        
        self.basic_analysis_thread.start()

    def _on_basic_analysis_finished(self, result):
        """Обработка завершения анализа базовых механизмов"""
        self.basic_progress_bar.setVisible(False)
        self.analyze_basic_btn.setEnabled(True)
        self.export_basic_btn.setEnabled(True)
        self.ready_status.setText("Анализ журналов ОС завершен")
        
        self.current_basic_analysis_result = result
        
        # Отображаем результаты
        self._display_basic_analysis_result(result)

    def _display_basic_analysis_result(self, result):
        """Отображение результатов анализа базовых механизмов"""
        # Показываем переключатель журналов
        self.os_log_switch_combo.setVisible(True)
        
        # Отображаем события в таблице
        self._display_os_events_by_log_type(0)  # По умолчанию показываем журнал приложения
        
        # Также показываем текстовое представление
        self.basic_result_text.setPlainText(result['formatted_text'])
        self.basic_result_text.setVisible(True)
        self.os_events_table.setVisible(True)

    def _display_os_events_by_log_type(self, log_type_index):
        """Отображение событий ОС по типу журнала"""
        if not hasattr(self, 'current_basic_analysis_result'):
            return
        
        # 0 - Журнал приложения, 1 - Журнал системы
        if log_type_index == 0:
            events = self.current_basic_analysis_result['application_events']
            log_name = "Журнал приложения"
        else:
            events = self.current_basic_analysis_result['system_events']
            log_name = "Журнал системы"
        
        # Заполняем таблицу
        self.os_events_table.setRowCount(len(events))
        self.os_events_table.setColumnCount(5)
        self.os_events_table.setHorizontalHeaderLabels([
            "Дата и время", "Уровень", "Код события", "Источник", "Тип журнала"
        ])
        
        for row, event in enumerate(events):
            self.os_events_table.setItem(row, 0, QTableWidgetItem(event.timestamp))
            self.os_events_table.setItem(row, 1, QTableWidgetItem(event.level))
            self.os_events_table.setItem(row, 2, QTableWidgetItem(event.event_code))
            self.os_events_table.setItem(row, 3, QTableWidgetItem(event.source))
            self.os_events_table.setItem(row, 4, QTableWidgetItem(event.log_type))
        
        # Настраиваем заголовки таблицы
        header = self.os_events_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Дата и время
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Уровень
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Код события
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Источник
        header.setSectionResizeMode(4, QHeaderView.Stretch)           # Тип журнала

    def _on_basic_analysis_error(self, error_message):
        """Обработка ошибки анализа базовых механизмов"""
        self.basic_progress_bar.setVisible(False)
        self.analyze_basic_btn.setEnabled(True)
        self.export_basic_btn.setEnabled(False)
        self.ready_status.setText("Ошибка анализа журналов ОС")
        
        self._show_silent_message("Ошибка анализа", error_message)
        self.basic_result_text.setPlainText(f"❌ Ошибка: {error_message}")
        self.os_events_table.setVisible(False)
        self.os_log_switch_combo.setVisible(False)

    def _export_basic_analysis(self):
        """Экспорт результатов анализа базовых механизмов"""
        if not hasattr(self, 'current_basic_analysis_result'):
            self._show_silent_message("Ошибка", "Нет результатов для экспорта")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"анализ_журналов_ос_{timestamp}.txt"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить результаты анализа журналов ОС",
                default_name,
                "Text Files (*.txt);;All Files (*)"
            )
            
            if not file_path:
                return
            
            if not file_path.lower().endswith('.txt'):
                file_path += '.txt'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("=== АНАЛИЗ ЖУРНАЛОВ ОС WINDOWS ===\n\n")
                f.write(f"Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Дата логов: {self.basic_date_edit.date().toString('yyyy-MM-dd')}\n")
                f.write(f"Использование шаблона: {'Да' if self.use_custom_patterns_check.isChecked() else 'Нет'}\n")
                if self.use_custom_patterns_check.isChecked() and self.custom_patterns_input.text():
                    f.write(f"Шаблон кодов: {self.custom_patterns_input.text()}\n")
                f.write("\n" + "="*50 + "\n\n")
                f.write(self.current_basic_analysis_result['formatted_text'])
            
            self._show_silent_message(
                "Экспорт завершен", 
                f"✅ Результаты анализа журналов ОС успешно экспортированы:\n{file_path}"
            )
            self.ready_status.setText(f"Экспортировано: {os.path.basename(file_path)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка экспорта журналов ОС: {e}")
            self._show_silent_message(
                "Ошибка экспорта", 
                f"Не удалось экспортировать результаты:\n{str(e)}"
            )

    def _clear_basic_analysis(self):
        """Очистка результатов анализа базовых механизмов"""
        self.basic_result_text.clear()
        self.os_events_table.setRowCount(0)
        if hasattr(self, 'current_basic_archive'):
            del self.current_basic_archive
        if hasattr(self, 'current_basic_analysis_result'):
            del self.current_basic_analysis_result
        self.selected_basic_archive_label.setText("Архив не выбран")
        self.analyze_basic_btn.setEnabled(False)
        self.export_basic_btn.setEnabled(False)
        self.os_log_switch_combo.setVisible(False)
        self.basic_result_text.setVisible(False)
        self.os_events_table.setVisible(True)