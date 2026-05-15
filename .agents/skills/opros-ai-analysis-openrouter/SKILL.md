---
name: opros-ai-analysis-openrouter
description: Safe implementation workflow for Opros AI analysis via OpenRouter. Use this whenever adding, reviewing, or modifying AI-analysis, anonymized medical survey payloads, OpenRouter calls, AI report blocks, AI worker queue, AI retry/fallback behavior, or admin retry/status for the Opros project.
---

# Opros AI Analysis OpenRouter

Use this skill for any Opros change that touches AI analysis of patient survey answers. The project handles sensitive medical and personal data, so prefer small auditable changes and preserve the existing rule-based analysis.

## Safety contract

- Keep patient completion fast: never wait for OpenRouter in the patient-facing `/survey/complete` response.
- Send only allowlisted, anonymized clinical survey data to OpenRouter.
- Do not send names, `SurveySession.id`, `lead_id`, CRM IDs, token/hash, IP, user-agent, survey links, or raw CRM data.
- Use a random `analysis_case_id` as the only external case identifier.
- Do not log API keys, full prompts, outbound payloads, raw AI responses, names, or CRM identifiers.
- Treat OpenRouter as optional: if disabled or failed after retries, generate and send the normal report without an AI block.
- Keep the existing rule-based “Системный анализ для врача” independent and below the AI block.

## Implementation checklist

1. Add/verify settings: `AI_ANALYSIS_ENABLED`, `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, timeout, max attempts, prompt version, and feature flags.
2. Store AI job/result in `survey_ai_analyses` with one current job per survey session.
3. Queue jobs idempotently after completion. If AI is disabled, still ensure normal report processing continues.
4. Build OpenRouter payload only through an anonymizer allowlist that uses answered nodes from the survey config.
5. Validate AI output with Pydantic before storing or rendering it.
6. Render AI output using HTML escaping for every AI-provided string.
7. Save `report_snapshot.ai_analysis` metadata showing inclusion status, model, prompt version, analysis id, and priority where applicable.
8. Add admin visibility for status/model/attempts/priority/safe error and a controlled retry action for failed jobs.
9. Add tests for privacy, OpenRouter errors, report ordering/escaping, and completion idempotency.

## Verification defaults

- Unit tests: anonymizer, OpenRouter client, report generator, and affected survey flow tests.
- Local behavior: completion returns quickly; failed/disabled AI still creates a normal report; successful AI appears above system analysis in HTML/TXT/PDF.
- Security: inspect payload/log paths for forbidden identifiers before production rollout.
