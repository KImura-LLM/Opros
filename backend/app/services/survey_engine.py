# ============================================
# Survey Engine - Движок опросника
# ============================================
"""
Логика навигации по опроснику.
Обрабатывает ветвления и условные переходы.
"""

from typing import Any, Dict, List, Optional
from loguru import logger


class SurveyEngine:
    """
    Движок для обработки логики опросника.
    
    Отвечает за:
    - Определение следующего узла на основе ответа
    - Обработку условий ветвления
    - Расчёт прогресса
    """
    
    def __init__(self, config: dict):
        """
        Инициализация движка.
        
        Args:
            config: JSON-конфигурация опросника
        """
        self.config = config
        self.nodes = {node["id"]: node for node in config.get("nodes", [])}
        self.start_node = config.get("start_node", "welcome")
    
    def get_node(self, node_id: str) -> Optional[dict]:
        """
        Получение узла по ID.
        
        Args:
            node_id: ID узла
            
        Returns:
            Данные узла или None
        """
        return self.nodes.get(node_id)
    
    def get_next_node(
        self,
        current_node_id: str,
        answer: dict,
        all_answers: Dict[str, Any],
    ) -> Optional[str]:
        """
        Определение следующего узла на основе ответа.
        
        Args:
            current_node_id: ID текущего узла
            answer: Ответ на текущий вопрос
            all_answers: Все предыдущие ответы
            
        Returns:
            ID следующего узла или None (конец опроса)
        """
        node = self.get_node(current_node_id)
        if not node:
            logger.warning(f"Узел не найден: {current_node_id}")
            return None
        
        logic = node.get("logic", [])
        
        if not logic:
            # Если нет логики, ищем следующий узел по порядку
            return self._get_default_next_node(current_node_id)
        
        # Обработка условий
        for rule in logic:
            if rule.get("default", False):
                continue  # Пропускаем default, обработаем в конце
            
            condition = rule.get("condition")
            if condition and self._evaluate_condition(condition, answer, all_answers):
                next_node = rule.get("next_node")
                logger.debug(f"Условие выполнено: {condition} -> {next_node}")
                return next_node
        
        # Ищем default переход
        for rule in logic:
            if rule.get("default", False):
                return rule.get("next_node")
        
        # Fallback - следующий по порядку
        return self._get_default_next_node(current_node_id)
    
    def _evaluate_condition(
        self,
        condition: str,
        answer: dict,
        all_answers: Dict[str, Any],
    ) -> bool:
        """
        Вычисление условия.
        
        Поддерживаемые форматы условий:
        - "selected == 'value'" - для single_choice
        - "selected contains 'value'" - для multi_choice
        - "value > 5" - для scale/number
        
        Args:
            condition: Строка условия
            answer: Текущий ответ
            all_answers: Все ответы
            
        Returns:
            True если условие выполнено
        """
        try:
            # Простой парсер условий
            condition = condition.strip()
            
            # Обработка "selected == 'value'"
            if "==" in condition:
                parts = condition.split("==")
                field = parts[0].strip()
                expected = parts[1].strip().strip("'\"")
                
                actual = self._get_answer_value(field, answer)
                return str(actual) == expected
            
            # Обработка "selected contains 'value'"
            if "contains" in condition:
                parts = condition.split("contains")
                field = parts[0].strip()
                expected = parts[1].strip().strip("'\"")
                
                actual = self._get_answer_value(field, answer)
                if isinstance(actual, list):
                    return expected in actual
                return expected in str(actual)
            
            # Обработка "value > N"
            if ">" in condition:
                parts = condition.split(">")
                field = parts[0].strip()
                threshold = int(parts[1].strip())
                
                actual = self._get_answer_value(field, answer)
                return int(actual) > threshold if actual else False
            
            # Обработка "value < N"
            if "<" in condition:
                parts = condition.split("<")
                field = parts[0].strip()
                threshold = int(parts[1].strip())
                
                actual = self._get_answer_value(field, answer)
                return int(actual) < threshold if actual else False
            
            # Обработка "answer_node_id.field == 'value'" (проверка предыдущих ответов)
            if "." in condition.split("==")[0] if "==" in condition else False:
                parts = condition.split("==")
                node_field = parts[0].strip()
                expected = parts[1].strip().strip("'\"")
                
                node_id, field = node_field.rsplit(".", 1)
                prev_answer = all_answers.get(node_id, {})
                actual = self._get_answer_value(field, prev_answer)
                return str(actual) == expected
            
            logger.warning(f"Неподдерживаемый формат условия: {condition}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка вычисления условия '{condition}': {e}")
            return False
    
    def _get_answer_value(self, field: str, answer: dict) -> Any:
        """
        Извлечение значения из ответа.
        
        Args:
            field: Название поля
            answer: Данные ответа
            
        Returns:
            Значение поля
        """
        if field == "selected":
            return answer.get("selected")
        if field == "value":
            return answer.get("value")
        if field == "text":
            return answer.get("text")
        return answer.get(field)
    
    def _get_default_next_node(self, current_node_id: str) -> Optional[str]:
        """
        Получение следующего узла по умолчанию (по порядку в списке).
        
        Args:
            current_node_id: ID текущего узла
            
        Returns:
            ID следующего узла или None
        """
        nodes_list = self.config.get("nodes", [])
        
        for i, node in enumerate(nodes_list):
            if node["id"] == current_node_id:
                if i + 1 < len(nodes_list):
                    return nodes_list[i + 1]["id"]
                return None  # Конец опроса
        
        return None
    
    def calculate_progress(self, answered_nodes: List[str]) -> float:
        """
        Расчёт прогресса прохождения.
        
        Args:
            answered_nodes: Список отвеченных узлов
            
        Returns:
            Процент прохождения (0-100)
        """
        total = len(self.nodes)
        if total == 0:
            return 100.0
        
        # Исключаем info_screen из подсчёта
        countable_nodes = [
            n for n in self.nodes.values()
            if n.get("type") != "info_screen"
        ]
        
        total_countable = len(countable_nodes)
        if total_countable == 0:
            return 100.0
        
        answered = len([n for n in answered_nodes if n in self.nodes])
        return min(100.0, (answered / total_countable) * 100)
    
    def get_branch_stack(self, answer: dict, all_answers: Dict[str, Any]) -> List[str]:
        """
        Получение стека веток для множественного выбора.
        
        Используется когда нужно показать несколько веток
        в зависимости от multi_choice ответа.
        
        Args:
            answer: Ответ с множественным выбором
            all_answers: Все ответы
            
        Returns:
            Список ID узлов для показа
        """
        selected = answer.get("selected", [])
        if not isinstance(selected, list):
            return []
        
        # Маппинг выбора на ветки (из конфига)
        branch_mapping = self.config.get("branch_mapping", {})
        
        branches = []
        for option in selected:
            if option in branch_mapping:
                branches.append(branch_mapping[option])
        
        return branches
