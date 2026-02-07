# ============================================
# API эндпоинты редактора опросника
# ============================================
"""
CRUD API для визуального редактора блок-схемы опросника.
Используется React Flow редактором в админ-панели.
"""

from datetime import datetime, timezone
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from loguru import logger

from app.core.database import get_db
from app.core.config import settings
from app.models import SurveyConfig


router = APIRouter()


# ==========================================
# Аутентификация администратора
# ==========================================

async def verify_admin_session(request: Request) -> bool:
    """
    Проверка аутентификации администратора через сессию.
    Использует ту же сессию, что и SQLAdmin.
    """
    # Проверяем сессию (совместима с SQLAdmin)
    is_authenticated = request.session.get("admin_authenticated", False)
    
    if not is_authenticated:
        # Альтернативная проверка через Basic Auth заголовок
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Basic "):
            import base64
            try:
                credentials = base64.b64decode(auth_header[6:]).decode("utf-8")
                username, password = credentials.split(":", 1)
                if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
                    return True
            except Exception:
                pass
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация администратора",
            headers={"WWW-Authenticate": "Basic realm='admin'"},
        )
    
    return True


# ==========================================
# Pydantic схемы для редактора
# ==========================================

class NodePosition(BaseModel):
    """Позиция узла на canvas."""
    x: float = 0
    y: float = 0


class NodeOption(BaseModel):
    """Вариант ответа."""
    id: str
    text: str
    value: Optional[str] = None
    icon: Optional[str] = None


class NodeLogic(BaseModel):
    """Правило перехода."""
    condition: Optional[str] = None
    next_node: str
    default: bool = False


class AdditionalField(BaseModel):
    """Дополнительное поле (для multi_choice_with_input)."""
    id: str
    type: str  # text, number, single_choice
    label: str
    placeholder: Optional[str] = None
    min: Optional[int] = None
    max: Optional[int] = None
    options: Optional[List[dict]] = None
    show_if: Optional[str] = None


class SurveyNode(BaseModel):
    """Полная структура узла опросника."""
    id: str
    type: str  # single_choice, multi_choice, text_input, slider, body_map, info_screen, multi_choice_with_input
    question_text: str
    description: Optional[str] = None
    required: bool = True
    options: Optional[List[NodeOption]] = None
    logic: Optional[List[NodeLogic]] = None
    additional_fields: Optional[List[AdditionalField]] = None
    
    # Для slider/scale типов
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    step: Optional[int] = None
    
    # Для text_input
    placeholder: Optional[str] = None
    max_length: Optional[int] = None
    
    # Для info_screen
    is_final: Optional[bool] = None
    
    # Позиция на canvas (для React Flow)
    position: Optional[NodePosition] = None


class SurveyStructure(BaseModel):
    """Полная структура опросника."""
    id: Optional[int] = None
    name: str
    version: str = "1.0"
    description: Optional[str] = None
    start_node: str
    branch_mapping: Optional[dict] = None
    nodes: List[SurveyNode]


class SurveyStructureUpdate(BaseModel):
    """Обновление структуры опросника."""
    name: Optional[str] = None
    description: Optional[str] = None
    start_node: Optional[str] = None
    branch_mapping: Optional[dict] = None
    nodes: Optional[List[SurveyNode]] = None


class ValidationError(BaseModel):
    """Ошибка валидации."""
    type: str  # error, warning
    node_id: Optional[str] = None
    message: str


class ValidationResult(BaseModel):
    """Результат валидации структуры."""
    valid: bool
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []


class SurveyListItem(BaseModel):
    """Элемент списка опросников."""
    id: int
    name: str
    version: str
    description: Optional[str]
    is_active: bool
    nodes_count: int
    created_at: datetime
    updated_at: Optional[datetime]


# ==========================================
# Вспомогательные функции
# ==========================================

