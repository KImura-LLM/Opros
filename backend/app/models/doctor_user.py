"""
Модель учетной записи врача для защищенного портала.
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, text
from sqlalchemy.sql import func

from app.core.database import Base


class DoctorUser(Base):
    """Учетная запись врача для входа в портал результатов."""

    __tablename__ = "doctor_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True, comment="Логин врача")
    hashed_password = Column(String(255), nullable=False, comment="Хэш пароля врача")
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"), comment="Аккаунт активен")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<DoctorUser(id={self.id}, username='{self.username}', active={self.is_active})>"
