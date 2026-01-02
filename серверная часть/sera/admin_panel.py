# admin_panel.py
from flask import Flask, jsonify, request, render_template_string
import sqlite3
from datetime import datetime, timedelta
import secrets
import string
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()

class AdminDatabase:
    def __init__(self, db_path: str = "licenses.db"):
        self.db_path = db_path
    
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
                    # Добавляем лог о блокировке
                    cursor.execute('''
                        INSERT INTO logs 
                        (license_key, log_level, message)
                        VALUES (?, ?, ?)
                    ''', (license_key, "WARNING", "Лицензия заблокирована администратором"))
                    conn.commit()
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
                    # Добавляем лог о разблокировке
                    cursor.execute('''
                        INSERT INTO logs 
                        (license_key, log_level, message)
                        VALUES (?, ?, ?)
                    ''', (license_key, "INFO", "Лицензия разблокирована администратором"))
                    conn.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка разблокировки лицензии: {e}")
            return False

db = AdminDatabase()

def check_auth(username, password):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return username == ADMIN_USERNAME and password_hash == ADMIN_PASSWORD_HASH

ADMIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Панель управления Saby Helper</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --secondary: #64748b;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --dark: #1e293b;
            --light: #f8fafc;
            --gray: #94a3b8;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
            width: 100%;
            max-width: 1400px;
            min-height: 800px;
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .main-content {
            display: flex;
            min-height: 600px;
        }
        
        .sidebar {
            background: var(--dark);
            color: white;
            width: 280px;
            padding: 0;
        }
        
        .nav-item {
            padding: 20px 30px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 15px;
            font-size: 1.1rem;
        }
        
        .nav-item:hover {
            background: rgba(255,255,255,0.1);
        }
        
        .nav-item.active {
            background: var(--primary);
            border-right: 4px solid var(--warning);
        }
        
        .content {
            flex: 1;
            padding: 30px;
            background: var(--light);
            overflow-y: auto;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
            animation: fadeIn 0.5s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            border: 1px solid rgba(0,0,0,0.05);
        }
        
        .card h2 {
            color: var(--dark);
            margin-bottom: 20px;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: var(--dark);
        }
        
        .form-control {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        .form-control:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-primary {
            background: var(--primary);
            color: white;
        }
        
        .btn-primary:hover {
            background: var(--primary-dark);
            transform: translateY(-2px);
        }
        
        .btn-success {
            background: var(--success);
            color: white;
        }
        
        .btn-danger {
            background: var(--danger);
            color: white;
        }
        
        .btn-warning {
            background: var(--warning);
            color: white;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }
        
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        
        th {
            background: var(--primary);
            color: white;
            font-weight: 600;
        }
        
        tr:hover {
            background: #f8fafc;
        }
        
        .license-key {
            font-family: 'Courier New', monospace;
            background: #f1f5f9;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: 600;
            color: var(--primary);
        }
        
        .status-active {
            background: var(--success);
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .status-inactive {
            background: var(--danger);
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .status-blocked {
            background: var(--warning);
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .action-buttons {
            display: flex;
            gap: 5px;
        }
        
        .action-btn {
            padding: 6px 12px;
            border: none;
            border-radius: 5px;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .btn-block {
            background: var(--warning);
            color: white;
        }
        
        .btn-unblock {
            background: var(--success);
            color: white;
        }
        
        .btn-delete {
            background: var(--danger);
            color: white;
        }
        
        .alert {
            padding: 15px 20px;
            border-radius: 10px;
            margin: 20px 0;
            font-weight: 500;
        }
        
        .alert-success {
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #a7f3d0;
        }
        
        .alert-error {
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            border-left: 5px solid var(--primary);
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 10px;
        }
        
        .stat-label {
            color: var(--secondary);
            font-size: 1rem;
            font-weight: 600;
        }
        
        .login-container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        
        .login-title {
            color: var(--primary);
            margin-bottom: 30px;
            font-size: 1.8rem;
            font-weight: 700;
        }
        
        .logout-btn {
            margin-top: auto;
            background: var(--danger);
            color: white;
            border: none;
            padding: 15px;
            width: 100%;
            font-size: 1rem;
            cursor: pointer;
            transition: background 0.3s ease;
        }
        
        .logout-btn:hover {
            background: #dc2626;
        }
    </style>
</head>
<body>
    <div id="loginContainer" class="login-container">
        <div class="login-title">🔐 Панель управления</div>
        <form id="loginForm">
            <div class="form-group">
                <input type="text" id="username" class="form-control" placeholder="Логин" required>
            </div>
            <div class="form-group">
                <input type="password" id="password" class="form-control" placeholder="Пароль" required>
            </div>
            <button type="submit" class="btn btn-primary" style="width: 100%;">Войти в систему</button>
        </form>
        <div id="loginError" class="alert alert-error" style="display: none; margin-top: 20px;">
            Неверный логин или пароль
        </div>
    </div>

    <div id="adminPanel" class="container" style="display: none;">
        <div class="header">
            <h1>🎯 Saby Helper Admin</h1>
            <p>Панель управления лицензиями и пользователями</p>
        </div>
        
        <div class="main-content">
            <div class="sidebar">
                <div class="nav-item active" data-tab="dashboard">
                    📊 Дашборд
                </div>
                <div class="nav-item" data-tab="licenses">
                    🔑 Лицензии
                </div>
                <div class="nav-item" data-tab="users">
                    👥 Пользователи
                </div>
                <div class="nav-item" data-tab="logs">
                    📝 Логи системы
                </div>
                <div class="nav-item" data-tab="updates">
                    🔄 Управление обновлениями
                </div>
                <button class="logout-btn" onclick="logout()">🚪 Выйти из системы</button>
            </div>
            
            <div class="content">
                <!-- Дашборд -->
                <div id="dashboard" class="tab-content active">
                    <div class="card">
                        <h2>📈 Общая статистика</h2>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-number" id="totalLicenses">0</div>
                                <div class="stat-label">Всего лицензий</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number" id="activeLicenses">0</div>
                                <div class="stat-label">Активных лицензий</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number" id="blockedLicenses">0</div>
                                <div class="stat-label">Заблокированных</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number" id="totalUsers">0</div>
                                <div class="stat-label">Всего пользователей</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>⚡ Быстрые действия</h2>
                        <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                            <button class="btn btn-primary" onclick="showTab('licenses')">
                                ➕ Создать лицензию
                            </button>
                            <button class="btn btn-success" onclick="loadLicenses()">
                                🔄 Обновить данные
                            </button>
                            <button class="btn btn-warning" onclick="showTab('logs')">
                                📊 Просмотреть логи
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Лицензии -->
                <div id="licenses" class="tab-content">
                    <div class="card">
                        <h2>🎯 Генерация новой лицензии</h2>
                        <form id="generateForm">
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                                <div class="form-group">
                                    <label>Срок действия (дней):</label>
                                    <input type="number" name="days_valid" class="form-control" value="365" min="1">
                                </div>
                                <div class="form-group">
                                    <label>Максимум активаций:</label>
                                    <input type="number" name="max_activations" class="form-control" value="1" min="1" required>
                                </div>
                            </div>
                            <div class="form-group">
                                <label>Комментарий:</label>
                                <textarea name="notes" class="form-control" placeholder="Описание лицензии..." rows="3"></textarea>
                            </div>
                            <div class="form-group">
                                <label style="display: flex; align-items: center; gap: 10px;">
                                    <input type="checkbox" name="is_permanent" value="1">
                                    Бессрочная лицензия
                                </label>
                            </div>
                            <button type="submit" class="btn btn-primary">🎯 Сгенерировать лицензию</button>
                        </form>
                        <div id="generateResult" style="margin-top: 20px;"></div>
                    </div>

                    <div class="card">
                        <h2>📊 Список лицензий</h2>
                        <button class="btn btn-success" onclick="loadLicenses()">
                            🔄 Обновить список
                        </button>
                        <div id="licensesList" style="margin-top: 20px;"></div>
                    </div>
                </div>

                <!-- Пользователи -->
                <div id="users" class="tab-content">
                    <div class="card">
                        <h2>👥 Реестр пользователей</h2>
                        <button class="btn btn-success" onclick="loadUsers()">
                            🔄 Обновить список
                        </button>
                        <div id="usersList" style="margin-top: 20px;"></div>
                    </div>
                </div>

                <!-- Логи -->
                <div id="logs" class="tab-content">
                    <div class="card">
                        <h2>📝 Журнал системных логов</h2>
                        <div style="display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap;">
                            <input type="text" id="logSearchKey" class="form-control" placeholder="Фильтр по ключу лицензии..." style="width: 300px;">
                            <button class="btn btn-primary" onclick="loadLogs()">
                                🔍 Загрузить логи
                            </button>
                            <button class="btn btn-danger" onclick="clearLogs()">
                                🗑️ Очистить все логи
                            </button>
                        </div>
                        <div id="logsList"></div>
                    </div>
                </div>

                <!-- Управление обновлениями -->
                <div id="updates" class="tab-content">
                    <div class="card">
                        <h2>🔄 Управление обновлениями приложения</h2>
                        <div class="form-group">
                            <label>Новая версия:</label>
                            <input type="text" id="newVersion" class="form-control" placeholder="например: 1.2.0">
                        </div>
                        <div class="form-group">
                            <label>Описание обновления:</label>
                            <textarea id="updateDescription" class="form-control" placeholder="Опишите изменения в новой версии..." rows="4"></textarea>
                        </div>
                        <div class="form-group">
                            <label>Файл обновления (.exe):</label>
                            <input type="file" id="updateFile" class="form-control" accept=".exe">
                        </div>
                        <button class="btn btn-primary" onclick="uploadUpdate()">
                            📤 Загрузить обновление
                        </button>
                        <div id="updateResult" style="margin-top: 20px;"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentTab = 'dashboard';

        // Проверка авторизации
        if (!localStorage.getItem('adminAuthenticated')) {
            document.getElementById('loginContainer').style.display = 'block';
        } else {
            showAdminPanel();
        }

        // Навигация
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', function() {
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
                showTab(this.dataset.tab);
            });
        });

        function showTab(tabName) {
            currentTab = tabName;
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabName).classList.add('active');
            
            if (tabName === 'dashboard') loadDashboard();
            if (tabName === 'licenses') loadLicenses();
            if (tabName === 'users') loadUsers();
            if (tabName === 'logs') loadLogs();
        }

        function showAdminPanel() {
            document.getElementById('loginContainer').style.display = 'none';
            document.getElementById('adminPanel').style.display = 'block';
            loadDashboard();
        }

        // Авторизация
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/admin/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                if (response.ok) {
                    localStorage.setItem('adminAuthenticated', 'true');
                    showAdminPanel();
                } else {
                    document.getElementById('loginError').style.display = 'block';
                }
            } catch (error) {
                document.getElementById('loginError').style.display = 'block';
            }
        });

        function logout() {
            localStorage.removeItem('adminAuthenticated');
            document.getElementById('adminPanel').style.display = 'none';
            document.getElementById('loginContainer').style.display = 'block';
            document.getElementById('loginForm').reset();
            document.getElementById('loginError').style.display = 'none';
        }

        // Дашборд
        async function loadDashboard() {
            try {
                const [licenses, users] = await Promise.all([
                    fetch('/admin/licenses').then(r => r.json()),
                    fetch('/admin/users').then(r => r.json())
                ]);
                
                document.getElementById('totalLicenses').textContent = licenses.length;
                document.getElementById('activeLicenses').textContent = licenses.filter(l => l.is_active).length;
                document.getElementById('blockedLicenses').textContent = licenses.filter(l => !l.is_active).length;
                document.getElementById('totalUsers').textContent = users.length;
                
            } catch (error) {
                console.error('Ошибка загрузки дашборда:', error);
            }
        }

        // Лицензии
        async function loadLicenses() {
            try {
                const response = await fetch('/admin/licenses');
                const licenses = await response.json();
                
                let html = `
                    <table>
                        <thead>
                            <tr>
                                <th>Ключ лицензии</th>
                                <th>Пользователь</th>
                                <th>Статус</th>
                                <th>Активации</th>
                                <th>Создана</th>
                                <th>Срок действия</th>
                                <th>Тип</th>
                                <th>Комментарий</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                licenses.forEach(license => {
                    let status, statusClass;
                    if (license.is_active) {
                        status = '<span class="status-active">АКТИВНА</span>';
                        statusClass = 'status-active';
                    } else {
                        status = '<span class="status-blocked">ЗАБЛОКИРОВАНА</span>';
                        statusClass = 'status-blocked';
                    }
                    
                    const activations = `${license.current_activations || 0}/${license.max_activations}`;
                    const created = new Date(license.created_at).toLocaleDateString('ru-RU');
                    const expires = license.is_permanent ? 'Бессрочная' : 
                                  (license.expires_at ? new Date(license.expires_at).toLocaleDateString('ru-RU') : 'Не указан');
                    const type = license.is_permanent ? '♾️ Бессрочная' : '📅 Временная';
                    
                    const actions = license.is_active ? 
                        `<button class="action-btn btn-block" onclick="blockLicense('${license.license_key}')">🚫 Блокировать</button>` :
                        `<button class="action-btn btn-unblock" onclick="unblockLicense('${license.license_key}')">✅ Разблокировать</button>`;
                    
                    html += `
                        <tr>
                            <td><span class="license-key">${license.license_key}</span></td>
                            <td>${license.client_name || '-'}</td>
                            <td>${status}</td>
                            <td>${activations}</td>
                            <td>${created}</td>
                            <td>${expires}</td>
                            <td>${type}</td>
                            <td>${license.notes || '-'}</td>
                            <td>
                                <div class="action-buttons">
                                    ${actions}
                                </div>
                            </td>
                        </tr>
                    `;
                });
                
                html += '</tbody></table>';
                document.getElementById('licensesList').innerHTML = html;
                
            } catch (error) {
                document.getElementById('licensesList').innerHTML = `
                    <div class="alert alert-error">Ошибка загрузки лицензий: ${error.message}</div>
                `;
            }
        }

        // Блокировка лицензии
        async function blockLicense(licenseKey) {
            if (!confirm(`Вы уверены, что хотите заблокировать лицензию?\n\n${licenseKey}`)) {
                return;
            }
            
            try {
                const response = await fetch('/admin/block-license', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ license_key: licenseKey })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('✅ Лицензия успешно заблокирована');
                    loadLicenses();
                    loadDashboard();
                } else {
                    alert('❌ Ошибка: ' + result.error);
                }
            } catch (error) {
                alert('❌ Ошибка сети: ' + error.message);
            }
        }

        // Разблокировка лицензии
        async function unblockLicense(licenseKey) {
            if (!confirm(`Вы уверены, что хотите разблокировать лицензию?\n\n${licenseKey}`)) {
                return;
            }
            
            try {
                const response = await fetch('/admin/unblock-license', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ license_key: licenseKey })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('✅ Лицензия успешно разблокирована');
                    loadLicenses();
                    loadDashboard();
                } else {
                    alert('❌ Ошибка: ' + result.error);
                }
            } catch (error) {
                alert('❌ Ошибка сети: ' + error.message);
            }
        }

        // Генерация лицензии
        document.getElementById('generateForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/admin/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                const resultDiv = document.getElementById('generateResult');
                
                if (result.success) {
                    resultDiv.innerHTML = `
                        <div class="alert alert-success">
                            <strong>✅ Лицензия успешно создана!</strong><br>
                            <strong>Ключ лицензии:</strong> <span class="license-key">${result.license_key}</span><br>
                            <strong>Сообщение:</strong> ${result.message}
                        </div>
                    `;
                    loadLicenses();
                    loadDashboard();
                } else {
                    resultDiv.innerHTML = `
                        <div class="alert alert-error">
                            <strong>❌ Ошибка:</strong> ${result.error}
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('generateResult').innerHTML = `
                    <div class="alert alert-error">Ошибка сети: ${error.message}</div>
                `;
            }
        });

        // Пользователи
        async function loadUsers() {
            try {
                const response = await fetch('/admin/users');
                const users = await response.json();
                
                let html = `
                    <table>
                        <thead>
                            <tr>
                                <th>Ключ лицензии</th>
                                <th>Имя пользователя</th>
                                <th>Устройство</th>
                                <th>IP адрес</th>
                                <th>Профиль Saby</th>
                                <th>Дата активации</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                users.forEach(user => {
                    const activated = new Date(user.activated_at).toLocaleString('ru-RU');
                    
                    html += `
                        <tr>
                            <td><span class="license-key">${user.license_key}</span></td>
                            <td>${user.client_name}</td>
                            <td>${user.machine_name || '-'}</td>
                            <td>${user.ip_address || '-'}</td>
                            <td>${user.saby_profile_url || '-'}</td>
                            <td>${activated}</td>
                        </tr>
                    `;
                });
                
                html += '</tbody></table>';
                document.getElementById('usersList').innerHTML = html;
                
            } catch (error) {
                document.getElementById('usersList').innerHTML = `
                    <div class="alert alert-error">Ошибка загрузки пользователей: ${error.message}</div>
                `;
            }
        }

        // Логи
        async function loadLogs() {
            try {
                const licenseKey = document.getElementById('logSearchKey').value;
                const url = licenseKey ? `/admin/logs/${licenseKey}` : '/admin/logs';
                
                const response = await fetch(url);
                const logs = await response.json();
                
                let html = `
                    <table>
                        <thead>
                            <tr>
                                <th>Дата и время</th>
                                <th>Уровень</th>
                                <th>Ключ лицензии</th>
                                <th>Устройство</th>
                                <th>IP адрес</th>
                                <th>Сообщение</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                logs.forEach(log => {
                    const date = new Date(log.created_at).toLocaleString('ru-RU');
                    const licenseKey = log.license_key ? `<span class="license-key">${log.license_key}</span>` : '-';
                    const machineName = log.machine_name || '-';
                    const ip = log.ip_address || '-';
                    
                    html += `
                        <tr>
                            <td>${date}</td>
                            <td>${log.log_level}</td>
                            <td>${licenseKey}</td>
                            <td>${machineName}</td>
                            <td>${ip}</td>
                            <td>${log.message}</td>
                        </tr>
                    `;
                });
                
                html += '</tbody></table>';
                document.getElementById('logsList').innerHTML = html;
                
            } catch (error) {
                document.getElementById('logsList').innerHTML = `
                    <div class="alert alert-error">Ошибка загрузки логов: ${error.message}</div>
                `;
            }
        }

        async function clearLogs() {
            if (!confirm('Вы уверены, что хотите очистить все логи системы? Это действие нельзя отменить.')) {
                return;
            }
            
            try {
                const response = await fetch('/admin/logs/clear', { method: 'DELETE' });
                if (response.ok) {
                    loadLogs();
                    loadDashboard();
                    alert('✅ Все логи успешно очищены');
                }
            } catch (error) {
                alert('❌ Ошибка при очистке логов');
            }
        }

        // Управление обновлениями
        async function uploadUpdate() {
            const version = document.getElementById('newVersion').value;
            const description = document.getElementById('updateDescription').value;
            const fileInput = document.getElementById('updateFile');
            
            if (!version || !description || !fileInput.files[0]) {
                alert('❌ Заполните все поля и выберите файл обновления');
                return;
            }
            
            const formData = new FormData();
            formData.append('version', version);
            formData.append('description', description);
            formData.append('file', fileInput.files[0]);
            
            try {
                const response = await fetch('/admin/upload-update', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                const resultDiv = document.getElementById('updateResult');
                
                if (result.success) {
                    resultDiv.innerHTML = `
                        <div class="alert alert-success">
                            <strong>✅ Обновление успешно загружено!</strong><br>
                            Версия: ${result.version}<br>
                            Файл: ${result.filename}
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <div class="alert alert-error">
                            <strong>❌ Ошибка:</strong> ${result.error}
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('updateResult').innerHTML = `
                    <div class="alert alert-error">Ошибка сети: ${error.message}</div>
                `;
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
@app.route('/admin')
def admin_panel():
    return render_template_string(ADMIN_HTML)

@app.route('/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if check_auth(username, password):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False}), 401
            
    except Exception as e:
        logger.error(f"Ошибка аутентификации: {e}")
        return jsonify({"success": False}), 500

@app.route('/admin/generate', methods=['POST'])
def admin_generate_license():
    try:
        data = request.get_json()
        
        days_valid = int(data.get('days_valid', 365))
        max_activations = int(data.get('max_activations', 1))
        notes = data.get('notes', '')
        is_permanent = bool(data.get('is_permanent'))
        
        license_key = db.create_license(days_valid, max_activations, notes, is_permanent)
        
        return jsonify({
            "success": True, 
            "license_key": license_key,
            "message": "Лицензия создана успешно"
        })
        
    except Exception as e:
        logger.error(f"Ошибка генерации лицензии: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@app.route('/admin/licenses')
def admin_get_licenses():
    try:
        licenses = db.get_all_licenses()
        return jsonify(licenses)
    except Exception as e:
        logger.error(f"Ошибка получения лицензий: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/admin/users')
def admin_get_users():
    try:
        users = db.get_all_users()
        return jsonify(users)
    except Exception as e:
        logger.error(f"Ошибка получения пользователей: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/admin/logs')
@app.route('/admin/logs/<license_key>')
def admin_get_logs(license_key=None):
    try:
        logs = db.get_logs(license_key)
        return jsonify(logs)
    except Exception as e:
        logger.error(f"Ошибка получения логов: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/admin/logs/clear', methods=['DELETE'])
def admin_clear_logs():
    try:
        if db.clear_logs():
            return jsonify({"success": True, "message": "Логи очищены"})
        else:
            return jsonify({"error": "Ошибка очистки логов"}), 500
    except Exception as e:
        logger.error(f"Ошибка очистки логов: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/admin/upload-update', methods=['POST'])
def admin_upload_update():
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "Файл не выбран"})
        
        file = request.files['file']
        version = request.form.get('version')
        description = request.form.get('description')
        
        if file.filename == '':
            return jsonify({"success": False, "error": "Файл не выбран"})
        
        if not version:
            return jsonify({"success": False, "error": "Версия не указана"})
        
        # Сохраняем файл обновления
        filename = f"SabyHelper_Update.exe"
        file.save(filename)
        
        return jsonify({
            "success": True,
            "version": version,
            "filename": filename,
            "message": "Обновление успешно загружено"
        })
        
    except Exception as e:
        logger.error(f"Ошибка загрузки обновления: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500

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
    print("🚀 Админ-панель запускается на порту 5001...")
    print("🔗 Адрес: http://155.212.171.112:5001/admin")
    app.run(host='0.0.0.0', port=5001, debug=False)