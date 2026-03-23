# Doctor Portal Development Tasks

## 1. Environment & Skills
- [x] Draft skill `opros-bitrix-extractor`
- [x] Draft skill `opros-sqladmin-manager`
- [x] Review and test skills with user (Approved, skipped tests)

## 2. Database & Models
- [x] Define `DoctorUser` model in SQLAlchemy (`backend/app/models/doctor_user.py`)
- [x] Add `doctor_name` column to `SurveySession` model
- [x] Generate and apply Alembic migrations

## 3. Admin Panel Integration
- [x] Create SQLAdmin view for `DoctorUser` for CRUD operations
- [x] Register the view in the main admin setup

## 4. Backend Authentication & API
- [x] Implement doctor login endpoint (`POST /api/v1/doctors/login`) returning JWT
- [x] Implement current doctor endpoint (`GET /api/v1/doctors/me`)
- [x] Implement session list endpoint (`GET /api/v1/doctors/sessions`) with filtering support

## 5. Bitrix Integration
- [x] Update webhook handler (`bitrix_webhook.py`) to map correct Bitrix funnels (0, 1, 3) to the `doctor_name` field in `SurveySession`

## 6. Frontend: Setup & State
- [x] Add `useDoctorStore.ts` (Zustand) for auth and filter state preservation
- [x] Add frontend routing for `/doctors` layout and subpages
- [x] Create `doctorApi.ts` client layer

## 7. Frontend: UI Components
- [x] Build Doctor Login Page
- [x] Build Doctor Dashboard (table view)
- [x] Implement Table Filters (Doctor name, Date range)
- [x] Connect PDF View/Download buttons

## 8. Verification & Deployment
- [x] Test Bitrix payload extraction logic locally with mock payloads
- [x] Test frontend sorting, filtering, and state persistence
- [ ] Deploy to production using Git & non-interactive SSH
- [ ] Verify functionality on live server
