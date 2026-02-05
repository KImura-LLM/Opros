# ============================================
# Report Generator - Генератор отчётов
# ============================================
"""
Генерация HTML-отчёта для Битрикс24.
Формат согласно otchet.md.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from loguru import logger


class ReportGenerator:
    """
    Генератор HTML-отчётов для отправки в Битрикс24.
    
    Формирует структурированный отчёт с:
    - Основной жалобой
    - Скринингом систем (только положительные находки)
    - Факторами риска
    - Системными алертами для врача
    """
    
    def __init__(self, config: dict):
        """
        Инициализация генератора.
        
        Args:
            config: JSON-конфигурация опросника
        """
        self.config = config
        self.nodes = {node["id"]: node for node in config.get("nodes", [])}
    
    def generate_html_report(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
    ) -> str:
        """
        Генерация HTML-отчёта.
        
        Args:
            patient_name: Имя пациента
            answers: Словарь ответов {node_id: answer_data}
            
        Returns:
            HTML-строка для Битрикс24
        """
        report_parts = []
        
        # Заголовок
        report_parts.append(self._generate_header(patient_name))
        
        # Основная жалоба
        main_complaint = self._generate_main_complaint(answers)
        if main_complaint:
            report_parts.append(main_complaint)
        
        # Детализация боли (если есть)
        pain_details = self._generate_pain_details(answers)
        if pain_details:
            report_parts.append(pain_details)
        
        # Скрининг систем (только положительные)
        systems_screening = self._generate_systems_screening(answers)
        if systems_screening:
            report_parts.append(systems_screening)
        
        # Факторы риска
        risk_factors = self._generate_risk_factors(answers)
        if risk_factors:
            report_parts.append(risk_factors)
        
        # Системный анализ (алерты)
        alerts = self._generate_alerts(answers)
        if alerts:
            report_parts.append(alerts)
        
        return "<br><br>".join(report_parts)
    
    def _generate_header(self, patient_name: Optional[str]) -> str:
        """Генерация заголовка отчёта."""
        name = patient_name or "Не указано"
        date = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        return (
            f"<b>📋 АНКЕТА ПАЦИЕНТА</b> (Предварительный опрос)<br>"
            f"<b>Пациент:</b> {name}<br>"
            f"<b>Дата:</b> {date}"
        )
    
    def _generate_main_complaint(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока основной жалобы."""
        # Ищем ответ на вопрос об основной причине обращения
        main_trigger = answers.get("main_trigger", {})
        selected = main_trigger.get("selected")
        
        if not selected:
            return None
        
        complaints_map = {
            "pain": "Беспокоит боль",
            "discomfort": "Общее недомогание / Дискомфорт",
            "checkup": "Плановый осмотр / Справка / Анализы",
        }
        
        complaint_text = complaints_map.get(selected, selected)
        
        return f"📌 <b>ОСНОВНАЯ ПРИЧИНА ОБРАЩЕНИЯ:</b> {complaint_text}"
    
    def _generate_pain_details(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока детализации боли."""
        pain_data = answers.get("pain_details", {})
        
        if not pain_data:
            return None
        
        parts = ["🩺 <b>ХАРАКТЕРИСТИКА БОЛИ:</b>"]
        
        # Локализация
        locations = pain_data.get("locations", [])
        if locations:
            locations_map = {
                "head": "Голова",
                "throat": "Горло",
                "chest": "Грудная клетка",
                "abdomen": "Живот",
                "back": "Поясница",
                "joints": "Суставы/Конечности",
            }
            loc_names = [locations_map.get(loc, loc) for loc in locations]
            parts.append(f"• <b>Локализация:</b> {', '.join(loc_names)}")
        
        # Интенсивность
        intensity = pain_data.get("intensity")
        if intensity:
            parts.append(f"• <b>Интенсивность:</b> {intensity}/10")
        
        return "<br>".join(parts)
    
    def _generate_systems_screening(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока скрининга систем (только положительные находки)."""
        screening = answers.get("systems_screening", {})
        selected_systems = screening.get("selected", [])
        
        if not selected_systems or "none" in selected_systems:
            return None
        
        parts = []
        
        # Дыхательная система
        if "respiratory" in selected_systems:
            respiratory_details = answers.get("respiratory_details", {})
            resp_selected = respiratory_details.get("selected", [])
            
            if resp_selected:
                resp_parts = ["🫁 <b>ДЫХАТЕЛЬНАЯ СИСТЕМА:</b>"]
                symptoms_map = {
                    "dry_cough": "Кашель сухой",
                    "wet_cough": "Кашель с мокротой",
                    "dyspnea_walking": "Одышка при ходьбе",
                    "asthma_attacks": "Приступы удушья",
                }
                for symptom in resp_selected:
                    if symptom in symptoms_map:
                        resp_parts.append(f"• {symptoms_map[symptom]}")
                
                # Курение
                smoking_years = respiratory_details.get("smoking_years")
                if smoking_years and smoking_years > 0:
                    resp_parts.append(f"• 🚬 Стаж курения: {smoking_years} лет")
                
                parts.append("<br>".join(resp_parts))
        
        # Сердечно-сосудистая система
        if "cardio" in selected_systems:
            cardio_details = answers.get("cardio_details", {})
            cardio_selected = cardio_details.get("selected")
            
            if cardio_selected:
                cardio_parts = ["❤️ <b>СЕРДЕЧНО-СОСУДИСТАЯ СИСТЕМА:</b>"]
                timing_map = {
                    "exercise": "Симптомы при физической нагрузке",
                    "rest": "Симптомы в покое / Ночью",
                    "constant": "Симптомы постоянно",
                }
                if cardio_selected in timing_map:
                    cardio_parts.append(f"• {timing_map[cardio_selected]}")
                
                # Отёки
                edema = cardio_details.get("edema")
                if edema and edema != "none":
                    edema_map = {"legs": "Отёки на ногах", "face": "Отёки на лице"}
                    cardio_parts.append(f"• {edema_map.get(edema, edema)}")
                
                parts.append("<br>".join(cardio_parts))
        
        # Пищеварительная система
        if "gastro" in selected_systems:
            gastro_details = answers.get("gastro_details", {})
            gastro_selected = gastro_details.get("selected", [])
            
            if gastro_selected:
                gastro_parts = ["🍽️ <b>ПИЩЕВАРИТЕЛЬНАЯ СИСТЕМА:</b>"]
                symptoms_map = {
                    "hungry_pain": "Боли 'голодные' или ночные",
                    "after_meal_pain": "Боли после еды",
                    "constipation": "Запоры",
                    "diarrhea": "Диарея",
                    "nausea": "Тошнота/Рвота",
                }
                for symptom in gastro_selected:
                    if symptom in symptoms_map:
                        gastro_parts.append(f"• {symptoms_map[symptom]}")
                
                parts.append("<br>".join(gastro_parts))
        
        # Неврология
        if "neuro" in selected_systems:
            parts.append("🧠 <b>НЕВРОЛОГИЯ:</b><br>• Головные боли, головокружение, нарушения сна")
        
        # Мочевыделительная система
        if "urinary" in selected_systems:
            parts.append("💧 <b>МОЧЕВЫДЕЛИТЕЛЬНАЯ СИСТЕМА:</b><br>• Боли в пояснице, проблемы с мочеиспусканием")
        
        if not parts:
            return None
        
        return "<br><br>".join(parts)
    
    def _generate_risk_factors(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока факторов риска."""
        risk_data = answers.get("risk_factors", {})
        selected = risk_data.get("selected", [])
        
        if not selected or "none" in selected:
            return None
        
        parts = ["💊 <b>ФАКТОРЫ РИСКА (Anamnesis Vitae):</b>"]
        
        factors_map = {
            "allergy": "⚠️ Аллергия на лекарства или продукты",
            "diabetes": "Сахарный диабет (личный или семейный анамнез)",
            "oncology": "🧬 Онкология у кровных родственников",
            "cardiovascular": "Инфаркты/Инсульты у родителей до 60 лет",
        }
        
        for factor in selected:
            if factor in factors_map:
                parts.append(f"• {factors_map[factor]}")
        
        # Детали аллергии
        allergy_details = risk_data.get("allergy_details")
        if allergy_details:
            parts.append(f"  └ Детали: {allergy_details}")
        
        return "<br>".join(parts)
    
    def _generate_alerts(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока системных алертов для врача."""
        alerts = []
        
        # Анализ на ХОБЛ
        copd_alert = self._check_copd_risk(answers)
        if copd_alert:
            alerts.append(copd_alert)
        
        # Анализ на кардио-риск
        cardio_alert = self._check_cardio_risk(answers)
        if cardio_alert:
            alerts.append(cardio_alert)
        
        # Анализ на гастро
        gastro_alert = self._check_gastro_risk(answers)
        if gastro_alert:
            alerts.append(gastro_alert)
        
        # Онконастороженность
        onco_alert = self._check_onco_risk(answers)
        if onco_alert:
            alerts.append(onco_alert)
        
        if not alerts:
            return None
        
        return "🚨 <b>СИСТЕМНЫЙ АНАЛИЗ (Для врача):</b><br>" + "<br>".join(alerts)
    
    def _check_copd_risk(self, answers: Dict[str, Any]) -> Optional[str]:
        """Проверка риска ХОБЛ."""
        screening = answers.get("systems_screening", {})
        selected_systems = screening.get("selected", [])
        
        respiratory_details = answers.get("respiratory_details", {})
        smoking_years = respiratory_details.get("smoking_years", 0)
        resp_symptoms = respiratory_details.get("selected", [])
        
        # Условие: дыхательные симптомы + стаж курения > 10 лет
        has_respiratory = "respiratory" in selected_systems or any(
            s in resp_symptoms for s in ["wet_cough", "dry_cough", "dyspnea_walking"]
        )
        
        if has_respiratory and smoking_years and smoking_years > 10:
            pack_years = smoking_years  # Упрощённо, без учёта пачек в день
            return (
                f"⚠️ <b>Подозрение на ХОБЛ:</b> Стаж курения {smoking_years} лет + "
                f"респираторные симптомы. <u>Рекомендовано: Спирометрия</u>"
            )
        
        return None
    
    def _check_cardio_risk(self, answers: Dict[str, Any]) -> Optional[str]:
        """Проверка кардио-риска."""
        screening = answers.get("systems_screening", {})
        selected_systems = screening.get("selected", [])
        
        if "cardio" not in selected_systems:
            return None
        
        cardio_details = answers.get("cardio_details", {})
        timing = cardio_details.get("selected")
        edema = cardio_details.get("edema")
        
        # Наследственность
        risk_factors = answers.get("risk_factors", {})
        has_family_cardio = "cardiovascular" in risk_factors.get("selected", [])
        
        alerts = []
        
        if timing == "exercise":
            alerts.append("Боли при нагрузке (типичная стенокардия)")
        if edema and edema != "none":
            alerts.append("Отёки")
        if has_family_cardio:
            alerts.append("Отягощённый семейный анамнез")
        
        if alerts:
            return (
                f"⚠️ <b>Кардио-риск:</b> {', '.join(alerts)}. "
                f"<u>Рекомендовано: ЭКГ, консультация кардиолога</u>"
            )
        
        return None
    
    def _check_gastro_risk(self, answers: Dict[str, Any]) -> Optional[str]:
        """Проверка гастро-риска."""
        screening = answers.get("systems_screening", {})
        selected_systems = screening.get("selected", [])
        
        if "gastro" not in selected_systems:
            return None
        
        gastro_details = answers.get("gastro_details", {})
        symptoms = gastro_details.get("selected", [])
        
        if "hungry_pain" in symptoms:
            return (
                "⚠️ <b>Гастропатология:</b> 'Голодные' боли (подозрение на язвенную болезнь). "
                "<u>Рекомендовано: ФГДС, УЗИ ОБП</u>"
            )
        
        return None
    
    def _check_onco_risk(self, answers: Dict[str, Any]) -> Optional[str]:
        """Проверка онконастороженности."""
        risk_factors = answers.get("risk_factors", {})
        selected = risk_factors.get("selected", [])
        
        if "oncology" in selected:
            return (
                "❗ <b>Онконастороженность:</b> Онкология в семейном анамнезе. "
                "<u>Рекомендовано: Тщательный осмотр, пальпация лимфоузлов</u>"
            )
        
        return None
