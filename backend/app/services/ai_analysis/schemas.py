"""Pydantic-схемы валидированного ответа ИИ-анализа."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Priority = Literal["red", "yellow", "green"]


def _looks_like_generation_garbage(value: str) -> bool:
    text = " ".join(str(value or "").split())
    if len(text) < 20:
        return False
    meaningful_chars = sum(1 for char in text if char.isalnum())
    bracket_chars = sum(1 for char in text if char in "{}[]()")
    return meaningful_chars == 0 or (bracket_chars >= 20 and meaningful_chars / len(text) < 0.15)


class AiEvidence(BaseModel):
    """Основание из фактического ответа пациента."""

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., min_length=1, max_length=100)
    question: str = Field(..., min_length=1, max_length=500)
    answer: str = Field(..., min_length=1, max_length=1000)


class AiRedFlag(BaseModel):
    """Потенциальный красный флаг, который врач должен проверить."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    evidence: list[AiEvidence] = Field(default_factory=list, max_length=10)


class AiKeyFinding(BaseModel):
    """Ключевое наблюдение по анкете."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    priority: Priority
    description: str = Field(..., min_length=1, max_length=1000)
    evidence: list[AiEvidence] = Field(default_factory=list, max_length=10)


class AiDoctorRecommendation(BaseModel):
    """Практический пункт для врача на приёме."""

    model_config = ConfigDict(extra="forbid")

    priority: Priority
    text: str = Field(..., min_length=1, max_length=500)


class AiAnalysisResponse(BaseModel):
    """Строго валидируемый JSON, который можно сохранить и отрендерить."""

    model_config = ConfigDict(extra="forbid")

    overall_priority: Priority
    summary: str = Field(..., min_length=1, max_length=1200)
    red_flags: list[AiRedFlag] = Field(default_factory=list, max_length=10)
    key_findings: list[AiKeyFinding] = Field(default_factory=list, max_length=10)
    doctor_recommendations: list[AiDoctorRecommendation] = Field(default_factory=list, max_length=10)
    limitations: str = Field(..., min_length=1, max_length=1000)

    @field_validator("summary", "limitations")
    @classmethod
    def reject_generation_garbage(cls, value: str) -> str:
        """Не принимаем технический мусор вида длинных последовательностей скобок."""
        if _looks_like_generation_garbage(value):
            raise ValueError("AI text looks like generation garbage")
        return value
