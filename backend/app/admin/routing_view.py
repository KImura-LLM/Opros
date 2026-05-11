"""SQLAdmin entry point for survey routing rules."""

from sqladmin import BaseView, expose
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.core.config import settings


class SurveyRoutingAdmin(BaseView):
    """Меню админ-панели для экрана маршрутизации опросников."""

    name = "Маршрутизация"
    icon = "fa-solid fa-route"

    @expose("/routing", identity="routing", include_in_schema=False)
    async def routing_page(self, request: Request):
        """Перенаправление авторизованного администратора на React-экран правил."""
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        request_host = request.url.hostname or ""

        if frontend_url.startswith("http://localhost") and request_host not in {
            "localhost",
            "127.0.0.1",
        }:
            return RedirectResponse(url="/routing", status_code=302)

        return RedirectResponse(url=f"{frontend_url}/routing", status_code=302)
