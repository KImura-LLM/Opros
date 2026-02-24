# ============================================
# Pydantic схемы для API
# ============================================
"""
Схемы валидации входящих и исходящих данных.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
import json


# Максимальный размер JSON-данных ответа (16 КБ)
MAX_ANSWER_DATA_SIZE = 16 * 1024


# ==========================================
# Схемы для авторизации
# ==========================================

class TokenValidationResponse(BaseModel):
    """Ответ после валидации токена."""
    valid: bool
    session_id: Optional[UUID] = None
    patient_name: Optional[str] = None
    message: Optional[str] = None
    expires_at: Optional[datetime] = None
    resolved_token: Optional[str] = None  # JWT токен (при использовании короткого кода)


class SurveyConfigResponse(BaseModel):
    """Ответ API с конфигурацией опросника."""
    id: int
    name: str
    description: Optional[str] = None
    version: str
    json_config: dict


# ==========================================
# Схемы для сессии опроса
# ==========================================

class SurveyStartRequest(BaseModel):
    """Запрос на начало опроса."""
    token: str = Field(..., description="JWT токен")
    consent_given: bool = Field(..., description="Согласие на обработку ПДн")


class SurveyStartResponse(BaseModel):
    """Ответ при начале опроса."""
    session_id: UUID
    patient_name: Optional[str] = None
    survey_config: dict
    message: str
    expires_at: Optional[datetime] = Field(None, description="Время истечения сессии")


class SurveyAnswerRequest(BaseModel):
    """Запрос на сохранение ответа."""
    session_id: UUID
    node_id: str = Field(..., description="ID текущего вопроса", max_length=200)
    answer_data: dict = Field(..., description="Ответ пользователя")
    
    @field_validator("answer_data")
    @classmethod
    def validate_answer_data_size(cls, v: dict) -> dict:
        """Проверка размера и глубины answer_data для защиты от DoS."""
        serialized = json.dumps(v, ensure_ascii=False)
        if len(serialized) > MAX_ANSWER_DATA_SIZE:
            raise ValueError(
                f"Размер ответа превышает допустимый лимит ({MAX_ANSWER_DATA_SIZE // 1024} КБ)"
            )
        # Проверка глубины вложенности (максимум 5 уровней)
        def check_depth(obj, depth=0):
            if depth > 5:
                raise ValueError("Слишком глубокая вложенность данных ответа (максимум 5)")
            if isinstance(obj, dict):
                for val in obj.values():
                    check_depth(val, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    check_depth(item, depth + 1)
        check_depth(v)
        return v


class SurveyAnswerResponse(BaseModel):
    """Ответ после сохранения."""
    success: bool
    next_node: Optional[str] = Field(None, description="ID следующего узла")
    progress: float = Field(..., description="Прогресс прохождения (0-100)")


class SurveyProgressResponse(BaseModel):
    """Текущий прогресс опроса."""
    session_id: UUID
    current_node: str
    history: List[str]
    progress_percent: float


class SurveyCompleteRequest(BaseModel):
    """Запрос на завершение опроса."""
    session_id: UUID


class SurveyCompleteResponse(BaseModel):
    """Ответ после завершения."""
    success: bool
    message: str
    report_sent: bool = Field(..., description="Отчёт отправлен в Битрикс24")
    pdf_sent: bool = Field(False, description="PDF-отчёт прикреплён к карточке Битрикс24")


