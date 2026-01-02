"""
Страницы интерфейса приложения - ОБНОВЛЕННАЯ ВЕРСИЯ С БАЗОВЫМИ МЕХАНИЗМАМИ И ПЛАТЕЖНЫМИ ТЕРМИНАЛАМИ
"""

import os
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QFileDialog, QTextEdit, 
                             QProgressBar, QGroupBox, QTabWidget, QFormLayout,
                             QDateEdit, QCheckBox, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QToolButton, QRadioButton, QButtonGroup,
                             QSplitter, QFrame, QLineEdit, QGridLayout, QSpinBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDesktopServices

from config import DEPARTMENTS, MONTHS, CURRENT_YEAR, CONTACT_INFO, APP_VERSION
from analyzer import ErrorAnalyzer
from report_generator import ReportGenerator
from pdf_generator import PDFReportGenerator
from marking_analyzer import MarkingLogAnalyzer
from modules.log_downloader import LogDownloader

def create_home_page(main_window):
    """Создание домашней страницы"""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(40, 40, 40, 40)
    
    welcome_label = QLabel("Добро пожаловать в Saby Helper!")
    welcome_label.setStyleSheet("""
        QLabel {
            color: #f8f8f2;
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 20px;
        }
    """)
    layout.addWidget(welcome_label)
    
    # Информация о лицензии
    license_group = QGroupBox("🔐 Информация о лицензии")
    license_group.setStyleSheet("""
        QGroupBox {
            color: #f8f8f2;
            font-size: 16px;
            font-weight: bold;
            border: 2px solid #6272a4;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
    """)
    
    license_layout = QFormLayout(license_group)
    
    main_window.license_status_home = QLabel("Не активирована")
    main_window.license_status_home.setStyleSheet("color: #ff5555; font-size: 14px;")
    
    main_window.license_info_home = QLabel("Для работы приложения требуется активация")
    main_window.license_info_home.setStyleSheet("color: #f8f8f2; font-size: 12px;")
    main_window.license_info_home.setWordWrap(True)
    
    license_btn = QPushButton("🎯 Управление лицензией")
    license_btn.setStyleSheet(main_window._get_button_style())
    license_btn.clicked.connect(main_window._show_license_dialog)
    
    license_layout.addRow("Статус:", main_window.license_status_home)
    license_layout.addRow("Информация:", main_window.license_info_home)
    license_layout.addRow(license_btn)
    
    layout.addWidget(license_group)
    
    # Статус серверов
    server_group = QGroupBox("🌐 Статус серверов")
    server_group.setStyleSheet(license_group.styleSheet())

    server_layout = QVBoxLayout(server_group)

    main_window.server_status_home = QLabel("Проверка статуса серверов...")
    main_window.server_status_home.setStyleSheet("color: #f8f8f2; font-size: 12px;")
    main_window.server_status_home.setWordWrap(True)

    server_check_btn = QPushButton("🔍 Проверить связь с серверами")
    server_check_btn.setStyleSheet(main_window._get_button_style())
    server_check_btn.clicked.connect(main_window._check_servers_manual)

    server_layout.addWidget(main_window.server_status_home)
    server_layout.addWidget(server_check_btn)

    layout.addWidget(server_group)
    
    # Выбор утилиты
    tools_group = QGroupBox("🛠️ Доступные утилиты")
    tools_group.setStyleSheet(license_group.styleSheet())
    
    tools_layout = QVBoxLayout(tools_group)
    
    error_analyzer_btn = QPushButton("📊 Аналитика ошибок")
    error_analyzer_btn.setStyleSheet(main_window._get_tool_button_style())
    error_analyzer_btn.clicked.connect(lambda: main_window._switch_to_page(1))
    
    log_analyzer_btn = QPushButton("📝 Анализатор логов")
    log_analyzer_btn.setStyleSheet(main_window._get_tool_button_style())
    log_analyzer_btn.clicked.connect(lambda: main_window._switch_to_page(2))
    
    log_download_btn = QPushButton("📥 Выгрузка логов")
    log_download_btn.setStyleSheet(main_window._get_tool_button_style())
    log_download_btn.clicked.connect(lambda: main_window._switch_to_page(3))
    
    tools_layout.addWidget(error_analyzer_btn)
    tools_layout.addWidget(log_analyzer_btn)
    tools_layout.addWidget(log_download_btn)
    
    layout.addWidget(tools_group)
    layout.addStretch()
    
    return page

