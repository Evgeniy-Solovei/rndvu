from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, OpenApiResponse, OpenApiExample


player_info_schema = extend_schema(
    tags=["Игрок"],
    summary="Создание или получение информации об игроке",
    description=(
        "Этот endpoint используется для создания нового игрока или получения информации о существующем "
        "на основе данных Telegram WebApp.\n\n"
        "⚠️ Требуется заголовок `X-Init-Data` с init_data от Telegram.\n"
        "Можно включить `X-Test-Mode: true`, чтобы протестировать без Telegram.\n\n"
        "При первом обращении игрок создаётся в системе, при последующих — возвращается существующий."
    ),
    request=None,
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное создание или получение игрока",
            examples=[
                OpenApiExample(
                    name="Игрок создан",
                    value={
                        "created": True,
                        "player": {
                            "id": 1,
                            "tg_id": 123456789,
                            "first_name": "Иван",
                            "username": "ivanov",
                            "language_code": "ru"
                        }
                    },
                ),
                OpenApiExample(
                    name="Игрок уже существует",
                    value={
                        "created": False,
                        "player": {
                            "id": 1,
                            "tg_id": 123456789,
                            "first_name": "Иван",
                            "username": "ivanov",
                            "language_code": "ru"
                        }
                    },
                ),
            ],
        ),
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Неверные данные или отсутствует init_data",
            examples=[
                OpenApiExample(
                    name="Ошибка: не передан init_data",
                    value={"error": "telegram_user not found"},
                ),
            ],
        ),
        500: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Внутренняя ошибка сервера",
            examples=[
                OpenApiExample(
                    name="Ошибка при работе с БД",
                    value={"error": "Ошибка при создании/получении игрока", "details": "..."},
                ),
            ],
        ),
    },
    parameters=[
        OpenApiParameter(
            name="X-Init-Data",
            type=str,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Строка init_data от Telegram WebApp (Telegram.WebApp.initData)"
        ),
        OpenApiParameter(
            name="X-Test-Mode",
            type=str,
            location=OpenApiParameter.HEADER,
            required=False,
            description="Если true — работает без проверки Telegram (тестовый режим)"
        ),
    ]
)



player_gender_update_schema = extend_schema(
    tags=["Игрок"],
    summary="Обновление пола игрока и создание соответствующего профиля",
    description=(
        "Этот endpoint используется для установки или изменения пола игрока "
        "и автоматического создания соответствующего профиля (мужского или женского).\n\n"
        "⚠️ Требуется заголовок `X-Init-Data` с init_data от Telegram.\n"
        "Можно включить `X-Test-Mode: true`, чтобы протестировать без Telegram.\n\n"
        "При выборе пола создаётся соответствующий тип профиля (ProfileMan или ProfileWoman)."
    ),
    request=OpenApiTypes.OBJECT,
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное обновление пола и создание профиля",
            examples=[
                OpenApiExample(
                    name="Установлен мужской пол",
                    value={
                        "player": {
                            "id": 1,
                            "tg_id": 123456789,
                            "first_name": "Иван",
                            "username": "ivanov",
                            "language_code": "ru",
                            "gender": "Man"
                        },
                        "profile": {
                            "id": 1,
                            "player": 1,
                            # ... другие поля ProfileMan
                        }
                    },
                ),
                OpenApiExample(
                    name="Установлен женский пол",
                    value={
                        "player": {
                            "id": 1,
                            "tg_id": 123456789,
                            "first_name": "Мария",
                            "username": "maria",
                            "language_code": "ru",
                            "gender": "Woman"
                        },
                        "profile": {
                            "id": 1,
                            "player": 1,
                            # ... другие поля ProfileWoman
                        }
                    },
                ),
            ],
        ),
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Неверные данные или ошибка валидации",
            examples=[
                OpenApiExample(
                    name="Ошибка: неверное значение gender",
                    value={"error": "Параметр gender обязателен (Man, Woman)"},
                ),
                OpenApiExample(
                    name="Ошибка: игрок не найден",
                    value={"error": "Player matching query does not exist"},
                ),
                OpenApiExample(
                    name="Ошибка: не передан gender",
                    value={"error": "KeyError: 'gender'"},
                ),
            ],
        ),
        500: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Внутренняя ошибка сервера",
            examples=[
                OpenApiExample(
                    name="Ошибка сервера",
                    value={"error": "Internal server error"},
                ),
            ],
        ),
    },
    parameters=[
        OpenApiParameter(
            name="X-Init-Data",
            type=str,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Строка init_data от Telegram WebApp (Telegram.WebApp.initData)"
        ),
        OpenApiParameter(
            name="X-Test-Mode",
            type=str,
            location=OpenApiParameter.HEADER,
            required=False,
            description="Если true — работает без проверки Telegram (тестовый режим)"
        ),
    ],
    examples=[
        OpenApiExample(
            name="Пример запроса для мужского пола",
            value={"gender": "Man"},
            request_only=True
        ),
        OpenApiExample(
            name="Пример запроса для женского пола",
            value={"gender": "Woman"},
            request_only=True
        ),
    ]
)



