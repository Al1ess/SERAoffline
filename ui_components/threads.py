# ui_components/threads.py
"""
Потоки для выполнения фоновых задач - ОБНОВЛЕННАЯ ВЕРСИЯ С БАЗОВЫМИ МЕХАНИЗМАМИ И ПЛАТЕЖНЫМИ ТЕРМИНАЛАМИ
"""

import logging
import requests
import tempfile
from PyQt5.QtCore import QThread, pyqtSignal

from log_analyzer import SupportLogAnalyzer
from marking_analyzer import MarkingLogAnalyzer
from basic_mechanisms_analyzer import BasicMechanismsAnalyzer
from payment_terminal_analyzer import PaymentTerminalAnalyzer

logger = logging.getLogger(__name__)

class AnalysisThread(QThread):
    """Поток для выполнения анализа ошибок"""
    
    analysis_finished = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, file_path, department, month):
        super().__init__()
        self.file_path = file_path
        self.department = department
        self.month = month
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        try:
            self.progress_updated.emit(10)
            
            from analyzer import ErrorAnalyzer
            analyzer = ErrorAnalyzer(self.file_path)
            self.progress_updated.emit(40)
            
            analysis_result = analyzer.analyze_errors()
            self.progress_updated.emit(80)
            
            self.progress_updated.emit(100)
            self.analysis_finished.emit(analysis_result)
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа: {e}")
            self.analysis_error.emit(str(e))

class LogAnalysisThread(QThread):
    """Поток для анализа логов"""
    
    analysis_finished = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, archive_path, analysis_method, analysis_date, include_warnings=False):
        super().__init__()
        self.archive_path = archive_path
        self.analysis_method = analysis_method
        self.analysis_date = analysis_date
        self.include_warnings = include_warnings
        self.analyzer = SupportLogAnalyzer()
    
    def run(self):
        try:
            self.progress_updated.emit(10)
            
            temp_dir = self.analyzer.extract_archive(self.archive_path)
            if not temp_dir:
                self.analysis_error.emit("Не удалось распаковать архив")
                return
            
            self.progress_updated.emit(30)
            
            log_dir = self.analyzer.find_logs_directory(self.analysis_date)
            if not log_dir:
                self.analysis_error.emit("Логов за выбранный период нет")
                return
            
            self.progress_updated.emit(60)
            
            if self.analysis_method == "general":
                result = self.analyzer.general_analysis(log_dir, self.include_warnings)
                formatted_result = self.analyzer.format_general_analysis_result(result)
                structured_data = result
            elif self.analysis_method == "receipt":
                result = self.analyzer.receipt_analysis(log_dir)
                formatted_result = self.analyzer.format_receipt_analysis_result(result)
                structured_data = result
            else:
                self.analysis_error.emit("Неизвестный метод анализа")
                return
            
            self.progress_updated.emit(90)
            
            final_result = {
                'formatted_text': formatted_result,
                'structured_data': structured_data,
                'analysis_method': self.analysis_method
            }
            
            self.analysis_finished.emit(final_result)
            self.progress_updated.emit(100)
            
        except Exception as e:
            self.analysis_error.emit(f"Ошибка анализа: {str(e)}")
        finally:
            self.analyzer.cleanup()

