# license_server.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
import secrets
import string
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class LicenseDatabase:
    def __init__(self, db_path: str = "licenses.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS licenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT UNIQUE NOT NULL,
                    client_name TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    activated_at DATETIME,
                    expires_at DATETIME,
                    is_active BOOLEAN DEFAULT 1,
                    max_activations INTEGER DEFAULT 1,
                    current_activations INTEGER DEFAULT 0,
                    ip_address TEXT,
                    saby_profile_url TEXT,
                    notes TEXT,
                    is_permanent BOOLEAN DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT NOT NULL,
                    client_name TEXT NOT NULL,
                    machine_name TEXT,
                    hardware_id TEXT,
                    ip_address TEXT,
                    saby_profile_url TEXT,
                    activated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (license_key) REFERENCES licenses (license_key)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT,
                    hardware_id TEXT,
                    ip_address TEXT,
                    machine_name TEXT,
                    log_level TEXT,
                    message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def generate_license_key(self):
        alphabet = string.ascii_uppercase + string.digits
        return '-'.join(
            ''.join(secrets.choice(alphabet) for _ in range(5))
            for _ in range(4)
        )
    
    def create_license(self, days_valid=365, max_activations=1, notes="", is_permanent=False):
        license_key = self.generate_license_key()
        
        if is_permanent:
            expires_at = None
        else:
            expires_at = datetime.now() + timedelta(days=days_valid)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO licenses 
                    (license_key, expires_at, max_activations, notes, is_permanent)
                    VALUES (?, ?, ?, ?, ?)
                ''', (license_key, expires_at, max_activations, notes, is_permanent))
                conn.commit()
            return license_key
        except sqlite3.IntegrityError:
            return self.create_license(days_valid, max_activations, notes, is_permanent)
    
    def get_all_licenses(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM licenses ORDER BY created_at DESC')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения лицензий: {e}")
            return []
    
    def get_license_info(self, license_key):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM licenses WHERE license_key = ?', (license_key,))
                result = cursor.fetchone()
                return dict(result) if result else {}
        except Exception as e:
            logger.error(f"Ошибка получения информации о лицензии: {e}")
            return {}
    
    def activate_license(self, license_key, hardware_id, client_name, ip_address="", machine_name="", saby_profile_url=""):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT is_active, expires_at, max_activations, current_activations, is_permanent
                    FROM licenses WHERE license_key = ?
                ''', (license_key,))
                
                result = cursor.fetchone()
                if not result:
                    return {"success": False, "error": "Лицензия не найдена"}
                
                is_active, expires_at, max_activations, current_activations, is_permanent = result
                
                if not is_active:
                    return {"success": False, "error": "Лицензия не активна"}
                
                if not is_permanent and expires_at and datetime.now() > datetime.fromisoformat(expires_at):
                    return {"success": False, "error": "Срок действия лицензии истек"}
                
                if current_activations >= max_activations:
                    return {"success": False, "error": "Достигнут лимит активаций"}
                
                cursor.execute('''
                    SELECT id FROM users 
                    WHERE license_key = ? AND hardware_id = ?
                ''', (license_key, hardware_id))
                
                if cursor.fetchone():
                    return {"success": False, "error": "Лицензия уже активирована на этом устройстве"}
                
                cursor.execute('''
                    UPDATE licenses 
                    SET current_activations = current_activations + 1,
                        activated_at = CURRENT_TIMESTAMP,
                        client_name = ?,
                        ip_address = ?,
                        saby_profile_url = ?
                    WHERE license_key = ?
                ''', (client_name, ip_address, saby_profile_url, license_key))
                
                cursor.execute('''
                    INSERT INTO users 
                    (license_key, client_name, machine_name, hardware_id, ip_address, saby_profile_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (license_key, client_name, machine_name, hardware_id, ip_address, saby_profile_url))
                
                conn.commit()
                
                self.add_log(license_key, hardware_id, ip_address, machine_name, "INFO", f"Лицензия активирована для пользователя: {client_name}")
                
                return {"success": True, "message": "Лицензия успешно активирована"}
                
        except Exception as e:
            logger.error(f"Ошибка активации лицензии: {e}")
            return {"success": False, "error": f"Ошибка активации: {str(e)}"}
    
    def get_all_users(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.*, l.notes, l.expires_at, l.is_permanent 
                    FROM users u 
                    LEFT JOIN licenses l ON u.license_key = l.license_key 
                    ORDER BY u.activated_at DESC
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения пользователей: {e}")
            return []
    
    def add_log(self, license_key, hardware_id, ip_address, machine_name, log_level, message):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO logs 
                    (license_key, hardware_id, ip_address, machine_name, log_level, message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (license_key, hardware_id, ip_address, machine_name, log_level, message))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка добавления лога: {e}")
    
    def get_logs(self, license_key=None, limit=1000):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if license_key:
                    cursor.execute('''
                        SELECT * FROM logs 
                        WHERE license_key = ?
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (license_key, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM logs 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения логов: {e}")
            return []
    
    def clear_logs(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM logs')
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка очистки логов: {e}")
            return False
    
    def block_license(self, license_key):
        """Блокировка лицензии"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE licenses 
                    SET is_active = 0 
                    WHERE license_key = ?
                ''', (license_key,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    self.add_log(license_key, "", "", "", "WARNING", "Лицензия заблокирована администратором")
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка блокировки лицензии: {e}")
            return False
    
    def unblock_license(self, license_key):
        """Разблокировка лицензии"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE licenses 
                    SET is_active = 1 
                    WHERE license_key = ?
                ''', (license_key,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    self.add_log(license_key, "", "", "", "INFO", "Лицензия разблокирована администратором")
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка разблокировки лицензии: {e}")
            return False

db = LicenseDatabase()

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "license_server"})

@app.route('/api/activate', methods=['POST'])
def activate_license():
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        hardware_id = data.get('hardware_id')
        client_name = data.get('client_name', '')
        ip_address = request.remote_addr
        machine_name = data.get('machine_name', '')
        saby_profile_url = data.get('saby_profile_url', '')
        
        if not license_key or not hardware_id:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        if not client_name:
            return jsonify({"success": False, "error": "Имя пользователя обязательно"}), 400
        
        result = db.activate_license(license_key, hardware_id, client_name, ip_address, machine_name, saby_profile_url)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Ошибка активации: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/api/validate', methods=['POST'])
def validate_license():
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        hardware_id = data.get('hardware_id')
        
        if not license_key or not hardware_id:
            return jsonify({"valid": False, "error": "Missing required fields"}), 400
        
        info = db.get_license_info(license_key)
        if not info:
            return jsonify({"valid": False, "error": "License not found"})
        
        if not info.get('is_active'):
            return jsonify({"valid": False, "error": "License not active"})
        
        if not info.get('is_permanent') and info.get('expires_at'):
            expires_at = datetime.fromisoformat(info['expires_at'])
            if datetime.now() > expires_at:
                return jsonify({"valid": False, "error": "License expired"})
        
        return jsonify({"valid": True, "message": "License is valid"})
        
    except Exception as e:
        logger.error(f"Ошибка проверки лицензии: {e}")
        return jsonify({"valid": False, "error": "Internal server error"}), 500

@app.route('/api/info', methods=['POST'])
def get_license_info():
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        
        if not license_key:
            return jsonify({"error": "License key required"}), 400
        
        info = db.get_license_info(license_key)
        if not info:
            return jsonify({"error": "License not found"}), 404
        
        return jsonify(info)
        
    except Exception as e:
        logger.error(f"Ошибка получения информации: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/log', methods=['POST'])
def api_add_log():
    try:
        data = request.get_json()
        
        license_key = data.get('license_key')
        hardware_id = data.get('hardware_id')
        ip_address = request.remote_addr
        machine_name = data.get('machine_name')
        log_level = data.get('log_level', 'info')
        message = data.get('message')
        
        db.add_log(license_key, hardware_id, ip_address, machine_name, log_level, message)
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Ошибка добавления лога: {e}")
        return jsonify({"success": False}), 500

@app.route('/admin/block-license', methods=['POST'])
def admin_block_license():
    """Блокировка лицензии"""
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        
        if not license_key:
            return jsonify({"success": False, "error": "License key required"}), 400
        
        if db.block_license(license_key):
            return jsonify({"success": True, "message": "Лицензия заблокирована"})
        else:
            return jsonify({"success": False, "error": "Лицензия не найдена"})
            
    except Exception as e:
        logger.error(f"Ошибка блокировки лицензии: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/admin/unblock-license', methods=['POST'])
def admin_unblock_license():
    """Разблокировка лицензии"""
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        
        if not license_key:
            return jsonify({"success": False, "error": "License key required"}), 400
        
        if db.unblock_license(license_key):
            return jsonify({"success": True, "message": "Лицензия разблокирована"})
        else:
            return jsonify({"success": False, "error": "Лицензия не найдена"})
            
    except Exception as e:
        logger.error(f"Ошибка разблокировки лицензии: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

if __name__ == '__main__':
    print("🚀 Сервер лицензий запускается на порту 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)