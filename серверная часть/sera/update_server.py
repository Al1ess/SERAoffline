# update_server.py
from flask import Flask, jsonify, send_file, request
import os
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Файл для хранения информации об обновлениях
UPDATE_INFO_FILE = "update_info.json"
UPDATE_FILE = "SabyHelper_Update.exe"

def load_update_info():
    """Загрузка информации об обновлениях"""
    default_info = {
        "latest_version": "1.3.0",
        "update_available": False,
        "download_url": "http://155.212.171.112:5002/api/download-update",
        "release_notes": "• Исправлены ошибки активации\n• Добавлена система логов\n• Улучшен интерфейс",
        "update_history": []
    }
    
    try:
        if os.path.exists(UPDATE_INFO_FILE):
            with open(UPDATE_INFO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки информации об обновлениях: {e}")
    
    return default_info

def save_update_info(info):
    """Сохранение информации об обновлениях"""
    try:
        with open(UPDATE_INFO_FILE, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения информации об обновлениях: {e}")
        return False

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "update_server"})

@app.route('/api/check-update')
def check_update():
    """Проверка наличия обновлений"""
    update_info = load_update_info()
    return jsonify(update_info)

@app.route('/api/download-update')
def download_update():
    """Скачивание обновления"""
    if os.path.exists(UPDATE_FILE):
        return send_file(UPDATE_FILE, as_attachment=True)
    else:
        return jsonify({"error": "Update file not found"}), 404

@app.route('/admin/update-info', methods=['GET', 'POST'])
def admin_update_info():
    """Админ-панель для управления обновлениями"""
    if request.method == 'GET':
        return jsonify(load_update_info())
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            update_info = load_update_info()
            
            # Обновляем информацию
            if 'latest_version' in data:
                update_info['latest_version'] = data['latest_version']
            if 'update_available' in data:
                update_info['update_available'] = data['update_available']
            if 'release_notes' in data:
                update_info['release_notes'] = data['release_notes']
            
            # Добавляем в историю
            update_record = {
                "version": update_info['latest_version'],
                "timestamp": datetime.now().isoformat(),
                "notes": update_info['release_notes'],
                "available": update_info['update_available']
            }
            update_info['update_history'].insert(0, update_record)
            
            # Сохраняем
            if save_update_info(update_info):
                return jsonify({"success": True, "message": "Информация об обновлении сохранена"})
            else:
                return jsonify({"success": False, "error": "Ошибка сохранения"})
                
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

@app.route('/admin/upload-update', methods=['POST'])
def admin_upload_update():
    """Загрузка нового файла обновления - УПРОЩЕННАЯ ВЕРСИЯ"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "Файл не выбран"})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "Файл не выбран"})
        
        # Сохраняем файл с фиксированным именем
        file.save(UPDATE_FILE)
        
        return jsonify({
            "success": True,
            "message": "Файл обновления успешно загружен",
            "filename": UPDATE_FILE
        })
        
    except Exception as e:
        logger.error(f"Ошибка загрузки обновления: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/admin/toggle-update', methods=['POST'])
def admin_toggle_update():
    """Включение/выключение обновления"""
    try:
        data = request.get_json()
        update_available = data.get('update_available', False)
        
        update_info = load_update_info()
        update_info['update_available'] = update_available
        
        if save_update_info(update_info):
            status = "включено" if update_available else "выключено"
            return jsonify({
                "success": True, 
                "message": f"Обновление {status}",
                "update_available": update_available
            })
        else:
            return jsonify({"success": False, "error": "Ошибка сохранения"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Сервер обновлений запускается на порту 5002...")
    print("🔗 Адрес: http://155.212.171.112:5002")
    app.run(host='0.0.0.0', port=5002, debug=False)