class MarkingAnalysisThread(QThread):
    """Поток для анализа логов маркировки"""
    
    analysis_finished = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, archive_path, method_index, analysis_date, use_devices=True):
        super().__init__()
        self.archive_path = archive_path
        self.method_index = method_index
        self.analysis_date = analysis_date
        self.use_devices = use_devices
        self.analyzer = MarkingLogAnalyzer()
    
    def run(self):
        try:
            self.progress_updated.emit(10)
            
            temp_dir = self.analyzer.extract_archive(self.archive_path)
            if not temp_dir:
                self.analysis_error.emit("Не удалось распаковать архив маркировки")
                return
            
            self.progress_updated.emit(30)
            
            log_dir = self.analyzer.find_logs_directory(self.analysis_date)
            if not log_dir:
                self.analysis_error.emit("Логов маркировки за выбранный период нет")
                return
            
            self.progress_updated.emit(60)
            
            results = []
            formatted_text = ""
            
            if self.method_index == 0:  # Считать все сканирования
                if self.use_devices:
                    results = self.analyzer.analyze_all_scans_devices(log_dir)
                else:
                    results = self.analyzer.analyze_all_scans_console(log_dir)
                formatted_text = self.analyzer.format_scans_result(results)
                
            elif self.method_index == 1:  # Информация по КМ
                results = self.analyzer.analyze_marking_info(log_dir)
                formatted_text = self.analyzer.format_marking_info_result(results)
                
            elif self.method_index == 2:  # Подключение ЛМ ЧЗ
                results = self.analyzer.analyze_connection_issues(log_dir)
                formatted_text = self.analyzer.format_connection_issues_result(results)
                
            elif self.method_index == 3:  # Логин и пароль ЛМ ЧЗ
                results = self.analyzer.analyze_login_password(log_dir)
                formatted_text = self.analyzer.format_login_password_result(results)
                
            elif self.method_index == 4:  # Проверка вскрытия
                results = self.analyzer.analyze_opening_check(log_dir)
                formatted_text = self.analyzer.format_opening_check_result(results)
            
            else:
                self.analysis_error.emit("Неизвестный метод анализа маркировки")
                return
            
            self.progress_updated.emit(90)
            
            final_result = {
                'results': results,
                'formatted_text': formatted_text,
                'method_index': self.method_index
            }
            
            self.analysis_finished.emit(final_result)
            self.progress_updated.emit(100)
            
        except Exception as e:
            self.analysis_error.emit(f"Ошибка анализа маркировки: {str(e)}")
        finally:
            self.analyzer.cleanup()

class BasicMechanismsThread(QThread):
    """Поток для анализа базовых механизмов"""
    
    analysis_finished = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, archive_path, analysis_date, use_custom_patterns=False, custom_patterns=""):
        super().__init__()
        self.archive_path = archive_path
        self.analysis_date = analysis_date
        self.use_custom_patterns = use_custom_patterns
        self.custom_patterns = custom_patterns
        self.analyzer = BasicMechanismsAnalyzer()
    
    def run(self):
        try:
            self.progress_updated.emit(10)
            
            temp_dir = self.analyzer.extract_archive(self.archive_path)
            if not temp_dir:
                self.analysis_error.emit("Не удалось распаковать архив")
                return
            
            self.progress_updated.emit(30)
            
            # Настраиваем шаблоны если нужно
            if self.use_custom_patterns and self.custom_patterns:
                self.analyzer.set_custom_patterns(self.custom_patterns)
                self.analyzer.set_use_custom_patterns(True)
            
            log_dir = self.analyzer.find_system_info_directory()
            if not log_dir:
                self.analysis_error.emit("Директория system_info не найдена в архиве")
                return
            
            self.progress_updated.emit(60)
            
            # Анализируем журналы ОС
            app_events, sys_events = self.analyzer.analyze_os_logs(log_dir)
            formatted_text = self.analyzer.format_os_logs_result(app_events, sys_events)
            
            self.progress_updated.emit(90)
            
            final_result = {
                'application_events': app_events,
                'system_events': sys_events,
                'formatted_text': formatted_text,
                'total_events': len(app_events) + len(sys_events)
            }
            
            self.analysis_finished.emit(final_result)
            self.progress_updated.emit(100)
            
        except Exception as e:
            self.analysis_error.emit(f"Ошибка анализа базовых механизмов: {str(e)}")
        finally:
            self.analyzer.cleanup()

