import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.services.bitrix24 import Bitrix24Client
from app.services.doctor_portal_routing import (
    PORTAL_CLINIC_BUCKET_KEMEROVO,
    PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
    PORTAL_CLINIC_BUCKET_TEST,
    PORTAL_CLINIC_BUCKET_YAROSLAVL,
    resolve_portal_clinic_bucket,
)


class DoctorPortalRoutingTests(unittest.TestCase):
    def test_routes_category_0_to_novosibirsk(self) -> None:
        self.assertEqual(resolve_portal_clinic_bucket("0"), PORTAL_CLINIC_BUCKET_NOVOSIBIRSK)

    def test_routes_category_1_to_kemerovo(self) -> None:
        self.assertEqual(resolve_portal_clinic_bucket("1"), PORTAL_CLINIC_BUCKET_KEMEROVO)

    def test_routes_category_3_to_yaroslavl(self) -> None:
        self.assertEqual(resolve_portal_clinic_bucket("3"), PORTAL_CLINIC_BUCKET_YAROSLAVL)

    def test_routes_unknown_category_to_test(self) -> None:
        self.assertEqual(resolve_portal_clinic_bucket("19"), PORTAL_CLINIC_BUCKET_TEST)

    def test_routes_missing_category_to_test(self) -> None:
        self.assertEqual(resolve_portal_clinic_bucket(None), PORTAL_CLINIC_BUCKET_TEST)

    def test_extracts_routing_from_deal(self) -> None:
        category_id, clinic_bucket = Bitrix24Client.extract_portal_routing_from_deal(
            {"CATEGORY_ID": "1"}
        )

        self.assertEqual(category_id, 1)
        self.assertEqual(clinic_bucket, PORTAL_CLINIC_BUCKET_KEMEROVO)


