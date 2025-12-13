import os
import json
import hashlib
import hmac
from urllib.parse import parse_qsl, unquote, parse_qs
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from logger_conf import logger
from core_rndvu.models import BlacklistUser


EXCLUDED_PATHS = ["/admin/", "/media/", "/static/", "/docs/", "/favicon.ico", "/rndvu/schema/",
                  "/rndvu/schema/swagger-ui/", "/api/payment/webhook/"]


def verify_telegram_auth(init_data: str, bot_token: str):
    logger.debug(f"[1] Raw init_data: {init_data}")
    # Раскодируем URL-формат (но не парсим сразу!)
    init_data_unquoted = unquote(init_data)
    # Парсим как query string
    parsed_data = parse_qs(init_data_unquoted, keep_blank_values=True)
    qs_dict = {k: v[0] for k, v in parsed_data.items()}
    # Извлекаем хеш для проверки
    hash_check = qs_dict.pop("hash", None)
    if not hash_check:
        return False, {}
    # Проверяем наличие обязательных полей
    if "user" not in qs_dict:
        return False, {}
    # Формируем data_check_string
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(qs_dict.items()))
    # Генерируем secret_key по стандарту Telegram (WebAppData + токен)
    secret_key = hmac.new(key=b"WebAppData", msg=bot_token.encode(), digestmod=hashlib.sha256).digest()
    # Вычисляем HMAC
    calculated_hash = hmac.new(key=secret_key, msg=data_check_string.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
    # Сравниваем хэши
    ok = hmac.compare_digest(calculated_hash, hash_check)
    return ok, qs_dict


class AsyncTelegramAuthMiddleware(MiddlewareMixin):
    async def __call__(self, request):
        if any(request.path.startswith(p) for p in EXCLUDED_PATHS):
            return await self.get_response(request)
        # Получаем init_data из тех же источников
        init_data = (request.GET.get("init_data") or request.POST.get("init_data") or request.headers.get("X-Init-Data"))
        test_mode = (request.GET.get("test_mode") or request.POST.get("test_mode") or request.headers.get("X-Test-Mode"))
        # Тестовый режим (для отладки)
        if str(test_mode).lower() in ("1", "true", "yes"):
            request.telegram_user = {"id": 123456789, "first_name": "Test User", "language_code": "ru"}
            return await self.get_response(request)
        # Основная проверка
        if not init_data:
            return JsonResponse({"error": "init_data отсутствует"}, status=400)
        bot_token = os.getenv("TOKEN")
        if not bot_token:
            return JsonResponse({"error": "Bot token не настроен"}, status=500)
        ok, data = verify_telegram_auth(init_data, bot_token)
        if not ok:
            return JsonResponse({"error": "Недопустимый init_data"}, status=403)
        # Парсим user (без изменений исходных данных)
        try:
            request.telegram_user = json.loads(data["user"])
        except json.JSONDecodeError:
            return JsonResponse({"error": "Неверный формат user данных"}, status=400)
        
        # Проверяем черный список по tg_id через связь с Player
        tg_id = request.telegram_user.get("id")
        if tg_id:
            try:
                # Проверяем через связь с Player
                is_blocked = await BlacklistUser.objects.filter(player__tg_id=tg_id).aexists()
                if is_blocked:
                    return JsonResponse({"error": "Доступ запрещен. Ваш аккаунт заблокирован администратором."}, status=403)
            except Exception as e:
                logger.error(f"Ошибка при проверке черного списка: {e}")
                # В случае ошибки БД не блокируем пользователя, просто логируем
        
        return await self.get_response(request)