user_profile_schema = extend_schema(
    tags=["Анкета"],
    summary="Работа с анкетой пользователя (получение, обновление)",
    description=(
        "Этот endpoint позволяет получить, частично или полностью обновить анкету пользователя.\n\n"
        "⚠️ Требуется заголовок `X-Init-Data` с init_data от Telegram.\n"
        "Можно включить `X-Test-Mode: true`, чтобы протестировать без Telegram.\n\n"
        "GET - получить анкету с фото, счетчиками лайков и реакциями текущего пользователя\n"
        "PATCH - частичное обновление анкеты и фото\n"
        "PUT - полное обновление анкеты и фото\n\n"
        "Поддерживает multipart/form-data для загрузки файлов."
    ),
    parameters=[
        OpenApiParameter(
            name="X-Init-Data",
            type=str,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Строка init_data от Telegram WebApp (Telegram.WebApp.initData)"
        ),
        OpenApiParameter(
            name="X-Test-Mode",
            type=str,
            location=OpenApiParameter.HEADER,
            required=False,
            description="Если true — работает без проверки Telegram (тестовый режим)"
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное выполнение операции",
        ),
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Неверные данные или ошибка валидации",
            examples=[
                OpenApiExample(
                    name="Ошибка: пол не указан",
                    value={"error": "Пол пользователя не указан"},
                ),
                OpenApiExample(
                    name="Ошибка валидации",
                    value={"error": "Ошибка валидации", "details": {"field": ["Ошибка"]}},
                ),
            ],
        ),
        404: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Ресурс не найден",
            examples=[
                OpenApiExample(
                    name="Анкета не найдена",
                    value={"error": "Анкета не найдена"},
                ),
                OpenApiExample(
                    name="Игрок не найден",
                    value={"error": "Игрок не найден"},
                ),
            ],
        ),
        500: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Внутренняя ошибка сервера",
            examples=[
                OpenApiExample(
                    name="Ошибка сервера",
                    value={"error": "Internal server error"},
                ),
            ],
        ),
    }
)

user_profile_get_schema = extend_schema(
    summary="Получить анкету пользователя",
    description=(
        "Возвращает полную анкету пользователя с фото, счетчиками лайков/дизлайков "
        "и реакциями текущего пользователя на каждое фото."
    ),
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное получение анкеты",
            examples=[
                OpenApiExample(
                    name="Мужская анкета",
                    value={
                        "id": 1,
                        "player": {
                            "id": 1,
                            "tg_id": 123456789,
                            "first_name": "Иван",
                            "username": "ivanov",
                            "language_code": "ru",
                            "gender": "Man"
                        },
                        "photos": [
                            {
                                "id": 1,
                                "image": "http://example.com/photo1.jpg",
                                "likes_count": 5,
                                "dislikes_count": 2,
                                "user_reactions": [{"reaction_type": "like"}]
                            }
                        ],
                        # ... другие поля анкеты
                    },
                ),
                OpenApiExample(
                    name="Женская анкета",
                    value={
                        "id": 1,
                        "player": {
                            "id": 1,
                            "tg_id": 123456789,
                            "first_name": "Мария",
                            "username": "maria",
                            "language_code": "ru",
                            "gender": "Woman"
                        },
                        "photos": [
                            {
                                "id": 1,
                                "image": "http://example.com/photo1.jpg",
                                "likes_count": 15,
                                "dislikes_count": 3,
                                "user_reactions": [{"reaction_type": "dislike"}]
                            }
                        ],
                        # ... другие поля анкеты
                    },
                ),
            ],
        ),
    }
)

