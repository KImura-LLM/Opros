---
name: opros-bitrix-extractor
description: How to safely extract custom Bitrix24 fields (like doctor's name) based on the deal funnel ID in the Opros backend without disrupting existing webhook payloads. Use this skill whenever modifying `bitrix_webhook.py` or survey endpoints.
---

# Opros Bitrix Field Extractor

This skill guides the AI in safely extracting patient or doctor data from Bitrix24 deal/lead payloads in the Opros backend.

## Rules
1. **Never alter existing payload fields**: The webhook must continue returning all existing analytical data.
2. **Funnel-dependent mapping**: Bitrix fields (like `UF_CRM_XXX`) often depend on the funnel ID (`CATEGORY_ID`).
3. **Graceful fallbacks**: Always use `.get()` with a safe default. Never assume a field like `UF_CRM_1665032105080` is present.

## Field Map for Doctors (Example)
- Funnel `0`: `UF_CRM_1665032105080`
- Funnel `1`: `UF_CRM_1688542532`
- Funnel `3`: `UF_CRM_1616736315899`

## Implementation Pattern
```python
def extract_doctor_name(deal_data: dict, category_id: int) -> str | None:
    if category_id == 0:
        return deal_data.get('UF_CRM_1665032105080')
    elif category_id == 1:
        return deal_data.get('UF_CRM_1688542532')
    elif category_id == 3:
        return deal_data.get('UF_CRM_1616736315899')
    return None
```
