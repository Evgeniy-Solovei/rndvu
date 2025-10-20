from celery import shared_task
from core_rndvu.models import Player
from logger_conf import logger
from django.db.models import F


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
