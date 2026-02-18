# ============================================
# Утилиты безопасности для логирования
# ============================================
"""
Маскировка персональных данных (ПДн) в логах.
Соответствие требованиям 152-ФЗ.
"""


def mask_name(name: str | None) -> str:
    """
    Маскировка ФИО пациента для логов.
    
    Примеры:
        "Иванов Иван Иванович" -> "Ив***"
        "Петр" -> "Пе***"
        None -> "[не указано]"
    """
    if not name:
        return "[не указано]"
    name = name.strip()
    if len(name) <= 2:
        return name[0] + "***"
    return name[:2] + "***"


def mask_ip(ip: str | None) -> str:
    """
    Маскировка IP-адреса для логов.
    
    Примеры:
        "192.168.1.100" -> "192.168.x.x"
        None -> "[не указано]"
    """
    if not ip:
        return "[не указано]"
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.x.x"
    return ip[:8] + "***"


def mask_token(token: str | None) -> str:
    """
    Маскировка JWT-токена для логов.
    
    Примеры:
        "eyJhbGci..." -> "eyJh...ci"
        None -> "[нет]"
    """
    if not token:
        return "[нет]"
    if len(token) > 8:
        return f"{token[:4]}...{token[-2:]}"
    return "***"
