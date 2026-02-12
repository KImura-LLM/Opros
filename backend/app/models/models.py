# ============================================
# SQLAlchemy модели базы данных
# ============================================
"""
Модели для хранения данных опросника.
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SurveyConfig(Base):
    """
    Конфигурация опросника (JSON-структура с вопросами).
    Позволяет хранить несколько версий опросников.
    """
    __tablename__ = "survey_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="Название опросника")
    description = Column(Text, nullable=True, comment="Описание")
    json_config = Column(JSONB, nullable=False, comment="JSON-структура опросника")
    version = Column(String(50), default="1.0", comment="Версия опросника")
    is_active = Column(Boolean, default=True, comment="Активен ли опросник")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    sessions = relationship("SurveySession", back_populates="survey_config")
    
    def __repr__(self):
        return f"<SurveyConfig(id={self.id}, name='{self.name}', active={self.is_active})>"


class SurveySession(Base):
    """
    Сессия прохождения опроса.
    Создаётся при валидации токена и содержит привязку к Битрикс24.
    """
    __tablename__ = "survey_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Привязка к Битрикс24
    lead_id = Column(BigInteger, nullable=False, index=True, comment="ID сделки/лида в Битрикс24")
    entity_type = Column(String(10), default="DEAL", comment="Тип сущности: DEAL или LEAD")
    patient_name = Column(String(255), nullable=True, comment="Имя пациента (для приветствия)")
    
    # Привязка к конфигу опроса
    survey_config_id = Column(Integer, ForeignKey("survey_configs.id"), nullable=False)
    
    # Хэш токена для инвалидации
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    
    # Статус
    status = Column(
        String(20),
        default="in_progress",
        comment="Статус: in_progress, completed, abandoned",
    )
    
    # Согласие на обработку ПДн
    consent_given = Column(Boolean, default=False, comment="Дано согласие на обработку ПДн")
    consent_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Временные метки
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="Время автоматического истечения сессии")
    
    # IP адрес (для логирования, не связан с ПДн)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Связи
    survey_config = relationship("SurveyConfig", back_populates="sessions")
    answers = relationship("SurveyAnswer", back_populates="session", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="session", cascade="all, delete-orphan")
    
    # Индексы
    __table_args__ = (
        Index("ix_survey_sessions_lead_status", "lead_id", "status"),
        Index("ix_survey_sessions_created", "started_at"),
    )
    
    def __repr__(self):
        return f"<SurveySession(id={self.id}, lead_id={self.lead_id}, status='{self.status}')>"


class SurveyAnswer(Base):
    """
    Ответ на вопрос опроса.
    Каждый ответ привязан к сессии и узлу (node_id) опросника.
    """
    __tablename__ = "survey_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("survey_sessions.id", ondelete="CASCADE"), nullable=False)
    
    # ID узла из JSON-структуры опросника
    node_id = Column(String(100), nullable=False, comment="ID вопроса из JSON-конфига")
    
    # Данные ответа (гибкая структура)
    answer_data = Column(JSONB, nullable=False, comment="Ответ пользователя в JSON формате")
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    session = relationship("SurveySession", back_populates="answers")
    
    # Индексы
    __table_args__ = (
        Index("ix_survey_answers_session_node", "session_id", "node_id"),
    )
    
    def __repr__(self):
        return f"<SurveyAnswer(id={self.id}, node_id='{self.node_id}')>"


class AuditLog(Base):
    """
    Журнал аудита действий.
    Хранится не более AUDIT_LOG_RETENTION_HOURS часов (152-ФЗ).
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("survey_sessions.id", ondelete="CASCADE"), nullable=True)
    
    # Действие
    action = Column(String(100), nullable=False, comment="Тип действия")
    details = Column(JSONB, nullable=True, comment="Детали действия")
    
    # IP адрес (для безопасности)
    ip_address = Column(String(45), nullable=True)
    
    # Временная метка
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Связи
    session = relationship("SurveySession", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}')>"
