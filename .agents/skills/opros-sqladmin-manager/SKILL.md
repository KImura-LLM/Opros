---
name: opros-sqladmin-manager
description: How to safely create and register new SQLAdmin views in the Opros project. Use this whenever asked to add a new admin panel tab or model CRUD.
---

# Opros SQLAdmin Manager

This skill guides the AI in creating new `ModelView` classes for SQLAdmin in the Opros backend.

## Rules
1. **Location**: Place the view in `backend/app/admin/`.
2. **Naming**: Name the file `[model_name]_view.py` and the class `[ModelName]Admin(ModelView, model=[ModelName])`.
3. **Registration**: Always register the new view in `backend/app/admin/setup.py` or wherever the admin app is initialized.
4. **Icons**: Use FontAwesome icons (`icon = "fa-solid fa-user-doctor"`).
5. **Column formats**: Specify `column_list`, `column_searchable_list`, and `column_default_sort`.

## Implementation Pattern
```python
from sqladmin import ModelView
from app.models.doctor_user import DoctorUser

class DoctorUserAdmin(ModelView, model=DoctorUser):
    column_list = [DoctorUser.id, DoctorUser.username]
    column_searchable_list = [DoctorUser.username]
    name = "Настройка врачей"
    name_plural = "Настройки врачей"
    icon = "fa-solid fa-user-doctor"
```
