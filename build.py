# build.py
import PyInstaller.__main__
import os
import shutil
import sys
from pathlib import Path

def build_app():
    print("🛠️ Сборка приложения Saby Helper...")
    
    # Создаем config.txt если его нет
    if not os.path.exists("config.txt"):
        print("Создаю config.txt с адресом по умолчанию...")
        with open("config.txt", "w", encoding='utf-8') as f:
            f.write("155.212.171.112")
    
    # Очистка предыдущих сборок
    for folder in ['build', 'dist', '__pycache__']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    
    # Определяем разделитель для текущей ОС
    if os.name == 'nt':  # Windows
        separator = ';'
    else:  # Linux/Mac
        separator = ':'
    
    # Базовые параметры сборки
    params = [
        'main.py',  # Используем main.py как точку входа
        '--name=SabyHelper',
        '--onefile',
        '--windowed', 
        '--clean',
        '--noconfirm',
        '--icon=icon.ico',
        # Основные файлы
        f'--add-data=app.py{separator}.',
        f'--add-data=config.py{separator}.',
        f'--add-data=analyzer.py{separator}.',
        f'--add-data=log_analyzer.py{separator}.',
        f'--add-data=report_generator.py{separator}.', 
        f'--add-data=pdf_generator.py{separator}.',
        f'--add-data=license_client.py{separator}.',
        f'--add-data=license_window.py{separator}.',
        f'--add-data=update_manager.py{separator}.',
        f'--add-data=marking_analyzer.py{separator}.',
        f'--add-data=basic_mechanisms_analyzer.py{separator}.',
        f'--add-data=payment_terminal_analyzer.py{separator}.',
        # Конфигурационный файл
        f'--add-data=config.txt{separator}.',
        # Модули
        f'--add-data=modules{separator}modules',
        f'--add-data=utils{separator}utils',
        f'--add-data=ui_components{separator}ui_components',
        # Ключевые скрытые импорты
        '--hidden-import=pandas',
        '--hidden-import=reportlab',
        '--hidden-import=PIL._imaging',
        '--hidden-import=PIL.Image',
        '--hidden-import=reportlab.lib.rl_accel',
        '--hidden-import=reportlab.pdfbase._fontdata',
        '--hidden-import=reportlab.pdfbase.ttfonts',
        '--hidden-import=requests',
        '--hidden-import=urllib3',
        '--hidden-import=charset_normalizer',
        '--hidden-import=idna',
        '--hidden-import=certifi',
        '--hidden-import=xml.etree.ElementTree',
        '--hidden-import=xml.etree.ElementPath',
        '--noupx',
        '--log-level=WARN',
    ]
    
    try:
        PyInstaller.__main__.run(params)
        print("✅ Сборка завершена успешно!")
        print("📁 Исполняемый файл создан в папке 'dist'")
        print("🚀 Файл: dist/SabyHelper.exe")
        
        # Копируем config.txt рядом с EXE файлом
        exe_dir = Path("dist")
        if os.path.exists("config.txt"):
            shutil.copy2("config.txt", exe_dir / "config.txt")
            print("📋 config.txt скопирован в папку с EXE")
        
        print("✅ Сборка завершена! Файл готов к использованию.")
        
    except Exception as e:
        print(f"❌ Ошибка сборки: {e}")
        import traceback
        traceback.print_exc()
        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    build_app()