user_profile_patch_schema = extend_schema(
    summary="Частично обновить анкету",
    description=(
        "Частичное обновление анкеты пользователя. Поддерживает загрузку новых фото "
        "и удаление существующих через multipart/form-data.\n\n"
        "Параметры:\n"
        "- photos: файлы для загрузки (можно несколько)\n"
        "- delete_photo_ids: ID фото для удаления (через запятую или массив)\n"
        "- Любые другие поля анкеты для обновления"
    ),
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'photos': {
                    'type': 'array',
                    'items': {'type': 'string', 'format': 'binary'},
                    'description': 'Новые фото для загрузки'
                },
                'delete_photo_ids': {
                    'type': 'string',
                    'description': 'ID фото для удаления (через запятую)'
                },
                # Другие поля анкеты
                'field_name': {'type': 'string', 'description': 'Любое поле анкеты'}
            }
        }
    },
    examples=[
        OpenApiExample(
            name="Пример запроса с новыми фото",
            description="Загрузка 2 новых фото и удаление фото с ID 1 и 3",
            value={
                "photos": ["файл1.jpg", "файл2.jpg"],
                "delete_photo_ids": "1,3",
                "description": "Новое описание профиля",
                "age": 25
            },
            request_only=True,
            media_type='multipart/form-data'
        ),
    ]
)

user_profile_put_schema = extend_schema(
    summary="Полностью обновить анкету",
    description=(
        "Полное обновление анкеты пользователя. Все поля будут перезаписаны. "
        "Поддерживает загрузку новых фото и удаление существующих через multipart/form-data.\n\n"
        "Параметры аналогичные PATCH, но требуются все обязательные поля анкеты."
    ),
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'photos': {
                    'type': 'array',
                    'items': {'type': 'string', 'format': 'binary'},
                    'description': 'Новые фото для загрузки'
                },
                'delete_photo_ids': {
                    'type': 'string',
                    'description': 'ID фото для удаления (через запятую)'
                },
                # Другие поля анкеты
                'field_name': {'type': 'string', 'description': 'Все поля анкеты'}
            }
        }
    }
)



photo_reaction_schema = extend_schema(
    tags=["Реакции"],
    summary="Работа с реакциями на фото (лайки/дизлайки)",
    description=(
        "Этот endpoint позволяет ставить, изменять и удалять реакции (лайки/дизлайки) на фото.\n\n"
        "⚠️ Требуется заголовок `X-Init-Data` с init_data от Telegram.\n"
        "Можно включить `X-Test-Mode: true`, чтобы протестировать без Telegram.\n\n"
        "POST - поставить или изменить реакцию на фото\n"
        "DELETE - убрать реакцию с фото"
    ),
    parameters=[
        OpenApiParameter(
            name="X-Init-Data",
            type=str,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Строка init_data от Telegram WebApp (Telegram.WebApp.initData)"
        ),
        OpenApiParameter(
            name="X-Test-Mode",
            type=str,
            location=OpenApiParameter.HEADER,
            required=False,
            description="Если true — работает без проверки Telegram (тестовый режим)"
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное выполнение операции",
        ),
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Неверные данные или ошибка валидации",
            examples=[
                OpenApiExample(
                    name="Ошибка: неверный reaction_type",
                    value={"error": "Параметр reaction_type обязателен и должен быть 'like' или 'dislike'"},
                ),
                OpenApiExample(
                    name="Ошибка: фото не указано",
                    value={"error": "Должно быть указано одно фото (photo_id или woman_photo_id)"},
                ),
                OpenApiExample(
                    name="Ошибка: оба фото указаны",
                    value={"error": "Нельзя указать и мужское, и женское фото одновременно"},
                ),
            ],
        ),
        404: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Ресурс не найден",
            examples=[
                OpenApiExample(
                    name="Фото не найдено",
                    value={"error": "Мужское фото не найдено"},
                ),
                OpenApiExample(
                    name="Реакция не найдена",
                    value={"message": "Реакция не найдена"},
                ),
            ],
        ),
        500: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Внутренняя ошибка сервера",
            examples=[
                OpenApiExample(
                    name="Ошибка сервера",
                    value={"error": "Internal server error"},
                ),
            ],
        ),
    }
)

