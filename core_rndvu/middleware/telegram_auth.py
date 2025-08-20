import os
import json
import hashlib
import hmac
from urllib.parse import parse_qsl, unquote, parse_qs
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from logger_conf import logger


EXCLUDED_PATHS = ["/admin/", "/media/", "/static/", "/docs/", "/favicon.ico", "/rndvu/schema/",
                  "/rndvu/schema/swagger-ui/"]


def verify_telegram_auth(init_data: str, bot_token: str):
    logger.debug(f"[1] Raw init_data: {init_data}")
    # Раскодируем URL-формат (но не парсим сразу!)
    init_data_unquoted = unquote(init_data)
    logger.debug(f"[2] Unquoted init_data: {init_data_unquoted}")
    # Парсим как query string
    parsed_data = parse_qs(init_data_unquoted, keep_blank_values=True)
    qs_dict = {k: v[0] for k, v in parsed_data.items()}
    logger.debug(f"[3] Parsed qs_dict: {qs_dict}")
    # Извлекаем хеш для проверки
    hash_check = qs_dict.pop("hash", None)
    if not hash_check:
        logger.error("Hash parameter is missing!")
        return False, {}
    logger.debug(f"[4] Extracted hash_check: {hash_check}")
    # Проверяем наличие обязательных полей
    if "user" not in qs_dict:
        logger.error("User data is missing!")
        return False, {}
    # Формируем data_check_string
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(qs_dict.items()))
    logger.debug(f"[5] Data check string:\n{data_check_string}")
    # Генерируем secret_key по стандарту Telegram (WebAppData + токен)
    secret_key = hmac.new(key=b"WebAppData", msg=bot_token.encode(), digestmod=hashlib.sha256).digest()
    logger.debug(f"[6] Secret key (hex): {secret_key.hex()}")
    # Вычисляем HMAC
    calculated_hash = hmac.new(key=secret_key, msg=data_check_string.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
    logger.debug(f"[7] Calculated hash: {calculated_hash}")
    logger.debug(f"[8] Expected hash: {hash_check}")
    # Сравниваем хэши
    ok = hmac.compare_digest(calculated_hash, hash_check)
    logger.info(f"[9] Verification result: {ok}")
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
            logger.debug(f"Telegram user: {request.telegram_user}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Неверный формат user данных"}, status=400)
        return await self.get_response(request)
