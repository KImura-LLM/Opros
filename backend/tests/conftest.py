"""Shared pytest environment for local and container test runs."""

from pathlib import Path
import os


IN_CONTAINER = Path("/.dockerenv").exists()

# Tests must not depend on production-like values from a developer .env file.
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"
os.environ["ADMIN_USERNAME"] = "test-admin"
os.environ["ADMIN_PASSWORD"] = "test-admin-password"

# Keep tests runnable both from the host and from the backend Docker container.
if not os.environ.get("POSTGRES_HOST"):
    os.environ["POSTGRES_HOST"] = "postgres" if IN_CONTAINER else "localhost"
if not os.environ.get("REDIS_HOST"):
    os.environ["REDIS_HOST"] = "redis" if IN_CONTAINER else "localhost"
