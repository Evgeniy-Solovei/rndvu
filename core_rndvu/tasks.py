import asyncio
import os
from datetime import timedelta
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from celery import shared_task
from django.db.models import F
from django.utils import timezone
from core_rndvu.models import Event, PassedUser, Player
from logger_conf import logger


@shared_task(
    acks_late=True,  # Подтверждаем задачу только после выполнения
    autoretry_for=(Exception,),  # Повторяем при любых исключениях
    retry_kwargs={'max_retries': 3},  # Максимум 3 попытки
    retry_backoff=True  # Экспоненциальная задержка между попытками
)
def decrement_subscription_days_daily():
    """
    Ежедневно уменьшает остаток дней подписки на 1 у активных подписчиков.
    Если дни закончились — выключает paid_subscription.
    """
    # 1) уменьшаем на 1 у тех, у кого > 0
    dec_count = (Player.objects.filter(paid_subscription=True, count_days_paid_subscription__gt=0).
                 update(count_days_paid_subscription=F('count_days_paid_subscription') - 1))
    # 2) у кого стало 0 — выключаем флаг подписки
    off_count = (Player.objects.filter(paid_subscription=True, count_days_paid_subscription__lte=0).
                 update(paid_subscription=False))
    logger.info(f"Пользователям уменьшили дни: {dec_count}, отключили подписку: {off_count}")


@shared_task(
    acks_late=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True
)
def delete_old_passed_users():
    """
    Удаляет записи PassedUser, которые старше 2 дней.
    Это позволяет пропущенным пользователям снова появиться в игре через день.
    """
    one_day_ago = timezone.now() - timedelta(days=2)
    deleted_count, _ = PassedUser.objects.filter(created_at__lt=one_day_ago).delete()
    logger.info(f"Удалено записей о пропущенных пользователях старше 2 дней: {deleted_count}")


async def _send_event_notifications(players, text):
    """
    Асинхронно отправляем сообщения всем нужным пользователям.
    Вызывается из Celery через asyncio.run().
    """
    token = os.getenv("TOKEN")
    web_app_url = os.getenv("WEB_APP_URL")

    if not token:
        logger.warning("Нет TOKEN в окружении — рассылка ивента пропущена")
        return

    # создаём кнопку для мини-приложения
    keyboard = None
    if web_app_url:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Перейти", web_app=WebAppInfo(url=web_app_url))]])

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    async with bot:
        for player in players:
            try:
                await bot.send_message(
                    chat_id=player["tg_id"],
                    text=text,
                    disable_web_page_preview=True,
                    reply_markup=keyboard
                )
            except Exception as exc:
                logger.warning(f"Не удалось отправить сообщение {player['tg_id']}: {exc}")


@shared_task(
    acks_late=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True
)
def notify_opposite_gender_about_event(event_id: int):
    """
    После создания ивента отправляем тестовое сообщение всем пользователям
    противоположного пола. Используем Celery, чтобы не блокировать запрос.
    """
    try:
        event = Event.objects.select_related("profile").get(id=event_id)
    except Event.DoesNotExist:
        logger.warning(f"Ивент {event_id} не найден — рассылка пропущена")
        return

    creator = event.profile
    if not creator.gender:
        logger.info(f"У создателя ивента {event_id} не указан пол — рассылка пропущена")
        return

    target_gender = "Woman" if creator.gender == "Man" else "Man"
    players = list(
        Player.objects.filter(
            gender=target_gender,
            is_active=True,
            show_in_game=True,
        ).exclude(id=creator.id).values("tg_id")
    )
    if not players:
        logger.info(f"Нет получателей для ивента {event_id}")
        return

    text = "Новый ивент! Загляни в приложение, чтобы посмотреть детали."
    asyncio.run(_send_event_notifications(players, text))