photo_reaction_post_schema = extend_schema(
    summary="Поставить или изменить реакцию на фото",
    description=(
        "Ставит новую реакцию или изменяет существующую на фото.\n\n"
        "Параметры:\n"
        "- reaction_type: тип реакции ('like' или 'dislike')\n"
        "- photo_id: ID мужского фото (обязателен если не указан woman_photo_id)\n"
        "- woman_photo_id: ID женского фото (обязателен если не указан photo_id)"
    ),
    request=OpenApiTypes.OBJECT,
    examples=[
        OpenApiExample(
            name="Лайк на мужское фото",
            value={
                "reaction_type": "like",
                "photo_id": 1
            },
            request_only=True
        ),
        OpenApiExample(
            name="Дизлайк на женское фото",
            value={
                "reaction_type": "dislike",
                "woman_photo_id": 5
            },
            request_only=True
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешная операция",
            examples=[
                OpenApiExample(
                    name="Реакция поставлена",
                    value={
                        "message": "Реакция поставлена",
                        "reaction_type": "like",
                        "photo_id": 1,
                        "photo_type": "man"
                    },
                ),
                OpenApiExample(
                    name="Реакция изменена",
                    value={
                        "message": "Реакция изменена",
                        "reaction_type": "dislike",
                        "photo_id": 2,
                        "photo_type": "woman"
                    },
                ),
                OpenApiExample(
                    name="Реакция уже существует",
                    value={
                        "message": "Такая реакция уже поставлена",
                        "reaction": "like"
                    },
                ),
            ],
        ),
    }
)

photo_reaction_delete_schema = extend_schema(
    summary="Убрать реакцию с фото",
    description=(
        "Удаляет существующую реакцию с фото.\n\n"
        "Параметры:\n"
        "- photo_id: ID мужского фото (обязателен если не указан woman_photo_id)\n"
        "- woman_photo_id: ID женского фото (обязателен если не указан photo_id)"
    ),
    request=OpenApiTypes.OBJECT,
    examples=[
        OpenApiExample(
            name="Удаление реакции с мужского фото",
            value={
                "photo_id": 1
            },
            request_only=True
        ),
        OpenApiExample(
            name="Удаление реакции с женского фото",
            value={
                "woman_photo_id": 5
            },
            request_only=True
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное удаление",
            examples=[
                OpenApiExample(
                    name="Реакция убрана",
                    value={
                        "message": "Реакция убрана",
                        "photo_id": 1,
                        "photo_type": "man"
                    },
                ),
            ],
        ),
        404: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Реакция не найдена",
            examples=[
                OpenApiExample(
                    name="Реакция не существует",
                    value={"message": "Реакция не найдена"},
                ),
            ],
        ),
    }
)



game_users_schema = extend_schema(
    tags=["Игра"],
    summary="Получение пользователей для игры с фильтрацией",
    description=(
        "Этот endpoint возвращает пользователей противоположного пола для игры "
        "с фильтрацией по городу и возрасту. Пагинация по 10 пользователей на страницу.\n\n"
        "⚠️ Требуется заголовок `X-Init-Data` с init_data от Telegram.\n"
        "Можно включить `X-Test-Mode: true`, чтобы протестировать без Telegram.\n\n"
        "Особенности:\n"
        "- Возвращаются только пользователи противоположного пола\n"
        "- Исключаются пользователи с уже существующей симпатией\n"
        "- Случайный порядок выдачи (random)\n"
        "- Поддерживает фильтрацию по городу и возрасту"
    ),
    parameters=[
        OpenApiParameter(
            name="X-Init-Data",
            type=str,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Строка init_data от Telegram WebApp (Telegram.WebApp.initData)"
        ),
        OpenApiParameter(
            name="X-Test-Mode",
            type=str,
            location=OpenApiParameter.HEADER,
            required=False,
            description="Если true — работает без проверки Telegram (тестовый режим)"
        ),
        OpenApiParameter(
            name="city",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Фильтр по городу (частичное совпадение)"
        ),
        OpenApiParameter(
            name="min_age",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Минимальный возраст (включительно)"
        ),
        OpenApiParameter(
            name="max_age",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Максимальный возраст (включительно)"
        ),
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Номер страницы (по умолчанию 1)"
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное получение пользователей",
            examples=[
                OpenApiExample(
                    name="Успешный ответ",
                    value={
                        "results": [
                            {
                                "id": 1,
                                "tg_id": 123456789,
                                "first_name": "Мария",
                                "username": "maria",
                                "city": "Москва",
                                "age": 25,
                                "photos": [
                                    {
                                        "id": 1,
                                        "image": "http://example.com/photo1.jpg",
                                        "uploaded_at": "2024-01-15T10:30:00Z"
                                    }
                                ]
                            }
                        ],
                        "page": 1,
                        "page_size": 10,
                        "total_pages": 5
                    },
                ),
                OpenApiExample(
                    name="Пустой результат",
                    value={
                        "results": [],
                        "page": 1,
                        "page_size": 10,
                        "total_count": 0,
                        "total_pages": 0,
                        "has_prev": False,
                        "has_next": False,
                        "prev_page": None,
                        "next_page": None
                    },
                ),
            ],
        ),
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Неверные данные или ошибка валидации",
            examples=[
                OpenApiExample(
                    name="Ошибка: пол не указан",
                    value={"error": "Пол пользователя не указан"},
                ),
            ],
        ),
        500: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Внутренняя ошибка сервера",
            examples=[
                OpenApiExample(
                    name="Ошибка сервера",
                    value={"error": "Internal server error"},
                ),
            ],
        ),
    }
)


