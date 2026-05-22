# ============================================
# Report Generator - Генератор отчётов
# ============================================
"""
Генерация HTML-отчёта для Битрикс24.
Формат согласно otchet.md.
"""

from datetime import datetime
from html import escape
import re
from typing import Any, Dict, List, Optional


class ReportGenerator:
    """
    Генератор HTML-отчётов для отправки в Битрикс24.
    
    Формирует структурированный отчёт с:
    - Основной жалобой
    - Скринингом систем (только положительные находки)
    - Факторами риска
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

    @staticmethod
    def _escape_html(value: Any) -> str:
        """Экранирование динамического текста перед вставкой в HTML-отчёт."""
        return escape(str(value), quote=True)
    
    def _detect_version(self) -> int:
        """Определение версии опросника по наличию узлов."""
        # Узлы, уникальные для v2
        v2_nodes = {"body_location", "pain_character", "temperature_filter", "resp_filter", "cardio_filter", "gastro_filter"}
        if v2_nodes & set(self.nodes.keys()):
            return 2
        return 1

    # ============================================
    # Известные (захардкоженные) node_id для v2
    # Известные (захардкоженные) node_id для v1 (fallback-блок).
    V1_HANDLED_NODE_IDS = {
        "welcome", "finish",
        "main_trigger", "pain_details", "systems_screening",
        "respiratory_details", "cardio_details", "gastro_details",
        "risk_factors",
    }
    BODY_LOCATION_LABELS = {
        "head": "Голова",
        "throat": "Горло",
        "chest": "Грудная клетка",
        "abdomen": "Живот",
        "back": "Поясница",
        "joints": "Суставы/Конечности",
    }

    def _format_body_locations(self, locations: Any) -> Optional[str]:
        if not isinstance(locations, list) or not locations:
            return None

        loc_names = [self.BODY_LOCATION_LABELS.get(str(loc), str(loc)) for loc in locations]
        return ", ".join(loc_names)

    # ============================================
    # Универсальное форматирование ответа (fallback)
    # ============================================

    def _get_option_text(self, node: dict, value: str) -> str:
        """
        Получение текстового представления варианта ответа по его value.

        Args:
            node: Узел конфигурации
            value: Значение варианта (option.value)

        Returns:
            Текст варианта или исходное значение
        """
        for option in node.get("options", []):
            if option.get("value") == value:
                return option.get("text", value)
        return value

    def _format_answer_for_report(
        self, node_id: str, answer: dict, fmt: str = "html"
    ) -> Optional[str]:
        """
        Универсальное форматирование ответа для отчёта.

        Args:
            node_id: ID узла
            answer: Данные ответа
            fmt: Формат вывода — "html" (Битрикс), "readable" (PDF), "text"

        Returns:
            Отформатированная строка или None
        """
        node = self.nodes.get(node_id)
        if not node or not answer:
            return None

        node_type = node.get("type", "")
        question = node.get("question_text", node_id)

        # Пропускаем служебные экраны
        if node_type == "info_screen":
            return None

        # ── Извлечение текстового представления ответа ──
        answer_text = ""

        selected = answer.get("selected")
        if selected is not None:
            if isinstance(selected, list):
                # multi_choice
                texts = [self._get_option_text(node, v) for v in selected]
                answer_text = ", ".join(texts)
            elif isinstance(selected, bool):
                answer_text = "Да" if selected else "Нет"
            else:
                # single_choice
                answer_text = self._get_option_text(node, str(selected))

        value = answer.get("value")
        if value is not None and not answer_text:
            max_val = node.get("max_value")
            if max_val is not None:
                answer_text = f"{value}/{max_val}"
            else:
                answer_text = str(value)

        text = answer.get("text", "")
        if text and not answer_text:
            answer_text = text.strip()

        locations = answer.get("locations")
        if isinstance(locations, list) and locations and not answer_text:
            loc_map = {
                "head": "Голова", "throat": "Горло",
                "chest": "Грудная клетка", "abdomen": "Живот",
                "back": "Поясница", "joints": "Суставы",
            }
            answer_text = ", ".join(loc_map.get(l, l) for l in locations)

        # Интенсивность (body_map / карта тела)
        intensity = answer.get("intensity")
        if intensity is not None:
            intensity_str = f"Интенсивность: {intensity}/10"
            if answer_text:
                answer_text += f"; {intensity_str}"
            else:
                answer_text = intensity_str

        # Дополнительные поля (additional_fields)
        extra_parts: List[str] = []
        for field in node.get("additional_fields", []):
            fid = field.get("id", "")
            fval = answer.get(fid)
            if fval is not None and str(fval).strip():
                flabel = field.get("label", fid)
                extra_parts.append(f"{flabel}: {fval}")

        if not answer_text and not extra_parts:
            return None

        # ── Форматирование ──
        if fmt == "text":
            line = f"• {question}: {answer_text}"
            if extra_parts:
                line += " (" + "; ".join(extra_parts) + ")"
            return line

        question_html = self._escape_html(question)
        answer_html = self._escape_html(answer_text)
        extra_html = [self._escape_html(part) for part in extra_parts]

        if fmt == "readable":
            parts = [
                '<li class="qa-row">'
                f'<span class="qa-question">{question_html}</span>'
                '<span class="qa-kicker qa-answer-kicker">Ответ</span>'
                f'<span class="qa-answer">{answer_html}</span>'
            ]
            if extra_html:
                parts.append(
                    f'<span class="qa-extra"><em>({"; ".join(extra_html)})</em></span>'
                )
            parts.append("</li>")
            return "".join(parts)

        # html (Битрикс)
        line = f"• <b>{question_html}:</b> {answer_html}"
        if extra_html:
            line += " <i>(" + "; ".join(extra_html) + ")</i>"
        return line

    def _collect_unhandled_answers(
        self, answers: Dict[str, Any], handled_ids: set
    ) -> List[str]:
        """
        Возвращает список node_id ответов, которые не были обработаны
        специализированными блоками отчёта.
        """
        unhandled: List[str] = []
        seen: set[str] = set()

        # Основной порядок берём из конфигурации опроса, чтобы отчёт совпадал
        # с последовательностью вопросов в визуальном редакторе.
        for node in self._get_nodes_in_report_order():
            node_id = node.get("id")
            if not node_id or node_id in seen or node_id not in answers:
                continue
            if node_id not in handled_ids:
                current_node = self.nodes.get(node_id)
                if current_node and current_node.get("type") != "info_screen":
                    unhandled.append(node_id)
                    seen.add(node_id)

        # Сохраняем fallback для ответов, которых уже нет в схеме, но они есть
        # в старых сохранённых данных сессии.
        for node_id in answers:
            if node_id in seen or node_id in handled_ids:
                continue
            node = self.nodes.get(node_id)
            if node and node.get("type") != "info_screen":
                unhandled.append(node_id)
                seen.add(node_id)
        return unhandled

    def _generate_unhandled_block_html(
        self, answers: Dict[str, Any], handled_ids: set
    ) -> Optional[str]:
        """
        Генерация HTML-блока (Битрикс) для ответов, не покрытых
        специализированными блоками.
        """
        unhandled = self._collect_unhandled_answers(answers, handled_ids)
        if not unhandled:
            return None

        lines: List[str] = []
        for nid in unhandled:
            line = self._format_answer_for_report(nid, answers[nid], fmt="html")
            if line:
                lines.append(line)

        if not lines:
            return None

        items = "<br>".join(lines)
        return f"📝 <b>ДОПОЛНИТЕЛЬНЫЕ ВОПРОСЫ:</b><br>{items}"

    def _generate_unhandled_block_readable(
        self, answers: Dict[str, Any], handled_ids: set
    ) -> Optional[str]:
        """
        Генерация readable HTML-блока (PDF) для необработанных ответов.
        """
        unhandled = self._collect_unhandled_answers(answers, handled_ids)
        if not unhandled:
            return None

        items: List[str] = []
        for nid in unhandled:
            line = self._format_answer_for_report(nid, answers[nid], fmt="readable")
            if line:
                items.append(line)

        if not items:
            return None

        return "<ul>" + "".join(items) + "</ul>"

    def _generate_unhandled_block_text(
        self, answers: Dict[str, Any], handled_ids: set
    ) -> Optional[str]:
        """
        Генерация текстового блока для необработанных ответов.
        """
        unhandled = self._collect_unhandled_answers(answers, handled_ids)
        if not unhandled:
            return None

        lines: List[str] = ["📝 ДОПОЛНИТЕЛЬНЫЕ ВОПРОСЫ"]
        for nid in unhandled:
            line = self._format_answer_for_report(nid, answers[nid], fmt="text")
            if line:
                lines.append(f"  {line}")

        if len(lines) <= 1:
            return None

        return "\n".join(lines)

    # ============================================
    # Системный анализ для врача
    # ============================================

    def _check_trigger(self, trigger: dict, answer: Any) -> bool:
        """
        Проверка, сработал ли отдельный триггер для данного ответа.

        Поддерживаемые форматы answer_data:
        - {"selected": "value"}           — single_choice
        - {"selected": ["v1", "v2"]}     — multi_choice
        - {"value": 7}                    — slider / scale
        - {"locations": ["head", ...]}    — body_map
        - {"selected": true/false}        — consent / boolean
        - {"text": "свободный текст"}    — text_input
        """
        if not answer or not isinstance(answer, dict):
            return False

        option_value = trigger.get("option_value", "")
        match_mode = trigger.get("match_mode", "exact")

        # ── Режим «contains» — поиск подстроки (регистронезависимо) ──
        if match_mode == "contains":
            search = option_value.lower().strip()
            if not search:
                return False
            # Проверяем text (text_input)
            text = answer.get("text", "")
            if isinstance(text, str) and search in text.lower():
                return True
            # Проверяем selected (если строка)
            selected = answer.get("selected")
            if isinstance(selected, str) and search in selected.lower():
                return True
            # Проверяем additional_fields
            additional = answer.get("additional_fields", {})
            if isinstance(additional, dict):
                for val in additional.values():
                    if isinstance(val, str) and search in val.lower():
                        return True
            return False

        # ── Режим «gte» — числовое сравнение ≥ порога (слайдер / шкала) ──
        if match_mode == "gte":
            value = answer.get("value")
            if value is not None:
                try:
                    return float(value) >= float(option_value)
                except (ValueError, TypeError):
                    return False
            return False

        # ── Режим «exact» (по умолчанию) ──
        # Проверка поля selected (single_choice, multi_choice, consent)
        selected = answer.get("selected")
        if selected is not None:
            if isinstance(selected, list):
                return option_value in selected
            if isinstance(selected, bool):
                return str(selected).lower() == option_value.lower()
            return str(selected) == option_value

        # Проверка поля value (slider / scale)
        value = answer.get("value")
        if value is not None:
            try:
                return float(value) >= float(option_value)
            except (ValueError, TypeError):
                return str(value) == option_value

        # Проверка поля locations (body_map)
        locations = answer.get("locations")
        if isinstance(locations, list):
            return option_value in locations

        return False

    def _evaluate_analysis_rules_with_color(self, answers: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Оценка правил системного анализа по ответам пользователя (с цветом).

        Returns:
            Список словарей {'message': str, 'color': str, 'name': str}
            для сработавших правил.
        """
        rules = self.config.get("analysis_rules", [])
        if not rules:
            return []

        triggered: List[Dict[str, str]] = []

        for rule in rules:
            triggers = rule.get("triggers", [])
            if not triggers:
                continue

            mode = rule.get("trigger_mode", "any")
            message = rule.get("message", "").strip()
            if not message:
                continue

            if mode == "all":
                groups: Dict[str, List] = {}
                for t in triggers:
                    nid = t.get("node_id", "")
                    groups.setdefault(nid, []).append(t)

                fired = all(
                    any(
                        self._check_trigger(t, answers.get(t.get("node_id", "")))
                        for t in grp
                    )
                    for grp in groups.values()
                )
            else:
                fired = any(
                    self._check_trigger(t, answers.get(t.get("node_id", "")))
                    for t in triggers
                )

            if fired:
                triggered.append({
                    "message": message,
                    "color": rule.get("color", "red"),
                    "name": rule.get("name", ""),
                })

        return triggered

    # Палитра цветов для триггеров (HTML Битрикс24)
    TRIGGER_COLOR_MAP = {
        "red":    {"bg": "#fef2f2", "border": "#fca5a5", "text": "#991b1b", "emoji": "🔴"},
        "orange": {"bg": "#fff7ed", "border": "#fdba74", "text": "#9a3412", "emoji": "🟠"},
        "yellow": {"bg": "#fefce8", "border": "#fde047", "text": "#854d0e", "emoji": "🟡"},
        "green":  {"bg": "#f0fdf4", "border": "#86efac", "text": "#166534", "emoji": "🟢"},
    }

    AI_PRIORITY_COLOR_MAP = {
        "red": {"bg": "#fef2f2", "border": "#fca5a5", "text": "#991b1b", "emoji": "🔴"},
        "yellow": {"bg": "#fefce8", "border": "#fde047", "text": "#854d0e", "emoji": "🟡"},
        "green": {"bg": "#f0fdf4", "border": "#86efac", "text": "#166534", "emoji": "🟢"},
    }

    AI_DISCLAIMER = "ИИ-анализ является вспомогательным инструментом и не заменяет клиническое решение врача."
    AI_PRIORITY_LABELS = {
        "green": "удовлетворительный",
        "yellow": "Есть проблемы",
        "red": "Серьезные проблемы",
    }

    def _normalize_ai_analysis(self, ai_analysis: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Возвращает валидированный AI result в виде dict или None."""
        if not isinstance(ai_analysis, dict):
            return None
        if not ai_analysis.get("summary") or not ai_analysis.get("overall_priority"):
            return None
        return ai_analysis

    def _ai_priority_key(self, priority: str | None) -> str:
        key = str(priority or "yellow").lower()
        return key if key in self.AI_PRIORITY_COLOR_MAP else "yellow"

    def _ai_priority_label(self, priority: str | None) -> str:
        return self.AI_PRIORITY_LABELS[self._ai_priority_key(priority)]

    def _ai_palette(self, priority: str | None) -> Dict[str, str]:
        return self.AI_PRIORITY_COLOR_MAP[self._ai_priority_key(priority)]

    def _clean_ai_text(self, value: Any) -> str:
        """Очищает текст ИИ перед рендером, не пропуская генерационный мусор."""
        text = " ".join(str(value or "").split())
        if not text:
            return ""
        if len(text) >= 20:
            meaningful_chars = sum(1 for char in text if char.isalnum())
            bracket_chars = sum(1 for char in text if char in "{}[]()")
            if meaningful_chars == 0 or (bracket_chars >= 20 and meaningful_chars / len(text) < 0.15):
                return ""
            if re.search(r"(?:[\]\}\)\[\{\(][,;:.\s]*){20,}", text):
                return ""
        return text

    def _format_ai_evidence_readable(self, evidence: Any) -> str:
        """HTML-список оснований ИИ-вывода; все строки экранируются."""
        if not isinstance(evidence, list) or not evidence:
            return ""

        items: List[str] = []
        for item in evidence[:10]:
            if not isinstance(item, dict):
                continue
            question = self._escape_html(self._clean_ai_text(item.get("question", "")))
            answer = self._escape_html(self._clean_ai_text(item.get("answer", "")))
            if not question and not answer:
                continue
            items.append(
                '<li>'
                f'{question}: <strong>{answer}</strong>'
                '</li>'
            )
        if not items:
            return ""
        return '<ul style="margin:4px 0 0 16px">' + "".join(items) + "</ul>"

    def _format_ai_evidence_text(self, evidence: Any) -> List[str]:
        """Текстовые строки оснований ИИ-вывода для TXT fallback."""
        if not isinstance(evidence, list) or not evidence:
            return []

        lines: List[str] = []
        for item in evidence[:10]:
            if not isinstance(item, dict):
                continue
            question = self._escape_html(self._clean_ai_text(item.get("question", "")))
            answer = self._escape_html(self._clean_ai_text(item.get("answer", "")))
            if not question and not answer:
                continue
            lines.append(f"      Основание: {question} — {answer}")
        return lines

    def _format_ai_card_readable(
        self,
        *,
        title: str,
        description: str,
        priority: str,
        evidence: Any = None,
    ) -> str:
        palette = self._ai_palette(priority)
        title_html = self._escape_html(self._clean_ai_text(title))
        description_html = self._escape_html(self._clean_ai_text(description))
        if not title_html and not description_html:
            return ""
        evidence_html = self._format_ai_evidence_readable(evidence)
        return (
            f'<div style="background:{palette["bg"]};border-left:4px solid {palette["border"]};'
            f'padding:8px 10px;margin-bottom:7px;border-radius:6px;color:{palette["text"]};'
            f'font-size:8.5pt;line-height:1.55">'
            f'{palette["emoji"]} <strong>{title_html}</strong><br>{description_html}'
            f'{evidence_html}</div>'
        )

    def _generate_ai_analysis_block_readable(self, ai_analysis: Optional[Dict[str, Any]]) -> Optional[str]:
        """Генерация отдельного AI-блока для HTML preview/PDF выше rule-based анализа."""
        analysis = self._normalize_ai_analysis(ai_analysis)
        if not analysis:
            return None

        priority = str(analysis.get("overall_priority", "yellow"))
        palette = self._ai_palette(priority)
        priority_label = self._escape_html(self._ai_priority_label(priority))
        summary = self._escape_html(self._clean_ai_text(analysis.get("summary", "")))
        limitations_text = self._clean_ai_text(analysis.get("limitations", ""))
        limitations = self._escape_html(limitations_text or self.AI_DISCLAIMER)

        parts: List[str] = [
            '<div class="block ai-analysis-block" '
            f'style="border:1.5pt solid {palette["border"]};background:{palette["bg"]};margin-bottom:8px;">',
            '<div class="block-title" '
            f'style="background:{palette["bg"]};border-bottom:1pt solid {palette["border"]};'
            f'color:{palette["text"]};font-size:9.5pt;">🤖 ИИ-анализ для врача</div>',
            '<div class="block-body">',
            f'<p><strong>Общий приоритет:</strong> {palette["emoji"]} {priority_label}</p>',
            f'<p><strong>Краткое резюме:</strong> {summary}</p>',
        ]

        red_flags = analysis.get("red_flags") or []
        if isinstance(red_flags, list) and red_flags:
            parts.append("<h2>Красные флаги</h2>")
            for item in red_flags[:10]:
                if isinstance(item, dict):
                    parts.append(
                        self._format_ai_card_readable(
                            title=item.get("title", "Красный флаг"),
                            description=item.get("description", ""),
                            priority="red",
                            evidence=item.get("evidence"),
                        )
                    )

        key_findings = analysis.get("key_findings") or []
        if isinstance(key_findings, list) and key_findings:
            parts.append("<h2>Ключевые наблюдения</h2>")
            for item in key_findings[:10]:
                if isinstance(item, dict):
                    parts.append(
                        self._format_ai_card_readable(
                            title=item.get("title", "Наблюдение"),
                            description=item.get("description", ""),
                            priority=item.get("priority", "yellow"),
                            evidence=item.get("evidence"),
                        )
                    )

        recommendations = analysis.get("doctor_recommendations") or []
        if isinstance(recommendations, list) and recommendations:
            parts.append("<h2>Рекомендации врачу</h2>")
            recommendation_texts = [
                self._escape_html(self._clean_ai_text(item.get("text", "")))
                for item in recommendations[:10]
                if isinstance(item, dict) and self._clean_ai_text(item.get("text", ""))
            ]
            if recommendation_texts:
                parts.append(
                    "<p><strong>На что обратить внимание у пациента:</strong> "
                    + "; ".join(recommendation_texts)
                    + "</p>"
                )
            for item in recommendations[:10]:
                if not isinstance(item, dict):
                    continue
                rec_palette = self._ai_palette(item.get("priority", "yellow"))
                rec_label = self._escape_html(self._ai_priority_label(item.get("priority", "yellow")))
                text_html = self._escape_html(self._clean_ai_text(item.get("text", "")))
                if not text_html:
                    continue
                parts.append(
                    f'<div style="background:#fff;border-left:4px solid {rec_palette["border"]};'
                    f'padding:6px 9px;margin-bottom:6px;border-radius:6px;color:{rec_palette["text"]};'
                    f'font-size:8.5pt;line-height:1.5">{rec_palette["emoji"]} '
                    f'<strong>{rec_label}:</strong> {text_html}</div>'
                )

        parts.append(f'<p style="font-size:8pt;color:#64748b;"><em>{limitations}</em></p>')
        parts.append("</div></div>")
        return "".join(parts)

    def _generate_ai_analysis_block_text(self, ai_analysis: Optional[Dict[str, Any]]) -> Optional[str]:
        """Текстовый AI-блок для TXT fallback в Bitrix24."""
        analysis = self._normalize_ai_analysis(ai_analysis)
        if not analysis:
            return None

        lines: List[str] = [
            "🤖 ИИ-АНАЛИЗ ДЛЯ ВРАЧА",
            f"Общий приоритет: {self._ai_priority_label(analysis.get('overall_priority', 'yellow'))}",
            f"Краткое резюме: {self._escape_html(self._clean_ai_text(analysis.get('summary', '')))}",
        ]

        red_flags = analysis.get("red_flags") or []
        if isinstance(red_flags, list) and red_flags:
            lines.append("")
            lines.append("КРАСНЫЕ ФЛАГИ")
            for item in red_flags[:10]:
                if isinstance(item, dict):
                    lines.append(
                        f"  • {self._escape_html(self._clean_ai_text(item.get('title', 'Красный флаг')))}: "
                        f"{self._escape_html(self._clean_ai_text(item.get('description', '')))}"
                    )
                    lines.extend(self._format_ai_evidence_text(item.get("evidence")))

        key_findings = analysis.get("key_findings") or []
        if isinstance(key_findings, list) and key_findings:
            lines.append("")
            lines.append("КЛЮЧЕВЫЕ НАБЛЮДЕНИЯ")
            for item in key_findings[:10]:
                if isinstance(item, dict):
                    lines.append(
                        f"  • [{self._ai_priority_label(item.get('priority', 'yellow'))}] "
                        f"{self._escape_html(self._clean_ai_text(item.get('title', 'Наблюдение')))}: "
                        f"{self._escape_html(self._clean_ai_text(item.get('description', '')))}"
                    )
                    lines.extend(self._format_ai_evidence_text(item.get("evidence")))

        recommendations = analysis.get("doctor_recommendations") or []
        if isinstance(recommendations, list) and recommendations:
            lines.append("")
            lines.append("РЕКОМЕНДАЦИИ ВРАЧУ")
            recommendation_texts = [
                self._escape_html(self._clean_ai_text(item.get("text", "")))
                for item in recommendations[:10]
                if isinstance(item, dict) and self._clean_ai_text(item.get("text", ""))
            ]
            if recommendation_texts:
                lines.append("На что обратить внимание у пациента: " + "; ".join(recommendation_texts))
            for item in recommendations[:10]:
                if isinstance(item, dict):
                    lines.append(
                        f"  • [{self._ai_priority_label(item.get('priority', 'yellow'))}] "
                        f"{self._escape_html(self._clean_ai_text(item.get('text', '')))}"
                    )

        limitations = self._clean_ai_text(analysis.get("limitations")) or self.AI_DISCLAIMER
        if limitations:
            lines.append("")
            lines.append(f"Ограничения: {self._escape_html(limitations)}")

        return "\n".join(lines)

    def _generate_analysis_block_html(self, answers: Dict[str, Any]) -> Optional[str]:
        """
        Генерация HTML-блока «Системный анализ для врача» (формат Битрикс24).
        Каждый триггер — отдельный абзац с цветовым фоном.
        """
        triggered = self._evaluate_analysis_rules_with_color(answers)
        if not triggered:
            return None

        parts = ["⚠️ <b>СИСТЕМНЫЙ АНАЛИЗ ДЛЯ ВРАЧА:</b><br>"]
        for item in triggered:
            color = item.get("color", "red")
            palette = self.TRIGGER_COLOR_MAP.get(color, self.TRIGGER_COLOR_MAP["red"])
            name = self._escape_html(item.get("name") or "")
            message = self._escape_html(item.get("message") or "")
            label = f"<b>{name}</b>: " if name else ""
            parts.append(
                f'<div style="background:{palette["bg"]};border-left:4px solid {palette["border"]};'
                f'padding:8px 12px;margin-bottom:8px;border-radius:4px;color:{palette["text"]}">'
                f'{palette["emoji"]} {label}{message}</div>'
            )
        return "".join(parts)

    def _generate_analysis_block_readable(self, answers: Dict[str, Any]) -> Optional[str]:
        """
        Генерация читаемого HTML-блока анализа для предпросмотра / PDF.
        Каждый триггер — отдельная карточка с цветовым фоном.
        """
        triggered = self._evaluate_analysis_rules_with_color(answers)
        if not triggered:
            return None

        items_html = ""
        for item in triggered:
            color = item.get("color", "red")
            palette = self.TRIGGER_COLOR_MAP.get(color, self.TRIGGER_COLOR_MAP["red"])
            name = self._escape_html(item.get("name") or "")
            message = self._escape_html(item.get("message") or "")
            label = f"<strong>{name}:</strong> " if name else ""
            items_html += (
                f'<div class="analysis-trigger-card" style="background:{palette["bg"]};'
                f'border-left:4px solid {palette["border"]};padding:10px 14px;'
                f'margin-bottom:10px;border-radius:6px;color:{palette["text"]};'
                f'font-size:8.5pt;line-height:1.55">'
                f'{palette["emoji"]} {label}{message}</div>'
            )
        return (
            '<div class="block analysis-block">'
            '<div class="block-title">⚠️ СИСТЕМНЫЙ АНАЛИЗ ДЛЯ ВРАЧА</div>'
            f'<div class="block-body">{items_html}</div>'
            '</div>'
        )

    def _generate_analysis_block_text(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация текстового блока rule-based системного анализа."""
        triggered = self._evaluate_analysis_rules_with_color(answers)
        if not triggered:
            return None

        lines = ["⚠️ СИСТЕМНЫЙ АНАЛИЗ ДЛЯ ВРАЧА"]
        for item in triggered:
            color = item.get("color", "red")
            palette = self.TRIGGER_COLOR_MAP.get(color, self.TRIGGER_COLOR_MAP["red"])
            name = item.get("name") or ""
            message = item.get("message") or ""
            prefix = f"{palette['emoji']} "
            if name:
                lines.append(f"  • {prefix}{name}: {message}")
            else:
                lines.append(f"  • {prefix}{message}")
        return "\n".join(lines)
    
    # ============================================
    # Группировка вопросов для структурированного отчёта
    # ============================================

    def _get_groups(self) -> List[dict]:
        """Получение списка групп из конфигурации опросника."""
        return self.config.get("groups", []) or []

    def _get_nodes_in_report_order(self) -> List[dict]:
        """
        Возвращает узлы в порядке визуального редактора.

        Если у узла есть координаты на canvas, используем их и сортируем сверху
        вниз, а при равной высоте слева направо. Если координат нет, сохраняем
        исходный порядок узлов в конфигурации.
        """
        indexed_nodes = list(enumerate(self.config.get("nodes", []) or []))

        def sort_key(item: tuple[int, dict]) -> tuple[float, float, int]:
            index, node = item
            position = node.get("position") or {}
            x = position.get("x")
            y = position.get("y")

            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                return (float(y), float(x), index)

            return (float(index), 0.0, index)

        return [node for _, node in sorted(indexed_nodes, key=sort_key)]

    def _group_node_ids(self) -> Dict[str, str]:
        """
        Построение маппинга node_id -> group_id из конфигурации.

        Returns:
            Словарь {node_id: group_id}
        """
        mapping: Dict[str, str] = {}
        for node in self._get_nodes_in_report_order():
            gid = node.get("group_id")
            if gid:
                mapping[node["id"]] = gid
        return mapping

    def _generate_grouped_answers(
        self, answers: Dict[str, Any], fmt: str = "html"
    ) -> tuple:
        """
        Генерация ответов, разделённых на группированные и негруппированные.

        Args:
            answers: Словарь ответов {node_id: answer_data}
            fmt: Формат вывода — "html", "readable", "text"

        Returns:
            (группированные_блоки, негруппированные_ответы)
            – grouped: список туплов (group_name, items)
            – ungrouped: список форматированных строк
        """
        groups = self._get_groups()
        node_group_map = self._group_node_ids()
        group_map = {g["id"]: g["name"] for g in groups}

        # Собираем ответы по группам в порядке конфигурации
        grouped: Dict[str, List[str]] = {g["id"]: [] for g in groups}
        ungrouped: List[str] = []

        for node in self._get_nodes_in_report_order():
            node_id = node.get("id", "")
            if node_id not in answers:
                continue
            line = self._format_answer_for_report(node_id, answers[node_id], fmt=fmt)
            if not line:
                continue

            gid = node_group_map.get(node_id)
            if gid and gid in grouped:
                grouped[gid].append(line)
            else:
                ungrouped.append(line)

        # Собираем непустые группы с сохранением порядка
        result_groups = []
        for g in groups:
            items = grouped.get(g["id"], [])
            if items:
                result_groups.append((group_map[g["id"]], items))

        return result_groups, ungrouped

    def generate_readable_html_report(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
        ai_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Генерация читаемого HTML-отчёта для просмотра и экспорта.
        Всегда использует единый compact/V2 стиль, в том числе для
        новых кастомных опросников из редактора.
        
        Args:
            patient_name: Имя пациента
            answers: Словарь ответов {node_id: answer_data}
            
        Returns:
            Полный HTML-документ с встроенными стилями
        """
        return self._generate_readable_html_report_v2(patient_name, answers, ai_analysis)
    
    def _generate_readable_html_report_v1(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
        ai_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Генерация читаемого HTML-отчёта для v1 опросника."""
        # Генерируем содержимое
        content_parts = []
        
        # Заголовок
        name = patient_name or "Не указано"
        name_html = self._escape_html(name)
        date = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        content_parts.append(f"""
        <div class="header">
            <h1>📋 АНКЕТА ПАЦИЕНТА</h1>
            <p class="subtitle">Предварительный опрос</p>
            <div class="patient-info">
                <div><strong>Пациент:</strong> {name_html}</div>
                <div><strong>Дата:</strong> {date}</div>
            </div>
        </div>
        """)
        
        # ИИ-анализ для врача — отдельный вспомогательный блок выше rule-based анализа.
        ai_analysis_html = self._generate_ai_analysis_block_readable(ai_analysis)
        if ai_analysis_html:
            content_parts.append(ai_analysis_html)

        # Системный анализ для врача (rule-based, ниже AI-блока)
        analysis_html = self._generate_analysis_block_readable(answers)
        if analysis_html:
            content_parts.append(analysis_html)
        
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
        
        # Fallback: необработанные ответы (v1)
        unhandled_readable = self._generate_unhandled_block_readable(
            answers, self.V1_HANDLED_NODE_IDS
        )
        if unhandled_readable:
            content_parts.append(
                f'<div class="section"><h2>📝 Дополнительные вопросы</h2>{unhandled_readable}</div>'
            )
        
        # Собираем полный HTML документ
        html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Анкета пациента - {name_html}</title>
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
        ai_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Генерация читаемого HTML-отчёта для v2 опросника — один лист А4.

        Ответы группируются по настроенным группам, остаток в «Результаты опроса».
        """
        name = patient_name or "Не указано"
        date = datetime.now().strftime("%d.%m.%Y %H:%M")

        # ИИ-анализ для врача — отдельный вспомогательный блок выше rule-based анализа.
        ai_analysis_html = self._generate_ai_analysis_block_readable(ai_analysis) or ""

        # Системный анализ для врача
        analysis_html = self._generate_analysis_block_readable(answers) or ""

        # Группировка ответов
        grouped, ungrouped = self._generate_grouped_answers(answers, fmt="readable")

        # Блоки групп (строго над «Результаты опроса»)
        groups_html = ""
        for group_name, items in grouped:
            group_name_html = self._escape_html(group_name)
            groups_html += (
                '<div class="block">'
                f'<div class="block-title">📁 {group_name_html}</div>'
                '<div class="block-body"><ul>'
                + "".join(items)
                + '</ul></div>'
                '</div>'
            )

        # Блок «Результаты опроса» (скрывается если пустой)
        answers_html = ""
        if ungrouped:
            answers_html = (
                '<div class="block">'
                '<div class="block-title">📋 Результаты опроса</div>'
                '<div class="block-body"><ul>'
                + "".join(ungrouped)
                + '</ul></div>'
                '</div>'
            )

        section_html = ai_analysis_html + analysis_html + groups_html + answers_html
        html = self._wrap_in_html_document_compact(name, date, section_html)
        return html
    
    def _wrap_in_html_document_compact(self, patient_name: str, date: str, sections_html: str) -> str:
        """Компактный HTML-документ для вывода на одном листе А4."""
        patient_name_html = self._escape_html(patient_name)
        return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Анкета — {patient_name_html}</title>
    <style>
        @page {{ size: A4; margin: 8mm 10mm; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: Arial, sans-serif;
            font-size: 9pt;
            line-height: 1.6;
            color: #1a1a1a;
            background: #fff;
        }}
        .page {{
            width: 190mm;
            margin: 0 auto;
        }}
        /* ── Шапка ── */
        .report-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1.5pt solid #1d4ed8;
            padding-bottom: 5px;
            margin-bottom: 8px;
        }}
        .report-header h1 {{
            font-size: 11pt;
            font-weight: 700;
            color: #1d4ed8;
            letter-spacing: 0.3px;
        }}
        .report-meta {{
            font-size: 8pt;
            color: #555;
            text-align: right;
            line-height: 1.7;
        }}
        /* ── Блоки ── */
        .block {{
            border: 0.75pt solid #cbd5e1;
            border-radius: 4px;
            margin-bottom: 7px;
            page-break-inside: avoid;
        }}
        .block-title {{
            background: #eff6ff;
            border-bottom: 0.75pt solid #bfdbfe;
            padding: 4px 8px;
            font-size: 9pt;
            font-weight: 700;
            color: #1e40af;
            letter-spacing: 0.2px;
        }}
        .block-body {{
            padding: 5px 8px 6px;
        }}
        /* ── Подблоки внутри (h2) ── */
        .block-body h2 {{
            font-size: 8.5pt;
            font-weight: 700;
            color: #374151;
            margin-top: 7px;
            margin-bottom: 2px;
            border-bottom: 0.5pt solid #e5e7eb;
            padding-bottom: 2px;
        }}
        .block-body h2:first-child {{ margin-top: 0; }}
        .block-body p {{
            font-size: 8.5pt;
            margin-bottom: 3px;
            color: #1a1a1a;
            line-height: 1.55;
        }}
        .block-body ul {{
            margin: 2px 0 4px 14px;
            padding: 0;
        }}
        .block-body li {{
            font-size: 8.5pt;
            margin-bottom: 2px;
            color: #1a1a1a;
            line-height: 1.55;
            list-style: disc;
        }}
        .block-body li.qa-row {{
            list-style: none;
            display: block;
            margin-left: -14px;
            margin-bottom: 5px;
            padding: 5px 6px 6px;
            border: 0.75pt solid #e2e8f0;
            border-radius: 7px;
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            box-shadow: 0 1px 0 rgba(148, 163, 184, 0.08);
            page-break-inside: avoid;
        }}
        .block-body .qa-kicker {{
            display: inline-block;
            margin-bottom: 2px;
            padding: 1px 6px;
            font-size: 6.7pt;
            font-weight: 700;
            letter-spacing: 0.2px;
            text-transform: uppercase;
            color: #0f766e;
            background: #ecfeff;
            border-radius: 999px;
        }}
        .block-body .qa-question {{
            display: block;
            font-size: 8.9pt;
            font-weight: 400;
            line-height: 1.42;
            margin-bottom: 3px;
            color: #334155;
            word-break: break-word;
        }}
        .block-body .qa-answer-kicker {{
            color: #1d4ed8;
            background: #eff6ff;
            margin-bottom: 2px;
        }}
        .block-body .qa-answer {{
            display: block;
            font-size: 9.8pt;
            font-weight: 700;
            line-height: 1.4;
            text-align: left;
            padding: 4px 6px;
            border-radius: 6px;
            background: #f8fafc;
            border: 0.75pt solid #dbeafe;
            color: #0f172a;
            word-break: break-word;
        }}
        .block-body .qa-extra {{
            display: block;
            font-size: 7.8pt;
            line-height: 1.45;
            margin-top: 3px;
            color: #64748b;
        }}
        /* ── Системный анализ для врача ── */
        .analysis-block {{
            border: 1.5pt solid #f59e0b;
            background: #fffbeb;
            margin-bottom: 8px;
        }}
        .analysis-block .block-title {{
            background: #fef3c7;
            border-bottom: 1pt solid #fcd34d;
            color: #92400e;
            font-size: 9.5pt;
        }}
        .analysis-block .block-body ul {{
            margin: 3px 0 3px 16px;
        }}
        .analysis-block .block-body li {{
            color: #78350f;
            font-weight: 500;
            font-size: 8.5pt;
            margin-bottom: 3px;
        }}
        /* ── Алерты ── */
        .alert-block {{
            background: #fff7ed;
            border: 0.75pt solid #fed7aa;
        }}
        .alert-block .block-title {{
            background: #fff7ed;
            border-bottom-color: #fed7aa;
            color: #9a3412;
        }}
        .alert-item {{
            background: #fff;
            border-left: 2pt solid #f59e0b;
            padding: 4px 7px;
            margin-bottom: 4px;
            font-size: 8pt;
            line-height: 1.5;
            border-radius: 0 2px 2px 0;
        }}
        .alert-item:last-child {{ margin-bottom: 0; }}
        /* Интенсивность */
        .badge {{
            display: inline-block;
            background: #fee2e2;
            color: #991b1b;
            border-radius: 2px;
            padding: 1px 5px;
            font-size: 8pt;
            font-weight: 600;
        }}
        strong {{ font-weight: 700; }}
        @media print {{
            body {{ background: white; }}
            .block {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
<div class="page">
    <div class="report-header">
        <h1>📋 АНКЕТА ПАЦИЕНТА</h1>
        <div class="report-meta">
            <div><strong>Пациент:</strong> {patient_name_html}</div>
            <div><strong>Дата:</strong> {date}</div>
        </div>
    </div>
    {sections_html}
</div>
</body>
</html>"""

    def generate_text_report(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
        ai_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Генерация текстового отчёта для экспорта в TXT.
        Использует единый V2-порядок/группировку ответов.
        
        Args:
            patient_name: Имя пациента
            answers: Словарь ответов {node_id: answer_data}
            
        Returns:
            Текстовая строка отчёта
        """
        return self._generate_text_report_v2(patient_name, answers, ai_analysis)
    
    def _generate_text_report_v1(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
        ai_analysis: Optional[Dict[str, Any]] = None,
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

        ai_text = self._generate_ai_analysis_block_text(ai_analysis)
        if ai_text:
            lines.append(ai_text)
            lines.append("")

        system_analysis = self._generate_analysis_block_text(answers)
        if system_analysis:
            lines.append(system_analysis)
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
        
        # Fallback: необработанные ответы (v1)
        unhandled_text = self._generate_unhandled_block_text(
            answers, self.V1_HANDLED_NODE_IDS
        )
        if unhandled_text:
            lines.append(unhandled_text)
            lines.append("")
        
        lines.append("=" * 70)
        lines.append("Конец отчёта")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def _generate_text_report_v2(
        self,
        patient_name: Optional[str],
        answers: Dict[str, Any],
        ai_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Генерация текстового отчёта для v2 опросника.

        Ответы выводятся в порядке узлов конфигурации опросника.
        """
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

        ai_text = self._generate_ai_analysis_block_text(ai_analysis)
        if ai_text:
            lines.append(ai_text)
            lines.append("")

        system_analysis = self._generate_analysis_block_text(answers)
        if system_analysis:
            lines.append(system_analysis)
            lines.append("")
        
        # Группированные ответы
        grouped, ungrouped = self._generate_grouped_answers(answers, fmt="text")

        for group_name, items in grouped:
            lines.append(f"📁 {group_name.upper()}:")
            lines.extend(items)
            lines.append("")

        # Остаток — «Результаты опроса» (скрывается если пустой)
        if ungrouped:
            lines.append("📋 РЕЗУЛЬТАТЫ ОПРОСА:")
            lines.extend(ungrouped)
            lines.append("")
        
        lines.append("=" * 70)
        lines.append("Конец отчёта")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def _generate_header(self, patient_name: Optional[str]) -> str:
        """Генерация заголовка отчёта."""
        name = patient_name or "Не указано"
        name_html = self._escape_html(name)
        date = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        return (
            f"<b>📋 АНКЕТА ПАЦИЕНТА</b> (Предварительный опрос)<br>"
            f"<b>Пациент:</b> {name_html}<br>"
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
        
        complaint_text = self._escape_html(complaints_map.get(selected, selected))
        
        return f"📌 <b>ОСНОВНАЯ ПРИЧИНА ОБРАЩЕНИЯ:</b> {complaint_text}"
    
    def _generate_pain_details(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока детализации боли."""
        pain_data = answers.get("pain_details", {})
        
        if not pain_data:
            return None
        
        parts = ["🩺 <b>ХАРАКТЕРИСТИКА БОЛИ:</b>"]
        
        # Локализация
        loc_names = self._format_body_locations(pain_data.get("locations"))
        if loc_names:
            parts.append(f"• <b>Локализация:</b> {self._escape_html(loc_names)}")
        
        # Интенсивность
        intensity = pain_data.get("intensity")
        if intensity:
            parts.append(f"• <b>Интенсивность:</b> {self._escape_html(intensity)}/10")
        
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
                    resp_parts.append(f"• 🚬 Стаж курения: {self._escape_html(smoking_years)} лет")
                
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
                    cardio_parts.append(f"• {self._escape_html(edema_map.get(edema, edema))}")
                
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
            parts.append(f"  └ Детали: {self._escape_html(allergy_details)}")
        
        return "<br>".join(parts)
    
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
        
        complaint_text = self._escape_html(complaints_map.get(selected, selected))
        
        return f"<h2>📌 Основная причина обращения</h2><p><strong>{complaint_text}</strong></p>"
    
    def _generate_readable_pain_details(self, answers: Dict[str, Any]) -> Optional[str]:
        """Генерация блока детализации боли для читаемого формата."""
        pain_data = answers.get("pain_details", {})
        
        if not pain_data:
            return None
        
        parts = ["<h2>🩺 Характеристика боли</h2>"]
        
        # Локализация
        loc_names = self._format_body_locations(pain_data.get("locations"))
        if loc_names:
            parts.append(f"<p><strong>Локализация:</strong> {self._escape_html(loc_names)}</p>")
        
        # Интенсивность
        intensity = pain_data.get("intensity")
        if intensity:
            parts.append(f'<p><strong>Интенсивность:</strong> <span class="intensity-badge">{self._escape_html(intensity)}/10</span></p>')
        
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
                    parts.append(f'<li>🚬 Стаж курения: <strong>{self._escape_html(smoking_years)} лет</strong></li>')
                
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
                    parts.append(f"<li>{self._escape_html(edema_map.get(edema, edema))}</li>")
                
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
            parts.append(f"<p><em>Детали аллергии: {self._escape_html(allergy_details)}</em></p>")
        
        return "".join(parts)
    
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
        
        loc_names = self._format_body_locations(pain_data.get("locations"))
        if loc_names:
            lines.append(f"  • Локализация: {loc_names}")
        
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
