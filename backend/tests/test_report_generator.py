import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.services.report_generator import ReportGenerator


class ReportGeneratorFormattingTests(unittest.TestCase):
    def test_formats_body_locations_from_shared_mapping(self) -> None:
        generator = ReportGenerator({"nodes": []})

        self.assertEqual(
            generator._format_body_locations(["head", "unknown_location"]),
            "Голова, unknown_location",
        )

    def test_pain_location_mapping_is_consistent_across_report_formats(self) -> None:
        generator = ReportGenerator({"nodes": []})
        answers = {"pain_details": {"locations": ["head"], "intensity": 7}}

        html = generator._generate_pain_details(answers)
        readable = generator._generate_readable_pain_details(answers)
        text = generator._generate_text_pain_details(answers)

        self.assertIn("Голова", html)
        self.assertIn("Голова", readable)
        self.assertIn("Голова", text)


if __name__ == "__main__":
    unittest.main()