def validate_survey_structure(structure: dict) -> ValidationResult:
    """
    Валидация структуры опросника.
    Проверяет корректность связей, наличие стартового/финального узла.
    """
    errors = []
    warnings = []
    
    nodes = structure.get("nodes", [])
    node_ids = {n.get("id") for n in nodes}
    start_node = structure.get("start_node")
    
    # 1. Проверка наличия стартового узла
    if not start_node:
        errors.append(ValidationError(
            type="error",
            message="Не указан стартовый узел (start_node)"
        ))
    elif start_node not in node_ids:
        errors.append(ValidationError(
            type="error",
            node_id=start_node,
            message=f"Стартовый узел '{start_node}' не найден среди узлов"
        ))
    
    # 2. Проверка наличия финального узла
    final_nodes = [n for n in nodes if n.get("is_final") or n.get("type") == "info_screen"]
    if not final_nodes:
        warnings.append(ValidationError(
            type="warning",
            message="Не найден финальный узел (info_screen или is_final=true)"
        ))
    
    # 3. Проверка каждого узла
    reachable_nodes = set()
    
    def collect_reachable(node_id: str, visited: set):
        """Рекурсивный сбор достижимых узлов."""
        if node_id in visited or node_id not in node_ids:
            return
        visited.add(node_id)
        
        node = next((n for n in nodes if n.get("id") == node_id), None)
        if not node:
            return
            
        logic = node.get("logic", [])
        for rule in logic:
            next_id = rule.get("next_node")
            if next_id:
                collect_reachable(next_id, visited)
    
    if start_node and start_node in node_ids:
        collect_reachable(start_node, reachable_nodes)
    
    for node in nodes:
        node_id = node.get("id")
        node_type = node.get("type")
        
        # Проверка текста вопроса
        if not node.get("question_text"):
            errors.append(ValidationError(
                type="error",
                node_id=node_id,
                message=f"Узел '{node_id}' не имеет текста вопроса"
            ))
        
        # Проверка вариантов для choice типов
        if node_type in ["single_choice", "multi_choice", "multi_choice_with_input"]:
            options = node.get("options", [])
            if not options:
                errors.append(ValidationError(
                    type="error",
                    node_id=node_id,
                    message=f"Узел '{node_id}' типа '{node_type}' не имеет вариантов ответа"
                ))
        
        # Проверка логики переходов
        logic = node.get("logic", [])
        if not logic and not node.get("is_final") and node_type != "info_screen":
            warnings.append(ValidationError(
                type="warning",
                node_id=node_id,
                message=f"Узел '{node_id}' не имеет правил перехода"
            ))
        
        for rule in logic:
            next_id = rule.get("next_node")
            if next_id and next_id not in node_ids:
                errors.append(ValidationError(
                    type="error",
                    node_id=node_id,
                    message=f"Узел '{node_id}' ссылается на несуществующий узел '{next_id}'"
                ))
        
        # Проверка достижимости
        if node_id not in reachable_nodes and node_id != start_node:
            warnings.append(ValidationError(
                type="warning",
                node_id=node_id,
                message=f"Узел '{node_id}' недостижим от стартового узла"
            ))
        
        # Проверка slider
        if node_type == "slider":
            if node.get("min_value") is None or node.get("max_value") is None:
                errors.append(ValidationError(
                    type="error",
                    node_id=node_id,
                    message=f"Узел '{node_id}' типа slider должен иметь min_value и max_value"
                ))
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def convert_to_json_config(structure: SurveyStructure) -> dict:
    """Конвертация Pydantic модели в JSON config."""
    return {
        "id": structure.id,
        "name": structure.name,
        "version": structure.version,
        "description": structure.description,
        "start_node": structure.start_node,
        "branch_mapping": structure.branch_mapping or {},
        "nodes": [node.model_dump(exclude_none=True) for node in structure.nodes]
    }


def extract_structure_from_config(config: dict) -> dict:
    """Извлечение структуры из json_config."""
    return {
        "name": config.get("name", ""),
        "version": config.get("version", "1.0"),
        "description": config.get("description"),
        "start_node": config.get("start_node", ""),
        "branch_mapping": config.get("branch_mapping", {}),
        "nodes": config.get("nodes", [])
    }


# ==========================================
# API Эндпоинты
# ==========================================

