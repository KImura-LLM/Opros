# Doctor Portal Implementation Plan

This plan details the technical steps to create the protected `/doctors` portal, ensuring seamless Bitrix CRM integration without breaking existing surveys.

## Proposed Changes

### Backend: Database & Admin
#### [NEW] backend/app/models/doctor_user.py
- Define `DoctorUser` with `id`, `username`, `hashed_password`.
#### [MODIFY] backend/app/models/survey.py
- Add `doctor_name` to `SurveySession`.
#### [NEW] backend/alembic/versions/...
- Alembic migration script for the new tables and columns.
#### [NEW] backend/app/admin/doctor_view.py
- SQLAdmin `ModelView` for `DoctorUser`.
#### [MODIFY] backend/app/admin/setup.py
- Register `DoctorUser` view.

### Backend: API & Bitrix mapping
#### [NEW] backend/app/api/v1/endpoints/doctors.py
- `POST /login`
- `GET /me`
- `GET /sessions` (returns all sessions, API handles fast lookup).
#### [MODIFY] backend/app/main.py
- Include new `doctors` router.
#### [MODIFY] backend/app/api/v1/endpoints/bitrix_webhook.py (or where logic resides)
- Map funnel ID to the corresponding Bitrix user field:
  - Funnel 0: `UF_CRM_1665032105080`
  - Funnel 1: `UF_CRM_1688542532`
  - Funnel 3: `UF_CRM_1616736315899`
- Store into `SurveySession.doctor_name`.

### Frontend: UI & Logic
#### [NEW] frontend/src/store/doctorStore.ts
- Zustand store with `persist` middleware for doctor name filter and auth token.
#### [NEW] frontend/src/api/doctorApi.ts
- API calls to backend endpoints.
#### [NEW] frontend/src/pages/doctors/DoctorLogin.tsx
- Login form.
#### [NEW] frontend/src/pages/doctors/DoctorDashboard.tsx
- Table component, Date picker, input for Doctor Last Name.
- Buttons for View PDF / Download PDF.
#### [MODIFY] frontend/src/App.tsx
- Add `/doctors` protected route.

## Verification Plan

### Automated/Local Tests
- Run `alembic upgrade head` locally to ensure migrations work cleanly.
- Create mock Bitrix payload requests in `tests/test_webhook.py` or via shell to ensure `doctor_name` defaults safely.

### Manual Verification
- **Admin**: Log into `http://localhost:XX/admin` and create a test doctor account.
- **Login**: Go to `http://localhost:XX/doctors`, login.
- **Filters**: Ensure name is retained in localStorage after page reload.
- **Bitrix**: Trigger a real Bitrix deal webhook via Postman, and verify the doctor's name appears on the dashboard.
