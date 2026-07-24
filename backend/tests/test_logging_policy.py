"""Regression guard: чувствительные идентификаторы не должны попадать в logger.*."""

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {
    "analysis_id",
    "client_ip",
    "contact_id",
    "deal_id",
    "lead_id",
    "patient_name",
    "provided_hash",
    "session_id",
    "token",
    "token_hint",
    "token_hash",
}
FORBIDDEN_ATTRIBUTES = {
    "analysis.id",
    "request.client.host",
    "session.id",
    "session.lead_id",
    "session.patient_name",
    "session.token_hash",
    "token_data.lead_id",
    "token_data.patient_name",
    "token_data.token_hash",
}


def _logger_calls(tree: ast.AST):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if isinstance(owner, ast.Name) and owner.id == "logger":
            yield node


def test_logger_calls_do_not_reference_sensitive_identifiers():
    violations: list[str] = []

    for path in sorted((BACKEND_ROOT / "app").rglob("*.py")) + sorted(
        (BACKEND_ROOT / "scripts").rglob("*.py")
    ):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for call in _logger_calls(tree):
            referenced_names = {
                node.id for node in ast.walk(call) if isinstance(node, ast.Name)
            }
            forbidden = sorted(referenced_names & FORBIDDEN_NAMES)
            referenced_attributes = {
                ast.unparse(node) for node in ast.walk(call) if isinstance(node, ast.Attribute)
            }
            forbidden.extend(sorted(referenced_attributes & FORBIDDEN_ATTRIBUTES))
            if forbidden:
                relative_path = path.relative_to(BACKEND_ROOT)
                violations.append(f"{relative_path}:{call.lineno}: {', '.join(forbidden)}")

    assert not violations, "Чувствительные идентификаторы используются в логах:\n" + "\n".join(
        violations
    )