class DoctorPortalBitrixMappingTests(unittest.TestCase):
    def test_extracts_appointment_datetime_from_deal(self) -> None:
        deal_data = {
            "UF_CRM_1665031646808": "31.03.2026 14:30",
        }

        appointment_at = Bitrix24Client.extract_appointment_datetime_from_deal(deal_data)

        self.assertEqual(appointment_at, "31.03.2026 14:30")

    def test_returns_none_for_empty_appointment_datetime(self) -> None:
        deal_data = {
            "UF_CRM_1665031646808": "   ",
        }

        appointment_at = Bitrix24Client.extract_appointment_datetime_from_deal(deal_data)

        self.assertIsNone(appointment_at)

    def test_extracts_doctor_name_for_funnel_0(self) -> None:
        deal_data = {
            "CATEGORY_ID": "0",
            "UF_CRM_1665032105080": "Иванов Иван Иванович",
        }

        doctor_name = Bitrix24Client.extract_doctor_name_from_deal(deal_data)

        self.assertEqual(doctor_name, "Иванов Иван Иванович")

    def test_extracts_doctor_name_for_funnel_1(self) -> None:
        deal_data = {
            "CATEGORY_ID": "1",
            "UF_CRM_1688542532": "Петров Петр Петрович",
        }

        doctor_name = Bitrix24Client.extract_doctor_name_from_deal(deal_data)

        self.assertEqual(doctor_name, "Петров Петр Петрович")

    def test_extracts_doctor_name_for_funnel_3(self) -> None:
        deal_data = {
            "CATEGORY_ID": "3",
            "UF_CRM_1616736315899": "Сидорова Анна Викторовна",
        }

        doctor_name = Bitrix24Client.extract_doctor_name_from_deal(deal_data)

        self.assertEqual(doctor_name, "Сидорова Анна Викторовна")

    def test_extracts_doctor_name_for_test_funnel_19_from_first_supported_field(self) -> None:
        deal_data = {
            "CATEGORY_ID": "19",
            "UF_CRM_1665032105080": "Иванов Иван Иванович",
        }

        doctor_name = Bitrix24Client.extract_doctor_name_from_deal(deal_data)

        self.assertEqual(doctor_name, "Иванов Иван Иванович")

    def test_extracts_doctor_name_for_test_funnel_19_from_second_supported_field(self) -> None:
        deal_data = {
            "CATEGORY_ID": "19",
            "UF_CRM_1688542532": "Петров Петр Петрович",
        }

        doctor_name = Bitrix24Client.extract_doctor_name_from_deal(deal_data)

        self.assertEqual(doctor_name, "Петров Петр Петрович")

    def test_extracts_doctor_name_for_test_funnel_19_from_third_supported_field(self) -> None:
        deal_data = {
            "CATEGORY_ID": "19",
            "UF_CRM_1616736315899": "Сидорова Анна Викторовна",
        }

        doctor_name = Bitrix24Client.extract_doctor_name_from_deal(deal_data)

        self.assertEqual(doctor_name, "Сидорова Анна Викторовна")

    def test_returns_none_for_unknown_funnel(self) -> None:
        deal_data = {
            "CATEGORY_ID": "7",
            "UF_CRM_1665032105080": "Не должно использоваться",
        }

        doctor_name = Bitrix24Client.extract_doctor_name_from_deal(deal_data)

        self.assertIsNone(doctor_name)

    def test_returns_none_when_expected_field_is_missing(self) -> None:
        deal_data = {
            "CATEGORY_ID": "0",
        }

        doctor_name = Bitrix24Client.extract_doctor_name_from_deal(deal_data)

        self.assertIsNone(doctor_name)

    def test_trims_whitespace_and_ignores_empty_value(self) -> None:
        deal_data = {
            "CATEGORY_ID": "1",
            "UF_CRM_1688542532": "   ",
        }

        doctor_name = Bitrix24Client.extract_doctor_name_from_deal(deal_data)

        self.assertIsNone(doctor_name)

    def test_extracts_first_value_from_list_field(self) -> None:
        deal_data = {
            "CATEGORY_ID": "19",
            "UF_CRM_1688542532": ["", "Иванов Иван Иванович"],
        }

        doctor_name = Bitrix24Client.extract_doctor_name_from_deal(deal_data)

        self.assertEqual(doctor_name, "Иванов Иван Иванович")

    def test_extracts_value_from_dict_field(self) -> None:
        deal_data = {
            "CATEGORY_ID": "19",
            "UF_CRM_1616736315899": {"VALUE": "Петров Петр Петрович"},
        }

        doctor_name = Bitrix24Client.extract_doctor_name_from_deal(deal_data)

        self.assertEqual(doctor_name, "Петров Петр Петрович")

    def test_resolves_bitrix_user_id_to_full_name(self) -> None:
        client = Bitrix24Client("https://example.invalid/rest")
        client.get_deal = AsyncMock(return_value={
            "CATEGORY_ID": "19",
            "UF_CRM_1665032105080": 3959,
        })
        client.get_deal_field_definition = AsyncMock(return_value=None)
        client.get_user = AsyncMock(return_value={
            "LAST_NAME": "Иванов",
            "NAME": "Иван",
            "SECOND_NAME": "Иванович",
        })

        doctor_name = self._run_async(client.get_doctor_name_from_deal(123))

        self.assertEqual(doctor_name, "Иванов Иван Иванович")

    def test_keeps_text_doctor_name_without_user_lookup(self) -> None:
        client = Bitrix24Client("https://example.invalid/rest")
        client.get_deal = AsyncMock(return_value={
            "CATEGORY_ID": "19",
            "UF_CRM_1688542532": "Сидорова Анна Викторовна",
        })
        client.get_user = AsyncMock()

        doctor_name = self._run_async(client.get_doctor_name_from_deal(123))

        self.assertEqual(doctor_name, "Сидорова Анна Викторовна")
        client.get_user.assert_not_called()

    def test_falls_back_to_raw_value_when_user_lookup_returns_nothing(self) -> None:
        client = Bitrix24Client("https://example.invalid/rest")
        client.get_deal = AsyncMock(return_value={
            "CATEGORY_ID": "19",
            "UF_CRM_1665032105080": "3959",
        })
        client.get_deal_field_definition = AsyncMock(return_value=None)
        client.get_user = AsyncMock(return_value=None)

        doctor_name = self._run_async(client.get_doctor_name_from_deal(123))

        self.assertEqual(doctor_name, "3959")

    def test_resolves_enumeration_doctor_id_to_label(self) -> None:
        client = Bitrix24Client("https://example.invalid/rest")
        client.get_deal = AsyncMock(return_value={
            "CATEGORY_ID": "19",
            "UF_CRM_1616736315899": "3959",
        })
        client.get_deal_field_definition = AsyncMock(return_value={
            "type": "enumeration",
            "items": [
                {"ID": "3959", "VALUE": "Авдеева Надежда Алексеевна"},
            ],
        })
        client.get_user = AsyncMock(return_value=None)

        doctor_name = self._run_async(client.get_doctor_name_from_deal(123))

        self.assertEqual(doctor_name, "Авдеева Надежда Алексеевна")
        client.get_user.assert_not_called()

    @staticmethod
    def _run_async(awaitable):
        import asyncio

        return asyncio.run(awaitable)


if __name__ == "__main__":
    unittest.main()
