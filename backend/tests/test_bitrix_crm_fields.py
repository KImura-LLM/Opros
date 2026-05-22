import sys
import unittest
from unittest.mock import patch
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.services.bitrix24 import Bitrix24Client
from app.services.bitrix_crm_fields import crm_field_title


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeAsyncClient:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = [FakeResponse(response) for response in responses]
        self.requests: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _tb) -> None:
        return None

    async def post(self, url: str, json: dict):
        self.requests.append(json)
        return self.responses.pop(0)


class BitrixCrmFieldTitleTests(unittest.TestCase):
    def test_uses_user_field_label_when_bitrix_title_is_technical_id(self) -> None:
        title = crm_field_title(
            "UF_CRM_1582887280105",
            {
                "title": "UF_CRM_1582887280105",
                "EDIT_FORM_LABEL": "Источник обращения",
            },
        )

        self.assertEqual(title, "Источник обращения")

    def test_uses_nested_russian_label(self) -> None:
        title = crm_field_title(
            "UF_CRM_1582887280105",
            {
                "title": "UF_CRM_1582887280105",
                "LIST_COLUMN_LABEL": {"ru": "Клиника"},
            },
        )

        self.assertEqual(title, "Клиника")

    def test_keeps_standard_nontechnical_title(self) -> None:
        title = crm_field_title("TITLE", {"title": "Название сделки"})

        self.assertEqual(title, "Название сделки")

    def test_falls_back_to_field_id_when_only_technical_values_exist(self) -> None:
        title = crm_field_title("UF_CRM_1582887280105", {"title": "UF_CRM_1582887280105"})

        self.assertEqual(title, "UF_CRM_1582887280105")


class Bitrix24UserFieldListTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_deal_user_fields_reads_all_bitrix_pages(self) -> None:
        fake_client = FakeAsyncClient(
            [
                {"result": [{"FIELD_NAME": "UF_CRM_1"}], "next": 50},
                {"result": [{"FIELD_NAME": "UF_CRM_2"}]},
            ]
        )

        with patch("app.services.bitrix24.httpx.AsyncClient", return_value=fake_client):
            fields = await Bitrix24Client("https://example.test/rest/1/token").get_deal_user_fields()

        self.assertEqual(fields, [{"FIELD_NAME": "UF_CRM_1"}, {"FIELD_NAME": "UF_CRM_2"}])
        self.assertEqual(fake_client.requests, [{}, {"start": 50}])


if __name__ == "__main__":
    unittest.main()
