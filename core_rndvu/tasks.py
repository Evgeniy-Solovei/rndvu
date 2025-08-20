from celery import shared_task
from django.db.models import Q, F
from django.utils import timezone



# @shared_task(
#     acks_late=True,  # Подтверждаем задачу только после выполнения
#     autoretry_for=(Exception,),  # Повторяем при любых исключениях
#     retry_kwargs={'max_retries': 3},  # Максимум 3 попытки
#     retry_backoff=True  # Экспоненциальная задержка между попытками
# )
# def reset_today_free_attempts():
#     """Сбрасывает free_attempts до 3, игрокам у кого меньше 3 попыток."""
#     updated_count = Player.objects.filter(free_attempts__lt=3).update(free_attempts=3)
#     logger.info(f"Сброс бесплатных попыток: обновлено {updated_count} игроков")
#
