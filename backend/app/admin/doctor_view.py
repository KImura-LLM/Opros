"""
SQLAdmin-представление для управления учетными записями врачей.
"""

from sqladmin import ModelView
from sqladmin.forms import get_model_form
from wtforms import PasswordField

from app.core.security import get_password_hash
from app.models import DoctorUser


class DoctorUserAdmin(ModelView, model=DoctorUser):
    """CRUD-интерфейс для учетных записей врачей."""

    identity = "doctor-user"
    name = "Настройка врача"
    name_plural = "Настройка врачей"
    icon = "fa-solid fa-user-doctor"

    column_list = [
        DoctorUser.id,
        DoctorUser.username,
        DoctorUser.is_active,
        DoctorUser.created_at,
    ]
    column_details_list = [
        DoctorUser.id,
        DoctorUser.username,
        DoctorUser.is_active,
        DoctorUser.created_at,
        DoctorUser.updated_at,
    ]
    column_searchable_list = [DoctorUser.username]
    column_sortable_list = [DoctorUser.id, DoctorUser.username, DoctorUser.created_at]
    column_default_sort = [("id", True)]

    form_columns = [DoctorUser.username, DoctorUser.is_active]

    column_labels = {
        DoctorUser.username: "Логин",
        DoctorUser.is_active: "Активен",
        DoctorUser.created_at: "Создан",
        DoctorUser.updated_at: "Обновлен",
    }

    async def scaffold_form(self):
        form = await get_model_form(
            model=self.model,
            session_maker=self.session_maker,
            only=self._form_prop_names,
            column_labels=self._column_labels,
            form_args=self.form_args,
            form_widget_args=self.form_widget_args,
            form_class=self.form_base_class,
            form_overrides=self.form_overrides,
            form_ajax_refs=self._form_ajax_refs,
            form_include_pk=self.form_include_pk,
            form_converter=self.form_converter,
        )
        form.password = PasswordField("Пароль")
        return form

    async def on_model_change(self, data, model, is_created, request):
        password = (data.get("password") or "").strip()
        if is_created and not password:
            raise ValueError("Пароль обязателен при создании учетной записи врача.")

        if password:
            model.hashed_password = get_password_hash(password)
