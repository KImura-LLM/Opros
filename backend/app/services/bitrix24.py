# ============================================
# Bitrix24 Client - Клиент интеграции
# ============================================
"""
HTTP-клиент для отправки данных в Битрикс24.
"""

import httpx
from typing import Optional
from loguru import logger

from app.core.config import settings


class Bitrix24Client:
    """
    Клиент для взаимодействия с REST API Битрикс24.
    
    Использует входящий вебхук для отправки комментариев
    в ленту сделок/лидов.
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Инициализация клиента.
        
        Args:
            webhook_url: URL входящего вебхука (если не указан, берётся из settings)
        """
        self.webhook_url = webhook_url or settings.BITRIX24_WEBHOOK_URL
        self.timeout = 30.0
    
    async def send_comment(
        self,
        entity_id: int,
        entity_type: str,
        comment: str,
    ) -> bool:
        """
        Отправка комментария в ленту сущности (сделки/лида).
        
        Метод API: crm.timeline.comment.add
        
        Args:
            entity_id: ID сделки или лида
            entity_type: Тип сущности ('DEAL' или 'LEAD')
            comment: HTML-текст комментария
            
        Returns:
            True если успешно, False при ошибке
        """
        if not self.webhook_url:
            logger.warning("BITRIX24_WEBHOOK_URL не настроен, пропускаем отправку")
            return False
        
        # Формирование URL метода
        method_url = f"{self.webhook_url.rstrip('/')}/crm.timeline.comment.add"
        
        # Параметры запроса
        # Битрикс24 использует числовые коды для типов сущностей
        entity_type_map = {
            "DEAL": "deal",
            "LEAD": "lead",
        }
        
        payload = {
            "fields": {
                "ENTITY_ID": entity_id,
                "ENTITY_TYPE": entity_type_map.get(entity_type, "deal"),
                "COMMENT": comment,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(method_url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("result"):
                    logger.info(
                        f"Комментарий отправлен в Битрикс24: "
                        f"entity_type={entity_type}, entity_id={entity_id}"
                    )
                    return True
                else:
                    error = result.get("error_description", "Неизвестная ошибка")
                    logger.error(f"Ошибка Битрикс24: {error}")
                    return False
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при отправке в Битрикс24: {e}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Ошибка соединения с Битрикс24: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке в Битрикс24: {e}")
            return False
    
    async def update_deal_field(
        self,
        deal_id: int,
        fields: dict,
    ) -> bool:
        """
        Обновление полей сделки.
        
        Метод API: crm.deal.update
        
        Args:
            deal_id: ID сделки
            fields: Словарь полей для обновления
            
        Returns:
            True если успешно
        """
        if not self.webhook_url:
            logger.warning("BITRIX24_WEBHOOK_URL не настроен")
            return False
        
        method_url = f"{self.webhook_url.rstrip('/')}/crm.deal.update"
        
        payload = {
            "id": deal_id,
            "fields": fields,
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(method_url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                return result.get("result", False)
                
        except Exception as e:
            logger.error(f"Ошибка обновления сделки в Битрикс24: {e}")
            return False
    
    async def get_deal(self, deal_id: int) -> Optional[dict]:
        """
        Получение данных сделки.
        
        Метод API: crm.deal.get
        
        Args:
            deal_id: ID сделки
            
        Returns:
            Данные сделки или None
        """
        if not self.webhook_url:
            return None
        
        method_url = f"{self.webhook_url.rstrip('/')}/crm.deal.get"
        
        payload = {"id": deal_id}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(method_url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                return result.get("result")
                
        except Exception as e:
            logger.error(f"Ошибка получения сделки из Битрикс24: {e}")
            return None
