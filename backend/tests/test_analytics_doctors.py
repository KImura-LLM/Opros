import unittest
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete

from app.api.v1.endpoints.analytics import get_dashboard_stats
from app.api.v1.endpoints.doctors import _get_session_for_doctor, doctor_sessions
from app.core.database import async_session_maker, engine
from app.models import DoctorUser, SurveyAnswer, SurveyConfig, SurveySession
from app.services.doctor_portal_routing import PORTAL_CLINIC_BUCKET_NOVOSIBIRSK


class AnalyticsAndDoctorsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.created_config_ids: list[int] = []
        self.created_session_ids = []
        self.created_doctor_ids: list[int] = []

    async def asyncTearDown(self) -> None:
        async with async_session_maker() as db:
            if self.created_session_ids:
                await db.execute(delete(SurveyAnswer).where(SurveyAnswer.session_id.in_(self.created_session_ids)))
                await db.execute(delete(SurveySession).where(SurveySession.id.in_(self.created_session_ids)))
            if self.created_config_ids:
                await db.execute(delete(SurveyConfig).where(SurveyConfig.id.in_(self.created_config_ids)))
            if self.created_doctor_ids:
                await db.execute(delete(DoctorUser).where(DoctorUser.id.in_(self.created_doctor_ids)))
            await db.commit()
        await engine.dispose()

    async def test_dashboard_uses_selected_period_and_locations_for_body_map(self) -> None:
        now = datetime(2099, 1, 15, 12, 0, tzinfo=UTC)

        async with async_session_maker() as db:
            config = SurveyConfig(
                name="Analytics test config",
                description="analytics-test",
                version="test",
                is_active=False,
                json_config={
                    "start_node": "pain_map",
                    "nodes": [
                        {
                            "id": "pain_map",
                            "type": "body_map",
                            "question_text": "Где болит?",
                            "required": True,
                        },
                        {
                            "id": "chief_complaint",
                            "type": "single_choice",
                            "question_text": "Главная жалоба",
                            "required": True,
                            "options": [
                                {"value": "pain", "text": "Боль"},
                                {"value": "swelling", "text": "Отек"},
                            ],
                        },
                    ],
                },
            )
            db.add(config)
            await db.flush()
            self.created_config_ids.append(config.id)

            completed_recent = SurveySession(
                lead_id=910001,
                entity_type="DEAL",
                patient_name="Пациент А",
                doctor_name="Доктор А",
                survey_config_id=config.id,
                token_hash="analytics-test-910001",
                status="completed",
                consent_given=True,
                portal_clinic_bucket="test",
                started_at=now - timedelta(minutes=10),
                completed_at=now,
            )
            completed_old = SurveySession(
                lead_id=910002,
                entity_type="DEAL",
                patient_name="Пациент Б",
                doctor_name="Доктор Б",
                survey_config_id=config.id,
                token_hash="analytics-test-910002",
                status="completed",
                consent_given=True,
                portal_clinic_bucket="test",
                started_at=now - timedelta(days=12, minutes=8),
                completed_at=now - timedelta(days=12),
            )
            in_progress_recent = SurveySession(
                lead_id=910003,
                entity_type="DEAL",
                patient_name="Пациент В",
                doctor_name="Доктор В",
                survey_config_id=config.id,
                token_hash="analytics-test-910003",
                status="in_progress",
                consent_given=True,
                portal_clinic_bucket="test",
                started_at=now - timedelta(minutes=5),
            )
            db.add_all([completed_recent, completed_old, in_progress_recent])
            await db.flush()

            self.created_session_ids.extend(
                [completed_recent.id, completed_old.id, in_progress_recent.id]
            )

            db.add_all(
                [
                    SurveyAnswer(
                        session_id=completed_recent.id,
                        node_id="pain_map",
                        answer_data={"locations": ["left_leg"], "intensity": 7},
                        duration_seconds=30,
                    ),
                    SurveyAnswer(
                        session_id=completed_recent.id,
                        node_id="chief_complaint",
                        answer_data={"selected": "pain"},
                        duration_seconds=90,
                    ),
                    SurveyAnswer(
                        session_id=completed_old.id,
                        node_id="pain_map",
                        answer_data={"locations": ["old_location"], "intensity": 3},
                        duration_seconds=180,
                    ),
                    SurveyAnswer(
                        session_id=completed_old.id,
                        node_id="chief_complaint",
                        answer_data={"selected": "swelling"},
                        duration_seconds=120,
                    ),
                ]
            )
            await db.commit()

            date_str = now.date().isoformat()
            stats = await get_dashboard_stats(
                date_from=date_str,
                date_to=date_str,
                db=db,
                _admin=True,
            )

        self.assertEqual(stats["chart"]["total"], 1)
        self.assertEqual(stats["statuses"].get("completed"), 1)
        self.assertEqual(stats["statuses"].get("in_progress"), 1)
        self.assertAlmostEqual(stats["chart"]["avg_minutes"], 10.0, places=1)

        top_answer_labels = [item["label"] for item in stats["top_answers"]]
        self.assertIn("Где болит? → left_leg", top_answer_labels)
        self.assertNotIn("Где болит? → old_location", top_answer_labels)

        answer_time_labels = [item["label"] for item in stats["answer_times"]]
        self.assertIn("Главная жалоба", answer_time_labels)

    async def test_dashboard_without_dates_uses_all_sessions(self) -> None:
        now = datetime(2099, 3, 20, 12, 0, tzinfo=UTC)

        async with async_session_maker() as db:
            config = SurveyConfig(
                name="Analytics all-time test config",
                description="analytics-all-time-test",
                version="test",
                is_active=False,
                json_config={
                    "start_node": "chief_complaint",
                    "nodes": [
                        {
                            "id": "chief_complaint",
                            "type": "single_choice",
                            "question_text": "Жалоба",
                            "required": True,
                            "options": [{"value": "pain", "text": "Боль"}],
                        },
                    ],
                },
            )
            db.add(config)
            await db.flush()
            self.created_config_ids.append(config.id)

            completed_recent = SurveySession(
                lead_id=911001,
                entity_type="DEAL",
                patient_name="Пациент свежий",
                doctor_name="Доктор",
                survey_config_id=config.id,
                token_hash="analytics-all-time-911001",
                status="completed",
                consent_given=True,
                portal_clinic_bucket="test",
                started_at=now - timedelta(minutes=10),
                completed_at=now,
            )
            completed_old = SurveySession(
                lead_id=911002,
                entity_type="DEAL",
                patient_name="Пациент старый",
                doctor_name="Доктор",
                survey_config_id=config.id,
                token_hash="analytics-all-time-911002",
                status="completed",
                consent_given=True,
                portal_clinic_bucket="test",
                started_at=now - timedelta(days=60, minutes=10),
                completed_at=now - timedelta(days=60),
            )
            db.add_all([completed_recent, completed_old])
            await db.flush()
            self.created_session_ids.extend([completed_recent.id, completed_old.id])

            db.add_all(
                [
                    SurveyAnswer(
                        session_id=completed_recent.id,
                        node_id="chief_complaint",
                        answer_data={"selected": "pain"},
                        duration_seconds=10,
                    ),
                    SurveyAnswer(
                        session_id=completed_old.id,
                        node_id="chief_complaint",
                        answer_data={"selected": "pain"},
                        duration_seconds=20,
                    ),
                ]
            )
            await db.commit()

            stats = await get_dashboard_stats(
                date_from=None,
                date_to=None,
                db=db,
                _admin=True,
            )

        self.assertGreaterEqual(stats["chart"]["total"], 2)
        self.assertIn("20.03", stats["chart"]["labels"])
        self.assertIn("19.01", stats["chart"]["labels"])

    async def test_doctor_sessions_use_saved_bucket_data_without_extra_enrichment(self) -> None:
        now = datetime(2099, 2, 20, 12, 0, tzinfo=UTC)

        async with async_session_maker() as db:
            config = SurveyConfig(
                name="Doctor portal test config",
                description="doctor-test",
                version="test",
                is_active=False,
                json_config={"start_node": "welcome", "nodes": []},
            )
            doctor = DoctorUser(
                username="doctor_test_user",
                hashed_password="hashed",
                is_active=True,
                can_view_test_tab=True,
            )
            db.add_all([config, doctor])
            await db.flush()

            self.created_config_ids.append(config.id)
            self.created_doctor_ids.append(doctor.id)

            explicit_bucket = SurveySession(
                lead_id=920001,
                entity_type="DEAL",
                patient_name="Пациент 1",
                doctor_name="Доктор тестовый",
                survey_config_id=config.id,
                token_hash="doctor-test-920001",
                status="completed",
                consent_given=True,
                portal_clinic_bucket=PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
                started_at=now - timedelta(minutes=20),
                completed_at=now - timedelta(minutes=5),
            )
            fallback_bucket = SurveySession(
                lead_id=920002,
                entity_type="DEAL",
                patient_name="Пациент 2",
                doctor_name="Доктор тестовый",
                survey_config_id=config.id,
                token_hash="doctor-test-920002",
                status="completed",
                consent_given=True,
                portal_clinic_bucket="",
                bitrix_category_id=0,
                started_at=now - timedelta(minutes=30),
                completed_at=now - timedelta(minutes=15),
            )
            other_bucket = SurveySession(
                lead_id=920003,
                entity_type="DEAL",
                patient_name="Пациент 3",
                doctor_name="Доктор другой",
                survey_config_id=config.id,
                token_hash="doctor-test-920003",
                status="completed",
                consent_given=True,
                portal_clinic_bucket="test",
                started_at=now - timedelta(minutes=25),
                completed_at=now - timedelta(minutes=10),
            )
            db.add_all([explicit_bucket, fallback_bucket, other_bucket])
            await db.commit()

            self.created_session_ids.extend(
                [explicit_bucket.id, fallback_bucket.id, other_bucket.id]
            )

            response = await doctor_sessions(
                clinic_bucket=PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
                doctor_name="тестовый",
                date_from=now.date(),
                date_to=now.date(),
                db=db,
                doctor=doctor,
            )

        self.assertEqual(response.total, 2)
        self.assertEqual(
            {item.patient_name for item in response.items},
            {"Пациент 1", "Пациент 2"},
        )
        for item in response.items:
            self.assertIn(f"/api/v1/doctors/sessions/{item.session_id}/share/pdf", item.share_url)

    async def test_doctor_sessions_apply_strict_visibility_settings(self) -> None:
        now = datetime(2099, 2, 21, 12, 0, tzinfo=UTC)

        async with async_session_maker() as db:
            config = SurveyConfig(
                name="Doctor strict visibility config",
                description="doctor-strict-visibility",
                version="test",
                is_active=False,
                json_config={"start_node": "welcome", "nodes": []},
            )
            doctor = DoctorUser(
                username="doctor_visibility_user",
                hashed_password="hashed",
                is_active=True,
                allowed_clinic_bucket=PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
                session_doctor_name_filter="Иванов Иван Иванович",
                can_view_test_tab=True,
            )
            db.add_all([config, doctor])
            await db.flush()

            self.created_config_ids.append(config.id)
            self.created_doctor_ids.append(doctor.id)

            matching_session = SurveySession(
                lead_id=930001,
                entity_type="DEAL",
                patient_name="Пациент видимый",
                doctor_name="Иванов Иван Иванович",
                survey_config_id=config.id,
                token_hash="doctor-visibility-930001",
                status="completed",
                consent_given=True,
                portal_clinic_bucket=PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
                started_at=now - timedelta(minutes=30),
                completed_at=now - timedelta(minutes=10),
            )
            normalized_spacing_session = SurveySession(
                lead_id=930002,
                entity_type="DEAL",
                patient_name="Пациент с пробелами",
                doctor_name="  Иванов   Иван   Иванович  ",
                survey_config_id=config.id,
                token_hash="doctor-visibility-930002",
                status="completed",
                consent_given=True,
                portal_clinic_bucket="",
                bitrix_category_id=0,
                started_at=now - timedelta(minutes=25),
                completed_at=now - timedelta(minutes=5),
            )
            other_doctor_session = SurveySession(
                lead_id=930003,
                entity_type="DEAL",
                patient_name="Пациент чужой врач",
                doctor_name="Петров Петр Петрович",
                survey_config_id=config.id,
                token_hash="doctor-visibility-930003",
                status="completed",
                consent_given=True,
                portal_clinic_bucket=PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
                started_at=now - timedelta(minutes=20),
                completed_at=now - timedelta(minutes=3),
            )
            other_bucket_session = SurveySession(
                lead_id=930004,
                entity_type="DEAL",
                patient_name="Пациент чужой город",
                doctor_name="Иванов Иван Иванович",
                survey_config_id=config.id,
                token_hash="doctor-visibility-930004",
                status="completed",
                consent_given=True,
                portal_clinic_bucket="kemerovo",
                started_at=now - timedelta(minutes=22),
                completed_at=now - timedelta(minutes=4),
            )
            db.add_all(
                [
                    matching_session,
                    normalized_spacing_session,
                    other_doctor_session,
                    other_bucket_session,
                ]
            )
            await db.commit()

            self.created_session_ids.extend(
                [
                    matching_session.id,
                    normalized_spacing_session.id,
                    other_doctor_session.id,
                    other_bucket_session.id,
                ]
            )

            response = await doctor_sessions(
                clinic_bucket=PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
                doctor_name="Петров",
                date_from=now.date(),
                date_to=now.date(),
                db=db,
                doctor=doctor,
            )

        self.assertEqual(response.total, 2)
        self.assertEqual(
            {item.patient_name for item in response.items},
            {"Пациент видимый", "Пациент с пробелами"},
        )

    async def test_get_session_for_doctor_blocks_direct_access_to_foreign_session(self) -> None:
        now = datetime(2099, 2, 22, 12, 0, tzinfo=UTC)

        async with async_session_maker() as db:
            config = SurveyConfig(
                name="Doctor strict direct access config",
                description="doctor-strict-direct-access",
                version="test",
                is_active=False,
                json_config={"start_node": "welcome", "nodes": []},
            )
            doctor = DoctorUser(
                username="doctor_direct_access_user",
                hashed_password="hashed",
                is_active=True,
                allowed_clinic_bucket=PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
                session_doctor_name_filter="Иванов Иван Иванович",
            )
            db.add_all([config, doctor])
            await db.flush()

            self.created_config_ids.append(config.id)
            self.created_doctor_ids.append(doctor.id)

            foreign_session = SurveySession(
                lead_id=940001,
                entity_type="DEAL",
                patient_name="Пациент закрытый",
                doctor_name="Петров Петр Петрович",
                survey_config_id=config.id,
                token_hash="doctor-direct-access-940001",
                status="completed",
                consent_given=True,
                portal_clinic_bucket=PORTAL_CLINIC_BUCKET_NOVOSIBIRSK,
                started_at=now - timedelta(minutes=10),
                completed_at=now - timedelta(minutes=2),
            )
            db.add(foreign_session)
            await db.commit()

            self.created_session_ids.append(foreign_session.id)

            with self.assertRaises(HTTPException) as error_context:
                await _get_session_for_doctor(foreign_session.id, doctor, db)

        self.assertEqual(error_context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
