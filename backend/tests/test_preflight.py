from app.core.preflight import check_production_environment


def valid_environment() -> dict[str, str]:
    return {
        "ENVIRONMENT": "production",
        "DEBUG": "false",
        "SECRET_KEY": "s" * 32,
        "JWT_SECRET_KEY": "j" * 32,
        "JWT_ALGORITHM": "HS256",
        "ADMIN_USERNAME": "clinic-operator",
        "ADMIN_PASSWORD": "a" * 16,
        "POSTGRES_PASSWORD": "p" * 16,
        "REDIS_PASSWORD": "r" * 16,
        "BITRIX24_INCOMING_TOKEN": "b" * 24,
        "FRONTEND_URL": "https://survey.example.ru",
        "CORS_ORIGINS_STR": "https://survey.example.ru",
        "AI_ANALYSIS_ENABLED": "false",
        "BITRIX24_WEBHOOK_URL": "https://example.bitrix24.ru/rest/redacted",
    }


def test_valid_production_environment_passes():
    result = check_production_environment(valid_environment())

    assert result.ok
    assert result.errors == ()


def test_insecure_defaults_and_http_origin_are_rejected():
    env = valid_environment()
    env.update(
        {
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "admin",
            "REDIS_PASSWORD": "",
            "FRONTEND_URL": "http://localhost:5173",
            "CORS_ORIGINS_STR": "*",
        }
    )

    result = check_production_environment(env)

    assert not result.ok
    assert any("ADMIN_USERNAME" in error for error in result.errors)
    assert any("REDIS_PASSWORD" in error for error in result.errors)
    assert any("FRONTEND_URL" in error for error in result.errors)
    assert any("CORS_ORIGINS_STR" in error for error in result.errors)


def test_ai_requires_key_and_warns_when_zdr_is_disabled():
    env = valid_environment()
    env.update(
        {
            "AI_ANALYSIS_ENABLED": "true",
            "OPENROUTER_API_KEY": "",
            "AI_ANALYSIS_ZDR_REQUIRED": "false",
        }
    )

    result = check_production_environment(env)

    assert any("OPENROUTER_API_KEY" in error for error in result.errors)
    assert any("ZDR" in warning for warning in result.warnings)