sympathy_schema = extend_schema(
    tags=["Симпатии"],
    summary="Работа с симпатиями между пользователями",
    description=(
        "Этот endpoint позволяет управлять симпатиями между пользователями.\n\n"
        "⚠️ Требуется заголовок `X-Init-Data` с init_data от Telegram.\n"
        "Можно включить `X-Test-Mode: true`, чтобы протестировать без Telegram.\n\n"
        "POST - поставить симпатию другому пользователю\n"
        "GET - получить список взаимных симпатий\n"
        "DELETE - удалить симпатию (свою или взаимную)"
    ),
    parameters=[
        OpenApiParameter(
            name="X-Init-Data",
            type=str,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Строка init_data от Telegram WebApp (Telegram.WebApp.initData)"
        ),
        OpenApiParameter(
            name="X-Test-Mode",
            type=str,
            location=OpenApiParameter.HEADER,
            required=False,
            description="Если true — работает без проверки Telegram (тестовый режим)"
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное выполнение операции",
        ),
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Неверные данные или ошибка валидации",
            examples=[
                OpenApiExample(
                    name="Ошибка: tg_id не указан",
                    value={"error": "Укажите tg_id получателя симпатии"},
                ),
                OpenApiExample(
                    name="Ошибка: симпатия себе",
                    value={"error": "Нельзя поставить симпатию себе"},
                ),
            ],
        ),
        404: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Ресурс не найден",
            examples=[
                OpenApiExample(
                    name="Пользователь не найден",
                    value={"error": "Пользователь не найден"},
                ),
                OpenApiExample(
                    name="Симпатия не найдена",
                    value={"deleted": False, "message": "Симпатия не найдена"},
                ),
            ],
        ),
        500: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Внутренняя ошибка сервера",
            examples=[
                OpenApiExample(
                    name="Ошибка сервера",
                    value={"error": "Internal server error"},
                ),
            ],
        ),
    }
)

sympathy_post_schema = extend_schema(
    summary="Поставить симпатию другому пользователю",
    description=(
        "Создает симпатию к другому пользователю. Если симпатия уже существует "
        "в обратном направлении, устанавливает взаимность.\n\n"
        "Параметры:\n"
        "- tg_id: Telegram ID пользователя, к которому ставится симпатия"
    ),
    request=OpenApiTypes.OBJECT,
    examples=[
        OpenApiExample(
            name="Поставить симпатию",
            value={"tg_id": 987654321},
            request_only=True
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешная операция",
            examples=[
                OpenApiExample(
                    name="Симпатия создана",
                    value={
                        "message": "Симпатия создана",
                        "sympathy": {
                            "id": 1,
                            "from_player": {"tg_id": 123456789, "first_name": "Иван"},
                            "to_player": {"tg_id": 987654321, "first_name": "Мария"},
                            "is_mutual": False,
                            "created_at": "2024-01-15T10:30:00Z"
                        }
                    },
                ),
                OpenApiExample(
                    name="Взаимная симпатия",
                    value={
                        "message": "Совпадение! Взаимная симпатия",
                        "sympathy": {
                            "id": 1,
                            "from_player": {"tg_id": 987654321, "first_name": "Мария"},
                            "to_player": {"tg_id": 123456789, "first_name": "Иван"},
                            "is_mutual": True,
                            "created_at": "2024-01-15T10:30:00Z"
                        }
                    },
                ),
                OpenApiExample(
                    name="Симпатия уже существует",
                    value={
                        "message": "Симпатия уже есть",
                        "sympathy": {
                            "id": 1,
                            "from_player": {"tg_id": 123456789, "first_name": "Иван"},
                            "to_player": {"tg_id": 987654321, "first_name": "Мария"},
                            "is_mutual": False,
                            "created_at": "2024-01-15T10:30:00Z"
                        }
                    },
                ),
            ],
        ),
    }
)

