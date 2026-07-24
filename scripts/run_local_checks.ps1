$ErrorActionPreference = "Stop"

docker compose up -d --build postgres redis backend frontend
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose exec -T -w /app backend sh -lc "PYTHONPATH=/app alembic -c alembic.ini upgrade head"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose exec -T -w /app backend python -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Push-Location frontend
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    npm run type-check
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    npm run lint
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    npm run build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    npm audit --omit=dev --audit-level=high
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}

docker compose --env-file .env -f docker-compose.prod.yml config -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
