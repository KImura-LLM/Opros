# ============================================
# Pydantic схемы для API
# ============================================
"""
Схемы валидации входящих и исходящих данных.
"""

from datetime import datetime
from typing import Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ==========================================
# Схемы для опросника (Survey Config)
# ==========================================

class SurveyOptionSchema(BaseModel):
    """Вариант ответа на вопрос."""
    id: str = Field(..., description="Уникальный ID варианта")
    text: str = Field(..., description="Текст варианта ответа")
    value: Optional[str] = Field(None, description="Значение для логики")
    icon: Optional[str] = Field(None, description="Иконка (для UI)")


class SurveyNodeLogicSchema(BaseModel):
    """Логика перехода между узлами."""
    condition: Optional[str] = Field(None, description="Условие перехода")
    next_node: str = Field(..., description="ID следующего узла")
    default: bool = Field(False, description="Переход по умолчанию")


class SurveyNodeSchema(BaseModel):
    """Узел (вопрос) опросника."""
    id: str = Field(..., description="Уникальный ID узла")
    type: str = Field(..., description="Тип: single_choice, multi_choice, scale_1_10, body_map, text_input, number_input, info_screen")
    question_text: str = Field(..., description="Текст вопроса")
    description: Optional[str] = Field(None, description="Дополнительное описание")
    options: Optional[List[SurveyOptionSchema]] = Field(None, description="Варианты ответа")
    logic: Optional[List[SurveyNodeLogicSchema]] = Field(None, description="Правила перехода")
    required: bool = Field(True, description="Обязательность ответа")
    
    # Дополнительные поля для специфичных типов
    min_value: Optional[int] = Field(None, description="Минимальное значение (для scale/number)")
    max_value: Optional[int] = Field(None, description="Максимальное значение (для scale/number)")
    placeholder: Optional[str] = Field(None, description="Placeholder для текстового ввода")


class SurveyConfigSchema(BaseModel):
    """Полная структура опросника."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str] = None
    version: str
    nodes: List[SurveyNodeSchema] = Field(..., description="Узлы опросника")
    start_node: str = Field(..., description="ID стартового узла")


class SurveyConfigResponse(BaseModel):
    """Ответ API с конфигурацией опросника."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str] = None
    version: str
    json_config: dict


# ==========================================
# Схемы для авторизации
# ==========================================

class TokenValidationRequest(BaseModel):
    """Запрос на валидацию токена."""
    token: str = Field(..., description="JWT токен из URL")


class TokenValidationResponse(BaseModel):
    """Ответ после валидации токена."""
    valid: bool
    session_id: Optional[UUID] = None
    patient_name: Optional[str] = None
    message: Optional[str] = None


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
    node_id: str = Field(..., description="ID текущего вопроса")
    answer_data: dict = Field(..., description="Ответ пользователя")


class SurveyAnswerResponse(BaseModel):
    """Ответ после сохранения."""
    success: bool
    next_node: Optional[str] = Field(None, description="ID следующего узла")
    progress: float = Field(..., description="Прогресс прохождения (0-100)")


class SurveyProgressResponse(BaseModel):
    """Текущий прогресс опроса."""
    session_id: UUID
    current_node: str
    answers: dict
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


# ==========================================
# Схемы для ответов
# ==========================================

class SingleChoiceAnswer(BaseModel):
    """Ответ single_choice."""
    selected: str = Field(..., description="ID выбранного варианта")


class MultiChoiceAnswer(BaseModel):
    """Ответ multi_choice."""
    selected: List[str] = Field(..., description="Список ID выбранных вариантов")


class ScaleAnswer(BaseModel):
    """Ответ scale_1_10."""
    value: int = Field(..., ge=1, le=10, description="Значение от 1 до 10")


class TextAnswer(BaseModel):
    """Ответ text_input."""
    text: str = Field(..., description="Введённый текст")


class NumberAnswer(BaseModel):
    """Ответ number_input."""
    value: int = Field(..., description="Введённое число")


class BodyMapAnswer(BaseModel):
    """Ответ body_map."""
    locations: List[str] = Field(..., description="Выбранные локации на теле")
    intensity: Optional[int] = Field(None, ge=1, le=10, description="Интенсивность боли")


# ==========================================
# Общие схемы
# ==========================================

class ErrorResponse(BaseModel):
    """Ответ с ошибкой."""
    detail: str
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Успешный ответ."""
    success: bool = True
    message: str
