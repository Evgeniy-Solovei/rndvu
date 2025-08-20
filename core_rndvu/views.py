import math
from adrf.views import APIView
from django.db.models import Prefetch, Count, Q, F, Case, When, DateField
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema_view
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from core_rndvu.models import *
from core_rndvu.schemas import *
from core_rndvu.serializers import *

def availability_init_data(request):
    """Функция проверяющая наличие init_data"""
    init_data = getattr(request, "telegram_user", None)
    if not init_data:
        return Response({"error": "Требуется авторизация через Telegram"}, status=status.HTTP_401_UNAUTHORIZED)
    return init_data


@player_info_schema
class PlayerInfoView(APIView):
    """Ручка для получения информации об игроке создан он или нет"""
    async def post(self, request):
        # Достаём данные игрока из init_data
        init_data = availability_init_data(request)
        try:
            # Создаём игрока или достаём из БД
            player, created = await Player.objects.aget_or_create(
                tg_id=init_data["id"],
                defaults={
                    "first_name": init_data.get("first_name") or "",
                    "username": init_data.get("username") or "",
                    "language_code": init_data.get("language_code") or "ru",
                }
            )
            return Response({"created": created, "player": PlayerSerializer(player).data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Ошибка при создании/получении игрока", "details": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@player_gender_update_schema
class PlayerGenderUpdateView(APIView):
    """Ручка для обновления gender у пользователя"""
    async def post(self, request):
        # Достаём данные игрока из init_data
        init_data = availability_init_data(request)
        try:
            # Достаём гендер от фронта
            gender = request.data.get("gender")
            # Проверка допустимых значений чойсов
            if gender not in ['Man', 'Woman']:
                return Response({"error": "Параметр gender обязателен (Man, Woman)"}, status=status.HTTP_400_BAD_REQUEST)
            player = await Player.objects.aget(tg_id=init_data["id"])
            player.gender = gender
            await player.asave(update_fields=["gender"])
            # Если пользователь мужчина, создаём мужскую анкету
            if gender == "Man":
                try:
                    profile = await ProfileMan.objects.aget(player=player)
                except ProfileMan.DoesNotExist:
                    profile = ProfileMan(player=player)
                    await profile.asave()
                serializer = ProfileManSerializer(profile)
            # Если пользователь женщина, создаём женскую анкету
            else:
                try:
                    profile = await ProfileWoman.objects.aget(player=player)
                except ProfileWoman.DoesNotExist:
                    profile = ProfileWoman(player=player)
                    await profile.asave()
                serializer = ProfileWomanSerializer(profile)
            return Response({"player": PlayerSerializer(player).data, "profile": serializer.data,},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@user_profile_schema
@extend_schema_view(get=user_profile_get_schema, patch=user_profile_patch_schema, put=user_profile_put_schema)
class UserProfileView(APIView):
    """Ручка для работы с анкетой пользователя (GET, PATCH, PUT)"""
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    async def get(self, request):
        """Получить анкету пользователя с фото, счётчиками и реакцией текущего пользователя"""
        init_data = availability_init_data(request)
        try:
            # Получаем игрока по tg_id
            player = await Player.objects.aget(tg_id=init_data["id"])
            if not player.gender:
                return Response({"error": "Пол пользователя не указан"}, status=status.HTTP_400_BAD_REQUEST)

            if player.gender == "Man":
                # Подготавливаем QS реакций ТЕКУЩЕГО пользователя ТОЛЬКО на мужские фото:
                my_reactions = PhotoReaction.objects.filter(
                    player=player, man_photo__isnull=False
                ).only("id", "reaction_type", "man_photo_id")

                # [БД #3] QS фото с аннотациями:
                #  - likes_count: количество связанных реакций с типом "like"
                #  - dislikes_count: количество связанных реакций с типом "dislike"
                # При сериализации эти поля читаются как атрибуты, ДОП. запросов нет.
                # Дополнительно префетчим ТОЛЬКО реакции текущего игрока в to_attr="user_reactions":
                #   Prefetch("reactions", queryset=my_reactions, to_attr="user_reactions")
                # Это положит СПИСОК реакций данного пользователя на КАЖДОЕ фото (обычно 0 или 1 элемент).
                man_photos_qs = (
                    ManPhoto.objects
                    .annotate(
                        likes_count=Count("reactions", filter=Q(reactions__reaction_type="like")),
                        dislikes_count=Count("reactions", filter=Q(reactions__reaction_type="dislike")),
                    )
                    .prefetch_related(
                        Prefetch("reactions", queryset=my_reactions, to_attr="user_reactions")
                    )
                )
                # Получаем профиль мужчины с:
                # - JOIN на player (select_related) — чтобы не было ленивой догрузки
                # - PREFETCH photo queryset (man_photos_qs) — одним доп. запросом притянет все фото профиля
                profile = await (
                    ProfileMan.objects
                    .select_related("player")
                    .prefetch_related(Prefetch("photos", queryset=man_photos_qs))
                ).aget(player=player)

                serializer = FullProfileManSerializer(profile, context={"request": request})

            else:
                # QS реакций ТЕКУЩЕГО пользователя ТОЛЬКО на женские фото
                my_reactions = PhotoReaction.objects.filter(
                    player=player, woman_photo__isnull=False
                ).only("id", "reaction_type", "woman_photo_id")
                # QS фото женщин + аннотации лайков/дизлайков + префетч реакций текущего пользователя
                woman_photos_qs = (
                    WomanPhoto.objects
                    .annotate(
                        likes_count=Count("reactions", filter=Q(reactions__reaction_type="like")),
                        dislikes_count=Count("reactions", filter=Q(reactions__reaction_type="dislike")),
                    )
                    .prefetch_related(
                        Prefetch("reactions", queryset=my_reactions, to_attr="user_reactions")
                    )
                )
                # Получаем профиль женщины с JOIN player и PREFETCH фото
                profile = await (
                    ProfileWoman.objects
                    .select_related("player")
                    .prefetch_related(Prefetch("photos", queryset=woman_photos_qs))
                ).aget(player=player)

                serializer = FullProfileWomanSerializer(profile, context={"request": request})

            return Response(serializer.data, status=status.HTTP_200_OK)

        except (ProfileMan.DoesNotExist, ProfileWoman.DoesNotExist):
            return Response({"error": "Анкета не найдена"}, status=status.HTTP_404_NOT_FOUND)
        except Player.DoesNotExist:
            return Response({"error": "Игрок не найден"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    async def patch(self, request):
        """Частично обновить анкету (и фото)"""
        return await self._update_profile(request, partial=True)

    async def put(self, request):
        """Полностью обновить анкету (и фото)"""
        return await self._update_profile(request, partial=False)

    async def _update_profile(self, request, partial=True):
        """
        Последовательность:
          1) Найти профиль игрока (по полу).
          2) Валидировать и сохранить поля анкеты через async-сериализатор (adrf).
          3) Обработать файлы:
             - загрузить новые (form-data key: photos / photos[])
             - удалить выбранные (form-data key: delete_photo_ids = "1,3,5" или несколько отдельных ключей)
          4) Перечитать профиль с аннотациями лайков/дизлайков и реакциями текущего пользователя (как в GET) и вернуть.
        """
        init_data = availability_init_data(request)
        try:
            # Игрок по tg_id
            player = await Player.objects.aget(tg_id=init_data["id"])
            if not player.gender:
                return Response({"error": "Пол пользователя не указан"}, status=status.HTTP_400_BAD_REQUEST)

            is_man = (player.gender == "Man")
            if is_man:
                # SELECT ProfileMan
                profile = await ProfileMan.objects.aget(player=player)
                # Update-сериализатор: читает ТОЛЬКО request.data (текстовая часть multipart)
                serializer = ProfileUpdateSerializer(
                    profile, data=request.data, partial=partial,
                    context={"model": ProfileMan, "request": request},
                )
            else:
                # SELECT ProfileWoman
                profile = await ProfileWoman.objects.aget(player=player)
                serializer = ProfileUpdateSerializer(
                    profile, data=request.data, partial=partial,
                    context={"model": ProfileWoman, "request": request},
                )

            if not serializer.is_valid():
                return Response({"error": "Ошибка валидации", "details": serializer.errors},
                                status=status.HTTP_400_BAD_REQUEST)
            # Сохраняем поля анкеты
            await serializer.asave()

            """Если пришли поля из модели Player, то меняем их в БД"""
            allowed_player_fields = {"first_name", "username", "language_code", "hide_age_in_profile", "hide_age_in_profile", "is_active", "city"}
            updated = []
            for field in allowed_player_fields:
                if field in request.data:
                    value = request.data.get(field)
                    setattr(player, field, value)
                    updated.append(field)
            if updated:
                await player.asave(update_fields=updated)

            """Файлы: загрузка/удаление"""
            files = request.FILES.getlist("photos") or request.FILES.getlist("photos[]")

            delete_ids_raw = request.data.get("delete_photo_ids")
            if delete_ids_raw is None:
                delete_ids = request.data.getlist("delete_photo_ids")
            else:
                delete_ids = [x.strip() for x in str(delete_ids_raw).split(",") if x.strip()]

            if is_man:
                # INSERT новых фото — по одному на файл (asave)
                for f in files:
                    obj = ManPhoto(profile=profile, image=f)
                    await obj.asave()
                # DELETE выбранных фото (фильтр по своему профилю обязательно)
                if delete_ids:
                    await ManPhoto.objects.filter(profile=profile, id__in=delete_ids).adelete()
            else:
                # INSERT новых фото для женского профиля
                for f in files:
                    obj = WomanPhoto(profile=profile, image=f)
                    await obj.asave()
                # DELETE выбранных фото
                if delete_ids:
                    await WomanPhoto.objects.filter(profile=profile, id__in=delete_ids).adelete()

            # 4) Рефетчим профиль для ответа (с лайками/дизлайками и реакцией текущего пользователя)
            if is_man:
                # Реакции текущего пользователя на мужские фото
                my_reactions = PhotoReaction.objects.filter(
                    player=player, man_photo__isnull=False
                ).only("id", "reaction_type", "man_photo_id")
                # Фото c аннотациями и префетчем user_reactions
                man_photos_qs = (
                    ManPhoto.objects
                    .annotate(
                        likes_count=Count("reactions", filter=Q(reactions__reaction_type="like")),
                        dislikes_count=Count("reactions", filter=Q(reactions__reaction_type="dislike")),
                    )
                    .prefetch_related(
                        Prefetch("reactions", queryset=my_reactions, to_attr="user_reactions")
                    )
                )
                # Профиль мужчины с JOIN player + PREFETCH фото
                profile_refetched = await (
                    ProfileMan.objects
                    .select_related("player")
                    .prefetch_related(Prefetch("photos", queryset=man_photos_qs))
                ).aget(pk=profile.pk)

                full = FullProfileManSerializer(profile_refetched, context={"request": request})
            else:
                # Реакции текущего пользователя на женские фото
                my_reactions = PhotoReaction.objects.filter(
                    player=player, woman_photo__isnull=False
                ).only("id", "reaction_type", "woman_photo_id")
                # Фото женщин с аннотациями и префетчем user_reactions
                woman_photos_qs = (
                    WomanPhoto.objects
                    .annotate(
                        likes_count=Count("reactions", filter=Q(reactions__reaction_type="like")),
                        dislikes_count=Count("reactions", filter=Q(reactions__reaction_type="dislike")),
                    )
                    .prefetch_related(
                        Prefetch("reactions", queryset=my_reactions, to_attr="user_reactions")
                    )
                )
                # Профиль женщины с JOIN player + PREFETCH фото
                profile_refetched = await (
                    ProfileWoman.objects
                    .select_related("player")
                    .prefetch_related(Prefetch("photos", queryset=woman_photos_qs))
                ).aget(pk=profile.pk)

                full = FullProfileWomanSerializer(profile_refetched, context={"request": request})

            return Response(full.data, status=status.HTTP_200_OK)

        except (ProfileMan.DoesNotExist, ProfileWoman.DoesNotExist):
            return Response({"error": "Анкета не найдена"}, status=status.HTTP_404_NOT_FOUND)
        except Player.DoesNotExist:
            return Response({"error": "Игрок не найден"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@photo_reaction_schema
@extend_schema_view(post=photo_reaction_post_schema, delete=photo_reaction_delete_schema)
class PhotoReactionView(APIView):
    """Ручка для работы с реакциями на фото (лайки/дизлайки)"""
    async def post(self, request):
        """Поставить или изменить реакцию на фото"""
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            # Получаем пользователя
            player = await Player.objects.aget(tg_id=init_data["id"])
            # Получаем данные от фронта
            man_photo_id = request.data.get("photo_id")
            woman_photo_id = request.data.get("woman_photo_id")
            reaction_type = request.data.get("reaction_type")
            # Валидация
            if not reaction_type or reaction_type not in ['like', 'dislike']:
                return Response({"error": "Параметр reaction_type обязателен и должен быть 'like' или 'dislike'"}, 
                              status=status.HTTP_400_BAD_REQUEST)
            if not man_photo_id and not woman_photo_id:
                return Response({"error": "Должно быть указано одно фото (photo_id или woman_photo_id)"}, 
                              status=status.HTTP_400_BAD_REQUEST)
            if man_photo_id and woman_photo_id:
                return Response({"error": "Нельзя указать и мужское, и женское фото одновременно"}, 
                              status=status.HTTP_400_BAD_REQUEST)
            # Проверяем существование фото
            if man_photo_id:
                try:
                    photo = await ManPhoto.objects.aget(id=man_photo_id)
                except ManPhoto.DoesNotExist:
                    return Response({"error": "Мужское фото не найдено"}, status=status.HTTP_404_NOT_FOUND)
            else:
                try:
                    photo = await WomanPhoto.objects.aget(id=woman_photo_id)
                except WomanPhoto.DoesNotExist:
                    return Response({"error": "Женское фото не найдено"}, status=status.HTTP_404_NOT_FOUND)
            # Проверяем, существует ли уже реакция от этого пользователя
            try:
                if man_photo_id:
                    existing_reaction = await PhotoReaction.objects.aget(player=player, man_photo=photo)
                else:
                    existing_reaction = await PhotoReaction.objects.aget(player=player, woman_photo=photo)
                # Если реакция уже существует, обновляем её
                if existing_reaction.reaction_type == reaction_type:
                    return Response({"message": "Такая реакция уже поставлена", "reaction": reaction_type}, 
                                  status=status.HTTP_200_OK)
                else:
                    # Изменяем тип реакции
                    existing_reaction.reaction_type = reaction_type
                    await existing_reaction.asave(update_fields=['reaction_type'])
                    message = "Реакция изменена"
            except PhotoReaction.DoesNotExist:
                # Создаем новую реакцию
                if man_photo_id:
                    reaction = PhotoReaction(player=player, man_photo=photo, reaction_type=reaction_type)
                else:
                    reaction = PhotoReaction(player=player, woman_photo=photo, reaction_type=reaction_type)
                await reaction.asave()
                message = "Реакция поставлена"
            # Возвращаем результат
            return Response({"message": message, "reaction_type": reaction_type,
                            "photo_id": man_photo_id or woman_photo_id, "photo_type": "man" if man_photo_id else "woman"},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    async def delete(self, request):
        """Убрать реакцию с фото"""
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            # Получаем пользователя
            player = await Player.objects.aget(tg_id=init_data["id"])
            # Получаем данные от фронта
            photo_id = request.data.get("photo_id")
            woman_photo_id = request.data.get("woman_photo_id")
            # Валидация
            if not photo_id and not woman_photo_id:
                return Response({"error": "Должно быть указано одно фото (photo_id или woman_photo_id)"}, 
                              status=status.HTTP_400_BAD_REQUEST)
            if photo_id and woman_photo_id:
                return Response({"error": "Нельзя указать и мужское, и женское фото одновременно"}, 
                              status=status.HTTP_400_BAD_REQUEST)
            # Удаляем реакцию
            try:
                if photo_id:
                    reaction = await PhotoReaction.objects.aget(player=player, man_photo_id=photo_id)
                else:
                    reaction = await PhotoReaction.objects.aget(player=player, woman_photo_id=woman_photo_id)
                await reaction.adelete()
                return Response({
                    "message": "Реакция убрана",
                    "photo_id": photo_id or woman_photo_id,
                    "photo_type": "man" if photo_id else "woman"
                }, status=status.HTTP_200_OK)
            except PhotoReaction.DoesNotExist:
                return Response({"message": "Реакция не найдена"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@game_users_schema
class GameUsersView(APIView):
    """GET: Пользователи для игры по фильтрам (город, возраст), по 10 на страницу"""
    async def get(self, request):
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            player = await Player.objects.aget(tg_id=init_data["id"])
            if not player.gender:
                return Response({"error": "Пол пользователя не указан"}, status=status.HTTP_400_BAD_REQUEST)

            # Параметры запроса для фильтрации передаваемых в URL
            city = request.query_params.get("city")
            min_age = request.query_params.get("min_age")
            max_age = request.query_params.get("max_age")
            page = int(request.query_params.get("page", 1) or 1)
            if page < 1:
                page = 1

            # Базовый QS: показываем ТОЛЬКО противоположный пол + активные + исключает себя
            opposite_gender = "Woman" if player.gender == "Man" else "Man"
            qs = Player.objects.filter(gender=opposite_gender, is_active=True).exclude(id=player.id)

            # Фильтр по городу (если задан)
            if city:
                qs = qs.filter(city__icontains=city)
            # Исключаем пользователей, с которыми уже есть симпатия (я → он ИЛИ он → я).
            qs = qs.exclude(Q(id__in=Sympathy.objects.filter(from_player=player).values_list("to_player_id", flat=True))
                            |Q(id__in=Sympathy.objects.filter(to_player=player).values_list("from_player_id", flat=True)))
            # Аннотируем ЕДИНУЮ дату рождения из соответствующего профиля.
            # Для женщин берём woman_profile.birth_date, для мужчин — man_profile.birth_date.
            # Это даёт одно поле `birth_date_any`, по которому удобно фильтровать и считать возраст.
            qs = qs.annotate(
                birth_date_any=Case(When(gender="Man",   then=F("man_profile__birth_date")),
                                    When(gender="Woman", then=F("woman_profile__birth_date")), output_field=DateField()))
            # Фильтр по возрасту через сравнение дат рождения
            today = timezone.localtime()

            def years_ago(years: int):
                """Дата 'сегодня минус N лет'; фикс для 29 февраля."""
                try:
                    return today.replace(year=today.year - years)
                except ValueError:
                    return today.replace(month=2, day=28, year=today.year - years)

            if min_age:
                upper = years_ago(int(min_age))
                qs = qs.filter(birth_date_any__lte=upper)

            if max_age:
                lower = years_ago(int(max_age) + 1) + timedelta(days=1)
                qs = qs.filter(birth_date_any__gte=lower)
            # ВАЖНО: префетчим фото соответствующего профиля
            if opposite_gender == "Man":
                # Мужские фото: select_related чтобы иметь сам профиль, и префетч фото
                qs = qs.select_related("man_profile").prefetch_related(
                    Prefetch("man_profile__photos", queryset=ManPhoto.objects.only("id", "image", "uploaded_at")))
            else:
                # Женские фото select_related чтобы иметь сам профиль, и префетч фото
                qs = qs.select_related("woman_profile").prefetch_related(
                    Prefetch("woman_profile__photos", queryset=WomanPhoto.objects.only("id", "image", "uploaded_at")))

            # Рандомная выдача
            qs = qs.order_by("?")

            # Пагинация
            page_size = 10
            # Считаем всего и страницы для пагинации + зажимаем page на последнюю страницу
            total_count = await qs.acount()
            if total_count == 0:
                return Response({"results": [], "page": 1, "page_size": page_size, "total_count": 0,
                                 "total_pages": 0, "has_prev": False, "has_next": False, "prev_page": None,
                                 "next_page": None}, status=status.HTTP_200_OK)
            total_pages = max(1, math.ceil(total_count / page_size))
            if page > total_pages:
                page = total_pages  # clamp к последней странице
            start = (page - 1) * page_size
            end = start + page_size
            # Асинхронно достаём первых 10 пользователей
            users = [obj async for obj in qs[start:end].aiterator()]
            # Сериализация.
            # Сериализатор может читать `obj.birth_date_any` вместо «склейки».
            # Дадим ему в объект поле `birth_date` (чтобы get_age() не менять).
            for u in users:
                u.birth_date = getattr(u, "birth_date_any", None)
            data = GameUserSerializer(users, many=True).data
            return Response({"results": data, "page": page, "page_size": page_size, "total_pages": total_pages},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@sympathy_schema
@extend_schema_view(post=sympathy_post_schema, get=sympathy_get_schema, delete=sympathy_delete_schema)
class SympathyView(APIView):
    """POST поставить симпатию; GET вернуть мои симпатии; DELETE снять мою симпатию"""
    async def post(self, request):
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            # Достаём пользователя, который делает запрос из init data
            player = await Player.objects.aget(tg_id=init_data["id"])
            # Принимаем от фронта tg_id пользователя, которому делаем симпатию
            tg_id = request.data.get("tg_id")
            if not tg_id:
                return Response({"error": "Укажите tg_id получателя симпатии"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                # Достаём из БД пользователя который получает симпатию (получатель)
                recipient = await Player.objects.aget(tg_id=tg_id)
            except Player.DoesNotExist:
                return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)
            # Проверяем, что получатель симпатии, не тот кто делает симпатию
            if recipient.tg_id == player.tg_id:
                return Response({"error": "Нельзя поставить симпатию себе"}, status=status.HTTP_400_BAD_REQUEST)
            # Ищем запись: recipient → player
            try:
                # От кого симпатия from_player, получатель симпатии to_player
                reverse = await Sympathy.objects.select_related("from_player", "to_player").aget(from_player=recipient, to_player=player)
            except Sympathy.DoesNotExist:
                reverse = None
            if reverse:
                # Есть симпатия ко мне → уже было от этого пользователя ко мне (НЕ создаём новую)
                if not reverse.is_mutual:
                    reverse.is_mutual = True
                    await reverse.asave(update_fields=["is_mutual"])
                    message = "Совпадение! Взаимная симпатия"
                else:
                    message = "Симпатия уже взаимная"
                data = SympathySerializer(reverse).data
                return Response({"message": message, "sympathy": data}, status=status.HTTP_200_OK)
            # Симпатии от получателя нету → создаём/находим мою направленную запись player → recipient
            obj, created = await Sympathy.objects.aget_or_create(from_player=player, to_player=recipient,
                                                                 defaults={"is_mutual": False})
            if not created:
                # прикрепляем, чтобы сериализатор не лез в БД, мы уже достали из init data player и человека для симпатии recipient
                obj.from_player = player
                obj.to_player = recipient
            message = "Симпатия создана" if created else "Симпатия уже есть"
            return Response({"message": message, "sympathy": SympathySerializer(obj).data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    async def get(self, request):
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            player = await Player.objects.aget(tg_id=init_data["id"])

            # Только взаимные пары, где я участник
            qs = (Sympathy.objects.filter(is_mutual=True).filter(Q(from_player=player) | Q(to_player=player))
                  .select_related("from_player", "to_player").order_by("-created_at"))
            items = [s async for s in qs.aiterator()]
            data = SympathySerializer(items, many=True).data
            return Response({"mutual": data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    async def delete(self, request):
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            # Достаём пользователя, который делает запрос из init data
            player = await Player.objects.aget(tg_id=init_data["id"])
            # Принимаем от фронта tg_id пользователя, которому дуляем симпатию
            tg_id = request.data.get("tg_id")
            if not tg_id:
                return Response({"error": "Укажите tg_id"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                other = await Player.objects.aget(tg_id=tg_id)
            except Player.DoesNotExist:
                return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)
            # Проверяем, что получатель симпатии, не тот кто делает симпатию
            if other.tg_id == player.tg_id:
                return Response({"error": "Нельзя оперировать на себе"}, status=status.HTTP_400_BAD_REQUEST)

            # Пробуем найти запись в направлении me -> other
            sympathy = await Sympathy.objects.filter(from_player=player, to_player=other).afirst()
            if sympathy:
                await sympathy.adelete()
                return Response({"deleted": True}, status=status.HTTP_200_OK)

            # Не нашли — пробуем обратное направление other -> me
            sympathy = await Sympathy.objects.filter(from_player=other, to_player=player).afirst()
            if sympathy:
                await sympathy.adelete()
                return Response({"deleted": True}, status=status.HTTP_200_OK)
            # Вообще нет симпатии между парой
            return Response({"deleted": False, "message": "Симпатия не найдена"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


    # async def get(self, request):
    #   """outgoing (ты выразил симпатию), incoming (тебя дали симпатию), mutual (взаимные симпатии)."""
    #     # Проверяем авторизацию через Telegram
    #     init_data = availability_init_data(request)
    #     try:
    #         # Достаём пользователя, который делает запрос из init data
    #         player = await Player.objects.aget(tg_id=init_data["id"])
    #         # все, где я получатель симпатия from_player + где я отправляю симпатию to_player
    #         outgoing_qs = (Sympathy.objects.filter(Q(from_player=player) | Q(to_player=player, is_mutual=True))
    #                        .select_related("from_player", "to_player").order_by("-created_at"))
    #         outgoing = [s async for s in outgoing_qs.aiterator()]
    #         outgoing_data = SympathySerializer(outgoing, many=True).data
    #
    #         # все, где я получатель симпатии to_player + где я отправляю симпатию from_player
    #         incoming_qs = (Sympathy.objects.filter(Q(to_player=player) | Q(from_player=player, is_mutual=True))
    #                        .select_related("from_player", "to_player").order_by("-created_at"))
    #         incoming = [s async for s in incoming_qs.aiterator()]
    #         incoming_data = SympathySerializer(incoming, many=True).data
    #         # Взаимные — одна запись на пару, где я участник и is_mutual=True
    #         mutual_qs = (
    #             Sympathy.objects.filter(Q(is_mutual=True) & (Q(from_player=player) | Q(to_player=player)))
    #             .select_related("from_player", "to_player").order_by("-created_at"))
    #         mutual = [s async for s in mutual_qs.aiterator()]
    #         mutual_data = SympathySerializer(mutual, many=True).data
    #         return Response({"outgoing": outgoing_data, "incoming": incoming_data, "mutual": mutual_data,}, status=status.HTTP_200_OK)
    #     except Exception as e:
    #         return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@favorite_schema
@extend_schema_view(post=favorite_post_schema, get=favorite_get_schema, delete=favorite_delete_schema)
class FavoriteView(APIView):
    """Избранное: POST добавить, GET показать список, DELETE удалить"""
    async def post(self, request):
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            # Получаем пользователя
            player = await Player.objects.aget(tg_id=init_data["id"])
            # Получаем пользователя для добавления в избранные
            tg_id = request.data.get("tg_id")
            if not tg_id:
                return Response({"error": "Укажите tg_id (добавляем в избранное пользователя)"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                target = await Player.objects.aget(tg_id=tg_id)
                if target.id == player.id:
                    return Response({"error": "Нельзя добавить себя в избранное"},
                                    status=status.HTTP_400_BAD_REQUEST)
            except Player.DoesNotExist:
                return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)
            obj, created = await Favorite.objects.aget_or_create(owner=player, target=target)
            if not created:
                # прикрепляем, чтобы сериализатор не лез в БД, мы уже достали из init data player и человека для симпатии recipient
                obj.owner = player
                obj.target = target
            data = FavoriteSerializer(obj).data
            return Response({"created": created, "favorite": data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    async def get(self, request):
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            # Получаем пользователя
            player = await Player.objects.aget(tg_id=init_data["id"])
            qs = Favorite.objects.filter(owner=player).select_related("target").order_by("-created_at")
            items = []
            async for fav in qs.aiterator():
                items.append({
                    "id": fav.id,
                    "created_at": fav.created_at,
                    "target": PlayerSerializer(fav.target).data,
                })
            return Response({"results": items, "count": len(items)}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    async def delete(self, request):
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            # Получаем пользователя
            player = await Player.objects.aget(tg_id=init_data["id"])
            tg_id = request.data.get("tg_id")
            if not tg_id:
                return Response({"error": "Укажите tg_id"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                target = await Player.objects.aget(tg_id=tg_id)
            except Player.DoesNotExist:
                return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)
            deleted, _ = await Favorite.objects.filter(owner=player, target=target).adelete()
            return Response({"deleted": bool(deleted)}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@profile_detail_schema
class ProfileDetailView(APIView):
    """
    GET: Посмотреть анкету другого пользователя по tg_id.
    Возвращает профиль (м/ж) + фото с лайками/дизлайками + реакцию ТЕКУЩЕГО пользователя на каждое фото.
    """
    async def get(self, request):
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            # Получаем пользователя
            player = await Player.objects.aget(tg_id=init_data["id"])
        except Player.DoesNotExist:
            return Response({"error": "Игрок не найден"}, status=status.HTTP_404_NOT_FOUND)
        # Получаем пользователя для просмотра профиля
        tg_id = request.data.get("tg_id")
        if not tg_id:
            return Response({"error": "Укажите tg_id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target = await Player.objects.aget(tg_id=tg_id)
        except Player.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        if not target.gender:
            return Response({"error": "У пользователя не указан пол"}, status=status.HTTP_400_BAD_REQUEST)
        if target.gender == "Man":
            # QS реакций ТЕКУЩЕГО игрока на фото МУЖЧИН (нужен для user_reactions)
            my_reactions_qs = (PhotoReaction.objects.filter(player=player, man_photo__isnull=False)
                               .only("id", "reaction_type", "man_photo_id"))
            # QS фото мужчины:
            #   + аннотация лайков/дизлайков через Count
            #   + префетч реакций текущего игрока → лягут в атрибут user_reactions
            man_photos_qs = (ManPhoto.objects.annotate( likes_count=Count("reactions",
                    filter=Q(reactions__reaction_type="like")), dislikes_count=Count("reactions",
                    filter=Q(reactions__reaction_type="dislike")),).prefetch_related(
                    Prefetch("reactions", queryset=my_reactions_qs, to_attr="user_reactions"))
            )
            try:
                # профиль мужчины цели + подтянутые фото
                profile = await (ProfileMan.objects.select_related("player")
                                 .prefetch_related(Prefetch("photos", queryset=man_photos_qs))).aget(player=target)
            except ProfileMan.DoesNotExist:
                return Response({"error": "Анкета не найдена"}, status=status.HTTP_404_NOT_FOUND)
            serializer = FullProfileManSerializer(profile, context={"request": request})
        else:
            # QS реакций ТЕКУЩЕГО игрока на фото ЖЕНЩИН
            my_reactions_qs = (PhotoReaction.objects.filter(player=player, woman_photo__isnull=False)
                               .only("id", "reaction_type", "woman_photo_id"))
            # QS фото женщины с аннотациями лайков/дизлайков + реакциями текущего игрока
            woman_photos_qs = (WomanPhoto.objects.annotate(likes_count=Count("reactions",
                    filter=Q(reactions__reaction_type="like")), dislikes_count=Count("reactions",
                    filter=Q(reactions__reaction_type="dislike")),).prefetch_related(
                    Prefetch("reactions", queryset=my_reactions_qs, to_attr="user_reactions"))
            )
            try:
                # профиль женщины + подтянутые фото
                profile = await (ProfileWoman.objects.select_related("player")
                                 .prefetch_related(Prefetch("photos", queryset=woman_photos_qs))).aget(player=target)
            except ProfileWoman.DoesNotExist:
                return Response({"error": "Анкета не найдена"}, status=status.HTTP_404_NOT_FOUND)
            serializer = FullProfileWomanSerializer(profile, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