sympathy_get_schema = extend_schema(
    summary="Получить список взаимных симпатий",
    description="Возвращает список всех взаимных симпатий, где текущий пользователь является участником.",
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное получение списка",
            examples=[
                OpenApiExample(
                    name="Список взаимных симпатий",
                    value={
                        "mutual": [
                            {
                                "id": 1,
                                "from_player": {"tg_id": 123456789, "first_name": "Иван"},
                                "to_player": {"tg_id": 987654321, "first_name": "Мария"},
                                "is_mutual": True,
                                "created_at": "2024-01-15T10:30:00Z"
                            },
                            {
                                "id": 2,
                                "from_player": {"tg_id": 555555555, "first_name": "Анна"},
                                "to_player": {"tg_id": 123456789, "first_name": "Иван"},
                                "is_mutual": True,
                                "created_at": "2024-01-14T15:20:00Z"
                            }
                        ]
                    },
                ),
                OpenApiExample(
                    name="Нет взаимных симпатий",
                    value={"mutual": []},
                ),
            ],
        ),
    }
)

sympathy_delete_schema = extend_schema(
    summary="Удалить симпатию",
    description=(
        "Удаляет симпатию между текущим пользователем и указанным пользователем.\n\n"
        "Работает в обоих направлениях (удаляет как свою симпатию к другому пользователю, "
        "так и симпатию другого пользователя к себе).\n\n"
        "Параметры:\n"
        "- tg_id: Telegram ID пользователя, с которым нужно удалить симпатию"
    ),
    request=OpenApiTypes.OBJECT,
    examples=[
        OpenApiExample(
            name="Удалить симпатию",
            value={"tg_id": 987654321},
            request_only=True
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное удаление",
            examples=[
                OpenApiExample(
                    name="Симпатия удалена",
                    value={"deleted": True},
                ),
            ],
        ),
        404: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Симпатия не найдена",
            examples=[
                OpenApiExample(
                    name="Симпатия не существует",
                    value={"deleted": False, "message": "Симпатия не найдена"},
                ),
            ],
        ),
    }
)



favorite_schema = extend_schema(
    tags=["Избранное"],
    summary="Работа с избранными пользователями",
    description=(
        "Этот endpoint позволяет управлять списком избранных пользователей.\n\n"
        "⚠️ Требуется заголовок `X-Init-Data` с init_data от Telegram.\n"
        "Можно включить `X-Test-Mode: true`, чтобы протестировать без Telegram.\n\n"
        "POST - добавить пользователя в избранное\n"
        "GET - получить список избранных пользователей\n"
        "DELETE - удалить пользователя из избранного"
    ),
    parameters=[
        OpenApiParameter(
            name="X-Init-Data",
            type=str,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Строка init_data от Telegram WebApp (Telegram.WebApp.initData)"
        ),
        OpenApiParameter(
            name="X-Test-Mode",
            type=str,
            location=OpenApiParameter.HEADER,
            required=False,
            description="Если true — работает без проверки Telegram (тестовый режим)"
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное выполнение операции",
        ),
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Неверные данные или ошибка валидации",
            examples=[
                OpenApiExample(
                    name="Ошибка: tg_id не указан",
                    value={"error": "Укажите tg_id (добавляем в избранное пользователя)"},
                ),
                OpenApiExample(
                    name="Ошибка: добавление себя",
                    value={"error": "Нельзя добавить себя в избранное"},
                ),
            ],
        ),
        404: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Ресурс не найден",
            examples=[
                OpenApiExample(
                    name="Пользователь не найден",
                    value={"error": "Пользователь не найден"},
                ),
            ],
        ),
        500: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Внутренняя ошибка сервера",
            examples=[
                OpenApiExample(
                    name="Ошибка сервера",
                    value={"error": "Internal server error"},
                ),
            ],
        ),
    }
)

