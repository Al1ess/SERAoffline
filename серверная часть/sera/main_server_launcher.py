import subprocess
import sys
import os
import time
import signal

def run_server(name, script_name, port):
    """Запускает сервер правильно"""
    print(f"\n🚀 Запуск {name} на порту {port}...")
    
    # Полный путь к файлу
    script_path = os.path.join(os.getcwd(), script_name)
    
    if not os.path.exists(script_path):
        print(f"❌ Файл {script_name} не найден!")
        return None
    
    # Запускаем процесс
    try:
        # ВАЖНО: Используем полную команду с явным указанием хоста и порта
        if script_name == "license_server.py":
            cmd = [sys.executable, script_path]
        elif script_name == "admin_panel.py":
            cmd = [sys.executable, "-c", f'''
import sys
sys.path.insert(0, '{os.getcwd()}')
from admin_panel import app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port={port}, debug=False, threaded=True)
''']
        elif script_name == "update_server.py":
            cmd = [sys.executable, "-c", f'''
import sys
sys.path.insert(0, '{os.getcwd()}')
from update_server import app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port={port}, debug=False, threaded=True)
''']
        else:
            cmd = [sys.executable, script_path]
        
        # Запускаем
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ, 'PYTHONUNBUFFERED': '1'}
        )
        
        # Даем время на запуск
        time.sleep(3)
        
        # Проверяем, жив ли процесс
        if process.poll() is None:
            print(f"✅ {name} запущен на порту {port} (PID: {process.pid})")
            return process
        else:
            # Читаем ошибку
            output, _ = process.communicate()
            print(f"❌ Ошибка запуска {name}:")
            print(output[:200])
            return None
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def main():
    print("="*60)
    print("🎯 ЗАПУСК СЕРВЕРОВ НА НУЖНЫХ ПОРТАХ: 5000, 5001, 5002")
    print("="*60)
    
    # Убиваем старые процессы
    print("\n🛑 Останавливаем старые процессы...")
    os.system("pkill -f 'license_server.py' 2>/dev/null")
    os.system("pkill -f 'admin_panel.py' 2>/dev/null")
    os.system("pkill -f 'update_server.py' 2>/dev/null")
    time.sleep(2)
    
    # Проверяем порты
    print("\n📡 Проверка портов...")
    for port in [5000, 5001, 5002]:
        import socket
        try:
            s = socket.socket()
            s.bind(('0.0.0.0', port))
            s.close()
            print(f"  ✅ Порт {port} свободен")
        except:
            print(f"  ❌ Порт {port} занят!")
    
    # Запускаем серверы
    processes = []
    
    # 1. License Server (5000)
    p1 = run_server("License Server", "license_server.py", 5000)
    if p1:
        processes.append(("License Server", p1, 5000))
    
    # 2. Admin Panel (5001)
    p2 = run_server("Admin Panel", "admin_panel.py", 5001)
    if p2:
        processes.append(("Admin Panel", p2, 5001))
    
    # 3. Update Server (5002)
    p3 = run_server("Update Server", "update_server.py", 5002)
    if p3:
        processes.append(("Update Server", p3, 5002))
    
    print("\n" + "="*60)
    print("📊 РЕЗУЛЬТАТ:")
    print("="*60)
    
    if processes:
        print("✅ Успешно запущены:")
        for name, proc, port in processes:
            print(f"   • {name}: порт {port} (PID: {proc.pid})")
        
        print("\n🌐 Ссылки для проверки:")
        for name, proc, port in processes:
            print(f"   • {name}: http://155.212.171.112:{port}")
        
        print("\n📋 Проверка:")
        print("   curl http://localhost:5000/health")
        print("   curl http://localhost:5001/health")
        print("   curl http://localhost:5002/health")
        
        print("\n⏹️  Для остановки нажмите Ctrl+C")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Остановка серверов...")
            for name, proc, port in processes:
                proc.terminate()
                print(f"✅ {name} остановлен")
    else:
        print("❌ Ни один сервер не запустился!")
        print("\n🔧 Попробуем запустить вручную:")
        print("   python3 license_server.py")

if __name__ == "__main__":
    main()