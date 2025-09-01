from datetime import timedelta
import httpx
from adrf.views import APIView
from django.http import JsonResponse, HttpResponse
from django.utils.timezone import localtime
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import sync_and_async_middleware, method_decorator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from core_rndvu.models import Player, Product, Purchase
from logger_conf import logger
import json
import uuid
from rndvu import settings


async def create_yookassa_payment(amount: int, return_url: str, description: str, metadata: dict = None):
    url = "https://api.yookassa.ru/v3/payments"  # URL API Юкассы для создания платежа
    # Заголовки запроса: указываем, что отправляем JSON и задаём уникальный ключ идемпотентности (чтобы платеж не создавался дважды)
    headers = {"Content-Type": "application/json", "Idempotence-Key": str(uuid.uuid4()),}
    # Данные для аутентификации — берём из настроек вашего проекта (идентификатор магазина и секретный ключ)
    auth = (settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)
    # Генерим левую почту на основе tg_id из metadata
    tg_id = metadata.get("tg_id", "unknown") if metadata else "unknown"
    fake_email = f"user_{tg_id}@astro.ru"
    data = {
        "amount": {
            "value": f"{amount:.2f}",  # Преобразуем сумму в строку с 2 знаками после запятой
            "currency": "RUB",         # Валюта — российский рубль
        },
        "confirmation": {
            "type": "redirect",        # Тип подтверждения — перенаправление пользователя на страницу оплаты
            "return_url": return_url,  # URL, на который пользователь вернётся после оплаты
        },
        "capture": True,               # Автоматически подтвердить платёж после оплаты
        "description": description,    # Описание платежа (например, "Оплата подписки")
        "metadata": metadata or {},    # Дополнительные данные (можно передать любую инфу, тут передаем tg_id и product_id)
        "receipt": {
            "customer": {
                "email": fake_email  # Левая почта
            },
            "items": [
                {
                    "description": description[:128],  # Обрезаем если длинное
                    "quantity": "1.00",
                    "amount": {
                        "value": f"{amount:.2f}",
                        "currency": "RUB"
                    },
                    "vat_code": 4,  # Без НДС (самый простой вариант)
                    "payment_mode": "full_payment",
                    "payment_subject": "commodity"
                }
            ]
        }
    }
    # Создаём асинхронного клиента для HTTP-запросов
    async with httpx.AsyncClient() as client:
        # Отправляем POST-запрос на создание платежа с телом data, с авторизацией и заголовками
        response = await client.post(url, json=data, auth=auth, headers=headers)
    # Проверяем успешность ответа (201 — создано, 200 — успешно)
    if response.status_code == 200 or response.status_code == 201:
        return response.json()  # Возвращаем JSON с данными платежа (там будет ссылка для перехода пользователя)
    else:
        # Если ошибка — поднимаем исключение с текстом ошибки от Юкассы
        raise Exception(f"Ошибка при создании платежа: {response.text}")


@extend_schema(
    tags=["Юкасса"],
    summary="Webhook YooKassa",
    description=(
        "ЮKassa шлёт сюда уведомления о платеже.\n\n"
        "В продакшене вызывается внешним сервисом; вручную трогать не нужно."
    ),
    responses={
        200: OpenApiResponse(description="OK (принято)"),
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Недостаточно данных",
            examples=[OpenApiExample("Missing data", value="Missing data")],
        ),
    },
)
@method_decorator(csrf_exempt, name='dispatch')
class YookassaWebhookView(APIView):
    async def post(self, request):
        # Получаем тело POST-запроса из webhook от Юкассы (в бинарном виде)
        body = request.body
        # Декодируем JSON из тела запроса в словарь Python
        data = json.loads(body)
        # Получаем тип события (например, "payment.succeeded")
        event_type = data.get("event")
        # Получаем объект с данными платежа (внутри ключа "object")
        payment_data = data.get("object", {})
        # Если событие — успешная оплата
        if event_type == "payment.succeeded":
            payment_id = payment_data["id"]  # Получаем id платежа
            metadata = payment_data.get("metadata", {})  # Получаем метаданные из платежа (там хранятся tg_id и product_id)
            tg_id = metadata.get("tg_id")  # Извлекаем tg_id из метаданных
            product_id = metadata.get("product_id")  # Извлекаем product_id из метаданных
            if not all([payment_id, tg_id, product_id]):
                logger.error("❌ Не хватает обязательных данных в вебхуке")
                return HttpResponse("Missing data", status=400)
            # Вызываем функцию, которая помечает покупку как успешную и активирует подписку (если нужна)
            success = await mark_payment_success(tg_id=tg_id, product_id=product_id, payment_id=payment_id)
            if not success:
                return HttpResponse("Failed to process", status=400)
        elif event_type == "payment.waiting_for_capture":
            logger.info("⏳ Платёж ожидает подтверждения (capture), ID: %s", payment_data.get("id"))
        elif event_type == "payment.canceled":
            logger.warning("🚫 Платёж отменён, ID: %s", payment_data.get("id"))
        elif event_type == "payment.expired":
            logger.warning("⌛ Платёж просрочен, ID: %s", payment_data.get("id"))
        elif event_type == "refund.succeeded":
            logger.info("💸 Возврат успешно выполнен, ID: %s", payment_data.get("id"))
        else:
            logger.info(f"📨 Необработанный тип события: {event_type}")
        # Возвращаем Юкассе ответ, что webhook обработан успешно
        return HttpResponse("OK", status=200)


async def mark_payment_success(tg_id: int, product_id: int, payment_id: str):
    try:
        player = await Player.objects.aget(tg_id=tg_id)
        product = await Product.objects.aget(id=product_id)
        # Проверяем, существует ли уже покупка с таким payment_id
        exists = await Purchase.objects.filter(payment_id=payment_id).aexists()
        if exists:
            logger.warning(f"⚠️ Покупка с payment_id={payment_id} уже существует")
            return False
        # Создаем новую запись о покупке
        await Purchase.objects.acreate(player=player, product=product, payment_id=payment_id, is_successful=True)
        # подписка — отмечаем игрока как платного
        today = localtime().date()
        extra_days = timedelta(days=product.duration_days)
        if player.subscription_end_date and player.subscription_end_date >= today:
            # Подписка активна — продлеваем от текущей даты окончания
            player.subscription_end_date += extra_days
        else:
            # Подписки нет или она уже закончилась — начинаем с сегодняшнего дня
            player.subscription_end_date = today + extra_days
        player.paid_subscription = True
        player.count_days_paid_subscription += product.duration_days
        await player.asave(update_fields=['paid_subscription', 'count_days_paid_subscription', 'subscription_end_date'])
        return True
    except Player.DoesNotExist:
        logger.error(f"❌ Игрок с tg_id={tg_id} не найден")
    except Product.DoesNotExist:
        logger.error(f"❌ Продукт с id={product_id} не найден")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании покупки: {str(e)}")
    return False
