docker compose up -d postgres redis backend frontend
docker compose exec -T -w /app backend python -m unittest discover -s tests -q
Set-Location frontend
npm run type-check
npm run lint
