import hashlib
import hmac
import secrets
import string
from typing import Optional

class CryptoUtils:
    """Утилиты для криптографических операций"""
    
    @staticmethod
    def generate_license_key(length: int = 25) -> str:
        """Генерация лицензионного ключа"""
        alphabet = string.ascii_uppercase + string.digits
        # Разделяем ключ на группы для удобства чтения
        key = '-'.join(
            ''.join(secrets.choice(alphabet) for _ in range(5))
            for _ in range(length // 5)
        )
        return key
    
    @staticmethod
    def hash_data(data: str, secret: str) -> str:
        """Хеширование данных с секретом"""
        return hmac.new(
            secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def generate_hardware_id() -> str:
        """Генерация ID оборудования (упрощенная версия)"""
        import uuid
        return str(uuid.uuid4())
    
    @staticmethod
    def verify_signature(data: str, signature: str, secret: str) -> bool:
        """Проверка подписи данных"""
        expected_signature = CryptoUtils.hash_data(data, secret)
        return hmac.compare_digest(expected_signature, signature)