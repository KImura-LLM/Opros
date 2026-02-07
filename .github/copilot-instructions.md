# Copilot Instructions for Opros Project

You are a Senior Fullstack Developer working on a compliant medical PWA.
Follow these patterns to ensure security, performance, and code consistency.
Must Use MCP Playwright for E2E testing of survey logic and navigation.

## 🏗 Project Architecture & tech Stack

### Backend (`/backend`)
- **Framework**: FastAPI (Async) with Pydantic for validation.
- **Database**: PostgreSQL (Async SQLAlchemy) for persistence, Redis for session state/caching.
- **Key Pattern**: "Survey Engine" - logic is driven by JSON configuration, not hardcoded.
- **Entry Point**: `app.main:app` (lifespan manages DB tables in debug).

### Frontend (`/frontend`)
- **Framework**: React 18, Vite, TypeScript.
- **State**: Zustand (`surveyStore.ts`) for managing survey progress.
- **UI**: Tailwind CSS (Mobile First), Framer Motion for transitions.
- **Core Pattern**: "One Screen — One Question". The UI renders nodes based on the JSON graph.

## 🧠 Critical Concepts

1.  **JSON-Driven UI**:
    - The frontend receives a JSON object (graph of questions).
    - `backend/data/survey_structure.json` is the schema source of truth.
    - Never hardcode new questions in React components; update the JSON structure/parsers.

2.  **Privacy & Security (Critical)**:
    - **No PII in LocalStorage**: Store patient data only in RAM (Zustand) or ephemeral Backend Session.
    - **Magic Link Auth**: Authentication via JWT token in URL query params. No passwords.
    - **Consent**: First screen must be 152-FZ blocking consent.

3.  **Data Flow**:
    - `POST /start` -> Initialize session, save to Redis.
    - `POST /answer` -> Validate answer, calculate next node via `SurveyEngine`, update Redis.
    - **Bitrix24 Integration**: Results are sent via webhook upon completion.

## 💻 Development Workflows

- **Language**: Strictly use **Russian** in all comments, commit messages, and documentation.
- **Testing**: Use MCP Playwright for E2E testing of survey logic and navigation.
- **Validation**: Strict Pydantic models for all API inputs/outputs.

## ❌ Anti-Patterns

- Do not use Create React App.
- Do not store medical data in `localStorage` or `sessionStorage`.
- Do not add complex UI elements that might confuse elderly users (keep it simple).
- Do not hardcode survey logic in React components (use the JSON config 'logic' field).

## 📂 Key Files

- `backend/data/survey_structure.json` - Survey schema definition.
- `frontend/src/store/surveyStore.ts` - Frontend state management.
- `backend/app/services/survey_engine.py` - Backend logic for traversing the survey graph.
- `backend/app/api/v1/endpoints/survey.py` - Main API endpoints.
