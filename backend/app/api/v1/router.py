# ============================================
# Главный роутер API v1
# ============================================
"""
Подключение всех роутеров API версии 1.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, survey

api_router = APIRouter()

# Роутер авторизации
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Авторизация"],
)

# Роутер опроса
api_router.include_router(
    survey.router,
    prefix="/survey",
    tags=["Опрос"],
)
