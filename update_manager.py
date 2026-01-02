# update_manager.py
"""
Менеджер обновлений приложения - ИСПРАВЛЕННАЯ ВЕРСИЯ С ПРАВИЛЬНОЙ ЗАГРУЗКОЙ QT ПЛАГИНОВ
"""

import requests
import logging
import tempfile
import os
import sys
import shutil
import traceback
import json
import time
import subprocess
import zipfile
from pathlib import Path
from datetime import datetime
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt5.QtWidgets import QProgressDialog, QMessageBox, QApplication, QLabel, QVBoxLayout, QDialog
from PyQt5.QtGui import QIcon, QPixmap

from config import APP_VERSION, UPDATE_CHECK_URL, UPDATE_DOWNLOAD_URL
from modules.settings_manager import SettingsManager

class UpdateSignals(QObject):
    """Сигналы для обновлений"""
    update_found = pyqtSignal(dict)
    no_update = pyqtSignal()
    check_error = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    download_finished = pyqtSignal(str, str)  # file_path, version
    download_error = pyqtSignal(str)

class UpdateChecker(QThread):
    """Поток для проверки обновлений"""
    
    def __init__(self):
        super().__init__()
        self.signals = UpdateSignals()
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        try:
            self.logger.info("=== НАЧАЛО ПРОВЕРКИ ОБНОВЛЕНИЙ ===")
            
            # Создаем сессию без прокси
            session = requests.Session()
            session.trust_env = False
            
            # Формируем URL с параметрами
            url = f"{UPDATE_CHECK_URL}?version={APP_VERSION}"
            self.logger.info(f"Запрос к серверу обновлений: {url}")
            
            # Отправляем запрос с таймаутом
            response = session.get(url, timeout=10)
            self.logger.info(f"Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                update_info = response.json()
                self.logger.info(f"Получен ответ от сервера: {update_info}")
                
                if update_info.get('update_available'):
                    self.logger.info("🎯 ОБНОВЛЕНИЕ ДОСТУПНО!")
                    self.signals.update_found.emit(update_info)
                else:
                    self.logger.info("✅ Обновлений нет - установлена последняя версия")
                    self.signals.no_update.emit()
            else:
                error_msg = f"HTTP ошибка: {response.status_code}"
                self.logger.error(error_msg)
                self.signals.check_error.emit(error_msg)
            
        except requests.exceptions.Timeout:
            error_msg = "⏰ Таймаут подключения к серверу обновлений"
            self.logger.error(error_msg)
            self.signals.check_error.emit(error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "🔌 Ошибка подключения к серверу обновлений"
            self.logger.error(error_msg)
            self.signals.check_error.emit(error_msg)
        except requests.exceptions.JSONDecodeError as e:
            error_msg = f"❌ Ошибка разбора JSON ответа: {str(e)}"
            self.logger.error(error_msg)
            self.signals.check_error.emit(error_msg)
        except Exception as e:
            error_msg = f"❌ Критическая ошибка проверки обновлений: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            self.signals.check_error.emit(error_msg)

class UpdateDownloader(QThread):
    """Поток для загрузки обновлений"""
    
    def __init__(self, download_url, version, expected_size=0, expected_hash=""):
        super().__init__()
        self.signals = UpdateSignals()
        self.download_url = download_url
        self.version = version
        self.expected_size = expected_size
        self.expected_hash = expected_hash
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        try:
            self.logger.info(f"🚀 Начало загрузки обновления {self.version}")
            
            # Создаем сессию без прокси
            session = requests.Session()
            session.trust_env = False
            
            # Начинаем загрузку с потоковой передачей
            response = session.get(self.download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Получаем реальный размер файла из заголовков
            total_size = int(response.headers.get('content-length', 0))
            self.logger.info(f"Размер файла из заголовков: {total_size} байт")
            
            # Если ожидаемый размер указан, проверяем его
            if self.expected_size > 0 and total_size > 0:
                expected_bytes = self.expected_size * 1024 * 1024  # конвертируем МБ в байты
                if abs(total_size - expected_bytes) / expected_bytes > 0.1:  # 10% отклонение
                    self.logger.warning(f"Размер файла не совпадает: ожидалось {expected_bytes}, получено {total_size}")
            
            # Создаем временный файл
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            downloaded_size = 0
            
            # Загружаем файл по частям
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # Обновляем прогресс
                    if total_size > 0:
                        progress = int((downloaded_size / total_size) * 100)
                        self.signals.progress_updated.emit(min(progress, 100))
            
            temp_file.close()
            
            self.logger.info(f"✅ Загрузка завершена: {temp_file.name}, размер: {downloaded_size} байт")
            
            # Проверяем хеш если указан
            if self.expected_hash:
                self._verify_file_hash(temp_file.name, self.expected_hash)
            
            self.signals.download_finished.emit(temp_file.name, self.version)
            
        except Exception as e:
            error_msg = f"❌ Ошибка загрузки обновления: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            self.signals.download_error.emit(error_msg)
    
    def _verify_file_hash(self, file_path, expected_hash):
        """Проверка хеша файла"""
        try:
            import hashlib
            
            self.logger.info("🔐 Проверка целостности файла...")
            
            # Вычисляем SHA256 хеш
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            actual_hash = sha256_hash.hexdigest()
            
            if actual_hash != expected_hash:
                raise ValueError(f"Хеш файла не совпадает: ожидался {expected_hash[:16]}..., получен {actual_hash[:16]}...")
            
            self.logger.info("✅ Целостность файла подтверждена")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки хеша: {e}")
            # Не бросаем исключение, продолжаем установку

class UpdateManager:
    """Менеджер обновлений приложения - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    
    def __init__(self, license_client=None):
        self.logger = logging.getLogger(__name__)
        self.license_client = license_client
        self.settings_manager = SettingsManager()
        self.logger.info("✅ Менеджер обновлений инициализирован")
    
    def _log_to_server(self, level, message):
        """Логирование на сервер"""
        try:
            if self.license_client:
                self.license_client._send_log(level, message)
        except Exception as e:
            self.logger.error(f"Не удалось отправить лог на сервер: {e}")
    
    def check_for_updates(self):
        """Проверка наличия обновлений - СИНХРОННАЯ ВЕРСИЯ"""
        try:
            self.logger.info("🔍 Запуск синхронной проверки обновлений")
            self._log_to_server("INFO", "Запуск проверки обновлений")
            
            session = requests.Session()
            session.trust_env = False
            
            # Пытаемся подключиться до 3 раз
            for attempt in range(3):
                try:
                    url = f"{UPDATE_CHECK_URL}?version={APP_VERSION}"
                    self.logger.info(f"Попытка {attempt + 1}: Запрос к {url}")
                    
                    response = session.get(url, timeout=10)
                    self.logger.info(f"Статус ответа: {response.status_code}")
                    
                    if response.status_code == 200:
                        update_info = response.json()
                        self.logger.info(f"Получена информация об обновлениях: {update_info}")
                        
                        # Сохраняем дату проверки
                        self.settings_manager.set_last_update_check(
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
                        
                        return update_info
                    else:
                        self.logger.warning(f"HTTP ошибка {response.status_code}, попытка {attempt + 1}")
                        
                except requests.exceptions.Timeout:
                    self.logger.warning(f"Таймаут попытка {attempt + 1}")
                except requests.exceptions.ConnectionError as e:
                    self.logger.warning(f"Ошибка подключения попытка {attempt + 1}: {e}")
                except Exception as e:
                    self.logger.warning(f"Ошибка попытка {attempt + 1}: {e}")
                
                # Ждем перед повторной попыткой
                if attempt < 2:
                    import time
                    time.sleep(2)
            
            self.logger.error("Все попытки подключения не удались")
            self._log_to_server("ERROR", "Не удалось подключиться к серверу обновлений после 3 попыток")
            return None
                
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка проверки обновлений: {e}")
            self._log_to_server("ERROR", f"Критическая ошибка проверки обновлений: {str(e)}")
            return None
    
    def check_for_updates_async(self, callback):
        """Асинхронная проверка обновлений"""
        try:
            self.logger.info("🔍 Запуск асинхронной проверки обновлений")
            self._log_to_server("INFO", "Запуск асинхронной проверки обновлений")
            
            self.checker = UpdateChecker()
            
            def on_update_found(update_info):
                self.logger.info("🎯 Обновление найдено в асинхронном режиме")
                self._log_to_server("INFO", f"Обновление доступно: версия {update_info['latest_version']}")
                
                # Сохраняем дату проверки
                self.settings_manager.set_last_update_check(
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                
                callback(True, update_info)
            
            def on_no_update():
                self.logger.info("✅ Обновлений нет в асинхронном режиме")
                self._log_to_server("INFO", "Обновлений нет - установлена последняя версия")
                
                # Сохраняем дату проверки
                self.settings_manager.set_last_update_check(
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                
                callback(False, None)
            
            def on_check_error(error_msg):
                self.logger.error(f"❌ Ошибка проверки в асинхронном режиме: {error_msg}")
                self._log_to_server("ERROR", f"Ошибка проверки обновлений: {error_msg}")
                callback(False, None)
            
            self.checker.signals.update_found.connect(on_update_found)
            self.checker.signals.no_update.connect(on_no_update)
            self.checker.signals.check_error.connect(on_check_error)
            
            self.checker.start()
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка запуска асинхронной проверки: {e}")
            self._log_to_server("ERROR", f"Ошибка запуска проверки обновлений: {str(e)}")
            callback(False, None)
    
    def download_and_install_update(self, update_info, parent_window=None):
        """Загрузка и установка обновления - ИСПРАВЛЕННАЯ ВЕРСИЯ ДЛЯ ZIP"""
        try:
            latest_version = update_info['latest_version']
            self.logger.info(f"🚀 Запуск загрузки обновления {latest_version}")
            self._log_to_server("INFO", f"Начало загрузки обновления {latest_version}")
            
            # Создаем диалог прогресса
            progress = QProgressDialog("Загрузка обновления...", "Отмена", 0, 100, parent_window)
            progress.setWindowTitle(f"Обновление до версии {latest_version}")
            progress.setWindowModality(True)
            progress.setMinimumDuration(0)
            progress.setStyleSheet("""
                QProgressDialog {
                    background-color: #2a2c36;
                    color: #f8f8f2;
                }
                QProgressDialog QLabel {
                    color: #f8f8f2;
                }
                QProgressBar {
                    border: 2px solid #6272a4;
                    border-radius: 5px;
                    text-align: center;
                    color: #f8f8f2;
                }
                QProgressBar::chunk {
                    background-color: #50fa7b;
                }
            """)
            progress.show()
            
            # Получаем URL для загрузки
            download_url = update_info.get('download_url', UPDATE_DOWNLOAD_URL)
            file_size = update_info.get('file_size', 0)
            file_hash = update_info.get('file_hash', '')
            
            # Запускаем загрузку
            self.downloader = UpdateDownloader(
                download_url,
                latest_version,
                file_size,
                file_hash
            )
            
            def update_progress(value):
                progress.setValue(value)
                if value >= 100:
                    progress.setLabelText("Завершение загрузки...")
            
            def download_finished(file_path, version):
                progress.close()
                self.logger.info(f"✅ Загрузка завершена, запуск установки")
                self._log_to_server("INFO", f"Загрузка обновления {version} завершена")
                self._install_update(file_path, version, update_info, parent_window)
            
            def download_error(error_msg):
                progress.close()
                self.logger.error(f"❌ Ошибка загрузки: {error_msg}")
                self._log_to_server("ERROR", f"Ошибка загрузки обновления: {error_msg}")
                QMessageBox.critical(
                    parent_window,
                    "Ошибка загрузки",
                    f"Не удалось загрузить обновление:\n{error_msg}"
                )
            
            def cancel_download():
                if hasattr(self, 'downloader') and self.downloader.isRunning():
                    self.downloader.terminate()
                    self.downloader.wait()
                progress.close()
                self.logger.info("Загрузка отменена пользователем")
                self._log_to_server("INFO", "Загрузка обновления отменена пользователем")
            
            self.downloader.signals.progress_updated.connect(update_progress)
            self.downloader.signals.download_finished.connect(download_finished)
            self.downloader.signals.download_error.connect(download_error)
            progress.canceled.connect(cancel_download)
            
            self.downloader.start()
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка запуска загрузки: {e}")
            self._log_to_server("ERROR", f"Ошибка запуска загрузки обновления: {str(e)}")
            if parent_window:
                QMessageBox.critical(
                    parent_window,
                    "Ошибка",
                    f"Не удалось начать загрузку обновления:\n{str(e)}"
                )
    
    def _install_update(self, zip_path, version, update_info, parent_window=None):
        """Установка обновления из ZIP архива - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            # Проверяем принудительное обновление
            force_update = update_info.get('force_update', False)
            
            if force_update:
                message = (
                    f"Доступно ОБЯЗАТЕЛЬНОЕ обновление до версии {version}!\n\n"
                    f"Что нового:\n"
                    f"{update_info.get('release_notes', 'Улучшения и исправления ошибок')}\n\n"
                    "Приложение будет закрыто для установки обновления.\n"
                    "Продолжить?"
                )
                title = "ОБЯЗАТЕЛЬНОЕ ОБНОВЛЕНИЕ"
            else:
                message = (
                    f"Доступно обновление до версии {version}\n\n"
                    f"Что нового:\n"
                    f"{update_info.get('release_notes', 'Улучшения и исправления ошибок')}\n\n"
                    "Хотите установить обновление сейчас?\n"
                    "Приложение будет закрыто для установки."
                )
                title = "Обновление доступно"
            
            # В режиме автообновления для обязательных обновлений пропускаем диалог
            auto_update_enabled = self.settings_manager.get_auto_update_enabled()
            
            if auto_update_enabled and force_update:
                self.logger.info("Автообновление включено, начинаем автоматическую установку")
                reply = QMessageBox.Yes
            else:
                # Показываем диалог подтверждения
                msg_box = QMessageBox(parent_window)
                msg_box.setWindowTitle(title)
                msg_box.setText(message)
                msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg_box.setDefaultButton(QMessageBox.Yes)
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #2a2c36;
                        color: #f8f8f2;
                    }
                    QMessageBox QLabel {
                        color: #f8f8f2;
                    }
                """)
                
                reply = msg_box.exec_()
            
            if reply == QMessageBox.Yes:
                self.logger.info(f"🔄 Запуск процесса обновления из ZIP")
                self._log_to_server("INFO", f"Установка обновления {version} из ZIP")
                
                # Создаем диалог для отображения прогресса извлечения
                extract_dialog = QDialog(parent_window)
                extract_dialog.setWindowTitle("Установка обновления")
                extract_dialog.setFixedSize(400, 200)
                layout = QVBoxLayout()
                
                info_label = QLabel(f"Установка версии {version}...\n\nПожалуйста, подождите.")
                info_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(info_label)
                
                extract_dialog.setLayout(layout)
                extract_dialog.show()
                
                # Даем время показаться диалогу
                QApplication.processEvents()
                
                # Создаем Python скрипт для обновления
                updater_script = self._create_updater_script(zip_path, version)
                
                # Сохраняем скрипт обновления
                import tempfile
                updater_path = os.path.join(tempfile.gettempdir(), "saby_updater.py")
                
                with open(updater_path, 'w', encoding='utf-8') as f:
                    f.write(updater_script)
                
                self.logger.info(f"Создан скрипт обновления: {updater_path}")
                
                # Закрываем диалог
                extract_dialog.close()
                
                # Запускаем скрипт обновления в отдельном процессе
                import subprocess
                
                # Скрываем консольное окно
                startupinfo = None
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                
                self.logger.info("Запуск процесса обновления...")
                subprocess.Popen(
                    [sys.executable, updater_path],
                    startupinfo=startupinfo
                )
                
                # Сохраняем информацию об установленном обновлении
                self.settings_manager.settings.setValue(
                    f"last_installed_update_{version}",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                
                # Закрываем текущее приложение
                self.logger.info("Закрытие приложения для обновления")
                QApplication.quit()
                
            else:
                self.logger.info("Пользователь отказался от обновления")
                self._log_to_server("INFO", f"Пользователь отказался от обновления {version}")
                
                # Удаляем временный файл если пользователь отказался
                try:
                    if os.path.exists(zip_path):
                        os.unlink(zip_path)
                        self.logger.info("Временный файл обновления удален")
                except Exception as e:
                    self.logger.warning(f"Не удалось удалить временный файл обновления: {e}")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка установки обновления: {e}")
            self._log_to_server("ERROR", f"Ошибка установки обновления: {str(e)}")
            
            if parent_window:
                QMessageBox.critical(
                    parent_window,
                    "Ошибка установки",
                    f"Не удалось установить обновление:\n{str(e)}\n\n"
                    f"Пожалуйста, попробуйте обновить приложение вручную."
                )
    
    def _create_updater_script(self, zip_path, version):
        """Создание скрипта обновления для ZIP архива"""
        current_exe = sys.executable
        current_dir = os.path.dirname(current_exe)
        
        updater_script = f'''
import os
import sys
import time
import shutil
import zipfile
import subprocess
import tempfile
import traceback
from pathlib import Path

def main():
    print("=" * 60)
    print("🔄 ПРОЦЕСС ОБНОВЛЕНИЯ SABY HELPER")
    print("=" * 60)
    
    current_exe = r"{current_exe}"
    zip_file = r"{zip_path}"
    current_dir = r"{current_dir}"
    version = "{version}"
    
    print(f"Текущий файл: {{current_exe}}")
    print(f"ZIP архив: {{zip_file}}")
    print(f"Директория: {{current_dir}}")
    print(f"Версия: {{version}}")
    
    try:
        # Ждем пока основное приложение закроется
        print("\\n⏳ Ожидание закрытия основного приложения...")
        time.sleep(3)
        
        # Распаковываем ZIP архив во временную директорию
        print("📦 Распаковка обновления...")
        temp_dir = tempfile.mkdtemp(prefix="saby_update_")
        
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        print(f"Распаковано в: {{temp_dir}}")
        
        # Ищем обновленный EXE файл
        updated_exe = None
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith('.exe'):
                    updated_exe = os.path.join(root, file)
                    break
            if updated_exe:
                break
        
        if not updated_exe:
            raise FileNotFoundError("EXE файл не найден в архиве")
        
        print(f"Найден обновленный файл: {{updated_exe}}")
        
        # Ждем пока текущий EXE освободится
        print("⏳ Ожидание освобождения текущего файла...")
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                # Создаем временный файл для новой версии
                temp_new_exe = os.path.join(temp_dir, "saby_helper_new.exe")
                shutil.copy2(updated_exe, temp_new_exe)
                
                # Удаляем старый файл
                if os.path.exists(current_exe):
                    os.remove(current_exe)
                    print("✅ Старая версия удалена")
                    break
                else:
                    print("ℹ️ Старый файл не найден, продолжаем...")
                    break
            except PermissionError:
                if attempt < max_attempts - 1:
                    print(f"⏳ Ожидание освобождения файла... попытка {{attempt + 1}} из {{max_attempts}}")
                    time.sleep(2)
                else:
                    print("❌ Не удалось удалить старый файл")
                    # Пробуем переименовать старый файл
                    try:
                        old_backup = current_exe + ".old"
                        if os.path.exists(old_backup):
                            os.remove(old_backup)
                        os.rename(current_exe, old_backup)
                        print(f"✅ Переименован в {{old_backup}}")
                    except Exception as rename_e:
                        print(f"❌ Не удалось переименовать: {{rename_e}}")
                        return False
            except Exception as e:
                print(f"❌ Ошибка удаления файла: {{e}}")
                if attempt < max_attempts - 1:
                    time.sleep(2)
                else:
                    return False
        
        # Копируем новую версию из временного файла
        print("📋 Установка новой версии...")
        shutil.copy2(temp_new_exe, current_exe)
        print("✅ Новая версия установлена")
        
        # Устанавливаем права на выполнение
        try:
            os.chmod(current_exe, 0o755)  # rwxr-xr-x
        except:
            pass  # Игнорируем ошибки прав на Windows
        
        # Запускаем обновленное приложение
        print("🚀 Запуск обновленной версии...")
        
        # Пытаемся запустить несколько раз
        for attempt in range(3):
            try:
                # Используем абсолютный путь и правильную рабочую директорию
                startupinfo = None
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                
                # ВАЖНО: Устанавливаем переменную окружения для Qt
                env = os.environ.copy()
                if sys.platform == "win32":
                    # Указываем путь к плагинам Qt в той же директории
                    qt_plugin_path = os.path.join(current_dir, "PyQt5", "Qt5", "plugins")
                    if os.path.exists(qt_plugin_path):
                        env["QT_PLUGIN_PATH"] = qt_plugin_path
                        print(f"Установлен QT_PLUGIN_PATH: {{qt_plugin_path}}")
                
                process = subprocess.Popen(
                    [current_exe],
                    cwd=current_dir,
                    startupinfo=startupinfo,
                    env=env
                )
                print("✅ Приложение запущено")
                break
            except Exception as e:
                print(f"⚠️ Ошибка запуска попытка {{attempt + 1}}: {{e}}")
                if attempt < 2:
                    time.sleep(1)
                else:
                    print("❌ Не удалось запустить приложение")
                    return False
        
        # Очищаем временные файлы
        print("🗑️ Очистка временных файлов...")
        try:
            if os.path.exists(zip_file):
                os.remove(zip_file)
                print("✅ ZIP архив удален")
            
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                print("✅ Временная директория удалена")
            
            if os.path.exists(temp_new_exe):
                os.remove(temp_new_exe)
                print("✅ Временный файл новой версии удален")
        except Exception as e:
            print(f"⚠️ Не удалось удалить временные файлы: {{e}}")
        
        print("\\n" + "=" * 60)
        print("🎉 ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\\n❌ ОШИБКА ПРИ ОБНОВЛЕНИИ: {{e}}")
        traceback.print_exc()
        
        # Пытаемся восстановить из бэкапа
        try:
            old_backup = current_exe + ".old"
            if os.path.exists(old_backup):
                shutil.copy2(old_backup, current_exe)
                print("✅ Восстановлена старая версия из бэкапа")
                
                # Запускаем старую версию
                subprocess.Popen([current_exe])
        except Exception as restore_e:
            print(f"❌ Не удалось восстановить: {{restore_e}}")
        
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("\\n💥 ОБНОВЛЕНИЕ НЕ УДАЛОСЬ!")
        print("⚠️ Попробуйте переустановить приложение вручную")
        input("Нажмите Enter для выхода...")
    sys.exit(0 if success else 1)
'''
        
        return updater_script
    
    def check_and_notify(self, parent_window):
        """Проверка и уведомление о обновлениях - ОСНОВНОЙ МЕТОД ДЛЯ АВТОПРОВЕРКИ"""
        try:
            self.logger.info("🔍 АВТОМАТИЧЕСКАЯ проверка обновлений при запуске")
            self._log_to_server("INFO", "Автоматическая проверка обновлений при запуске")
            
            # Проверяем, нужно ли выполнять проверку
            auto_update_enabled = self.settings_manager.get_auto_update_enabled()
            if not auto_update_enabled:
                self.logger.info("Автообновление отключено, проверку не выполняем")
                return
            
            def check_callback(success, update_info):
                if success and update_info:
                    self.logger.info("🎯 Обновление найдено в автоматическом режиме")
                    
                    # Проверяем тип обновления
                    force_update = update_info.get('force_update', False)
                    
                    if force_update:
                        self.logger.info("ОБЯЗАТЕЛЬНОЕ обновление, запускаем автоматическую установку")
                        self.download_and_install_update(update_info, parent_window)
                    else:
                        self.logger.info("Обычное обновление, показываем диалог")
                        try:
                            from ui_components.dialogs import UpdateDialog
                            dialog = UpdateDialog(self, parent_window)
                            dialog.set_update_info(update_info)
                            dialog.exec_()
                        except Exception as e:
                            self.logger.error(f"❌ Ошибка показа диалога обновлений: {e}")
                            self._log_to_server("ERROR", f"Ошибка показа диалога обновлений: {str(e)}")
                else:
                    self.logger.info("✅ Автоматическая проверка: обновлений нет")
            
            # Запускаем асинхронную проверку
            self.check_for_updates_async(check_callback)
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка автоматической проверки обновлений: {e}")
            self._log_to_server("ERROR", f"Ошибка автоматической проверки обновлений: {str(e)}")
    
    def get_update_history(self):
        """Получение истории обновлений"""
        history = {}
        settings = self.settings_manager.settings
        
        for key in settings.allKeys():
            if key.startswith("last_installed_update_"):
                version = key.replace("last_installed_update_", "")
                timestamp = settings.value(key)
                history[version] = timestamp
        
        return history
    
    def get_last_update_check(self):
        """Получение даты последней проверки обновлений"""
        return self.settings_manager.get_last_update_check()
    
    def get_auto_update_status(self):
        """Получение статуса автообновления"""
        return self.settings_manager.get_auto_update_enabled()