favorite_post_schema = extend_schema(
    summary="Добавить пользователя в избранное",
    description=(
        "Добавляет пользователя в список избранных.\n\n"
        "Параметры:\n"
        "- tg_id: Telegram ID пользователя для добавления в избранное"
    ),
    request=OpenApiTypes.OBJECT,
    examples=[
        OpenApiExample(
            name="Добавить в избранное",
            value={"tg_id": 987654321},
            request_only=True
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное добавление",
            examples=[
                OpenApiExample(
                    name="Пользователь добавлен",
                    value={
                        "created": True,
                        "favorite": {
                            "id": 1,
                            "owner": {"tg_id": 123456789, "first_name": "Иван"},
                            "target": {"tg_id": 987654321, "first_name": "Мария"},
                            "created_at": "2024-01-15T10:30:00Z"
                        }
                    },
                ),
                OpenApiExample(
                    name="Пользователь уже в избранном",
                    value={
                        "created": False,
                        "favorite": {
                            "id": 1,
                            "owner": {"tg_id": 123456789, "first_name": "Иван"},
                            "target": {"tg_id": 987654321, "first_name": "Мария"},
                            "created_at": "2024-01-15T10:30:00Z"
                        }
                    },
                ),
            ],
        ),
    }
)

favorite_get_schema = extend_schema(
    summary="Получить список избранных пользователей",
    description="Возвращает список всех пользователей, добавленных в избранное.",
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное получение списка",
            examples=[
                OpenApiExample(
                    name="Список избранных",
                    value={
                        "results": [
                            {
                                "id": 1,
                                "created_at": "2024-01-15T10:30:00Z",
                                "target": {
                                    "tg_id": 987654321,
                                    "first_name": "Мария",
                                    "username": "maria",
                                    "language_code": "ru",
                                    "gender": "Woman",
                                    "city": "Москва"
                                }
                            },
                            {
                                "id": 2,
                                "created_at": "2024-01-14T15:20:00Z",
                                "target": {
                                    "tg_id": 555555555,
                                    "first_name": "Анна",
                                    "username": "anna",
                                    "language_code": "ru",
                                    "gender": "Woman",
                                    "city": "Санкт-Петербург"
                                }
                            }
                        ],
                        "count": 2
                    },
                ),
                OpenApiExample(
                    name="Пустой список",
                    value={"results": [], "count": 0},
                ),
            ],
        ),
    }
)

favorite_delete_schema = extend_schema(
    summary="Удалить пользователя из избранного",
    description=(
        "Удаляет пользователя из списка избранных.\n\n"
        "Параметры:\n"
        "- tg_id: Telegram ID пользователя для удаления из избранного"
    ),
    request=OpenApiTypes.OBJECT,
    examples=[
        OpenApiExample(
            name="Удалить из избранного",
            value={"tg_id": 987654321},
            request_only=True
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное удаление",
            examples=[
                OpenApiExample(
                    name="Пользователь удален",
                    value={"deleted": True},
                ),
                OpenApiExample(
                    name="Пользователь не был в избранном",
                    value={"deleted": False},
                ),
            ],
        ),
    }
)



profile_detail_schema = extend_schema(
    tags=["Анкета"],
    summary="Просмотр анкеты другого пользователя",
    description=(
        "Этот endpoint позволяет просмотреть полную анкету другого пользователя "
        "с фото, счетчиками лайков/дизлайков и реакциями текущего пользователя на каждое фото.\n\n"
        "⚠️ Требуется заголовок `X-Init-Data` с init_data от Telegram.\n"
        "Можно включить `X-Test-Mode: true`, чтобы протестировать без Telegram.\n\n"
        "Возвращает профиль в зависимости от пола пользователя (мужской/женский) "
        "с полной информацией и фотографиями."
    ),
    parameters=[
        OpenApiParameter(
            name="X-Init-Data",
            type=str,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Строка init_data от Telegram WebApp (Telegram.WebApp.initData)"
        ),
        OpenApiParameter(
            name="X-Test-Mode",
            type=str,
            location=OpenApiParameter.HEADER,
            required=False,
            description="Если true — работает без проверки Telegram (тестовый режим)"
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное получение анкеты",
        ),
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Неверные данные или ошибка валидации",
            examples=[
                OpenApiExample(
                    name="Ошибка: tg_id не указан",
                    value={"error": "Укажите tg_id"},
                ),
                OpenApiExample(
                    name="Ошибка: пол не указан",
                    value={"error": "У пользователя не указан пол"},
                ),
            ],
        ),
        404: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Ресурс не найден",
            examples=[
                OpenApiExample(
                    name="Игрок не найден",
                    value={"error": "Игрок не найден"},
                ),
                OpenApiExample(
                    name="Пользователь не найден",
                    value={"error": "Пользователь не найден"},
                ),
                OpenApiExample(
                    name="Анкета не найдена",
                    value={"error": "Анкета не найдена"},
                ),
            ],
        ),
        500: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Внутренняя ошибка сервера",
            examples=[
                OpenApiExample(
                    name="Ошибка сервера",
                    value={"error": "Internal server error"},
                ),
            ],
        ),
    }
)

