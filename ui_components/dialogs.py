# ui_components/dialogs.py
"""
Диалоговые окна приложения - ОБНОВЛЕННАЯ ВЕРСИЯ БЕЗ ПОМОЩИ
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QProgressBar, 
                             QDialogButtonBox, QMessageBox)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont

from config import APP_VERSION, CONTACT_INFO
from update_manager import UpdateManager, UpdateChecker

class ModernDialog(QDialog):
    """Современный диалог с анимацией"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        self.setStyleSheet("""
            ModernDialog {
                background-color: #2a2c36;
                border: 2px solid #6272a4;
                border-radius: 10px;
            }
        """)
        
    def showEvent(self, event):
        """Анимация появления"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(200)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()
        super().showEvent(event)
        
    def closeEvent(self, event):
        """Анимация закрытия"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(150)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.InCubic)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()
        event.ignore()

class OperationsHelpDialog(ModernDialog):
    """Диалог помощи по операциям с чеками"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("💡 Справка по операциям")
        title.setStyleSheet("""
            QLabel {
                color: #f8f8f2;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 15px;
            }
        """)
        layout.addWidget(title)
        
        help_text = """
📋 Информация по операциям с чеками:

• Время - время создания операции в логас
• Статус печати - будет ли чек отправлен на печать
• Сумма - общая сумма операции в рублях
• Тип чека - фискальный или нефискальный чек

💡 Примечания:
• Сумма продажи извлекается из поля 'TotalSum'
• Фискальный/нефискальный чек определяется по полю 'non_fiscal'
• Режим печати определяется по полю 'PrintMode'
        """
        
        text_edit = QTextEdit()
        text_edit.setPlainText(help_text.strip())
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #44475a;
                color: #f8f8f2;
                border: 1px solid #6272a4;
                border-radius: 5px;
                padding: 10px;
                font-size: 12px;
            }
        """)
        layout.addWidget(text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        button_box.setStyleSheet("""
            QDialogButtonBox QPushButton {
                background-color: #6272a4;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QDialogButtonBox QPushButton:hover {
                background-color: #7282b4;
            }
        """)
        layout.addWidget(button_box)

class UpdateDialog(ModernDialog):
    """Диалог обновлений - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    
    def __init__(self, update_manager, parent=None):
        super().__init__(parent)
        self.update_manager = update_manager
        self.update_info = None
        self._setup_ui()
        self._check_updates()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("🔄 Проверка обновлений")
        title.setStyleSheet("""
            QLabel {
                color: #f8f8f2;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 15px;
            }
        """)
        layout.addWidget(title)
        
        self.info_label = QLabel("Выполняется проверка обновлений...")
        self.info_label.setStyleSheet("""
            QLabel {
                color: #f8f8f2;
                background-color: #44475a;
                padding: 15px;
                border-radius: 5px;
                border: 1px solid #6272a4;
            }
        """)
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
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
        
        button_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("📥 Загрузить обновление")
        self.download_btn.setStyleSheet(self._get_button_style())
        self.download_btn.clicked.connect(self._download_update)
        self.download_btn.setVisible(False)
        
        self.manual_check_btn = QPushButton("🔍 Проверить вручную")
        self.manual_check_btn.setStyleSheet(self._get_button_style())
        self.manual_check_btn.clicked.connect(self._check_updates)
        
        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet(self._get_button_style())
        close_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.manual_check_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
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
            QPushButton:disabled {
                background-color: #404352;
                color: #888888;
            }
        """
    
    def _check_updates(self):
        """Проверка обновлений"""
        self.info_label.setText("Выполняется проверка обновлений...")
        self.download_btn.setVisible(False)
        self.manual_check_btn.setEnabled(False)
        
        self.checker_thread = UpdateChecker()
        self.checker_thread.signals.update_found.connect(self._on_update_found)
        self.checker_thread.signals.no_update.connect(self._on_no_update)
        self.checker_thread.signals.check_error.connect(self._on_check_error)
        self.checker_thread.start()
    
    def _on_update_found(self, update_info):
        """Обновление найдено"""
        self.update_info = update_info
        latest_version = update_info['latest_version']
        release_notes = update_info.get('release_notes', '')
        file_size = update_info.get('file_size', 0)
        
        # ИСПРАВЛЕННО: Правильное отображение размера
        size_text = self._format_file_size(file_size)
        
        message = f"✅ Доступно обновление!\n\nВерсия: {latest_version}\nРазмер: {size_text}"
        
        if update_info.get('force_update'):
            message += "\n\n⚠️ Это ОБЯЗАТЕЛЬНОЕ обновление!"
        
        message += f"\n\nЧто нового:\n{release_notes}"
        
        self.info_label.setText(message)
        self.download_btn.setVisible(True)
        self.manual_check_btn.setEnabled(True)
    
    def _on_no_update(self):
        """Обновлений нет"""
        self.info_label.setText("✅ У вас установлена последняя версия приложения!")
        self.manual_check_btn.setEnabled(True)
    
    def _on_check_error(self, error_message):
        """Ошибка проверки"""
        self.info_label.setText(f"❌ Ошибка проверки обновлений:\n{error_message}")
        self.manual_check_btn.setEnabled(True)
    
    def set_update_info(self, update_info):
        """Установка информации об обновлении (для автоматической проверки)"""
        self.update_info = update_info
        
        if update_info.get('update_available'):
            self._on_update_found(update_info)
        else:
            self._on_no_update()
    
    def _format_file_size(self, size_mb):
        """Форматирование размера файла из МБ в читаемый формат"""
        try:
            size_mb = float(size_mb)
            if size_mb == 0:
                return "0 МБ"
            elif size_mb < 1:
                size_kb = size_mb * 1024
                return f"{size_kb:.1f} КБ"
            elif size_mb < 1024:
                return f"{size_mb:.1f} МБ"
            else:
                size_gb = size_mb / 1024
                return f"{size_gb:.1f} ГБ"
        except (ValueError, TypeError):
            return "неизвестно"
        
    def _download_update(self):
        """Загрузка обновления"""
        if not self.update_info:
            return
            
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.download_btn.setEnabled(False)
            self.manual_check_btn.setEnabled(False)
            
            self.update_manager.download_and_install_update(self.update_info, self.parent())
            
        except Exception as e:
            self.info_label.setText(f"❌ Ошибка загрузки: {str(e)}")
            self.progress_bar.setVisible(False)
            self.download_btn.setEnabled(True)
            self.manual_check_btn.setEnabled(True)