class PaymentTerminalThread(QThread):
    """Поток для анализа платежных терминалов"""
    
    analysis_finished = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, archive_path, analysis_date):
        super().__init__()
        self.archive_path = archive_path
        self.analysis_date = analysis_date
        self.analyzer = PaymentTerminalAnalyzer()
    
    def run(self):
        try:
            self.progress_updated.emit(10)
            
            temp_dir = self.analyzer.extract_archive(self.archive_path)
            if not temp_dir:
                self.analysis_error.emit("Не удалось распаковать архив")
                return
            
            self.progress_updated.emit(30)
            
            # Ищем директорию pts_vendor
            pts_dir = self.analyzer.find_pts_vendor_directory()
            if not pts_dir:
                self.analysis_error.emit("Директория pts_vendor не найдена. Драйвер терминала не установлен.")
                return
            
            self.progress_updated.emit(50)
            
            # Обнаруживаем драйверы
            drivers = self.analyzer.detect_drivers(pts_dir)
            drivers_text = self.analyzer.format_drivers_result(drivers)
            
            # Анализируем найденные драйверы
            inpas_transactions = []
            sberbank_transactions = []
            
            for driver in drivers:
                if driver.driver_type == "INPAS" and driver.found:
                    inpas_transactions = self.analyzer.analyze_inpas_driver(
                        f"{pts_dir}/{driver.driver_name}", 
                        self.analysis_date
                    )
                
                elif driver.driver_type in ["SBERBANK", "SC552"] and driver.found:
                    sberbank_transactions = self.analyzer.analyze_sberbank_driver(
                        f"{pts_dir}/{driver.driver_name}", 
                        self.analysis_date
                    )
            
            self.progress_updated.emit(80)
            
            inpas_text = self.analyzer.format_inpas_result(inpas_transactions)
            sberbank_text = self.analyzer.format_sberbank_result(sberbank_transactions)
            
            # Объединяем все результаты
            formatted_text = f"{drivers_text}\n\n{inpas_text}\n\n{sberbank_text}"
            
            self.progress_updated.emit(90)
            
            final_result = {
                'drivers': drivers,
                'inpas_transactions': inpas_transactions,
                'sberbank_transactions': sberbank_transactions,
                'formatted_text': formatted_text,
                'total_transactions': len(inpas_transactions) + len(sberbank_transactions)
            }
            
            self.analysis_finished.emit(final_result)
            self.progress_updated.emit(100)
            
        except Exception as e:
            self.analysis_error.emit(f"Ошибка анализа платежных терминалов: {str(e)}")
        finally:
            self.analyzer.cleanup()

class ServerCheckThread(QThread):
    """Поток для проверки серверов"""
    
    check_finished = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
    
    def run(self):
        results = {}
        
        # Проверяем сервер Saby
        try:
            response = requests.get("https://online.sbis.ru", timeout=10)
            results['saby'] = {
                'status': '✅ Доступен' if response.status_code == 200 else '❌ Ошибка',
                'response_time': response.elapsed.total_seconds()
            }
        except Exception as e:
            results['saby'] = {
                'status': '❌ Не доступен',
                'error': str(e)
            }
        
        # Проверяем сервер обновлений
        try:
            response = requests.get("http://155.212.171.112:5002/health", timeout=10)
            results['update_server'] = {
                'status': '✅ Доступен' if response.status_code == 200 else '❌ Ошибка',
                'response_time': response.elapsed.total_seconds()
            }
        except Exception as e:
            results['update_server'] = {
                'status': '❌ Не доступен',
                'error': str(e)
            }
        
        # Проверяем сервер лицензий
        try:
            response = requests.get("http://155.212.171.112:5000/health", timeout=10)
            results['license_server'] = {
                'status': '✅ Доступен' if response.status_code == 200 else '❌ Ошибка',
                'response_time': response.elapsed.total_seconds()
            }
        except Exception as e:
            results['license_server'] = {
                'status': '❌ Не доступен',
                'error': str(e)
            }
        
        self.check_finished.emit(results)

class UpdateDownloadThread(QThread):
    """Поток для загрузки обновлений"""
    
    progress_updated = pyqtSignal(int)
    download_finished = pyqtSignal(str)
    download_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        try:
            session = requests.Session()
            session.trust_env = False
            
            download_url = "http://155.212.171.112:5002/api/download-update"
            
            response = session.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.exe')
            
            downloaded_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
                    downloaded_size += len(chunk)
                    
                    if total_size > 0:
                        progress = int((downloaded_size / total_size) * 100)
                        self.progress_updated.emit(progress)
            
            temp_file.close()
            self.download_finished.emit(temp_file.name)
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки обновления: {e}")
            self.download_error.emit(str(e))