@router.get("/surveys", response_model=List[SurveyListItem])
async def list_surveys(
    request: Request,
    db: AsyncSession = Depends(get_db),
    active_only: bool = False,
    _auth: bool = Depends(verify_admin_session),
):
    """
    Получить список всех опросников.
    """
    query = select(SurveyConfig)
    if active_only:
        query = query.where(SurveyConfig.is_active == True)
    query = query.order_by(SurveyConfig.id.desc())
    
    result = await db.execute(query)
    configs = result.scalars().all()
    
    return [
        SurveyListItem(
            id=c.id,
            name=c.name,
            version=c.json_config.get("version", "1.0") if c.json_config else "1.0",
            description=c.description,
            is_active=c.is_active,
            nodes_count=len(c.json_config.get("nodes", [])) if c.json_config else 0,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in configs
    ]


@router.get("/surveys/{survey_id}", response_model=SurveyStructure)
async def get_survey(
    request: Request,
    survey_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    """
    Получить структуру опросника для редактирования.
    """
    result = await db.execute(
        select(SurveyConfig).where(SurveyConfig.id == survey_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Опросник не найден"
        )
    
    json_config = config.json_config or {}
    
    return SurveyStructure(
        id=config.id,
        name=config.name,
        version=json_config.get("version", "1.0"),
        description=config.description,
        start_node=json_config.get("start_node", ""),
        branch_mapping=json_config.get("branch_mapping", {}),
        nodes=[SurveyNode(**node) for node in json_config.get("nodes", [])]
    )


@router.post("/surveys", response_model=SurveyStructure)
async def create_survey(
    request: Request,
    structure: SurveyStructure,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    """
    Создать новый опросник.
    """
    # Валидация
    json_config = convert_to_json_config(structure)
    validation = validate_survey_structure(json_config)
    
    if not validation.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Структура опросника содержит ошибки",
                "errors": [e.model_dump() for e in validation.errors]
            }
        )
    
    # Создание
    config = SurveyConfig(
        name=structure.name,
        description=structure.description,
        json_config=json_config,
        version=structure.version,
        is_active=True,
    )
    
    db.add(config)
    await db.commit()
    await db.refresh(config)
    
    logger.info(f"Создан опросник: {config.id} - {config.name}")
    
    structure.id = config.id
    return structure


@router.put("/surveys/{survey_id}", response_model=SurveyStructure)
async def update_survey(
    request: Request,
    survey_id: int,
    structure: SurveyStructure,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    """
    Обновить структуру опросника (перезапись текущей версии).
    """
    result = await db.execute(
        select(SurveyConfig).where(SurveyConfig.id == survey_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Опросник не найден"
        )
    
    # Валидация
    json_config = convert_to_json_config(structure)
    validation = validate_survey_structure(json_config)
    
    if not validation.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Структура опросника содержит ошибки",
                "errors": [e.model_dump() for e in validation.errors]
            }
        )
    
    # Обновление
    config.name = structure.name
    config.description = structure.description
    config.json_config = json_config
    config.version = structure.version
    config.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(config)
    
    logger.info(f"Обновлён опросник: {config.id} - {config.name}")
    
    structure.id = config.id
    return structure


@router.delete("/surveys/{survey_id}")
async def delete_survey(
    request: Request,
    survey_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    """
    Удалить опросник.
    """
    result = await db.execute(
        select(SurveyConfig).where(SurveyConfig.id == survey_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Опросник не найден"
        )
    
    await db.delete(config)
    await db.commit()
    
    logger.info(f"Удалён опросник: {survey_id}")
    
    return {"success": True, "message": "Опросник удалён"}


@router.post("/surveys/{survey_id}/validate", response_model=ValidationResult)
async def validate_survey(
    request: Request,
    survey_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    """
    Валидировать структуру опросника.
    """
    result = await db.execute(
        select(SurveyConfig).where(SurveyConfig.id == survey_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Опросник не найден"
        )
    
    return validate_survey_structure(config.json_config or {})


@router.post("/validate-structure", response_model=ValidationResult)
async def validate_structure(
    request: Request,
    structure: SurveyStructure,
    _auth: bool = Depends(verify_admin_session),
):
    """
    Валидировать структуру опросника без сохранения.
    """
    json_config = convert_to_json_config(structure)
    return validate_survey_structure(json_config)


@router.post("/surveys/{survey_id}/duplicate", response_model=SurveyStructure)
async def duplicate_survey(
    request: Request,
    survey_id: int,
    new_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    """
    Дублировать опросник.
    """
    result = await db.execute(
        select(SurveyConfig).where(SurveyConfig.id == survey_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Опросник не найден"
        )
    
    # Создание копии
    new_config = SurveyConfig(
        name=new_name or f"{config.name} (копия)",
        description=config.description,
        json_config=config.json_config.copy() if config.json_config else {},
        version="1.0",
        is_active=False,  # Копия неактивна по умолчанию
    )
    
    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)
    
    logger.info(f"Дублирован опросник {survey_id} -> {new_config.id}")
    
    json_config = new_config.json_config or {}
    return SurveyStructure(
        id=new_config.id,
        name=new_config.name,
        version=json_config.get("version", "1.0"),
        description=new_config.description,
        start_node=json_config.get("start_node", ""),
        branch_mapping=json_config.get("branch_mapping", {}),
        nodes=[SurveyNode(**node) for node in json_config.get("nodes", [])]
    )


@router.post("/surveys/{survey_id}/export")
async def export_survey(
    request: Request,
    survey_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    """
    Экспорт опросника в JSON формате.
    """
    result = await db.execute(
        select(SurveyConfig).where(SurveyConfig.id == survey_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Опросник не найден"
        )
    
    return {
        "name": config.name,
        "description": config.description,
        "version": config.version,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "config": config.json_config
    }


@router.post("/surveys/import", response_model=SurveyStructure)
async def import_survey(
    request: Request,
    data: dict,
    db: AsyncSession = Depends(get_db),
    _auth: bool = Depends(verify_admin_session),
):
    """
    Импорт опросника из JSON.
    """
    config_data = data.get("config", data)
    name = data.get("name", config_data.get("name", "Импортированный опросник"))
    description = data.get("description", config_data.get("description"))
    
    # Валидация
    validation = validate_survey_structure(config_data)
    if not validation.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Импортированная структура содержит ошибки",
                "errors": [e.model_dump() for e in validation.errors]
            }
        )
    
    # Создание
    config = SurveyConfig(
        name=name,
        description=description,
        json_config=config_data,
        version=config_data.get("version", "1.0"),
        is_active=False,  # Импорт неактивен по умолчанию
    )
    
    db.add(config)
    await db.commit()
    await db.refresh(config)
    
    logger.info(f"Импортирован опросник: {config.id} - {config.name}")
    
    return SurveyStructure(
        id=config.id,
        name=config.name,
        version=config_data.get("version", "1.0"),
        description=config.description,
        start_node=config_data.get("start_node", ""),
        branch_mapping=config_data.get("branch_mapping", {}),
        nodes=[SurveyNode(**node) for node in config_data.get("nodes", [])]
    )


# ==========================================
# Типы узлов (для UI редактора)
# ==========================================

@router.get("/node-types")
async def get_node_types():
    """
    Получить список доступных типов узлов.
    """
    return [
        {
            "id": "single_choice",
            "name": "Один выбор",
            "description": "Пользователь выбирает один вариант из списка",
            "icon": "circle-dot",
            "color": "#3b82f6",
            "has_options": True,
            "has_logic": True,
        },
        {
            "id": "multi_choice",
            "name": "Множественный выбор",
            "description": "Пользователь может выбрать несколько вариантов",
            "icon": "check-square",
            "color": "#8b5cf6",
            "has_options": True,
            "has_logic": True,
        },
        {
            "id": "multi_choice_with_input",
            "name": "Выбор + ввод",
            "description": "Множественный выбор с дополнительными полями ввода",
            "icon": "list-plus",
            "color": "#a855f7",
            "has_options": True,
            "has_logic": True,
            "has_additional_fields": True,
        },
        {
            "id": "text_input",
            "name": "Текстовый ответ",
            "description": "Пользователь вводит произвольный текст",
            "icon": "type",
            "color": "#10b981",
            "has_options": False,
            "has_logic": True,
        },
        {
            "id": "slider",
            "name": "Слайдер",
            "description": "Выбор значения на шкале (например, 1-10)",
            "icon": "sliders-horizontal",
            "color": "#f59e0b",
            "has_options": False,
            "has_logic": True,
            "has_min_max": True,
        },
        {
            "id": "body_map",
            "name": "Карта тела",
            "description": "Выбор зон на карте тела + интенсивность",
            "icon": "user",
            "color": "#ef4444",
            "has_options": True,
            "has_logic": True,
            "has_min_max": True,
        },
        {
            "id": "info_screen",
            "name": "Информационный экран",
            "description": "Текстовый экран без ввода (финиш, инструкция)",
            "icon": "info",
            "color": "#6b7280",
            "has_options": False,
            "has_logic": False,
            "can_be_final": True,
        },
        {
            "id": "consent_screen",
            "name": "Согласие (152-ФЗ)",
            "description": "Согласие на обработку персональных данных",
            "icon": "shield-check",
            "color": "#059669",
            "has_options": False,
            "has_logic": True,
            "can_be_final": False,
        },
    ]
