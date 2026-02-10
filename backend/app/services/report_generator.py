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
        # Автоматическое определение версии опросника
        self.survey_version = self._detect_version()
    
    def _detect_version(self) -> int:
        """Определение версии опросника по наличию узлов."""
        # Узлы, уникальные для v2
        v2_nodes = {"body_location", "pain_character", "temperature_filter", "resp_filter", "cardio_filter", "gastro_filter"}
        if v2_nodes & set(self.nodes.keys()):
            return 2
        return 1
    
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
        if self.survey_version == 2:
            return self._generate_html_report_v2(patient_name, answers)
        return self._generate_html_report_v1(patient_name, answers)
    
    def _generate_html_report_v1(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
    ) -> str:
        """Генерация HTML-отчёта для v1 опросника."""
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
    
    def _generate_html_report_v2(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
    ) -> str:
        """Генерация HTML-отчёта для v2 опросника (подробный клинический)."""
        report_parts = []
        
        # Заголовок
        report_parts.append(self._generate_header(patient_name))
        
        # Блок 1: Локализация и характеристика боли
        pain_block = self._generate_v2_pain_block(answers)
        if pain_block:
            report_parts.append(pain_block)
        
        # Свободное описание жалоб
        free_complaint = answers.get("free_complaint", {})
        free_text = free_complaint.get("text", "").strip()
        if free_text:
            report_parts.append(f"📝 <b>ЖАЛОБЫ СВОИМИ СЛОВАМИ:</b><br>{free_text}")
        
        # Блок 2: Общее состояние (температура)
        temp_block = self._generate_v2_temperature_block(answers)
        if temp_block:
            report_parts.append(temp_block)
        
        # Блок 2: Дыхательная система
        resp_block = self._generate_v2_respiratory_block(answers)
        if resp_block:
            report_parts.append(resp_block)
        
        # Блок 2: Сердечно-сосудистая система
        cardio_block = self._generate_v2_cardio_block(answers)
        if cardio_block:
            report_parts.append(cardio_block)
        
        # Блок 2: Пищеварительная система
        gastro_block = self._generate_v2_gastro_block(answers)
        if gastro_block:
            report_parts.append(gastro_block)
        
        # Блок 2: Мочевыделительная система
        urinary_block = self._generate_v2_urinary_block(answers)
        if urinary_block:
            report_parts.append(urinary_block)
        
        # Блок 3: История заболевания
        history_block = self._generate_v2_disease_history_block(answers)
        if history_block:
            report_parts.append(history_block)
        
        # Блок 4: Анамнез жизни
        life_block = self._generate_v2_life_history_block(answers)
        if life_block:
            report_parts.append(life_block)
        
        # Системный анализ (алерты)
        alerts = self._generate_v2_alerts(answers)
        if alerts:
            report_parts.append(alerts)
        
        return "<br><br>".join(report_parts)
    
    # ============================================
    # Методы генерации блоков для V2
    # ============================================
    
    def _generate_v2_pain_block(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока боли для v2."""
        parts = []
        
        # Локализация (body_map)
        body_data = answers.get("body_location", {})
        locations = body_data.get("locations", [])
        body_intensity = body_data.get("intensity")
        
        # Характер боли
        pain_char = answers.get("pain_character", {})
        pain_selected = pain_char.get("selected", [])
        
        # Интенсивность (шкала 1-10)
        pain_int = answers.get("pain_intensity", {})
        scale_value = pain_int.get("value")
        
        # Если пациент указал "боли нет"
        if isinstance(pain_selected, list) and "no_pain" in pain_selected:
            return "📌 <b>ОСНОВНЫЕ ЖАЛОБЫ:</b> Боль отсутствует (профилактика/другое)"
        
        if not locations and not pain_selected and scale_value is None:
            return None
        
        parts.append("🩺 <b>ОСНОВНЫЕ ЖАЛОБЫ И ХАРАКТЕРИСТИКА БОЛИ:</b>")
        
        if locations:
            loc_map = {
                "head": "Голова",
                "throat": "Горло",
                "chest": "Грудная клетка / Сердце",
                "abdomen": "Живот",
                "back": "Поясница / Пах",
                "joints": "Суставы / Конечности",
            }
            loc_names = [loc_map.get(loc, loc) for loc in locations]
            parts.append(f"• <b>Локализация:</b> {', '.join(loc_names)}")
        
        if body_intensity:
            parts.append(f"• <b>Интенсивность (карта тела):</b> {body_intensity}/10")
        
        if isinstance(pain_selected, list) and pain_selected:
            char_map = {
                "sharp": "Острая / Кинжальная",
                "dull": "Тупая / Ноющая",
                "pressing": "Сжимающая / Давящая",
                "stabbing": "Колющая",
                "burning": "Жгучая",
                "cramping": "Приступообразная (схватками)",
                "constant": "Постоянная",
            }
            chars = [char_map.get(c, c) for c in pain_selected if c != "no_pain"]
            if chars:
                parts.append(f"• <b>Характер боли:</b> {', '.join(chars)}")
        
        if scale_value is not None:
            parts.append(f"• <b>Интенсивность (шкала):</b> {scale_value}/10")
        
        return "<br>".join(parts)
    
    def _generate_v2_temperature_block(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока температуры для v2."""
        temp_filter = answers.get("temperature_filter", {})
        if temp_filter.get("selected") != "yes":
            return None
        
        parts = ["🌡️ <b>ТЕМПЕРАТУРА:</b> Повышена"]
        
        temp_details = answers.get("temperature_details", {})
        details_selected = temp_details.get("selected", [])
        if isinstance(details_selected, list):
            details_map = {
                "chills": "Озноб",
                "sweating": "Повышенная потливость",
                "temp_morning": "Температура выше утром",
                "temp_evening": "Температура выше вечером",
            }
            for d in details_selected:
                if d in details_map:
                    parts.append(f"• {details_map[d]}")
        
        return "<br>".join(parts)
    
    def _generate_v2_respiratory_block(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока дыхательной системы для v2."""
        resp_filter = answers.get("resp_filter", {})
        if resp_filter.get("selected") != "yes":
            return None
        
        parts = ["🫁 <b>ДЫХАТЕЛЬНАЯ СИСТЕМА:</b>"]
        
        # Кашель
        cough = answers.get("resp_cough", {})
        cough_val = cough.get("selected")
        if cough_val:
            cough_map = {"dry": "Сухой кашель", "wet": "Кашель с мокротой", "no_cough": "Кашля нет"}
            parts.append(f"• <b>Кашель:</b> {cough_map.get(cough_val, cough_val)}")
        
        # Цвет мокроты
        sputum = answers.get("resp_sputum_color", {})
        sputum_val = sputum.get("selected")
        if sputum_val:
            sputum_map = {
                "clear": "Прозрачная",
                "yellow_green": "Жёлто-зелёная",
                "rusty": "Ржавая",
                "bloody": "С кровью ⚠️",
            }
            parts.append(f"• <b>Мокрота:</b> {sputum_map.get(sputum_val, sputum_val)}")
        
        # Одышка
        dyspnea = answers.get("resp_dyspnea", {})
        dyspnea_selected = dyspnea.get("selected", [])
        if isinstance(dyspnea_selected, list) and dyspnea_selected and "no_dyspnea" not in dyspnea_selected:
            dysp_map = {
                "at_rest": "В покое",
                "on_exercise": "При физической нагрузке",
                "lying_down": "Лёжа в постели",
                "asthma_attacks": "Приступы удушья ⚠️",
            }
            dysp_items = [dysp_map.get(d, d) for d in dyspnea_selected if d != "no_dyspnea"]
            if dysp_items:
                parts.append(f"• <b>Одышка:</b> {', '.join(dysp_items)}")
        
        return "<br>".join(parts)
    
    def _generate_v2_cardio_block(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока сердечно-сосудистой системы для v2."""
        cardio_filter = answers.get("cardio_filter", {})
        if cardio_filter.get("selected") != "yes":
            return None
        
        parts = ["❤️ <b>СЕРДЕЧНО-СОСУДИСТАЯ СИСТЕМА:</b>"]
        
        # Иррадиация
        irrad = answers.get("cardio_pain_irradiation", {})
        irrad_val = irrad.get("selected")
        if irrad_val:
            irrad_map = {
                "left_arm": "В левую руку/лопатку",
                "neck_jaw": "В шею/челюсть",
                "nowhere": "Никуда не отдаёт",
            }
            parts.append(f"• <b>Иррадиация:</b> {irrad_map.get(irrad_val, irrad_val)}")
        
        # Триггер
        trigger = answers.get("cardio_trigger", {})
        trigger_val = trigger.get("selected")
        if trigger_val:
            trigger_map = {
                "exercise": "Физическая нагрузка",
                "stress": "Эмоциональный стресс",
                "at_rest": "В покое",
            }
            parts.append(f"• <b>Провоцирующий фактор:</b> {trigger_map.get(trigger_val, trigger_val)}")
        
        # Нитроглицерин
        nitro = answers.get("cardio_nitro", {})
        nitro_val = nitro.get("selected")
        if nitro_val:
            nitro_map = {
                "yes": "Да, проходит",
                "no": "Нет, не проходит",
                "never": "Не пробовал(а)",
            }
            parts.append(f"• <b>Купирование нитроглицерином:</b> {nitro_map.get(nitro_val, nitro_val)}")
        
        # Отёки
        edema = answers.get("cardio_edema", {})
        edema_val = edema.get("selected")
        if edema_val and edema_val != "no":
            edema_map = {
                "evening_legs": "Ноги отекают к вечеру",
                "morning_face": "Утром отекает лицо/веки",
            }
            parts.append(f"• <b>Отёки:</b> {edema_map.get(edema_val, edema_val)}")
        
        return "<br>".join(parts)
    
    def _generate_v2_gastro_block(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока ЖКТ для v2."""
        gastro_filter = answers.get("gastro_filter", {})
        if gastro_filter.get("selected") != "yes":
            return None
        
        parts = ["🍽️ <b>ПИЩЕВАРИТЕЛЬНАЯ СИСТЕМА (ЖКТ):</b>"]
        
        # Связь с едой
        meal = answers.get("gastro_meal_relation", {})
        meal_val = meal.get("selected")
        if meal_val:
            meal_map = {
                "hungry": "Голодные боли (натощак)",
                "right_after": "Боли сразу после еды",
                "delayed": "Боли через 1–2 часа после еды",
                "no_relation": "Не связано с едой",
            }
            parts.append(f"• <b>Связь с едой:</b> {meal_map.get(meal_val, meal_val)}")
        
        # Диспепсия
        dyspepsia = answers.get("gastro_dyspepsia", {})
        dysp_selected = dyspepsia.get("selected", [])
        if isinstance(dysp_selected, list) and dysp_selected and "none" not in dysp_selected:
            dysp_map = {
                "heartburn": "Изжога",
                "belching": "Отрыжка",
                "nausea": "Тошнота / Рвота",
                "coffee_ground_vomit": "Рвота «кофейной гущей» ⚠️",
                "bloating": "Вздутие живота",
            }
            symptoms = [dysp_map.get(s, s) for s in dysp_selected if s != "none"]
            if symptoms:
                parts.append(f"• <b>Диспепсия:</b> {', '.join(symptoms)}")
        
        # Стул
        stool = answers.get("gastro_stool", {})
        stool_val = stool.get("selected")
        if stool_val:
            stool_map = {
                "constipation": "Запор (стул твёрдый, комковатый)",
                "normal": "Норма",
                "diarrhea": "Диарея (стул мягкий, водянистый)",
            }
            parts.append(f"• <b>Стул:</b> {stool_map.get(stool_val, stool_val)}")
        
        # Кровь в стуле
        blood = answers.get("gastro_blood", {})
        blood_val = blood.get("selected")
        if blood_val == "yes":
            parts.append("• ⚠️ <b>Кровь в стуле:</b> Да (чёрный/дёгтеобразный или алая кровь)")
        
        return "<br>".join(parts)
    
    def _generate_v2_urinary_block(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока мочевыделительной системы для v2."""
        urinary_filter = answers.get("urinary_filter", {})
        if urinary_filter.get("selected") != "yes":
            return None
        
        parts = ["💧 <b>МОЧЕВЫДЕЛИТЕЛЬНАЯ СИСТЕМА:</b>"]
        
        details = answers.get("urinary_details", {})
        details_selected = details.get("selected", [])
        if isinstance(details_selected, list) and details_selected:
            det_map = {
                "dysuria": "Рези, жжение при мочеиспускании",
                "urine_color": "Изменение цвета мочи (тёмная, красная, мутная)",
                "nocturia": "Никтурия (ночные позывы)",
                "difficulty_start": "Затруднения с началом мочеиспускания",
            }
            for d in details_selected:
                if d in det_map:
                    parts.append(f"• {det_map[d]}")
        
        return "<br>".join(parts)
    
    def _generate_v2_disease_history_block(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока истории заболевания для v2."""
        parts = []
        
        # Начало заболевания
        onset = answers.get("disease_onset", {})
        onset_val = onset.get("selected")
        duration = onset.get("duration_text", "")
        
        history = answers.get("disease_history", {})
        history_text = history.get("text", "").strip()
        
        if not onset_val and not history_text:
            return None
        
        parts.append("📋 <b>ИСТОРИЯ ЗАБОЛЕВАНИЯ (Anamnesis Morbi):</b>")
        
        if onset_val:
            onset_map = {
                "acute": "Заболел остро (часы/дни назад)",
                "chronic_exacerbation": "Болеет давно, сейчас обострение",
            }
            parts.append(f"• <b>Начало:</b> {onset_map.get(onset_val, onset_val)}")
        
        if duration:
            parts.append(f"• <b>Длительность:</b> {duration}")
        
        if history_text:
            parts.append(f"• <b>Описание:</b> {history_text}")
        
        return "<br>".join(parts)
    
    def _generate_v2_life_history_block(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока анамнеза жизни для v2."""
        parts = []
        has_content = False
        
        parts.append("💊 <b>АНАМНЕЗ ЖИЗНИ (Anamnesis Vitae):</b>")
        
        # Аллергия
        allergy = answers.get("allergy", {})
        allergy_val = allergy.get("selected")
        if allergy_val == "yes":
            allergy_det = answers.get("allergy_details", {})
            allergy_text = allergy_det.get("text", "не уточнено")
            parts.append(f"• ⚠️ <b>Аллергия:</b> {allergy_text}")
            has_content = True
        elif allergy_val == "no":
            parts.append("• <b>Аллергия:</b> Нет")
            has_content = True
        
        # Курение
        smoking = answers.get("smoking", {})
        smoking_val = smoking.get("selected")
        if smoking_val == "yes":
            sm_details = answers.get("smoking_details", {})
            sm_selected = sm_details.get("selected", [])
            sm_years = sm_details.get("smoking_years")
            sm_first = sm_details.get("first_cig_time", "")
            
            cig_map = {
                "lt10": "<10",
                "11_20": "11–20",
                "21_30": "21–30",
                "gt30": ">30",
            }
            cig_per_day = ""
            if isinstance(sm_selected, list):
                for s in sm_selected:
                    if s in cig_map:
                        cig_per_day = cig_map[s]
                        break
            
            smoke_info = "🚬 Курит"
            if cig_per_day:
                smoke_info += f", {cig_per_day} сиг/день"
            if sm_years:
                smoke_info += f", стаж {sm_years} лет"
            if sm_first:
                smoke_info += f", первая сигарета: {sm_first}"
            
            parts.append(f"• {smoke_info}")
            has_content = True
        elif smoking_val == "no":
            parts.append("• <b>Курение:</b> Нет")
            has_content = True
        
        # Алкоголь
        alcohol = answers.get("alcohol", {})
        alc_val = alcohol.get("selected")
        if alc_val:
            alc_map = {
                "no": "Не употребляет",
                "rare": "Редко",
                "moderate": "Умеренно",
                "often": "Часто ⚠️",
            }
            parts.append(f"• <b>Алкоголь:</b> {alc_map.get(alc_val, alc_val)}")
            has_content = True
        
        # Наследственность
        heredity = answers.get("heredity", {})
        her_selected = heredity.get("selected", [])
        if isinstance(her_selected, list) and her_selected and "none" not in her_selected:
            her_map = {
                "cardio": "Инфаркт/Инсульт",
                "diabetes": "Сахарный диабет",
                "oncology": "Онкология",
                "tuberculosis": "Туберкулёз",
                "mental": "Психические расстройства",
            }
            items = [her_map.get(h, h) for h in her_selected if h in her_map]
            if items:
                parts.append(f"• <b>Наследственность:</b> {', '.join(items)}")
                has_content = True
        
        # Перенесённые заболевания
        past = answers.get("past_diseases", {})
        past_text = past.get("text", "").strip()
        if past_text:
            parts.append(f"• <b>Перенесённые заболевания/операции:</b> {past_text}")
            has_content = True
        
        # Профессия
        occupation = answers.get("occupation", {})
        occ_text = occupation.get("text", "").strip()
        if occ_text:
            parts.append(f"• <b>Профессия / Вредности:</b> {occ_text}")
            has_content = True
        
        if not has_content:
            return None
        
        return "<br>".join(parts)
    
    def _generate_v2_alerts(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока системных алертов для v2."""
        alerts = []
        
        # ХОБЛ: дыхательные симптомы + стаж курения > 10 лет
        resp_filter = answers.get("resp_filter", {})
        smoking_details = answers.get("smoking_details", {})
        smoking_years = smoking_details.get("smoking_years", 0)
        
        if resp_filter.get("selected") == "yes" and smoking_years and smoking_years > 10:
            alerts.append(
                f"⚠️ <b>Подозрение на ХОБЛ:</b> Стаж курения {smoking_years} лет + "
                f"респираторные симптомы. <u>Рекомендовано: Спирометрия</u>"
            )
        
        # Кровь в мокроте
        sputum = answers.get("resp_sputum_color", {})
        if sputum.get("selected") == "bloody":
            alerts.append(
                "❗ <b>Кровохарканье:</b> Кровь в мокроте. "
                "<u>Рекомендовано: Рентген/КТ грудной клетки, консультация пульмонолога</u>"
            )
        
        # Кардио: боль при нагрузке + иррадиация + не купируется
        cardio_filter = answers.get("cardio_filter", {})
        if cardio_filter.get("selected") == "yes":
            trigger = answers.get("cardio_trigger", {}).get("selected")
            irrad = answers.get("cardio_pain_irradiation", {}).get("selected")
            nitro = answers.get("cardio_nitro", {}).get("selected")
            edema = answers.get("cardio_edema", {}).get("selected")
            
            findings = []
            if trigger == "exercise":
                findings.append("Боли при нагрузке (типичная стенокардия)")
            if irrad in ("left_arm", "neck_jaw"):
                findings.append(f"Иррадиация: {'левая рука/лопатка' if irrad == 'left_arm' else 'шея/челюсть'}")
            if nitro == "yes":
                findings.append("Купируется нитроглицерином")
            if edema and edema != "no":
                findings.append("Отёки")
            
            # Наследственность
            heredity = answers.get("heredity", {})
            her_selected = heredity.get("selected", [])
            if isinstance(her_selected, list) and "cardio" in her_selected:
                findings.append("Отягощённая наследственность (кардио)")
            
            if findings:
                alerts.append(
                    f"⚠️ <b>Кардио-риск:</b> {', '.join(findings)}. "
                    f"<u>Рекомендовано: ЭКГ, консультация кардиолога</u>"
                )
        
        # Гастро: голодные боли
        gastro_filter = answers.get("gastro_filter", {})
        if gastro_filter.get("selected") == "yes":
            meal = answers.get("gastro_meal_relation", {}).get("selected")
            blood = answers.get("gastro_blood", {}).get("selected")
            dyspepsia = answers.get("gastro_dyspepsia", {})
            dysp_sel = dyspepsia.get("selected", [])
            
            if meal == "hungry":
                alerts.append(
                    "⚠️ <b>Гастропатология:</b> «Голодные» боли (подозрение на язвенную болезнь). "
                    "<u>Рекомендовано: ФГДС, УЗИ ОБП</u>"
                )
            
            if blood == "yes":
                alerts.append(
                    "❗ <b>ЖКТ-кровотечение:</b> Кровь в стуле (чёрный/дёгтеобразный). "
                    "<u>Рекомендовано: СРОЧНО — колоноскопия, общий анализ крови</u>"
                )
            
            if isinstance(dysp_sel, list) and "coffee_ground_vomit" in dysp_sel:
                alerts.append(
                    "❗ <b>Подозрение на ЖКТ-кровотечение:</b> Рвота «кофейной гущей». "
                    "<u>Рекомендовано: СРОЧНО — ФГДС</u>"
                )
        
        # Онконастороженность
        heredity = answers.get("heredity", {})
        her_selected = heredity.get("selected", [])
        if isinstance(her_selected, list) and "oncology" in her_selected:
            alerts.append(
                "❗ <b>Онконастороженность:</b> Онкология в семейном анамнезе. "
                "<u>Рекомендовано: Тщательный осмотр, пальпация лимфоузлов</u>"
            )
        
        if not alerts:
            return None
        
        return "🚨 <b>СИСТЕМНЫЙ АНАЛИЗ (Для врача):</b><br>" + "<br>".join(alerts)
    
    def generate_readable_html_report(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
    ) -> str:
        """
        Генерация читаемого HTML-отчёта для просмотра и экспорта.
        Отформатирован с CSS стилями для удобного чтения.
        
        Args:
            patient_name: Имя пациента
            answers: Словарь ответов {node_id: answer_data}
            
        Returns:
            Полный HTML-документ с встроенными стилями
        """
        if self.survey_version == 2:
            return self._generate_readable_html_report_v2(patient_name, answers)
        return self._generate_readable_html_report_v1(patient_name, answers)
    
    def _generate_readable_html_report_v1(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
    ) -> str:
        """Генерация читаемого HTML-отчёта для v1 опросника."""
        # Генерируем содержимое
        content_parts = []
        
        # Заголовок
        name = patient_name or "Не указано"
        date = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        content_parts.append(f"""
        <div class="header">
            <h1>📋 АНКЕТА ПАЦИЕНТА</h1>
            <p class="subtitle">Предварительный опрос</p>
            <div class="patient-info">
                <div><strong>Пациент:</strong> {name}</div>
                <div><strong>Дата:</strong> {date}</div>
            </div>
        </div>
        """)
        
        # Основная жалоба
        main_complaint = self._generate_readable_main_complaint(answers)
        if main_complaint:
            content_parts.append(f'<div class="section">{main_complaint}</div>')
        
        # Детализация боли
        pain_details = self._generate_readable_pain_details(answers)
        if pain_details:
            content_parts.append(f'<div class="section">{pain_details}</div>')
        
        # Скрининг систем
        systems_screening = self._generate_readable_systems_screening(answers)
        if systems_screening:
            content_parts.append(f'<div class="section">{systems_screening}</div>')
        
        # Факторы риска
        risk_factors = self._generate_readable_risk_factors(answers)
        if risk_factors:
            content_parts.append(f'<div class="section">{risk_factors}</div>')
        
        # Системный анализ
        alerts = self._generate_readable_alerts(answers)
        if alerts:
            content_parts.append(f'<div class="section alert-section">{alerts}</div>')
        
        # Собираем полный HTML документ
        html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Анкета пациента - {name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .header {{
            border-bottom: 3px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 28px;
            color: #1e293b;
            margin-bottom: 8px;
        }}
        
        .subtitle {{
            font-size: 16px;
            color: #64748b;
            margin-bottom: 15px;
        }}
        
        .patient-info {{
            display: flex;
            gap: 30px;
            font-size: 15px;
            color: #334155;
        }}
        
        .section {{
            margin-bottom: 30px;
            padding: 20px;
            background: #f8fafc;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
        }}
        
        .section h2 {{
            font-size: 20px;
            color: #1e293b;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .section h3 {{
            font-size: 17px;
            color: #334155;
            margin-top: 15px;
            margin-bottom: 10px;
        }}
        
        .section p {{
            margin-bottom: 8px;
            color: #475569;
        }}
        
        .section ul {{
            margin-left: 20px;
            margin-top: 10px;
        }}
        
        .section li {{
            margin-bottom: 6px;
            color: #475569;
        }}
        
        .alert-section {{
            background: #fef2f2;
            border-left-color: #dc2626;
        }}
        
        .alert-section h2 {{
            color: #991b1b;
        }}
        
        .alert-item {{
            background: white;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 6px;
            border-left: 3px solid #f59e0b;
        }}
        
        .intensity-badge {{
            display: inline-block;
            padding: 4px 12px;
            background: #fee2e2;
            color: #991b1b;
            border-radius: 4px;
            font-weight: 600;
            font-size: 14px;
        }}
        
        .risk-badge {{
            display: inline-block;
            padding: 4px 12px;
            background: #fef3c7;
            color: #92400e;
            border-radius: 4px;
            font-weight: 600;
            font-size: 14px;
            margin-left: 8px;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {"".join(content_parts)}
    </div>
</body>
</html>
        """
        
        return html
    
    def _generate_readable_html_report_v2(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
    ) -> str:
        """Генерация читаемого HTML-отчёта для v2 опросника."""
        content_parts = []
        
        # Заголовок
        name = patient_name or "Не указано"
        date = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        content_parts.append(f"""
        <div class="header">
            <h1>📋 ПОДРОБНАЯ АНКЕТА ПАЦИЕНТА</h1>
            <p class="subtitle">Клинический опрос v2.0</p>
            <div class="patient-info">
                <div><strong>Пациент:</strong> {name}</div>
                <div><strong>Дата:</strong> {date}</div>
            </div>
        </div>
        """)
        
        # Блок 1: Жалобы и боль
        pain_block = self._generate_v2_readable_pain_block(answers)
        if pain_block:
            content_parts.append(f'<div class="section">{pain_block}</div>')
        
        # Свободное описание
        free_complaint = answers.get("free_complaint", {})
        free_text = free_complaint.get("text", "").strip()
        if free_text:
            content_parts.append(f'<div class="section"><h2>📝 Жалобы своими словами</h2><p>{free_text}</p></div>')
        
        # Температура
        temp_block = self._generate_v2_readable_temperature(answers)
        if temp_block:
            content_parts.append(f'<div class="section">{temp_block}</div>')
        
        # Дыхательная система
        resp_block = self._generate_v2_readable_respiratory(answers)
        if resp_block:
            content_parts.append(f'<div class="section">{resp_block}</div>')
        
        # Сердечно-сосудистая
        cardio_block = self._generate_v2_readable_cardio(answers)
        if cardio_block:
            content_parts.append(f'<div class="section">{cardio_block}</div>')
        
        # ЖКТ
        gastro_block = self._generate_v2_readable_gastro(answers)
        if gastro_block:
            content_parts.append(f'<div class="section">{gastro_block}</div>')
        
        # Мочевыделительная
        urinary_block = self._generate_v2_readable_urinary(answers)
        if urinary_block:
            content_parts.append(f'<div class="section">{urinary_block}</div>')
        
        # История заболевания
        history_block = self._generate_v2_readable_disease_history(answers)
        if history_block:
            content_parts.append(f'<div class="section">{history_block}</div>')
        
        # Анамнез жизни
        life_block = self._generate_v2_readable_life_history(answers)
        if life_block:
            content_parts.append(f'<div class="section">{life_block}</div>')
        
        # Алерты
        alerts = self._generate_v2_readable_alerts(answers)
        if alerts:
            content_parts.append(f'<div class="section alert-section">{alerts}</div>')
        
        # Собираем HTML документ (используем те же стили)
        html = self._wrap_in_html_document(name, content_parts)
        return html
    
    def _generate_v2_readable_pain_block(self, answers: Dict[str, Any]) -> Optional[str]:
        """Блок боли для v2 readable."""
        body_data = answers.get("body_location", {})
        locations = body_data.get("locations", [])
        body_intensity = body_data.get("intensity")
        pain_char = answers.get("pain_character", {})
        pain_selected = pain_char.get("selected", [])
        pain_int = answers.get("pain_intensity", {})
        scale_value = pain_int.get("value")
        
        if isinstance(pain_selected, list) and "no_pain" in pain_selected:
            return "<h2>📌 Основные жалобы</h2><p>Боль отсутствует (профилактика/другое)</p>"
        
        if not locations and not pain_selected and scale_value is None:
            return None
        
        parts = ["<h2>🩺 Основные жалобы и характеристика боли</h2>"]
        
        if locations:
            loc_map = {"head": "Голова", "throat": "Горло", "chest": "Грудная клетка", "abdomen": "Живот", "back": "Поясница", "joints": "Суставы"}
            loc_names = [loc_map.get(l, l) for l in locations]
            parts.append(f"<p><strong>Локализация:</strong> {', '.join(loc_names)}</p>")
        
        if body_intensity:
            parts.append(f'<p><strong>Интенсивность:</strong> <span class="intensity-badge">{body_intensity}/10</span></p>')
        
        if isinstance(pain_selected, list) and pain_selected:
            char_map = {"sharp": "Острая", "dull": "Тупая/Ноющая", "pressing": "Сжимающая", "stabbing": "Колющая", "burning": "Жгучая", "cramping": "Приступообразная", "constant": "Постоянная"}
            chars = [char_map.get(c, c) for c in pain_selected if c != "no_pain"]
            if chars:
                parts.append(f"<p><strong>Характер:</strong> {', '.join(chars)}</p>")
        
        if scale_value is not None:
            parts.append(f'<p><strong>Интенсивность (шкала):</strong> <span class="intensity-badge">{scale_value}/10</span></p>')
        
        return "".join(parts)
    
    def _generate_v2_readable_temperature(self, answers: Dict[str, Any]) -> Optional[str]:
        """Температура для v2 readable."""
        temp = answers.get("temperature_filter", {})
        if temp.get("selected") != "yes":
            return None
        parts = ["<h2>🌡️ Температура</h2><p>Повышена</p><ul>"]
        details = answers.get("temperature_details", {}).get("selected", [])
        det_map = {"chills": "Озноб", "sweating": "Потливость", "temp_morning": "Выше утром", "temp_evening": "Выше вечером"}
        if isinstance(details, list):
            for d in details:
                if d in det_map:
                    parts.append(f"<li>{det_map[d]}</li>")
        parts.append("</ul>")
        return "".join(parts)
    
    def _generate_v2_readable_respiratory(self, answers: Dict[str, Any]) -> Optional[str]:
        """Дыхательная для v2 readable."""
        if answers.get("resp_filter", {}).get("selected") != "yes":
            return None
        parts = ["<h2>🫁 Дыхательная система</h2><ul>"]
        cough = answers.get("resp_cough", {}).get("selected")
        if cough:
            c_map = {"dry": "Сухой кашель", "wet": "Кашель с мокротой", "no_cough": "Кашля нет"}
            parts.append(f"<li><strong>Кашель:</strong> {c_map.get(cough, cough)}</li>")
        sputum = answers.get("resp_sputum_color", {}).get("selected")
        if sputum:
            s_map = {"clear": "Прозрачная", "yellow_green": "Жёлто-зелёная", "rusty": "Ржавая", "bloody": "С кровью ⚠️"}
            parts.append(f"<li><strong>Мокрота:</strong> {s_map.get(sputum, sputum)}</li>")
        dyspnea = answers.get("resp_dyspnea", {}).get("selected", [])
        if isinstance(dyspnea, list) and dyspnea and "no_dyspnea" not in dyspnea:
            d_map = {"at_rest": "В покое", "on_exercise": "При нагрузке", "lying_down": "Лёжа", "asthma_attacks": "Приступы удушья"}
            items = [d_map.get(d, d) for d in dyspnea if d != "no_dyspnea"]
            if items:
                parts.append(f"<li><strong>Одышка:</strong> {', '.join(items)}</li>")
        parts.append("</ul>")
        return "".join(parts)
    
    def _generate_v2_readable_cardio(self, answers: Dict[str, Any]) -> Optional[str]:
        """Кардио для v2 readable."""
        if answers.get("cardio_filter", {}).get("selected") != "yes":
            return None
        parts = ["<h2>❤️ Сердечно-сосудистая система</h2><ul>"]
        irrad = answers.get("cardio_pain_irradiation", {}).get("selected")
        if irrad:
            i_map = {"left_arm": "В левую руку/лопатку", "neck_jaw": "В шею/челюсть", "nowhere": "Никуда"}
            parts.append(f"<li><strong>Иррадиация:</strong> {i_map.get(irrad, irrad)}</li>")
        trigger = answers.get("cardio_trigger", {}).get("selected")
        if trigger:
            t_map = {"exercise": "Физическая нагрузка", "stress": "Эмоциональный стресс", "at_rest": "В покое"}
            parts.append(f"<li><strong>Провоцирует:</strong> {t_map.get(trigger, trigger)}</li>")
        nitro = answers.get("cardio_nitro", {}).get("selected")
        if nitro:
            n_map = {"yes": "Да", "no": "Нет", "never": "Не пробовал(а)"}
            parts.append(f"<li><strong>Нитроглицерин:</strong> {n_map.get(nitro, nitro)}</li>")
        edema = answers.get("cardio_edema", {}).get("selected")
        if edema and edema != "no":
            e_map = {"evening_legs": "Ноги к вечеру", "morning_face": "Лицо утром"}
            parts.append(f"<li><strong>Отёки:</strong> {e_map.get(edema, edema)}</li>")
        parts.append("</ul>")
        return "".join(parts)
    
    def _generate_v2_readable_gastro(self, answers: Dict[str, Any]) -> Optional[str]:
        """ЖКТ для v2 readable."""
        if answers.get("gastro_filter", {}).get("selected") != "yes":
            return None
        parts = ["<h2>🍽️ Пищеварительная система</h2><ul>"]
        meal = answers.get("gastro_meal_relation", {}).get("selected")
        if meal:
            m_map = {"hungry": "Голодные боли", "right_after": "Сразу после еды", "delayed": "Через 1–2 ч.", "no_relation": "Не связано"}
            parts.append(f"<li><strong>Связь с едой:</strong> {m_map.get(meal, meal)}</li>")
        dysp = answers.get("gastro_dyspepsia", {}).get("selected", [])
        if isinstance(dysp, list) and dysp and "none" not in dysp:
            d_map = {"heartburn": "Изжога", "belching": "Отрыжка", "nausea": "Тошнота/Рвота", "coffee_ground_vomit": "Рвота «кофейной гущей» ⚠️", "bloating": "Вздутие"}
            items = [d_map.get(d, d) for d in dysp if d != "none"]
            if items:
                parts.append(f"<li><strong>Диспепсия:</strong> {', '.join(items)}</li>")
        stool = answers.get("gastro_stool", {}).get("selected")
        if stool:
            s_map = {"constipation": "Запор", "normal": "Норма", "diarrhea": "Диарея"}
            parts.append(f"<li><strong>Стул:</strong> {s_map.get(stool, stool)}</li>")
        blood = answers.get("gastro_blood", {}).get("selected")
        if blood == "yes":
            parts.append("<li><strong>⚠️ Кровь в стуле:</strong> Да</li>")
        parts.append("</ul>")
        return "".join(parts)
    
    def _generate_v2_readable_urinary(self, answers: Dict[str, Any]) -> Optional[str]:
        """Мочевыделительная для v2 readable."""
        if answers.get("urinary_filter", {}).get("selected") != "yes":
            return None
        parts = ["<h2>💧 Мочевыделительная система</h2><ul>"]
        details = answers.get("urinary_details", {}).get("selected", [])
        d_map = {"dysuria": "Рези/жжение", "urine_color": "Изменение цвета мочи", "nocturia": "Никтурия", "difficulty_start": "Затруднение с началом"}
        if isinstance(details, list):
            for d in details:
                if d in d_map:
                    parts.append(f"<li>{d_map[d]}</li>")
        parts.append("</ul>")
        return "".join(parts)
    
    def _generate_v2_readable_disease_history(self, answers: Dict[str, Any]) -> Optional[str]:
        """История заболевания для v2 readable."""
        onset = answers.get("disease_onset", {})
        onset_val = onset.get("selected")
        duration = onset.get("duration_text", "")
        history_text = answers.get("disease_history", {}).get("text", "").strip()
        if not onset_val and not history_text:
            return None
        parts = ["<h2>📋 История заболевания</h2>"]
        if onset_val:
            o_map = {"acute": "Остро (часы/дни)", "chronic_exacerbation": "Давно, сейчас обострение"}
            parts.append(f"<p><strong>Начало:</strong> {o_map.get(onset_val, onset_val)}</p>")
        if duration:
            parts.append(f"<p><strong>Длительность:</strong> {duration}</p>")
        if history_text:
            parts.append(f"<p><strong>Описание:</strong> {history_text}</p>")
        return "".join(parts)
    
    def _generate_v2_readable_life_history(self, answers: Dict[str, Any]) -> Optional[str]:
        """Анамнез жизни для v2 readable."""
        parts = ["<h2>💊 Анамнез жизни</h2><ul>"]
        has = False
        
        allergy = answers.get("allergy", {}).get("selected")
        if allergy == "yes":
            det = answers.get("allergy_details", {}).get("text", "не уточнено")
            parts.append(f"<li><strong>⚠️ Аллергия:</strong> {det}</li>")
            has = True
        elif allergy == "no":
            parts.append("<li><strong>Аллергия:</strong> Нет</li>")
            has = True
        
        smoking_val = answers.get("smoking", {}).get("selected")
        if smoking_val == "yes":
            sm = answers.get("smoking_details", {})
            years = sm.get("smoking_years", "?")
            parts.append(f"<li><strong>🚬 Курение:</strong> Да, стаж {years} лет</li>")
            has = True
        elif smoking_val == "no":
            parts.append("<li><strong>Курение:</strong> Нет</li>")
            has = True
        
        alc = answers.get("alcohol", {}).get("selected")
        if alc:
            a_map = {"no": "Не употребляет", "rare": "Редко", "moderate": "Умеренно", "often": "Часто ⚠️"}
            parts.append(f"<li><strong>Алкоголь:</strong> {a_map.get(alc, alc)}</li>")
            has = True
        
        heredity = answers.get("heredity", {}).get("selected", [])
        if isinstance(heredity, list) and heredity and "none" not in heredity:
            h_map = {"cardio": "Инфаркт/Инсульт", "diabetes": "Диабет", "oncology": "Онкология", "tuberculosis": "Туберкулёз", "mental": "Психические расстройства"}
            items = [h_map.get(h, h) for h in heredity if h in h_map]
            if items:
                parts.append(f"<li><strong>Наследственность:</strong> {', '.join(items)}</li>")
                has = True
        
        past = answers.get("past_diseases", {}).get("text", "").strip()
        if past:
            parts.append(f"<li><strong>Перенесённые заболевания:</strong> {past}</li>")
            has = True
        
        occ = answers.get("occupation", {}).get("text", "").strip()
        if occ:
            parts.append(f"<li><strong>Профессия:</strong> {occ}</li>")
            has = True
        
        parts.append("</ul>")
        if not has:
            return None
        return "".join(parts)
    
    def _generate_v2_readable_alerts(self, answers: Dict[str, Any]) -> Optional[str]:
        """Алерты для v2 readable."""
        # Используем те же алерты что и для Bitrix HTML
        raw_alerts = self._generate_v2_alerts(answers)
        if not raw_alerts:
            return None
        
        # Преобразуем в readable формат
        parts = ["<h2>🚨 Системный анализ для врача</h2>"]
        parts.append("<p><em>Автоматически выявленные риски:</em></p>")
        
        # Разбираем alert строку на отдельные элементы
        alert_items = raw_alerts.replace("🚨 <b>СИСТЕМНЫЙ АНАЛИЗ (Для врача):</b><br>", "").split("<br>")
        for item in alert_items:
            if item.strip():
                parts.append(f'<div class="alert-item"><p>{item.strip()}</p></div>')
        
        return "".join(parts)
    
    def _wrap_in_html_document(self, patient_name: str, content_parts: List[str]) -> str:
        """Обёртка контента в полный HTML документ с CSS стилями."""
        return f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Анкета пациента - {patient_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 3px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 28px; color: #1e293b; margin-bottom: 8px; }}
        .subtitle {{ font-size: 16px; color: #64748b; margin-bottom: 15px; }}
        .patient-info {{ display: flex; gap: 30px; font-size: 15px; color: #334155; }}
        .section {{
            margin-bottom: 30px;
            padding: 20px;
            background: #f8fafc;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
        }}
        .section h2 {{ font-size: 20px; color: #1e293b; margin-bottom: 15px; }}
        .section h3 {{ font-size: 17px; color: #334155; margin-top: 15px; margin-bottom: 10px; }}
        .section p {{ margin-bottom: 8px; color: #475569; }}
        .section ul {{ margin-left: 20px; margin-top: 10px; }}
        .section li {{ margin-bottom: 6px; color: #475569; }}
        .alert-section {{ background: #fef2f2; border-left-color: #dc2626; }}
        .alert-section h2 {{ color: #991b1b; }}
        .alert-item {{
            background: white;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 6px;
            border-left: 3px solid #f59e0b;
        }}
        .intensity-badge {{
            display: inline-block;
            padding: 4px 12px;
            background: #fee2e2;
            color: #991b1b;
            border-radius: 4px;
            font-weight: 600;
            font-size: 14px;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; padding: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {"".join(content_parts)}
    </div>
</body>
</html>
        """

    def generate_text_report(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
    ) -> str:
        """
        Генерация текстового отчёта для экспорта в TXT.
        
        Args:
            patient_name: Имя пациента
            answers: Словарь ответов {node_id: answer_data}
            
        Returns:
            Текстовая строка отчёта
        """
        if self.survey_version == 2:
            return self._generate_text_report_v2(patient_name, answers)
        return self._generate_text_report_v1(patient_name, answers)
    
    def _generate_text_report_v1(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
    ) -> str:
        """Генерация текстового отчёта для v1 опросника."""
        lines = []
        
        # Заголовок
        name = patient_name or "Не указано"
        date = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        lines.append("=" * 70)
        lines.append("📋 АНКЕТА ПАЦИЕНТА (Предварительный опрос)")
        lines.append("=" * 70)
        lines.append(f"Пациент: {name}")
        lines.append(f"Дата: {date}")
        lines.append("=" * 70)
        lines.append("")
        
        # Основная жалоба
        main_complaint = self._generate_text_main_complaint(answers)
        if main_complaint:
            lines.append(main_complaint)
            lines.append("")
        
        # Детализация боли
        pain_details = self._generate_text_pain_details(answers)
        if pain_details:
            lines.append(pain_details)
            lines.append("")
        
        # Скрининг систем
        systems_screening = self._generate_text_systems_screening(answers)
        if systems_screening:
            lines.append(systems_screening)
            lines.append("")
        
        # Факторы риска
        risk_factors = self._generate_text_risk_factors(answers)
        if risk_factors:
            lines.append(risk_factors)
            lines.append("")
        
        # Системный анализ
        alerts = self._generate_text_alerts(answers)
        if alerts:
            lines.append(alerts)
            lines.append("")
        
        lines.append("=" * 70)
        lines.append("Конец отчёта")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def _generate_text_report_v2(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
    ) -> str:
        """Генерация текстового отчёта для v2 опросника."""
        lines = []
        name = patient_name or "Не указано"
        date = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        lines.append("=" * 70)
        lines.append("📋 ПОДРОБНАЯ АНКЕТА ПАЦИЕНТА (Клинический опрос v2.0)")
        lines.append("=" * 70)
        lines.append(f"Пациент: {name}")
        lines.append(f"Дата: {date}")
        lines.append("=" * 70)
        lines.append("")
        
        # Блок 1: Боль
        pain_html = self._generate_v2_pain_block(answers)
        if pain_html:
            # Конвертируем HTML в текст
            clean = pain_html.replace("<br>", "\n").replace("<b>", "").replace("</b>", "")
            lines.append(clean)
            lines.append("")
        
        # Свободное описание
        free_text = answers.get("free_complaint", {}).get("text", "").strip()
        if free_text:
            lines.append(f"📝 ЖАЛОБЫ СВОИМИ СЛОВАМИ:\n  {free_text}")
            lines.append("")
        
        # Температура
        temp_html = self._generate_v2_temperature_block(answers)
        if temp_html:
            clean = temp_html.replace("<br>", "\n").replace("<b>", "").replace("</b>", "")
            lines.append(clean)
            lines.append("")
        
        # Дыхательная
        resp_html = self._generate_v2_respiratory_block(answers)
        if resp_html:
            clean = resp_html.replace("<br>", "\n").replace("<b>", "").replace("</b>", "")
            lines.append(clean)
            lines.append("")
        
        # Кардио
        cardio_html = self._generate_v2_cardio_block(answers)
        if cardio_html:
            clean = cardio_html.replace("<br>", "\n").replace("<b>", "").replace("</b>", "")
            lines.append(clean)
            lines.append("")
        
        # ЖКТ
        gastro_html = self._generate_v2_gastro_block(answers)
        if gastro_html:
            clean = gastro_html.replace("<br>", "\n").replace("<b>", "").replace("</b>", "")
            lines.append(clean)
            lines.append("")
        
        # Мочевыделительная
        urinary_html = self._generate_v2_urinary_block(answers)
        if urinary_html:
            clean = urinary_html.replace("<br>", "\n").replace("<b>", "").replace("</b>", "")
            lines.append(clean)
            lines.append("")
        
        # История заболевания
        history_html = self._generate_v2_disease_history_block(answers)
        if history_html:
            clean = history_html.replace("<br>", "\n").replace("<b>", "").replace("</b>", "")
            lines.append(clean)
            lines.append("")
        
        # Анамнез жизни
        life_html = self._generate_v2_life_history_block(answers)
        if life_html:
            clean = life_html.replace("<br>", "\n").replace("<b>", "").replace("</b>", "")
            lines.append(clean)
            lines.append("")
        
        # Алерты
        alerts_html = self._generate_v2_alerts(answers)
        if alerts_html:
            clean = alerts_html.replace("<br>", "\n").replace("<b>", "").replace("</b>", "").replace("<u>", "").replace("</u>", "")
            lines.append(clean)
            lines.append("")
        
        lines.append("=" * 70)
        lines.append("Конец отчёта")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
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
    
    # ============================================
    # Методы для читаемого HTML формата
    # ============================================
    
    def _generate_readable_main_complaint(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока основной жалобы для читаемого формата."""
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
        
        return f"<h2>📌 Основная причина обращения</h2><p><strong>{complaint_text}</strong></p>"
    
    def _generate_readable_pain_details(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока детализации боли для читаемого формата."""
        pain_data = answers.get("pain_details", {})
        
        if not pain_data:
            return None
        
        parts = ["<h2>🩺 Характеристика боли</h2>"]
        
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
            parts.append(f"<p><strong>Локализация:</strong> {', '.join(loc_names)}</p>")
        
        # Интенсивность
        intensity = pain_data.get("intensity")
        if intensity:
            parts.append(f'<p><strong>Интенсивность:</strong> <span class="intensity-badge">{intensity}/10</span></p>')
        
        return "".join(parts)
    
    def _generate_readable_systems_screening(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока скрининга систем для читаемого формата."""
        screening = answers.get("systems_screening", {})
        selected_systems = screening.get("selected", [])
        
        if not selected_systems or "none" in selected_systems:
            return None
        
        parts = ["<h2>🔍 Скрининг систем организма</h2>"]
        parts.append("<p><em>Выявленные отклонения (только положительные находки):</em></p>")
        
        # Дыхательная система
        if "respiratory" in selected_systems:
            respiratory_details = answers.get("respiratory_details", {})
            resp_selected = respiratory_details.get("selected", [])
            
            if resp_selected:
                parts.append("<h3>🫁 Дыхательная система</h3><ul>")
                symptoms_map = {
                    "dry_cough": "Кашель сухой",
                    "wet_cough": "Кашель с мокротой",
                    "dyspnea_walking": "Одышка при ходьбе",
                    "asthma_attacks": "Приступы удушья",
                }
                for symptom in resp_selected:
                    if symptom in symptoms_map:
                        parts.append(f"<li>{symptoms_map[symptom]}</li>")
                
                smoking_years = respiratory_details.get("smoking_years")
                if smoking_years and smoking_years > 0:
                    parts.append(f'<li>🚬 Стаж курения: <strong>{smoking_years} лет</strong></li>')
                
                parts.append("</ul>")
        
        # Сердечно-сосудистая система
        if "cardio" in selected_systems:
            cardio_details = answers.get("cardio_details", {})
            cardio_selected = cardio_details.get("selected")
            
            if cardio_selected:
                parts.append("<h3>❤️ Сердечно-сосудистая система</h3><ul>")
                timing_map = {
                    "exercise": "Симптомы при физической нагрузке",
                    "rest": "Симптомы в покое / Ночью",
                    "constant": "Симптомы постоянно",
                }
                if cardio_selected in timing_map:
                    parts.append(f"<li>{timing_map[cardio_selected]}</li>")
                
                edema = cardio_details.get("edema")
                if edema and edema != "none":
                    edema_map = {"legs": "Отёки на ногах", "face": "Отёки на лице"}
                    parts.append(f"<li>{edema_map.get(edema, edema)}</li>")
                
                parts.append("</ul>")
        
        # Пищеварительная система
        if "gastro" in selected_systems:
            gastro_details = answers.get("gastro_details", {})
            gastro_selected = gastro_details.get("selected", [])
            
            if gastro_selected:
                parts.append("<h3>🍽️ Пищеварительная система</h3><ul>")
                symptoms_map = {
                    "hungry_pain": "Боли 'голодные' или ночные",
                    "after_meal_pain": "Боли после еды",
                    "constipation": "Запоры",
                    "diarrhea": "Диарея",
                    "nausea": "Тошнота/Рвота",
                }
                for symptom in gastro_selected:
                    if symptom in symptoms_map:
                        parts.append(f"<li>{symptoms_map[symptom]}</li>")
                
                parts.append("</ul>")
        
        # Неврология
        if "neuro" in selected_systems:
            parts.append("<h3>🧠 Неврология</h3><ul>")
            parts.append("<li>Головные боли, головокружение, нарушения сна</li>")
            parts.append("</ul>")
        
        # Мочевыделительная система
        if "urinary" in selected_systems:
            parts.append("<h3>💧 Мочевыделительная система</h3><ul>")
            parts.append("<li>Боли в пояснице, проблемы с мочеиспусканием</li>")
            parts.append("</ul>")
        
        return "".join(parts)
    
    def _generate_readable_risk_factors(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока факторов риска для читаемого формата."""
        risk_data = answers.get("risk_factors", {})
        selected = risk_data.get("selected", [])
        
        if not selected or "none" in selected:
            return None
        
        parts = ["<h2>💊 Факторы риска (Anamnesis Vitae)</h2><ul>"]
        
        factors_map = {
            "allergy": "⚠️ Аллергия на лекарства или продукты",
            "diabetes": "Сахарный диабет (личный или семейный анамнез)",
            "oncology": "🧬 Онкология у кровных родственников",
            "cardiovascular": "Инфаркты/Инсульты у родителей до 60 лет",
        }
        
        for factor in selected:
            if factor in factors_map:
                parts.append(f"<li><strong>{factors_map[factor]}</strong></li>")
        
        parts.append("</ul>")
        
        # Детали аллергии
        allergy_details = risk_data.get("allergy_details")
        if allergy_details:
            parts.append(f"<p><em>Детали аллергии: {allergy_details}</em></p>")
        
        return "".join(parts)
    
    def _generate_readable_alerts(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока системных алертов для читаемого формата."""
        alerts = []
        
        # Анализ на ХОБЛ
        copd_alert = self._check_copd_risk_readable(answers)
        if copd_alert:
            alerts.append(copd_alert)
        
        # Анализ на кардио-риск
        cardio_alert = self._check_cardio_risk_readable(answers)
        if cardio_alert:
            alerts.append(cardio_alert)
        
        # Анализ на гастро
        gastro_alert = self._check_gastro_risk_readable(answers)
        if gastro_alert:
            alerts.append(gastro_alert)
        
        # Онконастороженность
        onco_alert = self._check_onco_risk_readable(answers)
        if onco_alert:
            alerts.append(onco_alert)
        
        if not alerts:
            return None
        
        parts = ["<h2>🚨 Системный анализ для врача</h2>"]
        parts.append("<p><em>Автоматически выявленные риски и рекомендации:</em></p>")
        parts.extend(alerts)
        
        return "".join(parts)
    
    def _check_copd_risk_readable(self, answers: Dict[str, Any]) -> Optional[str]:
        """Проверка риска ХОБЛ для читаемого формата."""
        screening = answers.get("systems_screening", {})
        selected_systems = screening.get("selected", [])
        
        respiratory_details = answers.get("respiratory_details", {})
        smoking_years = respiratory_details.get("smoking_years", 0)
        resp_symptoms = respiratory_details.get("selected", [])
        
        has_respiratory = "respiratory" in selected_systems or any(
            s in resp_symptoms for s in ["wet_cough", "dry_cough", "dyspnea_walking"]
        )
        
        if has_respiratory and smoking_years and smoking_years > 10:
            return f"""
            <div class="alert-item">
                <p><strong>⚠️ Подозрение на ХОБЛ</strong></p>
                <p>Стаж курения {smoking_years} лет + респираторные симптомы.</p>
                <p><strong>Рекомендовано:</strong> Спирометрия, консультация пульмонолога</p>
            </div>
            """
        
        return None
    
    def _check_cardio_risk_readable(self, answers: Dict[str, Any]) -> Optional[str]:
        """Проверка кардио-риска для читаемого формата."""
        screening = answers.get("systems_screening", {})
        selected_systems = screening.get("selected", [])
        
        if "cardio" not in selected_systems:
            return None
        
        cardio_details = answers.get("cardio_details", {})
        timing = cardio_details.get("selected")
        edema = cardio_details.get("edema")
        
        risk_factors = answers.get("risk_factors", {})
        has_family_cardio = "cardiovascular" in risk_factors.get("selected", [])
        
        findings = []
        
        if timing == "exercise":
            findings.append("Боли при нагрузке (типичная стенокардия)")
        if edema and edema != "none":
            findings.append("Отёки")
        if has_family_cardio:
            findings.append("Отягощённый семейный анамнез")
        
        if findings:
            findings_text = ", ".join(findings)
            return f"""
            <div class="alert-item">
                <p><strong>⚠️ Кардиоваскулярный риск</strong></p>
                <p>{findings_text}.</p>
                <p><strong>Рекомендовано:</strong> ЭКГ, консультация кардиолога</p>
            </div>
            """
        
        return None
    
    def _check_gastro_risk_readable(self, answers: Dict[str, Any]) -> Optional[str]:
        """Проверка гастро-риска для читаемого формата."""
        screening = answers.get("systems_screening", {})
        selected_systems = screening.get("selected", [])
        
        if "gastro" not in selected_systems:
            return None
        
        gastro_details = answers.get("gastro_details", {})
        symptoms = gastro_details.get("selected", [])
        
        if "hungry_pain" in symptoms:
            return """
            <div class="alert-item">
                <p><strong>⚠️ Гастропатология</strong></p>
                <p>'Голодные' боли (подозрение на язвенную болезнь).</p>
                <p><strong>Рекомендовано:</strong> ФГДС, УЗИ ОБП</p>
            </div>
            """
        
        return None
    
    def _check_onco_risk_readable(self, answers: Dict[str, Any]) -> Optional[str]:
        """Проверка онконастороженности для читаемого формата."""
        risk_factors = answers.get("risk_factors", {})
        selected = risk_factors.get("selected", [])
        
        if "oncology" in selected:
            return """
            <div class="alert-item">
                <p><strong>❗ Онконастороженность</strong></p>
                <p>Онкология в семейном анамнезе.</p>
                <p><strong>Рекомендовано:</strong> Тщательный осмотр, пальпация лимфоузлов</p>
            </div>
            """
        
        return None
    
    # ============================================
    # Методы для текстового формата
    # ============================================
    
    def _generate_text_main_complaint(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока основной жалобы для текстового формата."""
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
        
        return f"📌 ОСНОВНАЯ ПРИЧИНА ОБРАЩЕНИЯ\n{complaint_text}"
    
    def _generate_text_pain_details(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока детализации боли для текстового формата."""
        pain_data = answers.get("pain_details", {})
        
        if not pain_data:
            return None
        
        lines = ["🩺 ХАРАКТЕРИСТИКА БОЛИ"]
        
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
            lines.append(f"  • Локализация: {', '.join(loc_names)}")
        
        intensity = pain_data.get("intensity")
        if intensity:
            lines.append(f"  • Интенсивность: {intensity}/10")
        
        return "\n".join(lines)
    
    def _generate_text_systems_screening(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока скрининга систем для текстового формата."""
        screening = answers.get("systems_screening", {})
        selected_systems = screening.get("selected", [])
        
        if not selected_systems or "none" in selected_systems:
            return None
        
        lines = ["🔍 СКРИНИНГ СИСТЕМ ОРГАНИЗМА"]
        lines.append("(Выявленные отклонения - только положительные находки)")
        lines.append("")
        
        # Дыхательная система
        if "respiratory" in selected_systems:
            respiratory_details = answers.get("respiratory_details", {})
            resp_selected = respiratory_details.get("selected", [])
            
            if resp_selected:
                lines.append("🫁 Дыхательная система:")
                symptoms_map = {
                    "dry_cough": "Кашель сухой",
                    "wet_cough": "Кашель с мокротой",
                    "dyspnea_walking": "Одышка при ходьбе",
                    "asthma_attacks": "Приступы удушья",
                }
                for symptom in resp_selected:
                    if symptom in symptoms_map:
                        lines.append(f"  • {symptoms_map[symptom]}")
                
                smoking_years = respiratory_details.get("smoking_years")
                if smoking_years and smoking_years > 0:
                    lines.append(f"  • 🚬 Стаж курения: {smoking_years} лет")
                
                lines.append("")
        
        # Сердечно-сосудистая система
        if "cardio" in selected_systems:
            cardio_details = answers.get("cardio_details", {})
            cardio_selected = cardio_details.get("selected")
            
            if cardio_selected:
                lines.append("❤️ Сердечно-сосудистая система:")
                timing_map = {
                    "exercise": "Симптомы при физической нагрузке",
                    "rest": "Симптомы в покое / Ночью",
                    "constant": "Симптомы постоянно",
                }
                if cardio_selected in timing_map:
                    lines.append(f"  • {timing_map[cardio_selected]}")
                
                edema = cardio_details.get("edema")
                if edema and edema != "none":
                    edema_map = {"legs": "Отёки на ногах", "face": "Отёки на лице"}
                    lines.append(f"  • {edema_map.get(edema, edema)}")
                
                lines.append("")
        
        # Пищеварительная система
        if "gastro" in selected_systems:
            gastro_details = answers.get("gastro_details", {})
            gastro_selected = gastro_details.get("selected", [])
            
            if gastro_selected:
                lines.append("🍽️ Пищеварительная система:")
                symptoms_map = {
                    "hungry_pain": "Боли 'голодные' или ночные",
                    "after_meal_pain": "Боли после еды",
                    "constipation": "Запоры",
                    "diarrhea": "Диарея",
                    "nausea": "Тошнота/Рвота",
                }
                for symptom in gastro_selected:
                    if symptom in symptoms_map:
                        lines.append(f"  • {symptoms_map[symptom]}")
                
                lines.append("")
        
        # Неврология
        if "neuro" in selected_systems:
            lines.append("🧠 Неврология:")
            lines.append("  • Головные боли, головокружение, нарушения сна")
            lines.append("")
        
        # Мочевыделительная система
        if "urinary" in selected_systems:
            lines.append("💧 Мочевыделительная система:")
            lines.append("  • Боли в пояснице, проблемы с мочеиспусканием")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_text_risk_factors(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока факторов риска для текстового формата."""
        risk_data = answers.get("risk_factors", {})
        selected = risk_data.get("selected", [])
        
        if not selected or "none" in selected:
            return None
        
        lines = ["💊 ФАКТОРЫ РИСКА (Anamnesis Vitae)"]
        
        factors_map = {
            "allergy": "⚠️ Аллергия на лекарства или продукты",
            "diabetes": "Сахарный диабет (личный или семейный анамнез)",
            "oncology": "🧬 Онкология у кровных родственников",
            "cardiovascular": "Инфаркты/Инсульты у родителей до 60 лет",
        }
        
        for factor in selected:
            if factor in factors_map:
                lines.append(f"  • {factors_map[factor]}")
        
        allergy_details = risk_data.get("allergy_details")
        if allergy_details:
            lines.append(f"    └ Детали: {allergy_details}")
        
        return "\n".join(lines)
    
    def _generate_text_alerts(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока системных алертов для текстового формата."""
        alerts = []
        
        # Анализ на ХОБЛ
        copd_alert = self._check_copd_risk(answers)
        if copd_alert:
            # Удаляем HTML теги
            clean_alert = copd_alert.replace("<b>", "").replace("</b>", "").replace("<u>", "").replace("</u>", "")
            alerts.append(f"  • {clean_alert}")
        
        # Анализ на кардио-риск
        cardio_alert = self._check_cardio_risk(answers)
        if cardio_alert:
            clean_alert = cardio_alert.replace("<b>", "").replace("</b>", "").replace("<u>", "").replace("</u>", "")
            alerts.append(f"  • {clean_alert}")
        
        # Анализ на гастро
        gastro_alert = self._check_gastro_risk(answers)
        if gastro_alert:
            clean_alert = gastro_alert.replace("<b>", "").replace("</b>", "").replace("<u>", "").replace("</u>", "")
            alerts.append(f"  • {clean_alert}")
        
        # Онконастороженность
        onco_alert = self._check_onco_risk(answers)
        if onco_alert:
            clean_alert = onco_alert.replace("<b>", "").replace("</b>", "").replace("<u>", "").replace("</u>", "")
            alerts.append(f"  • {clean_alert}")
        
        if not alerts:
            return None
        
        lines = ["🚨 СИСТЕМНЫЙ АНАЛИЗ (Для врача)"]
        lines.extend(alerts)
        
        return "\n".join(lines)
