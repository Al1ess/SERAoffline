@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Компиляция Saby Helper v1.5.3
echo ========================================

echo.
echo 1. Создание config.txt если его нет...
if not exist "config.txt" (
    echo 155.212.171.112 > config.txt
    echo config.txt создан с адресом по умолчанию
)

echo.
echo 2. Очистка старых файлов...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "__pycache__" rmdir /s /q __pycache__
if exist "SabyHelper.spec" del SabyHelper.spec

echo.
echo 3. Установка зависимостей...
pip install PyQt5 requests pandas openpyxl reportlab pillow --upgrade

echo.
echo 4. Компиляция приложения...
pyinstaller ^
    --name=SabyHelper ^
    --onefile ^
    --windowed ^
    --clean ^
    --noconfirm ^
    --icon=icon.ico ^
    --add-data=config.txt;. ^
    --hidden-import=pandas ^
    --hidden-import=reportlab ^
    --hidden-import=PIL._imaging ^
    --hidden-import=PIL.Image ^
    --hidden-import=reportlab.lib.rl_accel ^
    --hidden-import=reportlab.pdfbase._fontdata ^
    --hidden-import=reportlab.pdfbase.ttfonts ^
    --hidden-import=requests ^
    --hidden-import=urllib3 ^
    --hidden-import=charset_normalizer ^
    --hidden-import=idna ^
    --hidden-import=certifi ^
    --hidden-import=xml.etree.ElementTree ^
    --hidden-import=xml.etree.ElementPath ^
    --noupx ^
    --log-level=WARN ^
    main.py

echo.
if exist "dist\SabyHelper.exe" (
    echo ========================================
    echo ✅ Компиляция успешно завершена!
    echo ========================================
    echo.
    echo 📂 Созданный файл: dist\SabyHelper.exe
    echo 📋 Обязательно: config.txt уже скопирован в папку dist
    echo.
    echo 💡 Для запуска: откройте dist\SabyHelper.exe
    echo.
    
    REM Копируем config.txt рядом с EXE
    copy config.txt dist\ >nul
    echo ✅ config.txt скопирован в папку dist
) else (
    echo ========================================
    echo ❌ Ошибка компиляции!
    echo ========================================
)

echo.
pause