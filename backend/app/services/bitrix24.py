# ============================================
# Bitrix24 Client - Клиент интеграции
# ============================================
"""
HTTP-клиент для отправки данных в Битрикс24.
Поддерживает:
- Отправку комментариев в ленту сущностей
- Загрузку файлов (PDF-отчётов) на диск
- Прикрепление файлов к карточке сделки/лида
"""

import base64
import httpx
from datetime import datetime
from io import BytesIO
from typing import Optional
from zoneinfo import ZoneInfo
from loguru import logger

from app.core.config import settings
from app.core.log_utils import mask_name


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
        
        entity_type_normalized = (entity_type or "DEAL").upper()
        if entity_type_normalized not in entity_type_map:
            entity_type_normalized = "DEAL"

        payload = {
            "fields": {
                "ENTITY_ID": entity_id,
                "ENTITY_TYPE": entity_type_map[entity_type_normalized],
                "COMMENT": comment,
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(method_url, json=payload)
                response.raise_for_status()
                
                result = response.json()

                if "error" in result:
                    error = result.get("error_description", result.get("error", "Неизвестная ошибка"))
                    logger.error(
                        f"Ошибка Битрикс24 при добавлении комментария: {error} "
                        f"(error={result.get('error')}, entity_type={entity_type_normalized}, entity_id={entity_id})"
                    )
                    return False

                raw_result = result.get("result")
                if isinstance(raw_result, int) and raw_result > 0:
                    logger.info(
                        f"Комментарий отправлен в Битрикс24: "
                        f"comment_id={raw_result}, entity_type={entity_type_normalized}, entity_id={entity_id}"
                    )
                    return True

                logger.warning(
                    "Неожиданный ответ Bitrix crm.timeline.comment.add: "
                    f"result={raw_result!r} (type={type(raw_result).__name__}), "
                    f"entity_type={entity_type_normalized}, entity_id={entity_id}, response={result}"
                )
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

    async def update_lead_field(
        self,
        lead_id: int,
        fields: dict,
    ) -> bool:
        """
        Обновление полей лида.

        Метод API: crm.lead.update

        Args:
            lead_id: ID лида
            fields: Словарь полей для обновления

        Returns:
            True если успешно
        """
        if not self.webhook_url:
            logger.warning("BITRIX24_WEBHOOK_URL не настроен")
            return False

        method_url = f"{self.webhook_url.rstrip('/')}/crm.lead.update"

        payload = {
            "id": lead_id,
            "fields": fields,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(method_url, json=payload)
                response.raise_for_status()

                result = response.json()
                return bool(result.get("result", False))

        except Exception as e:
            logger.error(f"Ошибка обновления лида в Битрикс24: {e}")
            return False

    async def update_entity_field(
        self,
        entity_id: int,
        entity_type: str,
        fields: dict,
    ) -> bool:
        """
        Универсальное обновление полей сущности (сделка или лид).

        Маршрутизирует вызов на crm.deal.update или crm.lead.update
        в зависимости от типа сущности.

        Args:
            entity_id: ID сделки или лида
            entity_type: Тип сущности ('DEAL' или 'LEAD')
            fields: Словарь полей для обновления

        Returns:
            True если успешно
        """
        entity_type_upper = (entity_type or "DEAL").upper()
        if entity_type_upper == "LEAD":
            return await self.update_lead_field(lead_id=entity_id, fields=fields)
        return await self.update_deal_field(deal_id=entity_id, fields=fields)

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

    async def get_contact(self, contact_id: int) -> Optional[dict]:
        """
        Получение данных контакта.
        
        Метод API: crm.contact.get
        
        Args:
            contact_id: ID контакта
            
        Returns:
            Данные контакта или None
        """
        if not self.webhook_url:
            return None
        
        method_url = f"{self.webhook_url.rstrip('/')}/crm.contact.get"
        payload = {"id": contact_id}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(method_url, json=payload)
                response.raise_for_status()
                return response.json().get("result")
        except Exception as e:
            logger.error(f"Ошибка получения контакта из Битрикс24: {e}")
            return None

    async def get_patient_name_from_deal(self, deal_id: int) -> Optional[str]:
        """
        Получение ФИО пациента (контакта) из сделки.
        
        1. Получаем сделку → берём CONTACT_ID
        2. Получаем контакт → берём NAME + LAST_NAME
        
        Args:
            deal_id: ID сделки
            
        Returns:
            ФИО контакта или None
        """
        deal = await self.get_deal(deal_id)
        if not deal:
            logger.warning(f"Не удалось получить сделку {deal_id} для извлечения имени")
            return None
        
        contact_id = deal.get("CONTACT_ID")
        if not contact_id:
            logger.warning(f"В сделке {deal_id} не указан контакт (CONTACT_ID)")
            return None
        
        contact = await self.get_contact(int(contact_id))
        if not contact:
            logger.warning(f"Не удалось получить контакт {contact_id}")
            return None
        
        name = contact.get("NAME", "")
        last_name = contact.get("LAST_NAME", "")
        full_name = f"{name} {last_name}".strip()
        
        if full_name:
            logger.info(f"Имя пациента из Битрикс24: {mask_name(full_name)} (сделка {deal_id})")
        
        return full_name or None

    async def upload_pdf_to_entity(
        self,
        entity_id: int,
        entity_type: str,
        pdf_bytes: bytes,
        filename: str,
    ) -> bool:
        """
        Загрузка PDF-отчёта в карточку сделки/лида через crm.timeline.comment.add
        с вложенным файлом (base64).
        
        Альтернативный подход: загрузка через disk.folder.uploadfile
        и прикрепление через crm.deal.update (UF_CRM_xxx).
        
        Здесь используем наиболее универсальный метод:
        1. Загрузка файла через REST (crm.activity.add с STORAGE_TYPE_DISK)
        2. Или через комментарий с base64-вложением
        
        Args:
            entity_id: ID сделки или лида
            entity_type: Тип сущности ('DEAL' или 'LEAD')
            pdf_bytes: Содержимое PDF-файла
            filename: Имя файла
            
        Returns:
            True если успешно, False при ошибке
        """
        if not self.webhook_url:
            logger.warning("BITRIX24_WEBHOOK_URL не настроен, пропускаем загрузку PDF")
            return False
        
        # Кодируем PDF в base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        
        # Метод 1: Создание дела (активности) с файлом
        success = await self._upload_via_activity(
            entity_id=entity_id,
            entity_type=entity_type,
            pdf_base64=pdf_base64,
            filename=filename,
        )
        
        if success:
            return True
        
        # Метод 2 (fallback): Комментарий со ссылкой на файл
        logger.warning("Не удалось загрузить PDF через активность, пробуем через комментарий")
        return await self._upload_via_comment_with_file(
            entity_id=entity_id,
            entity_type=entity_type,
            pdf_base64=pdf_base64,
            filename=filename,
        )
    
    async def _upload_via_activity(
        self,
        entity_id: int,
        entity_type: str,
        pdf_base64: str,
        filename: str,
    ) -> bool:
        """
        Загрузка PDF через crm.activity.add (создание дела с вложением).
        
        Этот метод создаёт «Дело» (активность) в карточке сделки/лида
        с прикреплённым PDF-файлом. Файл будет виден в ленте и во вкладке «Дела».
        """
        method_url = f"{self.webhook_url.rstrip('/')}/crm.activity.add"
        
        # Маппинг типов сущностей в ID Битрикс24
        owner_type_id = 2 if entity_type.upper() == "DEAL" else 1  # 2=DEAL, 1=LEAD
        
        payload = {
            "fields": {
                "OWNER_TYPE_ID": owner_type_id,
                "OWNER_ID": entity_id,
                "TYPE_ID": 4,  # 4 = Email (позволяет прикреплять файлы)
                "SUBJECT": "Результаты опроса пациента",
                "DESCRIPTION": (
                    "Пациент завершил прохождение опроса. "
                    "PDF-отчёт с результатами прикреплён к этому делу."
                ),
                "DESCRIPTION_TYPE": 1,  # 1 = Plain text
                "DIRECTION": 2,  # 2 = Исходящее
                "COMPLETED": "Y",
                "RESPONSIBLE_ID": 1,  # Ответственный (по умолчанию - ID=1)
                "FILES": [
                    {
                        "fileData": [filename, pdf_base64],
                    }
                ],
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(method_url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("result"):
                    activity_id = result["result"]
                    logger.info(
                        f"PDF загружен через активность в Битрикс24: "
                        f"activity_id={activity_id}, entity_type={entity_type}, "
                        f"entity_id={entity_id}, filename={filename}"
                    )
                    return True
                else:
                    error = result.get("error_description", "Неизвестная ошибка")
                    logger.error(f"Ошибка загрузки PDF через активность: {error}")
                    return False
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при загрузке PDF через активность: {e}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Ошибка соединения при загрузке PDF: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при загрузке PDF через активность: {e}")
            return False
    
    async def _upload_via_comment_with_file(
        self,
        entity_id: int,
        entity_type: str,
        pdf_base64: str,
        filename: str,
    ) -> bool:
        """
        Загрузка PDF через комментарий в таймлайне с прикреплённым файлом.
        
        Fallback-метод: если crm.activity.add не работает,
        добавляем комментарий с base64-файлом.
        """
        method_url = f"{self.webhook_url.rstrip('/')}/crm.timeline.comment.add"
        
        entity_type_map = {
            "DEAL": "deal",
            "LEAD": "lead",
        }
        
        payload = {
            "fields": {
                "ENTITY_ID": entity_id,
                "ENTITY_TYPE": entity_type_map.get(entity_type.upper(), "deal"),
                "COMMENT": (
                    f"Результаты опроса пациента.\n"
                    f"PDF-отчёт прикреплён к этому комментарию: {filename}"
                ),
                "FILES": {
                    "fileData": [filename, pdf_base64],
                },
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(method_url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("result"):
                    logger.info(
                        f"PDF загружен через комментарий в Битрикс24: "
                        f"entity_type={entity_type}, entity_id={entity_id}"
                    )
                    return True
                else:
                    error = result.get("error_description", "Неизвестная ошибка")
                    logger.error(f"Ошибка загрузки PDF через комментарий: {error}")
                    return False
                    
        except Exception as e:
            logger.error(f"Ошибка загрузки PDF через комментарий: {e}")
            return False
    
    async def get_lead(self, lead_id: int) -> Optional[dict]:
        """
        Получение данных лида.
        
        Метод API: crm.lead.get
        
        Args:
            lead_id: ID лида
            
        Returns:
            Данные лида или None
        """
        if not self.webhook_url:
            return None
        
        method_url = f"{self.webhook_url.rstrip('/')}/crm.lead.get"
        
        payload = {"id": lead_id}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(method_url, json=payload)
                response.raise_for_status()
                return response.json().get("result")
        except Exception as e:
            logger.error(f"Ошибка получения лида из Битрикс24: {e}")
            return None

    async def create_deal_activity(
        self,
        entity_id: int,
        entity_type: str = "DEAL",
        responsible_id: Optional[int] = None,
    ) -> bool:
        """
        Создание дела (Activity) в ленте сделки Битрикс24 со сроком «сегодня».

        Метод API: crm.activity.add

        Дело создаётся с:
        - заголовком «Прошел опрос (требуется действие)»
        - сроком выполнения: сегодня 23:59:59 (Europe/Moscow)
        - статусом COMPLETED = N
        - ответственным из сделки (ASSIGNED_BY_ID) или дефолтным из настроек

        Args:
            entity_id: ID сделки или лида
            entity_type: Тип сущности ('DEAL' или 'LEAD')
            responsible_id: ID ответственного (если None — берётся из сделки или настроек)

        Returns:
            True если дело создано, False при ошибке
        """
        if not self.webhook_url:
            logger.warning("BITRIX24_WEBHOOK_URL не настроен, пропускаем создание дела")
            return False

        entity_type_upper = (entity_type or "DEAL").upper()
        # OWNER_TYPE_ID: 2 = DEAL, 1 = LEAD
        owner_type_id = 2 if entity_type_upper == "DEAL" else 1

        # Получаем ответственного из сделки (ASSIGNED_BY_ID)
        if responsible_id is None and entity_type_upper == "DEAL":
            try:
                deal_data = await self.get_deal(entity_id)
                if deal_data:
                    assigned_by = deal_data.get("ASSIGNED_BY_ID")
                    if assigned_by:
                        responsible_id = int(assigned_by)
                        logger.info(
                            f"Ответственный для дела взят из сделки: "
                            f"deal_id={entity_id}, responsible_id={responsible_id}"
                        )
            except Exception as e:
                logger.warning(
                    f"Не удалось получить ответственного из сделки {entity_id}: {e}"
                )

        # Fallback на дефолтного ответственного из настроек
        if not responsible_id:
            default_resp = getattr(settings, "BITRIX24_DEFAULT_RESPONSIBLE_ID", 0)
            if default_resp:
                responsible_id = default_resp
                logger.info(
                    f"Используется дефолтный ответственный для дела: responsible_id={responsible_id}"
                )

        # Срок выполнения: сегодня 23:59:59 по Europe/Moscow
        moscow_tz = ZoneInfo("Europe/Moscow")
        today = datetime.now(tz=moscow_tz).date()
        deadline_dt = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=moscow_tz)
        deadline_str = deadline_dt.strftime("%Y-%m-%d %H:%M:%S")

        method_url = f"{self.webhook_url.rstrip('/')}/crm.activity.add"

        fields: dict = {
            "OWNER_TYPE_ID": owner_type_id,
            "OWNER_ID": entity_id,
            "TYPE_ID": 6,  # 6 = Task (дело)
            "SUBJECT": "Прошел опрос (требуется действие)",
            "DESCRIPTION": (
                "Нужно скопировать ссылку сделки и прикрепить "
                "в декстру в комментарий пациента."
            ),
            "DESCRIPTION_TYPE": 1,  # 1 = Plain text
            "DEADLINE": deadline_str,
            "COMPLETED": "N",
        }

        if responsible_id:
            fields["RESPONSIBLE_ID"] = responsible_id

        payload = {"fields": fields}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(method_url, json=payload)
                response.raise_for_status()

                result = response.json()

                if result.get("result"):
                    activity_id = result["result"]
                    logger.info(
                        f"Дело создано в Битрикс24: activity_id={activity_id}, "
                        f"entity_type={entity_type_upper}, entity_id={entity_id}, "
                        f"deadline={deadline_str}"
                    )
                    return True

                error = result.get("error_description", result.get("error", "Неизвестная ошибка"))
                logger.error(
                    f"Ошибка создания дела в Битрикс24 (crm.activity.add): {error} "
                    f"(entity_id={entity_id}, response={result})"
                )
                return False

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP ошибка при создании дела в Битрикс24: {e} (entity_id={entity_id})"
            )
            return False
        except httpx.RequestError as e:
            logger.error(
                f"Ошибка соединения при создании дела в Битрикс24: {e} (entity_id={entity_id})"
            )
            return False
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при создании дела в Битрикс24: {e} (entity_id={entity_id})"
            )
            return False
