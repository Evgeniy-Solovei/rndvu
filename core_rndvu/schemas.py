from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, OpenApiResponse, OpenApiExample, inline_serializer, \
    PolymorphicProxySerializer
from rest_framework import serializers
from core_rndvu.serializers import *

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
        200: inline_serializer(
            name='PlayerInfoResponse',
            fields={
                'created': serializers.BooleanField(),
                'player': PlayerSerializer(),
            }
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
        200: PolymorphicProxySerializer(
            component_name='PlayerGenderUpdateResponse',
            serializers=[
                inline_serializer(
                    name='ManResponse',
                    fields={
                        'player': PlayerSerializer(),
                        'profile': ProfileManSerializer(),
                    }
                ),
                inline_serializer(
                    name='WomanResponse',
                    fields={
                        'player': PlayerSerializer(),
                        'profile': ProfileWomanSerializer(),
                    }
                ),
            ],
            resource_type_field_name=None,
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
    ]
)

# Схема для GET метода
user_profile_get_schema = extend_schema(
    summary="Получить анкету пользователя",
    description="Получить анкету пользователя с фото (без лайков/дизлайков на фото)",
    responses={
        200: PolymorphicProxySerializer(
            component_name='UserProfileResponse',
            serializers=[
                FullProfileManSerializer,
                FullProfileWomanSerializer,
            ],
            resource_type_field_name=None,
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

# Схема для PATCH метода
user_profile_patch_schema = extend_schema(
    summary="Частично обновить анкету",
    description="Частично обновить анкету (и фото)",
    responses={
        200: PolymorphicProxySerializer(
            component_name='UserProfileResponse',
            serializers=[
                FullProfileManSerializer,
                FullProfileWomanSerializer,
            ],
            resource_type_field_name=None,
        ),
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Неверные данные или ошибка валидации",
            examples=[
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

# Схема для PUT метода
user_profile_put_schema = extend_schema(
    summary="Полностью обновить анкету",
    description="Полностью обновить анкету (и фото)",
    responses={
        200: PolymorphicProxySerializer(
            component_name='UserProfileResponse',
            serializers=[
                FullProfileManSerializer,
                FullProfileWomanSerializer,
            ],
            resource_type_field_name=None,
        ),
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Неверные данные или ошибка валидации",
            examples=[
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



user_main_photo_schema = extend_schema(
    tags=["Анкета"],
    summary="Выбор главного фото в анкете пользователя",
    description=(
        "Этот endpoint позволяет установить одно из загруженных фото как главное в анкете пользователя.\n\n"
        "⚠️ Требуется заголовок `X-Init-Data` с init_data от Telegram.\n"
        "Можно включить `X-Test-Mode: true`, чтобы протестировать без Telegram.\n\n"
        "При выборе главного фото:\n"
        "- С выбранного фото устанавливается флаг `main_photo = True`\n"
        "- Со всех остальных фото пользователя флаг `main_photo` снимается\n"
        "- Главное фото будет отображаться первым в анкете\n\n"
        "Фото должно быть предварительно загружено через endpoint загрузки фото."
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
    request={
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "photo_id": {
                            "type": "integer",
                            "description": "ID фото, которое нужно сделать главным"
                        }
                    },
                    "required": ["photo_id"]
                }
            }
        }
    },
    responses={
        200: MainPhotoResponseSerializer,
        400: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Неверные данные или ошибка валидации",
            examples=[
                OpenApiExample(
                    name="Ошибка: photo_id не указан",
                    value={"error": "Не указан photo_id"},
                ),
                OpenApiExample(
                    name="Ошибка: неверный формат",
                    value={"error": "photo_id должен быть числом"},
                ),
            ],
        ),
        404: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Ресурс не найден",
            examples=[
                OpenApiExample(
                    name="Фото не найдено",
                    value={"error": "Фото не найдено"},
                ),
                OpenApiExample(
                    name="Профиль не найден",
                    value={"error": "Профиль не найден"},
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
                    value={"error": "Ошибка сервера", "details": "..."},
                ),
            ],
        ),
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
        200: GameUsersResponseSerializer,
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
        200: MutualSympathyResponseSerializer,
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
        200: SympathyResponseSerializer,  # ← СЕРИАЛИЗАТОР ДЛЯ POST
        400: OpenApiResponse(...),
        404: OpenApiResponse(...),
    }
)

sympathy_get_schema = extend_schema(
    summary="Получить список взаимных симпатий",
    description="Возвращает список всех взаимных симпатий, где текущий пользователь является участником.",
    responses={
        200: MutualSympathyResponseSerializer,  # ← СЕРИАЛИЗАТОР ДЛЯ GET
        400: OpenApiResponse(...),
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
        200: DeleteSympathyResponseSerializer,  # ← СЕРИАЛИЗАТОР ДЛЯ DELETE
        404: OpenApiResponse(...),
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
        200: FavoriteListResponseSerializer,
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
        200: FavoriteResponseSerializer,  # ← СЕРИАЛИЗАТОР ДЛЯ POST
        400: OpenApiResponse(...),
        404: OpenApiResponse(...),
    }
)

favorite_get_schema = extend_schema(
    summary="Получить список избранных пользователей",
    description="Возвращает список всех пользователей, добавленных в избранное.",
    responses={
        200: FavoriteListResponseSerializer,  # ← СЕРИАЛИЗАТОР ДЛЯ GET
        400: OpenApiResponse(...),
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
        200: DeleteFavoriteResponseSerializer,  # ← СЕРИАЛИЗАТОР ДЛЯ DELETE
        400: OpenApiResponse(...),
        404: OpenApiResponse(...),
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
        200: PolymorphicProxySerializer(
            component_name='ProfileDetailResponse',
            serializers=[
                FullProfileManSerializer,
                FullProfileWomanSerializer,
            ],
            resource_type_field_name=None,
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



event_get_schema = extend_schema(
    tags=["Ивенты"],
    summary="Получить все ивенты текущего пользователя или один по ID",
    description="Возвращает один ивент если указан event_id, иначе список всех активных ивентов пользователя",
    parameters=[
        OpenApiParameter("event_id", OpenApiTypes.INT, OpenApiParameter.PATH, required=False),
        OpenApiParameter("X-Init-Data", OpenApiTypes.STR, OpenApiParameter.HEADER, required=True),
        OpenApiParameter("X-Test-Mode", OpenApiTypes.STR, OpenApiParameter.HEADER, required=False),
    ],
    responses={
        200: EventSerializer(many=True),  # для списка
        404: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Ивент или игрок не найден",
        ),
    }
)



event_post_schema = extend_schema(
    tags=["Ивенты"],
    summary="Создать новый ивент",
    description="Создает новый ивент текущего пользователя",
    parameters=[
        OpenApiParameter("X-Init-Data", OpenApiTypes.STR, OpenApiParameter.HEADER, required=True),
        OpenApiParameter("X-Test-Mode", OpenApiTypes.STR, OpenApiParameter.HEADER, required=False),
    ],
    request=EventSerializer,
    responses={200: EventSerializer}
)

event_patch_schema = extend_schema(
    tags=["Ивенты"],
    summary="Обновить существующий ивент (частично)",
    parameters=[
        OpenApiParameter("event_id", OpenApiTypes.INT, OpenApiParameter.PATH, required=True),
        OpenApiParameter("X-Init-Data", OpenApiTypes.STR, OpenApiParameter.HEADER, required=True),
        OpenApiParameter("X-Test-Mode", OpenApiTypes.STR, OpenApiParameter.HEADER, required=False),
    ],
    request=EventSerializer,
    responses={200: EventSerializer}
)

event_delete_schema = extend_schema(
    tags=["Ивенты"],
    summary="Удалить ивент",
    parameters=[
        OpenApiParameter("event_id", OpenApiTypes.INT, OpenApiParameter.PATH, required=True),
        OpenApiParameter("X-Init-Data", OpenApiTypes.STR, OpenApiParameter.HEADER, required=True),
        OpenApiParameter("X-Test-Mode", OpenApiTypes.STR, OpenApiParameter.HEADER, required=False),
    ],
    responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT)}
)



opposite_gender_events_get_schema = extend_schema(
    tags=["Ивенты"],
    summary="Получить ивенты противоположного пола с фильтрами",
    description=(
        "Возвращает список активных ивентов противоположного пола текущего пользователя.\n\n"
        "Можно передать фильтры:\n"
        "- city — фильтр по городу\n"
        "- min_age — минимальный возраст участников\n"
        "- max_age — максимальный возраст участников\n"
        "- page — номер страницы пагинации\n\n"
        "Если передан event_id — возвращается один конкретный ивент."
    ),
    parameters=[
        OpenApiParameter("event_id", OpenApiTypes.INT, OpenApiParameter.PATH, required=False),
        OpenApiParameter("city", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("min_age", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("max_age", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("X-Init-Data", OpenApiTypes.STR, OpenApiParameter.HEADER, required=True),
        OpenApiParameter("X-Test-Mode", OpenApiTypes.STR, OpenApiParameter.HEADER, required=False),
    ],
    responses={
        200: EventSerializer(many=True),
        401: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Пользователь не авторизован",
            examples=[
                OpenApiExample(
                    name="Не авторизован",
                    value={"error": "Не авторизован"}
                ),
            ],
        ),
        404: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Ресурс не найден",
            examples=[
                OpenApiExample(
                    name="Игрок не найден",
                    value={"error": "Пользователь не найден"}
                ),
                OpenApiExample(
                    name="Ивент не найден",
                    value={"error": "Ивент не найден"}
                ),
            ],
        ),
        500: OpenApiResponse(
            response=OpenApiTypes.OBJECT,
            description="Внутренняя ошибка сервера",
            examples=[
                OpenApiExample(
                    name="Ошибка сервера",
                    value={"error": "Internal server error"}
                ),
            ],
        ),
    }
)


reaction_to_the_questionnaire = extend_schema(
    tags=["Игрок"],
    summary="Лайк или дизлайк пользователя",
    description=(
        "Позволяет поставить или убрать лайк/дизлайк другому игроку.\n\n"
        "⚠️ Требуется заголовок `X-Init-Data` (init_data от Telegram WebApp)."
    ),
    request=UserLikeRequestSerializer,
    responses={
        200: UserLikeResponseSerializer,
        400: OpenApiResponse(
            response=UserLikeResponseSerializer,
            description="Неверные данные или ошибка валидации"
        ),
        404: OpenApiResponse(
            description="Игрок не найден"
        ),
    }
)


yookassa = extend_schema(
    tags=["Юкасса"],
    summary="Создать платёж YooKassa",
    description=(
        "Возвращает ссылку на оплату подписки/пакета рецептов.\n\n"
        "В теле запроса обязательно прокидывать:\n"
        "- `product_id` — id продукта для оплаты\n"
        "- `return_url` — url для редиректа после оплаты\n"
        "- `init_data` — данные инициализации (telegram_user)\n"
    ),
    request=CreatePaymentRequestSerializer,
    responses={
        200: CreatePaymentResponseSerializer,
        404: ErrorResponseSerializer,
        400: ErrorResponseSerializer,
        500: ErrorResponseSerializer,
    }
)


product_list = extend_schema(
    tags=["Платежи"],
    summary="Получить список платных продуктов",
    description=(
        "Возвращает список всех доступных платных продуктов (подписок).\n\n"
        "⚠️ Требуется заголовок `X-Init-Data` (init_data от Telegram WebApp)."
    ),
    responses={
        200: ProductSerializer(many=True),
        400: OpenApiResponse(
            description="Неверные данные авторизации"
        ),
    }
)



webhook_yookassa = extend_schema(
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


update_verification = extend_schema(
    tags=["Игрок"],
    summary="Верификация пользователя",
    description=(
        "Устанавливает флаг верификации пользователя в True.\n\n"
        "⚠️ Требуется заголовок `X-Init-Data` (init_data от Telegram WebApp)."
    ),
    responses={
        200: OpenApiResponse(
            description="Верификация успешно установлена",
            examples=[
                OpenApiExample(
                    "Пример ответа",
                    value={"verification": True}
                )
            ]
        ),
        404: OpenApiResponse(description="Пользователь не найден"),
    }
)