def create_error_analyzer_page(main_window):
    """Создание страницы аналитики ошибок"""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 20, 20, 20)
    
    title = QLabel("📊 Аналитика ошибок")
    title.setStyleSheet("color: #f8f8f2; font-size: 24px; font-weight: bold; margin-bottom: 20px;")
    layout.addWidget(title)
    
    tabs = QTabWidget()
    
    # Вкладка загрузки и анализа
    analysis_tab = QWidget()
    analysis_layout = QVBoxLayout(analysis_tab)
    
    # Группа выбора отдела
    dept_group = QGroupBox("Выбор отдела")
    dept_group.setStyleSheet("""
        QGroupBox {
            color: #f8f8f2;
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
    dept_layout = QVBoxLayout(dept_group)
    
    main_window.department_combo = QComboBox()
    main_window.department_combo.addItems(DEPARTMENTS.keys())
    main_window.department_combo.setStyleSheet("""
        QComboBox {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            padding: 8px;
            border-radius: 4px;
        }
    """)
    dept_layout.addWidget(QLabel("Отдел:"))
    dept_layout.addWidget(main_window.department_combo)
    analysis_layout.addWidget(dept_group)
    
    # Группа выбора месяца
    month_group = QGroupBox("Выбор периода")
    month_group.setStyleSheet(dept_group.styleSheet())
    month_layout = QVBoxLayout(month_group)
    
    main_window.month_combo = QComboBox()
    main_window.month_combo.addItems(MONTHS.keys())
    main_window.month_combo.setStyleSheet(main_window.department_combo.styleSheet())
    month_layout.addWidget(QLabel("Месяц:"))
    month_layout.addWidget(main_window.month_combo)
    analysis_layout.addWidget(month_group)
    
    # Группа загрузки файла
    file_group = QGroupBox("Загрузка файла")
    file_group.setStyleSheet(dept_group.styleSheet())
    file_layout = QVBoxLayout(file_group)
    
    main_window.file_label = QLabel("Файл не выбран")
    main_window.file_label.setWordWrap(True)
    main_window.file_label.setStyleSheet("color: #f8f8f2; background-color: #44475a; padding: 10px; border-radius: 4px;")
    
    main_window.load_file_btn = QPushButton("📁 Выбрать файл Excel")
    main_window.load_file_btn.setMinimumHeight(40)
    main_window.load_file_btn.setStyleSheet(main_window._get_button_style())
    main_window.load_file_btn.clicked.connect(main_window._load_file)
    
    file_layout.addWidget(QLabel("Файл отчета:"))
    file_layout.addWidget(main_window.file_label)
    file_layout.addWidget(main_window.load_file_btn)
    analysis_layout.addWidget(file_group)
    
    # Прогресс бар
    main_window.progress_bar = QProgressBar()
    main_window.progress_bar.setVisible(False)
    main_window.progress_bar.setStyleSheet("""
        QProgressBar {
            border: 2px solid #6272a4;
            border-radius: 5px;
            text-align: center;
            color: #f8f8f2;
        }
        QProgressBar::chunk {
            background-color: #50fa7b;
            width: 20px;
        }
    """)
    analysis_layout.addWidget(main_window.progress_bar)
    
    # Кнопка анализа
    main_window.analyze_btn = QPushButton("📊 Запустить анализ")
    main_window.analyze_btn.setMinimumHeight(50)
    main_window.analyze_btn.setEnabled(False)
    main_window.analyze_btn.setStyleSheet(main_window._get_button_style())
    main_window.analyze_btn.clicked.connect(main_window._start_analysis)
    analysis_layout.addWidget(main_window.analyze_btn)
    
    # Кнопка экспорта
    main_window.export_btn = QPushButton("📄 Экспорт в PDF")
    main_window.export_btn.setMinimumHeight(40)
    main_window.export_btn.setEnabled(False)
    main_window.export_btn.setStyleSheet(main_window._get_button_style())
    main_window.export_btn.clicked.connect(main_window._export_to_pdf)
    analysis_layout.addWidget(main_window.export_btn)
    
    analysis_layout.addStretch()
    
    # Вкладка результатов
    results_tab = QWidget()
    results_layout = QVBoxLayout(results_tab)
    
    main_window.text_report = QTextEdit()
    main_window.text_report.setReadOnly(True)
    main_window.text_report.setStyleSheet("""
        QTextEdit {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            border-radius: 5px;
            padding: 10px;
        }
    """)
    results_layout.addWidget(main_window.text_report)
    
    tabs.addTab(analysis_tab, "📁 Анализ")
    tabs.addTab(results_tab, "📋 Результаты")
    
    layout.addWidget(tabs)
    
    return page

def create_log_download_page(main_window):
    """Создание страницы выгрузки логов - УЛУЧШЕННАЯ ВЕРСИЯ БЕЗ ПРИМЕРА"""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(40, 40, 40, 40)
    
    title = QLabel("📥 Выгрузка диагностических логов")
    title.setStyleSheet("""
        QLabel {
            color: #f8f8f2;
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
        }
    """)
    layout.addWidget(title)
    
    # Основной контейнер
    container = QWidget()
    container_layout = QVBoxLayout(container)
    
    # Группа ввода номера инцидента
    incident_group = QGroupBox("Введите номер диагностической карты")
    incident_group.setStyleSheet("""
        QGroupBox {
            color: #f8f8f2;
            font-size: 16px;
            font-weight: bold;
            border: 2px solid #6272a4;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
    """)
    
    incident_layout = QVBoxLayout(incident_group)
    
    # Поле для ввода номера
    incident_layout.addWidget(QLabel("Номер диагностической карты:"))
    
    main_window.incident_input = QLineEdit()
    main_window.incident_input.setPlaceholderText("Введите цифровой номер диагностической карты...")
    main_window.incident_input.setStyleSheet("""
        QLineEdit {
            background-color: #44475a;
            color: #f8f8f2;
            border: 2px solid #6272a4;
            padding: 12px;
            border-radius: 6px;
            font-size: 14px;
        }
        QLineEdit:focus {
            border: 2px solid #50fa7b;
        }
    """)
    incident_layout.addWidget(main_window.incident_input)
    
    # Кнопка выгрузки
    download_btn = QPushButton("🚀 Выгрузить логи")
    download_btn.setMinimumHeight(50)
    download_btn.setStyleSheet(main_window._get_button_style())
    download_btn.clicked.connect(main_window._download_logs)
    incident_layout.addWidget(download_btn)
    
    container_layout.addWidget(incident_group)
    
    # Информационная группа
    info_group = QGroupBox("⚠️ Важная информация")
    info_group.setStyleSheet("""
        QGroupBox {
            color: #f8f8f2;
            font-size: 14px;
            border: 2px solid #ffb86c;
            border-radius: 8px;
            margin-top: 20px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #ffb86c;
        }
    """)
    
    info_layout = QVBoxLayout(info_group)
    
    info_text = QLabel(
        "Для успешной загрузки диагностических логов необходимо:\n\n"
        "✅ Рабочий VPN должен быть включен\n"
        "✅ Вы должны быть авторизованы в Cloud в браузере по умолчанию\n\n"
        "После нажатия кнопки 'Выгрузить логи' откроется браузер "
        "со ссылкой на скачивание логов."
    )
    info_text.setStyleSheet("color: #f8f8f2; font-size: 13px; line-height: 1.5;")
    info_text.setWordWrap(True)
    
    info_layout.addWidget(info_text)
    
    container_layout.addWidget(info_group)
    
    container_layout.addStretch()
    
    layout.addWidget(container)
    
    return page

def create_log_analyzer_page(main_window):
    """Создание страницы анализа логов - ОБНОВЛЕННАЯ ВЕРСИЯ С БАЗОВЫМИ МЕХАНИЗМАМИ И ПЛАТЕЖНЫМИ ТЕРМИНАЛАМИ"""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 20, 20, 20)
    
    title = QLabel("📝 Анализатор логов")
    title.setStyleSheet("color: #f8f8f2; font-size: 24px; font-weight: bold; margin-bottom: 20px;")
    layout.addWidget(title)
    
    tabs = QTabWidget()
    
    support_tab = _create_support_analyzer_tab(main_window)
    tabs.addTab(support_tab, "🔧 Поддержка оборудования")
    
    marking_tab = _create_marking_analyzer_tab(main_window)
    tabs.addTab(marking_tab, "🏷️ Маркировка")
    
    basic_mech_tab = _create_basic_mechanisms_tab(main_window)
    tabs.addTab(basic_mech_tab, "⚙️ Базовые механизмы")
    
    layout.addWidget(tabs)
    
    return page

def _create_support_analyzer_tab(main_window):
    """Создание вкладки анализатора поддержки оборудования"""
    tab = QWidget()
    layout = QVBoxLayout(tab)
    
    # Группа загрузки архива
    archive_group = QGroupBox("📁 Загрузка архива логов")
    archive_group.setStyleSheet("""
        QGroupBox {
            color: #f8f8f2;
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
    
    archive_layout = QVBoxLayout(archive_group)
    
    main_window.drop_area = QLabel("Перетащите архив логов сюда или нажмите для выбора")
    main_window.drop_area.setStyleSheet("""
        QLabel {
            color: #f8f8f2;
            background-color: #44475a;
            padding: 40px;
            border-radius: 10px;
            border: 2px dashed #6272a4;
            margin: 10px 0px;
        }
    """)
    main_window.drop_area.setAlignment(Qt.AlignCenter)
    main_window.drop_area.setAcceptDrops(True)
    main_window.drop_area.mousePressEvent = _select_log_archive_factory(main_window)
    main_window.drop_area.dragEnterEvent = _drag_enter_event_factory(main_window)
    main_window.drop_area.dropEvent = _drop_event_factory(main_window)
    
    archive_layout.addWidget(main_window.drop_area)
    
    main_window.selected_archive_label = QLabel("Архив не выбран")
    main_window.selected_archive_label.setStyleSheet("color: #f8f8f2; background-color: #44475a; padding: 10px; border-radius: 4px;")
    main_window.selected_archive_label.setWordWrap(True)
    archive_layout.addWidget(main_window.selected_archive_label)
    
    layout.addWidget(archive_group)
    
    # Группа настроек анализа
    settings_group = QGroupBox("⚙️ Настройки анализа")
    settings_group.setStyleSheet(archive_group.styleSheet())
    
    settings_layout = QFormLayout(settings_group)
    
    main_window.analysis_method_combo = QComboBox()
    main_window.analysis_method_combo.addItems(["🔍 Общий анализ", "🧾 Считать операции", "💳 Платежный терминал"])
    main_window.analysis_method_combo.setStyleSheet("""
        QComboBox {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            padding: 8px;
            border-radius: 4px;
        }
    """)
    main_window.analysis_method_combo.currentIndexChanged.connect(_on_analysis_method_changed_factory(main_window))
    settings_layout.addRow("Метод анализа:", main_window.analysis_method_combo)
    
    main_window.analysis_date_edit = QDateEdit()
    main_window.analysis_date_edit.setDate(datetime.now().date())
    main_window.analysis_date_edit.setCalendarPopup(True)
    main_window.analysis_date_edit.setStyleSheet("""
        QDateEdit {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            padding: 8px;
            border-radius: 4px;
        }
    """)
    settings_layout.addRow("Дата для анализа:", main_window.analysis_date_edit)
    
    main_window.include_warnings_check = QCheckBox("Прочитать предупреждения")
    main_window.include_warnings_check.setStyleSheet("QCheckBox { color: #f8f8f2; }")
    main_window.include_warnings_check.setEnabled(False)
    settings_layout.addRow(main_window.include_warnings_check)
    
    layout.addWidget(settings_group)
    
    # Кнопки анализа
    buttons_layout = QHBoxLayout()
    
    main_window.analyze_logs_btn = QPushButton("🔍 Запустить анализ логов")
    main_window.analyze_logs_btn.setStyleSheet(main_window._get_button_style())
    main_window.analyze_logs_btn.clicked.connect(main_window._start_log_analysis)
    main_window.analyze_logs_btn.setEnabled(False)
    
    main_window.export_logs_btn = QPushButton("💾 Экспорт в TXT")
    main_window.export_logs_btn.setStyleSheet(main_window._get_button_style())
    main_window.export_logs_btn.clicked.connect(main_window._export_log_analysis)
    main_window.export_logs_btn.setEnabled(False)
    
    main_window.clear_logs_btn = QPushButton("🗑️ Очистить результат")
    main_window.clear_logs_btn.setStyleSheet(main_window._get_button_style())
    main_window.clear_logs_btn.clicked.connect(main_window._clear_log_analysis)
    
    buttons_layout.addWidget(main_window.analyze_logs_btn)
    buttons_layout.addWidget(main_window.export_logs_btn)
    buttons_layout.addWidget(main_window.clear_logs_btn)
    
    layout.addLayout(buttons_layout)
    
    # Прогресс бар
    main_window.log_analysis_progress = QProgressBar()
    main_window.log_analysis_progress.setVisible(False)
    main_window.log_analysis_progress.setStyleSheet("""
        QProgressBar {
            border: 2px solid #6272a4;
            border-radius: 5px;
            text-align: center;
            color: #f8f8f2;
        }
        QProgressBar::chunk {
            background-color: #50fa7b;
            width: 20px;
        }
    """)
    layout.addWidget(main_window.log_analysis_progress)
    
    # Область результатов
    main_window.log_analysis_result_area = QWidget()
    result_layout = QVBoxLayout(main_window.log_analysis_result_area)
    
    # Таблицы для разных типов результатов
    main_window.operations_table = QTableWidget()
    main_window.operations_table.setStyleSheet("""
        QTableWidget {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            border-radius: 5px;
            gridline-color: #6272a4;
        }
        QTableWidget::item {
            padding: 5px;
            border-bottom: 1px solid #6272a4;
        }
        QHeaderView::section {
            background-color: #6272a4;
            color: white;
            padding: 5px;
            border: none;
        }
    """)
    main_window.operations_table.horizontalHeader().setStretchLastSection(True)
    main_window.operations_table.setAlternatingRowColors(True)
    main_window.operations_table.setEditTriggers(QTableWidget.NoEditTriggers)
    main_window.operations_table.setColumnCount(8)
    main_window.operations_table.setHorizontalHeaderLabels([
        "Время", "Статус печати", "Сумма", "Тип чека", 
        "№ операции", "Тип операции", "Способ оплаты", "РНМ"
    ])
    
    main_window.payment_terminal_table = QTableWidget()
    main_window.payment_terminal_table.setStyleSheet(main_window.operations_table.styleSheet())
    main_window.payment_terminal_table.horizontalHeader().setStretchLastSection(True)
    main_window.payment_terminal_table.setAlternatingRowColors(True)
    main_window.payment_terminal_table.setEditTriggers(QTableWidget.NoEditTriggers)
    
    main_window.log_analysis_result_text = QTextEdit()
    main_window.log_analysis_result_text.setReadOnly(True)
    main_window.log_analysis_result_text.setStyleSheet("""
        QTextEdit {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            border-radius: 5px;
            padding: 10px;
        }
    """)
    main_window.log_analysis_result_text.setPlaceholderText("Результаты анализа появятся здесь...")
    
    main_window.operations_summary_label = QLabel("")
    main_window.operations_summary_label.setStyleSheet("color: #f8f8f2; font-size: 14px; font-weight: bold; margin-top: 10px;")
    
    main_window.operations_help_btn = QToolButton()
    main_window.operations_help_btn.setText("💡")
    main_window.operations_help_btn.setToolTip("Показать справку по операциям")
    main_window.operations_help_btn.setStyleSheet("""
        QToolButton {
            background-color: #6272a4;
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 14px;
            width: 24px;
            height: 24px;
        }
        QToolButton:hover {
            background-color: #7282b4;
        }
    """)
    main_window.operations_help_btn.clicked.connect(main_window._show_operations_help_dialog)
    
    operations_header_layout = QHBoxLayout()
    operations_header_layout.addWidget(QLabel("📋 Операции с чеками"))
    operations_header_layout.addStretch()
    operations_header_layout.addWidget(main_window.operations_help_btn)
    
    result_layout.addLayout(operations_header_layout)
    result_layout.addWidget(main_window.operations_table)
    result_layout.addWidget(main_window.payment_terminal_table)
    result_layout.addWidget(main_window.operations_summary_label)
    result_layout.addWidget(main_window.log_analysis_result_text)
    
    # Скрываем все по умолчанию
    main_window.operations_table.setVisible(False)
    main_window.payment_terminal_table.setVisible(False)
    main_window.operations_summary_label.setVisible(False)
    main_window.operations_help_btn.setVisible(False)
    main_window.log_analysis_result_text.setVisible(True)
    
    layout.addWidget(main_window.log_analysis_result_area)
    
    return tab

def _create_marking_analyzer_tab(main_window):
    """Создание вкладки анализатора маркировки"""
    tab = QWidget()
    layout = QVBoxLayout(tab)
    
    # Группа загрузки архива
    archive_group = QGroupBox("📁 Загрузка архива логов маркировки")
    archive_group.setStyleSheet("""
        QGroupBox {
            color: #f8f8f2;
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
    
    archive_layout = QVBoxLayout(archive_group)
    
    main_window.marking_drop_area = QLabel("Перетащите архив логов маркировки сюда или нажмите для выбора")
    main_window.marking_drop_area.setStyleSheet("""
        QLabel {
            color: #f8f8f2;
            background-color: #44475a;
            padding: 40px;
            border-radius: 10px;
            border: 2px dashed #6272a4;
            margin: 10px 0px;
        }
    """)
    main_window.marking_drop_area.setAlignment(Qt.AlignCenter)
    main_window.marking_drop_area.setAcceptDrops(True)
    main_window.marking_drop_area.mousePressEvent = _select_marking_archive_factory(main_window)
    main_window.marking_drop_area.dragEnterEvent = _drag_enter_event_marking_factory(main_window)
    main_window.marking_drop_area.dropEvent = _drop_event_marking_factory(main_window)
    
    archive_layout.addWidget(main_window.marking_drop_area)
    
    main_window.selected_marking_archive_label = QLabel("Архив маркировки не выбран")
    main_window.selected_marking_archive_label.setStyleSheet("color: #f8f8f2; background-color: #44475a; padding: 10px; border-radius: 4px;")
    main_window.selected_marking_archive_label.setWordWrap(True)
    archive_layout.addWidget(main_window.selected_marking_archive_label)
    
    layout.addWidget(archive_group)
    
    # Группа настроек анализа маркировки
    marking_settings_group = QGroupBox("⚙️ Настройки анализа маркировки")
    marking_settings_group.setStyleSheet(archive_group.styleSheet())
    
    marking_settings_layout = QVBoxLayout(marking_settings_group)
    
    # Выбор метода анализа
    method_layout = QHBoxLayout()
    method_layout.addWidget(QLabel("Метод анализа:"))
    
    main_window.marking_method_combo = QComboBox()
    main_window.marking_method_combo.addItems([
        "🔍 Считать все сканирования",
        "📊 Информация по КМ", 
        "🔌 Подключение ЛМ ЧЗ",
        "🔑 Логин и пароль ЛМ ЧЗ",
        "📦 Проверка вскрытия"
    ])
    main_window.marking_method_combo.setStyleSheet("""
        QComboBox {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            padding: 8px;
            border-radius: 4px;
        }
    """)
    main_window.marking_method_combo.currentIndexChanged.connect(_on_marking_method_changed_factory(main_window))
    method_layout.addWidget(main_window.marking_method_combo)
    method_layout.addStretch()
    
    marking_settings_layout.addLayout(method_layout)
    
    # Принцип работы (только для сканирований)
    main_window.principle_group = QGroupBox("Принцип работы:")
    main_window.principle_group.setStyleSheet("""
        QGroupBox {
            color: #f8f8f2;
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
    
    principle_layout = QHBoxLayout(main_window.principle_group)
    
    main_window.devices_radio = QRadioButton("Devices")
    main_window.console_radio = QRadioButton("Console")
    main_window.devices_radio.setChecked(True)
    
    main_window.principle_button_group = QButtonGroup()
    main_window.principle_button_group.addButton(main_window.devices_radio)
    main_window.principle_button_group.addButton(main_window.console_radio)
    
    for radio in [main_window.devices_radio, main_window.console_radio]:
        radio.setStyleSheet("QRadioButton { color: #f8f8f2; }")
    
    principle_layout.addWidget(main_window.devices_radio)
    principle_layout.addWidget(main_window.console_radio)
    principle_layout.addStretch()
    
    marking_settings_layout.addWidget(main_window.principle_group)
    
    # Дата анализа
    date_layout = QHBoxLayout()
    date_layout.addWidget(QLabel("Дата для анализа:"))
    
    main_window.marking_date_edit = QDateEdit()
    main_window.marking_date_edit.setDate(datetime.now().date())
    main_window.marking_date_edit.setCalendarPopup(True)
    main_window.marking_date_edit.setStyleSheet("""
        QDateEdit {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            padding: 8px;
            border-radius: 4px;
        }
    """)
    date_layout.addWidget(main_window.marking_date_edit)
    date_layout.addStretch()
    
    marking_settings_layout.addLayout(date_layout)
    
    layout.addWidget(marking_settings_group)
    
    # Кнопки анализа маркировки
    marking_buttons_layout = QHBoxLayout()
    
    main_window.analyze_marking_btn = QPushButton("🔍 Запустить анализ маркировки")
    main_window.analyze_marking_btn.setStyleSheet(main_window._get_button_style())
    main_window.analyze_marking_btn.clicked.connect(main_window._start_marking_analysis)
    main_window.analyze_marking_btn.setEnabled(False)
    
    main_window.export_marking_btn = QPushButton("💾 Экспорт результатов")
    main_window.export_marking_btn.setStyleSheet(main_window._get_button_style())
    main_window.export_marking_btn.clicked.connect(main_window._export_marking_analysis)
    main_window.export_marking_btn.setEnabled(False)
    
    main_window.show_original_logs_btn = QPushButton("📄 Оригинальный лог")
    main_window.show_original_logs_btn.setStyleSheet(main_window._get_button_style())
    main_window.show_original_logs_btn.clicked.connect(main_window._show_original_marking_logs)
    main_window.show_original_logs_btn.setEnabled(False)
    
    main_window.clear_marking_btn = QPushButton("🗑️ Очистить результат")
    main_window.clear_marking_btn.setStyleSheet(main_window._get_button_style())
    main_window.clear_marking_btn.clicked.connect(main_window._clear_marking_analysis)
    
    marking_buttons_layout.addWidget(main_window.analyze_marking_btn)
    marking_buttons_layout.addWidget(main_window.export_marking_btn)
    marking_buttons_layout.addWidget(main_window.show_original_logs_btn)
    marking_buttons_layout.addWidget(main_window.clear_marking_btn)
    
    layout.addLayout(marking_buttons_layout)
    
    # Прогресс бар маркировки
    main_window.marking_progress_bar = QProgressBar()
    main_window.marking_progress_bar.setVisible(False)
    main_window.marking_progress_bar.setStyleSheet("""
        QProgressBar {
            border: 2px solid #6272a4;
            border-radius: 5px;
            text-align: center;
            color: #f8f8f2;
        }
        QProgressBar::chunk {
            background-color: #50fa7b;
            width: 20px;
        }
    """)
    layout.addWidget(main_window.marking_progress_bar)
    
    # Область результатов маркировки
    marking_results_splitter = QSplitter(Qt.Vertical)
    
    main_window.marking_result_text = QTextEdit()
    main_window.marking_result_text.setReadOnly(True)
    main_window.marking_result_text.setStyleSheet("""
        QTextEdit {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            border-radius: 5px;
            padding: 10px;
        }
    """)
    main_window.marking_result_text.setPlaceholderText("Результаты анализа маркировки появятся здесь...")
    main_window.marking_result_text.setVisible(False)
    
    main_window.marking_table = QTableWidget()
    main_window.marking_table.setStyleSheet("""
        QTableWidget {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            border-radius: 5px;
            gridline-color: #6272a4;
        }
        QTableWidget::item {
            padding: 5px;
            border-bottom: 1px solid #6272a4;
        }
        QHeaderView::section {
            background-color: #6272a4;
            color: white;
            padding: 5px;
            border: none;
        }
    """)
    main_window.marking_table.horizontalHeader().setStretchLastSection(True)
    main_window.marking_table.setAlternatingRowColors(True)
    main_window.marking_table.setEditTriggers(QTableWidget.NoEditTriggers)
    main_window.marking_table.setVisible(True)
    
    marking_results_splitter.addWidget(main_window.marking_result_text)
    marking_results_splitter.addWidget(main_window.marking_table)
    marking_results_splitter.setSizes([0, 500])
    
    layout.addWidget(marking_results_splitter)
    
    return tab

def _create_basic_mechanisms_tab(main_window):
    """Создание вкладки анализатора базовых механизмов"""
    tab = QWidget()
    layout = QVBoxLayout(tab)
    
    # Группа загрузки архива
    archive_group = QGroupBox("📁 Загрузка архива логов")
    archive_group.setStyleSheet("""
        QGroupBox {
            color: #f8f8f2;
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
    
    archive_layout = QVBoxLayout(archive_group)
    
    main_window.basic_drop_area = QLabel("Перетащите архив логов сюда или нажмите для выбора")
    main_window.basic_drop_area.setStyleSheet("""
        QLabel {
            color: #f8f8f2;
            background-color: #44475a;
            padding: 40px;
            border-radius: 10px;
            border: 2px dashed #6272a4;
            margin: 10px 0px;
        }
    """)
    main_window.basic_drop_area.setAlignment(Qt.AlignCenter)
    main_window.basic_drop_area.setAcceptDrops(True)
    main_window.basic_drop_area.mousePressEvent = _select_basic_archive_factory(main_window)
    main_window.basic_drop_area.dragEnterEvent = _drag_enter_event_basic_factory(main_window)
    main_window.basic_drop_area.dropEvent = _drop_event_basic_factory(main_window)
    
    archive_layout.addWidget(main_window.basic_drop_area)
    
    main_window.selected_basic_archive_label = QLabel("Архив не выбран")
    main_window.selected_basic_archive_label.setStyleSheet("color: #f8f8f2; background-color: #44475a; padding: 10px; border-radius: 4px;")
    main_window.selected_basic_archive_label.setWordWrap(True)
    archive_layout.addWidget(main_window.selected_basic_archive_label)
    
    layout.addWidget(archive_group)
    
    # Группа настроек анализа
    settings_group = QGroupBox("⚙️ Настройки анализа журналов ОС")
    settings_group.setStyleSheet(archive_group.styleSheet())
    
    settings_layout = QVBoxLayout(settings_group)
    
    # Метод анализа
    method_layout = QHBoxLayout()
    method_layout.addWidget(QLabel("Метод анализа:"))
    
    method_label = QLabel("Считать журналы ОС")
    method_label.setStyleSheet("color: #f8f8f2; font-weight: bold;")
    method_layout.addWidget(method_label)
    method_layout.addStretch()
    
    settings_layout.addLayout(method_layout)
    
    # Дата анализа
    date_layout = QHBoxLayout()
    date_layout.addWidget(QLabel("Дата для анализа:"))
    
    main_window.basic_date_edit = QDateEdit()
    main_window.basic_date_edit.setDate(datetime.now().date())
    main_window.basic_date_edit.setCalendarPopup(True)
    main_window.basic_date_edit.setStyleSheet("""
        QDateEdit {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            padding: 8px;
            border-radius: 4px;
        }
    """)
    date_layout.addWidget(main_window.basic_date_edit)
    date_layout.addStretch()
    
    settings_layout.addLayout(date_layout)
    
    # Настройка шаблонов
    patterns_group = QGroupBox("Настройка шаблонов кодов событий")
    patterns_group.setStyleSheet("""
        QGroupBox {
            color: #f8f8f2;
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
    
    patterns_layout = QVBoxLayout(patterns_group)
    
    main_window.use_custom_patterns_check = QCheckBox("Считать по шаблону")
    main_window.use_custom_patterns_check.setStyleSheet("QCheckBox { color: #f8f8f2; font-weight: bold; }")
    main_window.use_custom_patterns_check.stateChanged.connect(_on_use_custom_patterns_changed_factory(main_window))
    patterns_layout.addWidget(main_window.use_custom_patterns_check)
    
    patterns_layout.addWidget(QLabel("Укажите шаблон кодов через запятую:"))
    
    main_window.custom_patterns_input = QLineEdit()
    main_window.custom_patterns_input.setPlaceholderText("Например: 41, 55, 98, 7031, 7001, 7000")
    main_window.custom_patterns_input.setStyleSheet("""
        QLineEdit {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            padding: 8px;
            border-radius: 4px;
        }
    """)
    main_window.custom_patterns_input.setEnabled(False)
    patterns_layout.addWidget(main_window.custom_patterns_input)
    
    default_patterns_label = QLabel("Коды по умолчанию: 41, 55, 98, 7031, 7001, 7000")
    default_patterns_label.setStyleSheet("color: #6272a4; font-size: 11px; font-style: italic;")
    patterns_layout.addWidget(default_patterns_label)
    
    settings_layout.addWidget(patterns_group)
    
    layout.addWidget(settings_group)
    
    # Кнопки анализа
    buttons_layout = QHBoxLayout()
    
    main_window.analyze_basic_btn = QPushButton("🔍 Запустить анализ журналов ОС")
    main_window.analyze_basic_btn.setStyleSheet(main_window._get_button_style())
    main_window.analyze_basic_btn.clicked.connect(main_window._start_basic_analysis)
    main_window.analyze_basic_btn.setEnabled(False)
    
    main_window.export_basic_btn = QPushButton("💾 Экспорт результатов")
    main_window.export_basic_btn.setStyleSheet(main_window._get_button_style())
    main_window.export_basic_btn.clicked.connect(main_window._export_basic_analysis)
    main_window.export_basic_btn.setEnabled(False)
    
    main_window.clear_basic_btn = QPushButton("🗑️ Очистить результат")
    main_window.clear_basic_btn.setStyleSheet(main_window._get_button_style())
    main_window.clear_basic_btn.clicked.connect(main_window._clear_basic_analysis)
    
    buttons_layout.addWidget(main_window.analyze_basic_btn)
    buttons_layout.addWidget(main_window.export_basic_btn)
    buttons_layout.addWidget(main_window.clear_basic_btn)
    
    layout.addLayout(buttons_layout)
    
    # Прогресс бар
    main_window.basic_progress_bar = QProgressBar()
    main_window.basic_progress_bar.setVisible(False)
    main_window.basic_progress_bar.setStyleSheet("""
        QProgressBar {
            border: 2px solid #6272a4;
            border-radius: 5px;
            text-align: center;
            color: #f8f8f2;
        }
        QProgressBar::chunk {
            background-color: #50fa7b;
            width: 20px;
        }
    """)
    layout.addWidget(main_window.basic_progress_bar)
    
    # Область результатов
    results_widget = QWidget()
    results_layout = QVBoxLayout(results_widget)
    
    # Переключатель журналов
    log_switch_layout = QHBoxLayout()
    log_switch_layout.addWidget(QLabel("Журнал:"))
    
    main_window.os_log_switch_combo = QComboBox()
    main_window.os_log_switch_combo.addItems(["Журнал приложения", "Журнал системы"])
    main_window.os_log_switch_combo.setStyleSheet("""
        QComboBox {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            padding: 8px;
            border-radius: 4px;
        }
    """)
    main_window.os_log_switch_combo.currentIndexChanged.connect(_on_os_log_switch_changed_factory(main_window))
    log_switch_layout.addWidget(main_window.os_log_switch_combo)
    log_switch_layout.addStretch()
    
    results_layout.addLayout(log_switch_layout)
    
    # Таблица результатов
    main_window.os_events_table = QTableWidget()
    main_window.os_events_table.setStyleSheet("""
        QTableWidget {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            border-radius: 5px;
            gridline-color: #6272a4;
        }
        QTableWidget::item {
            padding: 5px;
            border-bottom: 1px solid #6272a4;
        }
        QHeaderView::section {
            background-color: #6272a4;
            color: white;
            padding: 5px;
            border: none;
        }
    """)
    main_window.os_events_table.horizontalHeader().setStretchLastSection(True)
    main_window.os_events_table.setAlternatingRowColors(True)
    main_window.os_events_table.setEditTriggers(QTableWidget.NoEditTriggers)
    main_window.os_events_table.setColumnCount(5)
    main_window.os_events_table.setHorizontalHeaderLabels([
        "Дата и время", "Уровень", "Код события", "Источник", "Тип журнала"
    ])
    
    results_layout.addWidget(main_window.os_events_table)
    
    # Текстовое представление
    main_window.basic_result_text = QTextEdit()
    main_window.basic_result_text.setReadOnly(True)
    main_window.basic_result_text.setStyleSheet("""
        QTextEdit {
            background-color: #44475a;
            color: #f8f8f2;
            border: 1px solid #6272a4;
            border-radius: 5px;
            padding: 10px;
        }
    """)
    main_window.basic_result_text.setPlaceholderText("Результаты анализа журналов ОС появятся здесь...")
    
    results_layout.addWidget(main_window.basic_result_text)
    
    # Скрываем элементы по умолчанию
    main_window.os_events_table.setVisible(True)
    main_window.basic_result_text.setVisible(False)
    main_window.os_log_switch_combo.setVisible(False)
    
    layout.addWidget(results_widget)
    
    return tab

def create_settings_page(main_window):
    """Создание страницы настроек"""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 20, 20, 20)
    
    title = QLabel("⚙️ Настройки")
    title.setStyleSheet("color: #f8f8f2; font-size: 24px; font-weight: bold; margin-bottom: 20px;")
    layout.addWidget(title)
    
    # Группа управления обновлениями
    update_group = QGroupBox("🔄 Управление обновлениями")
    update_group.setStyleSheet("""
        QGroupBox {
            color: #f8f8f2;
            font-size: 16px;
            font-weight: bold;
            border: 2px solid #6272a4;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
    """)
    
    update_layout = QFormLayout(update_group)
    
    # Текущая версия
    current_version_label = QLabel(f"Текущая версия: {APP_VERSION}")
    current_version_label.setStyleSheet("color: #f8f8f2; font-size: 14px; margin-bottom: 10px;")
    update_layout.addRow("Версия:", current_version_label)
    
    # Настройка автоматического обновления
    main_window.auto_update_check = QCheckBox("Обновлять автоматически")
    main_window.auto_update_check.setStyleSheet("QCheckBox { color: #f8f8f2; font-size: 14px; }")
    main_window.auto_update_check.stateChanged.connect(main_window._on_auto_update_changed)
    update_layout.addRow("Автообновление:", main_window.auto_update_check)
    
    # Кнопка проверки обновлений
    check_update_btn = QPushButton("🔍 Проверить обновления вручную")
    check_update_btn.setStyleSheet(main_window._get_button_style())
    check_update_btn.clicked.connect(main_window._show_update_dialog)
    update_layout.addRow("Ручная проверка:", check_update_btn)
    
    # Информация о последней проверке
    main_window.last_update_check_label = QLabel("Дата последней проверки: не проверялось")
    main_window.last_update_check_label.setStyleSheet("color: #f8f8f2; font-size: 12px;")
    update_layout.addRow("Последняя проверка:", main_window.last_update_check_label)
    
    layout.addWidget(update_group)
    
    # Группа системной информации
    system_group = QGroupBox("💻 Системная информация")
    system_group.setStyleSheet(update_group.styleSheet())
    
    system_layout = QFormLayout(system_group)
    
    import platform
    system_info = f"""
    ОС: {platform.system()} {platform.release()}
    Процессор: {platform.processor() or 'Не определен'}
    Архитектура: {platform.architecture()[0]}
    Пользователь: {platform.node()}
    """
    
    system_info_label = QLabel(system_info.strip())
    system_info_label.setStyleSheet("color: #f8f8f2; font-family: monospace; font-size: 12px;")
    system_info_label.setWordWrap(True)
    
    system_layout.addRow("Система:", system_info_label)
    
    license_info = _get_license_info_text(main_window)
    license_info_label = QLabel(license_info)
    license_info_label.setStyleSheet("color: #f8f8f2; font-family: monospace; font-size: 12px;")
    license_info_label.setWordWrap(True)
    
    system_layout.addRow("Лицензия:", license_info_label)
    
    layout.addWidget(system_group)
    
    layout.addStretch()
    
    return page

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ БАЗОВЫХ МЕХАНИЗМОВ =====

def _select_basic_archive_factory(main_window):
    """Фабрика для создания обработчика выбора архива базовых механизмов"""
    def handler(event=None):
        file_path, _ = QFileDialog.getOpenFileName(
            main_window,
            "Выберите архив логов",
            "",
            "Zip Archives (*.zip);;All Files (*)"
        )
    
        if file_path:
            main_window.current_basic_archive = file_path
            main_window.selected_basic_archive_label.setText(f"Выбран: {os.path.basename(file_path)}")
            main_window.analyze_basic_btn.setEnabled(True)
    return handler

def _drag_enter_event_basic_factory(main_window):
    """Фабрика для создания обработчика перетаскивания базовых механизмов"""
    def handler(event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            main_window.basic_drop_area.setStyleSheet("""
                QLabel {
                    color: #f8f8f2;
                    background-color: #6272a4;
                    padding: 40px;
                    border-radius: 10px;
                    border: 2px dashed #50fa7b;
                    margin: 10px 0px;
                }
            """)
    return handler

def _drop_event_basic_factory(main_window):
    """Фабрика для создания обработчика отпускания файла базовых механизмов"""
    def handler(event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.zip'):
                main_window.current_basic_archive = file_path
                main_window.selected_basic_archive_label.setText(f"Выбран: {os.path.basename(file_path)}")
                main_window.analyze_basic_btn.setEnabled(True)
            
            main_window.basic_drop_area.setStyleSheet("""
                QLabel {
                    color: #f8f8f2;
                    background-color: #44475a;
                    padding: 40px;
                    border-radius: 10px;
                    border: 2px dashed #6272a4;
                    margin: 10px 0px;
                }
            """)
            event.acceptProposedAction()
    return handler

def _on_use_custom_patterns_changed_factory(main_window):
    """Фабрика для обработчика изменения настроек шаблонов"""
    def handler(state):
        enabled = state == 2  # Qt.Checked
        main_window.custom_patterns_input.setEnabled(enabled)
    return handler

def _on_os_log_switch_changed_factory(main_window):
    """Фабрика для обработчика переключения журналов ОС"""
    def handler(index):
        if hasattr(main_window, 'current_basic_analysis_result'):
            main_window._display_os_events_by_log_type(index)
    return handler

# ===== СУЩЕСТВУЮЩИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def _get_license_info_text(main_window):
    """Получение текста информации о лицензии"""
    if main_window.license_client and main_window.license_client.is_license_active():
        info = main_window.license_client.get_license_info()
        if info and isinstance(info, dict):
            return f"""
            Статус: ✅ Активна
            Пользователь: {info.get('client_name', 'Не указан')}
            Активаций: {info.get('current_activations', 0)}/{info.get('max_activations', 1)}
            Срок: {info.get('expires_at', 'Бессрочная')[:10] if isinstance(info.get('expires_at'), str) else 'Бессрочная'}
            """
    return "Статус: ❌ Не активирована\nДля активации перейдите в раздел 'Главная'"

def _select_log_archive_factory(main_window):
    """Фабрика для создания обработчика выбора архива"""
    def handler(event=None):
        file_path, _ = QFileDialog.getOpenFileName(
            main_window,
            "Выберите архив логов",
            "",
            "Zip Archives (*.zip);;All Files (*)"
        )
    
        if file_path:
            main_window.current_log_archive = file_path
            main_window.selected_archive_label.setText(f"Выбран: {os.path.basename(file_path)}")
            main_window.analyze_logs_btn.setEnabled(True)
    return handler

def _drag_enter_event_factory(main_window):
    """Фабрика для создания обработчика перетаскивания"""
    def handler(event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            main_window.drop_area.setStyleSheet("""
                QLabel {
                    color: #f8f8f2;
                    background-color: #6272a4;
                    padding: 40px;
                    border-radius: 10px;
                    border: 2px dashed #50fa7b;
                    margin: 10px 0px;
                }
            """)
    return handler

def _drop_event_factory(main_window):
    """Фабрика для создания обработчика отпускания файла"""
    def handler(event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.zip'):
                main_window.current_log_archive = file_path
                main_window.selected_archive_label.setText(f"Выбран: {os.path.basename(file_path)}")
                main_window.analyze_logs_btn.setEnabled(True)
            
            main_window.drop_area.setStyleSheet("""
                QLabel {
                    color: #f8f8f2;
                    background-color: #44475a;
                    padding: 40px;
                    border-radius: 10px;
                    border: 2px dashed #6272a4;
                    margin: 10px 0px;
                }
            """)
            event.acceptProposedAction()
    return handler

def _on_analysis_method_changed_factory(main_window):
    """Фабрика для создания обработчика изменения метода анализа"""
    def handler(index):
        if index == 0:  # Общий анализ
            main_window.include_warnings_check.setEnabled(True)
        else:  # Считать операции или Платежный терминал
            main_window.include_warnings_check.setEnabled(False)
            main_window.include_warnings_check.setChecked(False)
    return handler

def _select_marking_archive_factory(main_window):
    """Фабрика для создания обработчика выбора архива маркировки"""
    def handler(event=None):
        file_path, _ = QFileDialog.getOpenFileName(
            main_window,
            "Выберите архив логов маркировки",
            "",
            "Zip Archives (*.zip);;All Files (*)"
        )
    
        if file_path:
            main_window.current_marking_archive = file_path
            main_window.selected_marking_archive_label.setText(f"Выбран: {os.path.basename(file_path)}")
            main_window.analyze_marking_btn.setEnabled(True)
            main_window.show_original_logs_btn.setEnabled(True)
    return handler

def _drag_enter_event_marking_factory(main_window):
    """Фабрика для создания обработчика перетаскивания маркировки"""
    def handler(event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            main_window.marking_drop_area.setStyleSheet("""
                QLabel {
                    color: #f8f8f2;
                    background-color: #6272a4;
                    padding: 40px;
                    border-radius: 10px;
                    border: 2px dashed #50fa7b;
                    margin: 10px 0px;
                }
            """)
    return handler

def _drop_event_marking_factory(main_window):
    """Фабрика для создания обработчика отпускания файла маркировки"""
    def handler(event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.zip'):
                main_window.current_marking_archive = file_path
                main_window.selected_marking_archive_label.setText(f"Выбран: {os.path.basename(file_path)}")
                main_window.analyze_marking_btn.setEnabled(True)
                main_window.show_original_logs_btn.setEnabled(True)
            
            main_window.marking_drop_area.setStyleSheet("""
                QLabel {
                    color: #f8f8f2;
                    background-color: #44475a;
                    padding: 40px;
                    border-radius: 10px;
                    border: 2px dashed #6272a4;
                    margin: 10px 0px;
                }
            """)
            event.acceptProposedAction()
    return handler

def _on_marking_method_changed_factory(main_window):
    """Фабрика для создания обработчика изменения метода анализа маркировки"""
    def handler(index):
        if index == 0:
            main_window.principle_group.setVisible(True)
        else:
            main_window.principle_group.setVisible(False)
    return handler