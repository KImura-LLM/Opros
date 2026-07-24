---
applyTo: '**'
---

# Opros repository instructions

Главные правила находятся в `AGENTS.md`; подробная архитектура — в
`docs/PROJECT_WIKI.md`. Не дублируйте их здесь.

- Медицинская логика остаётся JSON-driven.
- Не хранить данные пациента в localStorage и не логировать ПДн/идентификаторы.
- Перед изменениями проверить `git status`, после — выполнить
  `scripts/run_local_checks.ps1`.
- Для UI/E2E использовать Playwright и проверять console/network.
- Production настраивается по `docs/INSTALLATION.md`, эксплуатируется по
  `docs/OPERATIONS.md`.