profile_detail_get_schema = extend_schema(
    summary="Получить анкету пользователя по tg_id",
    description=(
        "Возвращает полную анкету пользователя с фотографиями, счетчиками лайков/дизлайков "
        "и реакциями текущего пользователя на каждое фото.\n\n"
        "Параметры:\n"
        "- tg_id: Telegram ID пользователя, анкету которого нужно просмотреть"
    ),
    request=OpenApiTypes.OBJECT,
    examples=[
        OpenApiExample(
            name="Запрос анкеты пользователя",
            value={"tg_id": 987654321},
            request_only=True
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Успешное получение анкеты",
            examples=[
                OpenApiExample(
                    name="Мужская анкета",
                    value={
                        "id": 1,
                        "player": {
                            "id": 1,
                            "tg_id": 987654321,
                            "first_name": "Алексей",
                            "username": "alex",
                            "language_code": "ru",
                            "gender": "Man",
                            "city": "Москва",
                            "hide_age_in_profile": False,
                            "is_active": True
                        },
                        "birth_date": "1994-05-20",
                        "description": "Люблю активный отдых, спорт и путешествия",
                        "height": 185,
                        "weight": 80,
                        "body_type": "athletic",
                        "eye_color": "brown",
                        "hair_color": "dark",
                        "has_children": "no",
                        "want_children": "yes",
                        "smoking": "never",
                        "alcohol": "socially",
                        "religion": "orthodox",
                        "education": "higher",
                        "profession": "Software Engineer",
                        "hobbies": ["спорт", "путешествия", "чтение"],
                        "relationship_goal": "serious",
                        "communication_style": "direct",
                        "photos": [
                            {
                                "id": 1,
                                "image": "http://example.com/photo1.jpg",
                                "likes_count": 8,
                                "dislikes_count": 2,
                                "user_reactions": [{"reaction_type": "like"}],
                                "uploaded_at": "2024-01-15T10:30:00Z"
                            },
                            {
                                "id": 2,
                                "image": "http://example.com/photo2.jpg",
                                "likes_count": 12,
                                "dislikes_count": 1,
                                "user_reactions": [],
                                "uploaded_at": "2024-01-16T14:20:00Z"
                            }
                        ],
                        "created_at": "2024-01-10T09:15:00Z",
                        "updated_at": "2024-01-20T16:45:00Z"
                    },
                ),
                OpenApiExample(
                    name="Женская анкета",
                    value={
                        "id": 1,
                        "player": {
                            "id": 1,
                            "tg_id": 987654321,
                            "first_name": "Екатерина",
                            "username": "kate",
                            "language_code": "ru",
                            "gender": "Woman",
                            "city": "Санкт-Петербург",
                            "hide_age_in_profile": True,
                            "is_active": True
                        },
                        "birth_date": "1996-08-12",
                        "description": "Увлекаюсь искусством, фотографией и путешествиями",
                        "height": 170,
                        "weight": 55,
                        "body_type": "slim",
                        "eye_color": "green",
                        "hair_color": "blonde",
                        "has_children": "no",
                        "want_children": "maybe",
                        "smoking": "never",
                        "alcohol": "rarely",
                        "religion": "not_religious",
                        "education": "higher",
                        "profession": "Designer",
                        "hobbies": ["искусство", "фотография", "йога"],
                        "relationship_goal": "friendship",
                        "communication_style": "emotional",
                        "photos": [
                            {
                                "id": 1,
                                "image": "http://example.com/photo1.jpg",
                                "likes_count": 15,
                                "dislikes_count": 3,
                                "user_reactions": [{"reaction_type": "dislike"}],
                                "uploaded_at": "2024-01-15T10:30:00Z"
                            },
                            {
                                "id": 2,
                                "image": "http://example.com/photo2.jpg",
                                "likes_count": 20,
                                "dislikes_count": 2,
                                "user_reactions": [{"reaction_type": "like"}],
                                "uploaded_at": "2024-01-18T11:45:00Z"
                            }
                        ],
                        "created_at": "2024-01-12T11:30:00Z",
                        "updated_at": "2024-01-22T13:20:00Z"
                    },
                ),
            ],
        ),
    }
)



