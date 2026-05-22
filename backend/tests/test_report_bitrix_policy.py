import unittest

from app.services.ai_analysis.service import _has_bitrix_report_upload_attempt


class ReportBitrixUploadPolicyTests(unittest.TestCase):
    def test_no_snapshot_allows_initial_upload_attempt(self) -> None:
        self.assertFalse(_has_bitrix_report_upload_attempt(None))

    def test_manual_snapshot_without_upload_marker_does_not_block_initial_upload(self) -> None:
        snapshot = {
            "regenerated": True,
            "bitrix_report": {
                "upload_attempted": False,
                "skipped_reason": "manual_report_regeneration",
            },
        }

        self.assertFalse(_has_bitrix_report_upload_attempt(snapshot))

    def test_old_snapshot_without_metadata_is_treated_as_already_finalized(self) -> None:
        self.assertTrue(_has_bitrix_report_upload_attempt({"regenerated": False}))


if __name__ == "__main__":
    unittest.main()
