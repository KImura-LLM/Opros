# ============================================
# SQLAlchemy модели базы данных
# ============================================
"""
Модели для хранения данных опросника.
"""

import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
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

    sessions = relationship("SurveySession", back_populates="survey_config")

    def __repr__(self):
        return f"<SurveyConfig(id={self.id}, name='{self.name}', active={self.is_active})>"


class SurveySession(Base):
    """
    Сессия прохождения опроса.
    Создается при валидации токена и содержит привязку к Bitrix24.
    """

    __tablename__ = "survey_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Привязка к Bitrix24
    lead_id = Column(BigInteger, nullable=False, index=True, comment="ID сделки/лида в Bitrix24")
    entity_type = Column(String(10), default="DEAL", comment="Тип сущности: DEAL или LEAD")
    patient_name = Column(String(255), nullable=True, comment="Имя пациента для приветствия")
    doctor_name = Column(String(255), nullable=True, comment="ФИО врача из Bitrix24")
    appointment_at = Column(String(50), nullable=True, comment="Дата и время приема из Bitrix24")
    bitrix_category_id = Column(Integer, nullable=True, comment="ID воронки в Bitrix24")
    portal_clinic_bucket = Column(
        String(50),
        nullable=False,
        default="test",
        comment="Вкладка портала врачей: novosibirsk, kemerovo, yaroslavl, test",
    )

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
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время автоматического истечения сессии",
    )

    # Служебные данные
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Снимок отчета на момент завершения опроса
    report_snapshot = Column(
        JSONB,
        nullable=True,
        comment="Снимок отчета на момент завершения опроса",
    )

    survey_config = relationship("SurveyConfig", back_populates="sessions")
    answers = relationship("SurveyAnswer", back_populates="session", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_survey_sessions_lead_status", "lead_id", "status"),
        Index("ix_survey_sessions_created", "started_at"),
        Index(
            "ix_survey_sessions_portal_bucket_status_completed",
            "portal_clinic_bucket",
            "status",
            "completed_at",
        ),
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
    node_id = Column(String(100), nullable=False, comment="ID вопроса из JSON-конфига")
    answer_data = Column(JSONB, nullable=False, comment="Ответ пользователя в JSON формате")
    duration_seconds = Column(Integer, nullable=True, comment="Время ответа на вопрос в секундах")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    session = relationship("SurveySession", back_populates="answers")

    __table_args__ = (
        Index("ix_survey_answers_session_node", "session_id", "node_id", unique=True),
    )

    def __repr__(self):
        return f"<SurveyAnswer(id={self.id}, node_id='{self.node_id}')>"


class AuditLog(Base):
    """
    Журнал аудита действий.
    Хранится ограниченное время согласно политике проекта.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("survey_sessions.id", ondelete="CASCADE"), nullable=True)
    action = Column(String(100), nullable=False, comment="Тип действия")
    details = Column(JSONB, nullable=True, comment="Детали действия")
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    session = relationship("SurveySession", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}')>"


class SurveyRoutingClinicSetting(Base):
    """Настройки маршрутизации опросников для одной клиники."""

    __tablename__ = "survey_routing_clinic_settings"

    id = Column(Integer, primary_key=True, index=True)
    clinic_key = Column(String(100), nullable=False, unique=True, index=True, comment="Ключ клиники из backend-конфигурации")
    default_survey_config_id = Column(
        Integer,
        ForeignKey("survey_configs.id"),
        nullable=True,
        comment="Опросник по умолчанию для клиники",
    )
    is_enabled = Column(Boolean, nullable=False, default=True, comment="Маршрутизация включена")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    default_survey_config = relationship("SurveyConfig")


class SurveyRoutingRule(Base):
    """Правило выбора опросника по данным сделки Bitrix24."""

    __tablename__ = "survey_routing_rules"

    id = Column(Integer, primary_key=True, index=True)
    clinic_key = Column(String(100), nullable=False, index=True, comment="Ключ клиники")
    name = Column(String(255), nullable=False, comment="Название правила")
    is_active = Column(Boolean, nullable=False, default=True, comment="Правило активно")
    survey_config_id = Column(Integer, ForeignKey("survey_configs.id"), nullable=False, comment="Выбранный опросник")
    condition_logic = Column(String(10), nullable=False, default="AND", comment="Логика условий: AND или OR")
    priority = Column(Integer, nullable=False, default=100, comment="Чем больше значение, тем выше приоритет")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    survey_config = relationship("SurveyConfig")
    conditions = relationship(
        "SurveyRoutingCondition",
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="SurveyRoutingCondition.id",
    )

    __table_args__ = (
        Index("ix_survey_routing_rules_clinic_active_priority", "clinic_key", "is_active", "priority"),
    )


class SurveyRoutingCondition(Base):
    """Одно условие правила маршрутизации опросника."""

    __tablename__ = "survey_routing_conditions"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("survey_routing_rules.id", ondelete="CASCADE"), nullable=False)
    crm_field_id = Column(String(255), nullable=False, comment="ID поля сделки Bitrix24")
    operator = Column(String(50), nullable=False, comment="Оператор сравнения")
    value = Column(JSONB, nullable=True, comment="Значение условия")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    rule = relationship("SurveyRoutingRule", back_populates="conditions")

    __table_args__ = (
        Index("ix_survey_routing_conditions_rule_id", "rule_id"),
    )


class BitrixCrmField(Base):
    """Локальный кэш metadata полей сделки Bitrix24."""

    __tablename__ = "bitrix_crm_fields"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(20), nullable=False, default="DEAL", comment="Тип CRM-сущности")
    field_id = Column(String(255), nullable=False, comment="ID поля Bitrix24")
    title = Column(String(255), nullable=False, comment="Название поля")
    type = Column(String(100), nullable=True, comment="Тип поля Bitrix24")
    is_list = Column(Boolean, nullable=False, default=False, comment="Поле содержит список вариантов")
    is_active = Column(Boolean, nullable=False, default=True, comment="Поле актуально в последней синхронизации")
    raw_metadata = Column(JSONB, nullable=True, comment="Исходные metadata Bitrix24")
    synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("entity_type", "field_id", name="uq_bitrix_crm_fields_entity_field"),
        Index("ix_bitrix_crm_fields_entity_active_title", "entity_type", "is_active", "title"),
    )


class BitrixCrmFieldOption(Base):
    """Локальный кэш вариантов списочного поля Bitrix24."""

    __tablename__ = "bitrix_crm_field_options"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(20), nullable=False, default="DEAL", comment="Тип CRM-сущности")
    field_id = Column(String(255), nullable=False, comment="ID поля Bitrix24")
    option_id = Column(String(255), nullable=False, comment="ID варианта Bitrix24")
    label = Column(String(255), nullable=False, comment="Отображаемый текст варианта")
    sort = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    raw_metadata = Column(JSONB, nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("entity_type", "field_id", "option_id", name="uq_bitrix_crm_field_options_entity_field_option"),
        Index("ix_bitrix_crm_field_options_field_active_label", "entity_type", "field_id", "is_active", "label"),
    )
