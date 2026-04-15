"""
SQLAdmin-представление для управления учетными записями врачей.
"""

from sqladmin import ModelView
from sqladmin.forms import get_model_form
from wtforms import PasswordField, SelectField

from app.core.security import get_password_hash
from app.models import DoctorUser
from app.services.doctor_portal_routing import (
    PORTAL_CLINIC_BUCKET_KEMEROVO,
    PORTAL_CLINIC_BUCKET_LABELS,
    PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
    PORTAL_CLINIC_BUCKET_YAROSLAVL,
)


DOCTOR_VISIBILITY_BUCKET_CHOICES = [
    ("", "Все доступные города"),
    (
        PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
        PORTAL_CLINIC_BUCKET_LABELS[PORTAL_CLINIC_BUCKET_NOVOSIBIRSK],
    ),
    (
        PORTAL_CLINIC_BUCKET_KEMEROVO,
        PORTAL_CLINIC_BUCKET_LABELS[PORTAL_CLINIC_BUCKET_KEMEROVO],
    ),
    (
        PORTAL_CLINIC_BUCKET_YAROSLAVL,
        PORTAL_CLINIC_BUCKET_LABELS[PORTAL_CLINIC_BUCKET_YAROSLAVL],
    ),
]


def _normalize_visibility_text(value: str | None) -> str | None:
    normalized = " ".join((value or "").split())
    return normalized or None


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
        DoctorUser.allowed_clinic_bucket,
        DoctorUser.session_doctor_name_filter,
        DoctorUser.can_view_test_tab,
        DoctorUser.created_at,
    ]
    column_details_list = [
        DoctorUser.id,
        DoctorUser.username,
        DoctorUser.is_active,
        DoctorUser.allowed_clinic_bucket,
        DoctorUser.session_doctor_name_filter,
        DoctorUser.can_view_test_tab,
        DoctorUser.created_at,
        DoctorUser.updated_at,
    ]
    column_searchable_list = [DoctorUser.username]
    column_sortable_list = [DoctorUser.id, DoctorUser.username, DoctorUser.created_at]
    column_default_sort = [("id", True)]

    form_columns = [
        DoctorUser.username,
        DoctorUser.is_active,
        DoctorUser.allowed_clinic_bucket,
        DoctorUser.session_doctor_name_filter,
        DoctorUser.can_view_test_tab,
    ]
    form_overrides = {
        DoctorUser.allowed_clinic_bucket.key: SelectField,
    }
    form_args = {
        DoctorUser.allowed_clinic_bucket.key: {
            "choices": DOCTOR_VISIBILITY_BUCKET_CHOICES,
            "coerce": str,
            "description": (
                "Параметры видимости данных. Если выбран город, врач увидит только эту воронку."
            ),
        },
        DoctorUser.session_doctor_name_filter.key: {
            "description": (
                "Параметры видимости данных. Если заполнено ФИО, врач увидит только записи "
                "с точным совпадением по полю «Врач»."
            ),
        },
    }
    form_widget_args = {
        DoctorUser.session_doctor_name_filter.key: {
            "placeholder": "Например, Иванов Иван Иванович",
        },
    }

    column_labels = {
        DoctorUser.username: "Логин",
        DoctorUser.is_active: "Активен",
        DoctorUser.allowed_clinic_bucket: "Параметры видимости данных: регион",
        DoctorUser.session_doctor_name_filter: "Параметры видимости данных: ФИО врача",
        DoctorUser.can_view_test_tab: "Доступ к тестовой вкладке",
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

        allowed_clinic_bucket = (data.get("allowed_clinic_bucket") or "").strip().lower()
        if allowed_clinic_bucket and allowed_clinic_bucket not in {
            PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
            PORTAL_CLINIC_BUCKET_KEMEROVO,
            PORTAL_CLINIC_BUCKET_YAROSLAVL,
        }:
            raise ValueError("Выбран неизвестный регион видимости данных.")

        model.allowed_clinic_bucket = allowed_clinic_bucket or None
        model.session_doctor_name_filter = _normalize_visibility_text(
            data.get("session_doctor_name_filter")
        )

        if password:
            model.hashed_password = get_password_hash(password)
