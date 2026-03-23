import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.services.bitrix24 import Bitrix24Client


class DoctorPortalBitrixMappingTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
