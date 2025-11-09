import json
import math

from adrf.generics import GenericAPIView
from adrf.views import APIView
from django.db.models import Prefetch, Count, Q, F, Case, When, DateField, Exists, OuterRef
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema_view
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from core_rndvu.models import *
from core_rndvu.schemas import *
from core_rndvu.serializers import *
from core_rndvu.yookassa_webhook import create_yookassa_payment


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
            if not player.gender:
                created = True
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
        """Получить анкету пользователя с фото (без лайков/дизлайков на фото)"""
        init_data = availability_init_data(request)
        try:
            # Получаем игрока по tg_id
            player = await Player.objects.aget(tg_id=init_data["id"])
            if not player.gender:
                return Response({"error": "Пол пользователя не указан"}, status=status.HTTP_400_BAD_REQUEST)

            if player.gender == "Man":
                # Просто подтягиваем фото без аннотаций реакций
                profile = await (
                    ProfileMan.objects
                    .select_related("player")
                    .prefetch_related("photos")
                ).aget(player=player)

                serializer = FullProfileManSerializer(profile, context={"request": request})

            else:
                # Просто подтягиваем фото без аннотаций реакций
                profile = await (
                    ProfileWoman.objects
                    .select_related("player")
                    .prefetch_related("photos")
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
        try:
            init_data = availability_init_data(request)
            player = await Player.objects.aget(tg_id=init_data["id"])
            if not player.gender:
                return Response({"error": "Пол пользователя не указан"}, status=status.HTTP_400_BAD_REQUEST)
            is_man = player.gender == "Man"
            # --- Защищаем ORM-запросы ---
            try:
                profile = await (ProfileMan.objects.aget(player=player) if is_man else ProfileWoman.objects.aget(player=player))
            except (ProfileMan.DoesNotExist, ProfileWoman.DoesNotExist):
                return Response({"error": "Анкета не найдена"}, status=status.HTTP_404_NOT_FOUND)

            # --- Безопасная валидация сериализатора ---
            serializer = ProfileUpdateSerializer(
                profile,
                data=request.data,
                partial=partial,
                context={"model": ProfileMan if is_man else ProfileWoman, "request": request},
            )

            if not serializer.is_valid():
                return Response({"error": "Ошибка валидации", "details": serializer.errors},
                                status=status.HTTP_400_BAD_REQUEST)

            await serializer.asave()

            # --- Безопасное обновление player ---
            try:
                allowed_player_fields = {
                    "first_name", "username", "language_code",
                    "hide_age_in_profile", "is_active", "city"
                }
                updated = [f for f in allowed_player_fields if f in request.data]
                for field in updated:
                    setattr(player, field, request.data.get(field))
                if updated:
                    await player.asave(update_fields=updated)
            except Exception as e:
                return Response({"error": f"Ошибка при обновлении игрока: {e}"}, status=status.HTTP_400_BAD_REQUEST)

            # --- Безопасная работа с файлами ---
            try:
                files = request.FILES.getlist("photos") or request.FILES.getlist("photos[]") or []
                delete_ids_raw = request.data.get("delete_photo_ids")
                delete_ids = []

                if delete_ids_raw is not None:
                    if isinstance(delete_ids_raw, list):
                        delete_ids = [str(x) for x in delete_ids_raw]
                    elif isinstance(delete_ids_raw, str):
                        delete_ids = [x.strip() for x in delete_ids_raw.split(",") if x.strip()]
                    elif isinstance(delete_ids_raw, int):
                        delete_ids = [str(delete_ids_raw)]

                PhotoModel = ManPhoto if is_man else WomanPhoto

                for f in files:
                    try:
                        obj = PhotoModel(profile=profile, image=f)
                        await obj.asave()
                    except Exception as e:
                        return Response({"error": f"Ошибка при сохранении файла: {e}"}, status=status.HTTP_400_BAD_REQUEST)

                if delete_ids:
                    await PhotoModel.objects.filter(profile=profile, id__in=delete_ids).adelete()
            except Exception as e:
                return Response({"error": f"Ошибка при обработке фото: {e}"}, status=status.HTTP_400_BAD_REQUEST)

            # --- Повторный запрос профиля ---
            try:
                profile_refetched = await (
                    (ProfileMan.objects if is_man else ProfileWoman.objects)
                    .select_related("player")
                    .prefetch_related("photos")
                ).aget(pk=profile.pk)
            except Exception as e:
                return Response({"error": f"Ошибка при повторном запросе анкеты: {e}"}, status=status.HTTP_400_BAD_REQUEST)

            serializer_cls = FullProfileManSerializer if is_man else FullProfileWomanSerializer
            full = serializer_cls(profile_refetched, context={"request": request})
            return Response(full.data, status=status.HTTP_200_OK)

        except Player.DoesNotExist:
            return Response({"error": "Игрок не найден"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Ловим любые неучтённые ошибки
            import traceback
            print("PATCH ERROR:\n", traceback.format_exc())  # лог в консоль
            return Response({"error": f"Необработанная ошибка: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # async def _update_profile(self, request, partial=True):
    #     """
    #     Последовательность:
    #       1) Найти профиль игрока (по полу).
    #       2) Валидировать и сохранить поля анкеты через async-сериализатор (adrf).
    #       3) Обработать файлы:
    #          - загрузить новые (form-data key: photos / photos[])
    #          - удалить выбранные (form-data key: delete_photo_ids = "1,3,5" или несколько отдельных ключей)
    #       4) Перечитать профиль с фото (без лайков/дизлайков) и вернуть.
    #     """
    #     init_data = availability_init_data(request)
    #     try:
    #         # Игрок по tg_id
    #         player = await Player.objects.aget(tg_id=init_data["id"])
    #         if not player.gender:
    #             return Response({"error": "Пол пользователя не указан"}, status=status.HTTP_400_BAD_REQUEST)

    #         is_man = (player.gender == "Man")
    #         if is_man:
    #             # SELECT ProfileMan
    #             profile = await ProfileMan.objects.aget(player=player)
    #             # Update-сериализатор: читает ТОЛЬКО request.data (текстовая часть multipart)
    #             serializer = ProfileUpdateSerializer(
    #                 profile, data=request.data, partial=partial,
    #                 context={"model": ProfileMan, "request": request},
    #             )
    #         else:
    #             # SELECT ProfileWoman
    #             profile = await ProfileWoman.objects.aget(player=player)
    #             serializer = ProfileUpdateSerializer(
    #                 profile, data=request.data, partial=partial,
    #                 context={"model": ProfileWoman, "request": request},
    #             )

    #         if not serializer.is_valid():
    #             return Response({"error": "Ошибка валидации", "details": serializer.errors},
    #                             status=status.HTTP_400_BAD_REQUEST)
    #         # Сохраняем поля анкеты
    #         await serializer.asave()

    #         """Если пришли поля из модели Player, то меняем их в БД"""
    #         allowed_player_fields = {"first_name", "username", "language_code", "hide_age_in_profile", "hide_age_in_profile", "is_active", "city"}
    #         updated = []
    #         for field in allowed_player_fields:
    #             if field in request.data:
    #                 value = request.data.get(field)
    #                 setattr(player, field, value)
    #                 updated.append(field)
    #         if updated:
    #             await player.asave(update_fields=updated)

    #         """Файлы: загрузка/удаление"""
    #         # Получаем файлы (если есть)
    #         files = []
    #         if request.FILES:
    #             files = request.FILES.getlist("photos") or request.FILES.getlist("photos[]") or []

    #         # УНИВЕРСАЛЬНАЯ обработка delete_photo_ids для JSON и FormData
    #         delete_ids = []
    #         delete_ids_raw = request.data.get("delete_photo_ids")

    #         if delete_ids_raw is not None:
    #             if isinstance(delete_ids_raw, list):
    #                 # Пришел JSON массив: [1, 2, 3]
    #                 delete_ids = [str(x) for x in delete_ids_raw]
    #             elif isinstance(delete_ids_raw, str):
    #                 # Пришла строка из FormData: "1,2,3"
    #                 delete_ids = [x.strip() for x in delete_ids_raw.split(",") if x.strip()]
    #             elif isinstance(delete_ids_raw, int):
    #                 # Пришел одиночный ID как число
    #                 delete_ids = [str(delete_ids_raw)]

    #         if is_man:
    #             # INSERT новых фото — по одному на файл (asave)
    #             for f in files:
    #                 obj = ManPhoto(profile=profile, image=f)
    #                 await obj.asave()
    #             # DELETE выбранных фото (фильтр по своему профилю обязательно)
    #             if delete_ids:
    #                 await ManPhoto.objects.filter(profile=profile, id__in=delete_ids).adelete()
    #         else:
    #             # INSERT новых фото для женского профиля
    #             for f in files:
    #                 obj = WomanPhoto(profile=profile, image=f)
    #                 await obj.asave()
    #             # DELETE выбранных фото
    #             if delete_ids:
    #                 await WomanPhoto.objects.filter(profile=profile, id__in=delete_ids).adelete()

    #         # 4) Рефетчим профиль для ответа (без лайков/дизлайков)
    #         if is_man:
    #             profile_refetched = await (
    #                 ProfileMan.objects
    #                 .select_related("player")
    #                 .prefetch_related("photos")
    #             ).aget(pk=profile.pk)

    #             full = FullProfileManSerializer(profile_refetched, context={"request": request})
    #         else:
    #             profile_refetched = await (
    #                 ProfileWoman.objects
    #                 .select_related("player")
    #                 .prefetch_related("photos")
    #             ).aget(pk=profile.pk)

    #             full = FullProfileWomanSerializer(profile_refetched, context={"request": request})

    #         return Response(full.data, status=status.HTTP_200_OK)

    #     except (ProfileMan.DoesNotExist, ProfileWoman.DoesNotExist):
    #         return Response({"error": "Анкета не найдена"}, status=status.HTTP_404_NOT_FOUND)
    #     except Player.DoesNotExist:
    #         return Response({"error": "Игрок не найден"}, status=status.HTTP_404_NOT_FOUND)
    #     except Exception as e:
    #         return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@user_main_photo_schema
class UserMainPhotoView(APIView):
    """Выбор главного фото у пользователя в анкете"""
    async def post(self, request):
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            # Получаем пользователя
            player = await Player.objects.aget(tg_id=init_data["id"])
            # Получаем данные от фронта
            photo_id = request.data.get("photo_id")
            if not photo_id:
                return Response({"error": "Не указан photo_id"}, status=status.HTTP_400_BAD_REQUEST)
            if player.gender == "Man":
                profile_man = await ProfileMan.objects.aget(player=player)
                try:
                    photo = await ManPhoto.objects.aget(id=photo_id, profile=profile_man)
                    # Сначала снимаем флаг со всех фото
                    await ManPhoto.objects.filter(profile=profile_man).aupdate(main_photo=False)
                    # Затем ставим флаг на выбранное фото
                    photo.main_photo = True
                    await photo.asave(update_fields=["main_photo"])
                    return Response({"message": "Главное фото обновлено", "main_photo_id": photo.id})
                except ManPhoto.DoesNotExist:
                    return Response({"error": "Фото не найдено"}, status=status.HTTP_404_NOT_FOUND)
            else:
                profile_woman = await ProfileWoman.objects.aget(player=player)
                try:
                    photo = await WomanPhoto.objects.aget(id=photo_id, profile=profile_woman)
                    # Сначала снимаем флаг со всех фото
                    await WomanPhoto.objects.filter(profile=profile_woman).aupdate(main_photo=False)
                    # Затем ставим флаг на выбранное фото
                    photo.main_photo = True
                    await photo.asave(update_fields=["main_photo"])
                    return Response({"message": "Главное фото обновлено", "main_photo_id": photo.id})
                except WomanPhoto.DoesNotExist:
                    return Response({"error": "Фото не найдено"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": "Ошибка сервера", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @photo_reaction_schema
# @extend_schema_view(post=photo_reaction_post_schema, delete=photo_reaction_delete_schema)
# class PhotoReactionView(APIView):
#     """Ручка для работы с реакциями на фото (лайки/дизлайки)"""
#     async def post(self, request):
#         """Поставить или изменить реакцию на фото"""
#         # Проверяем авторизацию через Telegram
#         init_data = availability_init_data(request)
#         try:
#             # Получаем пользователя
#             player = await Player.objects.aget(tg_id=init_data["id"])
#             # Получаем данные от фронта
#             man_photo_id = request.data.get("photo_id")
#             woman_photo_id = request.data.get("woman_photo_id")
#             reaction_type = request.data.get("reaction_type")
#             # Валидация
#             if not reaction_type or reaction_type not in ['like', 'dislike']:
#                 return Response({"error": "Параметр reaction_type обязателен и должен быть 'like' или 'dislike'"},
#                               status=status.HTTP_400_BAD_REQUEST)
#             if not man_photo_id and not woman_photo_id:
#                 return Response({"error": "Должно быть указано одно фото (photo_id или woman_photo_id)"},
#                               status=status.HTTP_400_BAD_REQUEST)
#             if man_photo_id and woman_photo_id:
#                 return Response({"error": "Нельзя указать и мужское, и женское фото одновременно"},
#                               status=status.HTTP_400_BAD_REQUEST)
#             # Проверяем существование фото
#             if man_photo_id:
#                 try:
#                     photo = await ManPhoto.objects.aget(id=man_photo_id)
#                 except ManPhoto.DoesNotExist:
#                     return Response({"error": "Мужское фото не найдено"}, status=status.HTTP_404_NOT_FOUND)
#             else:
#                 try:
#                     photo = await WomanPhoto.objects.aget(id=woman_photo_id)
#                 except WomanPhoto.DoesNotExist:
#                     return Response({"error": "Женское фото не найдено"}, status=status.HTTP_404_NOT_FOUND)
#             # Проверяем, существует ли уже реакция от этого пользователя
#             try:
#                 if man_photo_id:
#                     existing_reaction = await PhotoReaction.objects.aget(player=player, man_photo=photo)
#                 else:
#                     existing_reaction = await PhotoReaction.objects.aget(player=player, woman_photo=photo)
#                 # Если реакция уже существует, обновляем её
#                 if existing_reaction.reaction_type == reaction_type:
#                     return Response({"message": "Такая реакция уже поставлена", "reaction": reaction_type},
#                                   status=status.HTTP_200_OK)
#                 else:
#                     # Изменяем тип реакции
#                     existing_reaction.reaction_type = reaction_type
#                     await existing_reaction.asave(update_fields=['reaction_type'])
#                     message = "Реакция изменена"
#             except PhotoReaction.DoesNotExist:
#                 # Создаем новую реакцию
#                 if man_photo_id:
#                     reaction = PhotoReaction(player=player, man_photo=photo, reaction_type=reaction_type)
#                 else:
#                     reaction = PhotoReaction(player=player, woman_photo=photo, reaction_type=reaction_type)
#                 await reaction.asave()
#                 message = "Реакция поставлена"
#             # Возвращаем результат
#             return Response({"message": message, "reaction_type": reaction_type,
#                             "photo_id": man_photo_id or woman_photo_id, "photo_type": "man" if man_photo_id else "woman"},
#                             status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
#
#     async def delete(self, request):
#         """Убрать реакцию с фото"""
#         # Проверяем авторизацию через Telegram
#         init_data = availability_init_data(request)
#         try:
#             # Получаем пользователя
#             player = await Player.objects.aget(tg_id=init_data["id"])
#             # Получаем данные от фронта
#             photo_id = request.data.get("photo_id")
#             woman_photo_id = request.data.get("woman_photo_id")
#             # Валидация
#             if not photo_id and not woman_photo_id:
#                 return Response({"error": "Должно быть указано одно фото (photo_id или woman_photo_id)"},
#                               status=status.HTTP_400_BAD_REQUEST)
#             if photo_id and woman_photo_id:
#                 return Response({"error": "Нельзя указать и мужское, и женское фото одновременно"},
#                               status=status.HTTP_400_BAD_REQUEST)
#             # Удаляем реакцию
#             try:
#                 if photo_id:
#                     reaction = await PhotoReaction.objects.aget(player=player, man_photo_id=photo_id)
#                 else:
#                     reaction = await PhotoReaction.objects.aget(player=player, woman_photo_id=woman_photo_id)
#                 await reaction.adelete()
#                 return Response({
#                     "message": "Реакция убрана",
#                     "photo_id": photo_id or woman_photo_id,
#                     "photo_type": "man" if photo_id else "woman"
#                 }, status=status.HTTP_200_OK)
#             except PhotoReaction.DoesNotExist:
#                 return Response({"message": "Реакция не найдена"}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
            premium = request.query_params.get("premium", "").lower() == "true"
            if page < 1:
                page = 1

            # Базовый QS: показываем ТОЛЬКО противоположный пол + активные + исключает себя
            opposite_gender = "Woman" if player.gender == "Man" else "Man"
            qs = Player.objects.filter(gender=opposite_gender, is_active=True).exclude(id=player.id)

            # Для премиум-пользователей - каталог всех пользователей (не игра)
            if premium:
                # Фильтр по городу (если задан)
                if city:
                    qs = qs.filter(city__icontains=city)
                
                # Фильтруем пользователей, у которых есть профиль и хотя бы одно фото
                if opposite_gender == "Man":
                    qs = qs.filter(man_profile__isnull=False, man_profile__photos__isnull=False).distinct()
                else:
                    qs = qs.filter(woman_profile__isnull=False, woman_profile__photos__isnull=False).distinct()
                
                # Аннотируем дату рождения для фильтрации по возрасту
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
                
                # Сортировка по дате регистрации (новые сначала)
                qs = qs.order_by("-registration_date")
            else:
                # Для обычных пользователей - игра с фильтрами по симпатиям и пропущенным
                # Фильтр по городу (если задан)
                if city:
                    qs = qs.filter(city__icontains=city)

                # Исключаем тех, кому Я поставил симпатию (я → он)
                qs = qs.exclude(id__in=Sympathy.objects.filter(from_player=player).values_list("to_player_id", flat=True))
                
                # Исключаем взаимные симпатии (is_mutual=True) - тех, с кем уже есть взаимная симпатия
                qs = qs.exclude(
                    Q(id__in=Sympathy.objects.filter(from_player=player, is_mutual=True).values_list("to_player_id", flat=True))
                    | Q(id__in=Sympathy.objects.filter(to_player=player, is_mutual=True).values_list("from_player_id", flat=True))
                )
                
                # Исключаем пропущенных пользователей (те, кого мы пропустили)
                qs = qs.exclude(id__in=PassedUser.objects.filter(from_player=player).values_list("to_player_id", flat=True))
                
                # Фильтруем пользователей, у которых есть профиль и хотя бы одно фото
                if opposite_gender == "Man":
                    qs = qs.filter(man_profile__isnull=False, man_profile__photos__isnull=False).distinct()
                else:
                    qs = qs.filter(woman_profile__isnull=False, woman_profile__photos__isnull=False).distinct()
                
                # Аннотируем ЕДИНУЮ дату рождения из соответствующего профиля.
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
                
                # Случайная выдача для игры
                qs = qs.order_by("?")
            # ВАЖНО: префетчим фото соответствующего профиля
            if opposite_gender == "Man":
                # Мужские фото: select_related чтобы иметь сам профиль, и префетч фото
                qs = qs.select_related("man_profile").prefetch_related(
                    Prefetch("man_profile__photos", queryset=ManPhoto.objects.only("id", "image", "uploaded_at", "main_photo")))
            else:
                # Женские фото select_related чтобы иметь сам профиль, и префетч фото
                qs = qs.select_related("woman_profile").prefetch_related(
                    Prefetch("woman_profile__photos", queryset=WomanPhoto.objects.only("id", "image", "uploaded_at", "main_photo")))

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
            return Response({
                "results": data,
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
                "prev_page": page - 1 if page > 1 else None,
                "next_page": page + 1 if page < total_pages else None,
                "premium": premium
            }, status=status.HTTP_200_OK)
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
            # Принимаем от фронта tg_id пользователя
            tg_id = request.data.get("tg_id")
            if not tg_id:
                return Response({"error": "Укажите tg_id получателя симпатии"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Проверяем флаг skip (пропустить пользователя)
            skip = request.data.get("skip", False)
            if isinstance(skip, str):
                skip = skip.lower() in ("true", "1", "yes")
            
            try:
                # Достаём из БД пользователя
                recipient = await Player.objects.aget(tg_id=tg_id)
            except Player.DoesNotExist:
                return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)
            
            # Проверяем, что получатель симпатии, не тот кто делает симпатию
            if recipient.tg_id == player.tg_id:
                return Response({"error": "Нельзя оперировать на себе"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Если skip=True, создаём запись о пропуске
            if skip:
                # Удаляем симпатию если была (на случай если пользователь передумал)
                await Sympathy.objects.filter(from_player=player, to_player=recipient).adelete()
                await Sympathy.objects.filter(from_player=recipient, to_player=player).adelete()
                # Создаём запись о пропуске
                await PassedUser.objects.aget_or_create(from_player=player, to_player=recipient)
                return Response({"message": "Пользователь пропущен", "skipped": True}, status=status.HTTP_200_OK)
            
            # Если не skip, создаём симпатию (удаляем запись о пропуске если была)
            await PassedUser.objects.filter(from_player=player, to_player=recipient).adelete()
            
            # Сначала проверяем есть ли обратная симпатия (recipient → player)
            # Если есть - обновляем её, делая взаимной
            try:
                reverse_sympathy = await Sympathy.objects.select_related("from_player", "to_player").aget(from_player=recipient, to_player=player)
                # Есть обратная симпатия - обновляем её
                if not reverse_sympathy.is_mutual:
                    reverse_sympathy.is_mutual = True
                    await reverse_sympathy.asave(update_fields=["is_mutual"])
                    message = "Совпадение! Взаимная симпатия"
                else:
                    message = "Симпатия уже взаимная"
                # Удаляем прямую симпатию если она была создана (чтобы не было дубликатов)
                await Sympathy.objects.filter(from_player=player, to_player=recipient).adelete()
                data = SympathySerializer(reverse_sympathy).data
                return Response({"message": message, "sympathy": data}, status=status.HTTP_200_OK)
            except Sympathy.DoesNotExist:
                # Обратной симпатии нет - создаём/находим прямую запись player → recipient
                obj, created = await Sympathy.objects.aget_or_create(
                    from_player=player,
                    to_player=recipient,
                    defaults={"is_mutual": False}
                )
                # Загружаем связанные объекты для сериализатора
                obj = await Sympathy.objects.select_related("from_player", "to_player").aget(pk=obj.pk)
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
            # Вообще нет симпатии между парой - это нормально, пользователь просто пропустил профиль
            return Response({"deleted": False, "message": "Симпатия не найдена"}, status=status.HTTP_200_OK)
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
    """Избранное: GET показать список, DELETE удалить"""
    async def get(self, request):
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            # Получаем пользователя
            player = await Player.objects.aget(tg_id=init_data["id"])
            qs = (Favorite.objects.filter(owner=player).select_related("target", "target__man_profile", "target__woman_profile")
                  .prefetch_related("target__man_profile__photos", "target__woman_profile__photos").order_by("-created_at"))
            items = []
            async for fav in qs.aiterator():
                items.append({
                    "id": fav.id,
                    "created_at": fav.created_at,
                    "target": PlayerFovariteSerializer(fav.target).data,
                })
            return Response({"results": items, "count": len(items)}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    async def post(self, request):
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

            # Проверяем не добавлен ли уже в избранное
            if await Favorite.objects.filter(owner=player, target=target).aexists():
                return Response({"error": "Уже в избранном"}, status=status.HTTP_400_BAD_REQUEST)

            # Создаем запись в избранном
            favorite = await Favorite.objects.acreate(owner=player, target=target)

            return Response({
                "id": favorite.id,
                "created_at": favorite.created_at,
                "target": PlayerFovariteSerializer(favorite.target).data
            }, status=status.HTTP_201_CREATED)

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
    Возвращает профиль (м/ж) + фото (без лайков/дизлайков на фото).
    """
    async def get(self, request):
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            # Получаем пользователя
            current_player = await Player.objects.aget(tg_id=init_data["id"])
        except Player.DoesNotExist:
            return Response({"error": "Игрок не найден"}, status=status.HTTP_404_NOT_FOUND)
        # Получаем пользователя для просмотра профиля
        tg_id = request.query_params.get("tg_id")
        if not tg_id:
            return Response({"error": "Укажите tg_id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target = await Player.objects.aget(tg_id=tg_id)
        except Player.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        if not target.gender:
            return Response({"error": "У пользователя не указан пол"}, status=status.HTTP_400_BAD_REQUEST)
        if target.gender == "Man":
            try:
                # профиль мужчины + подтянутые фото (без реакций)
                profile = await (ProfileMan.objects.select_related("player")
                                 .prefetch_related("photos")).aget(player=target)
            except ProfileMan.DoesNotExist:
                return Response({"error": "Анкета не найдена"}, status=status.HTTP_404_NOT_FOUND)
            serializer = FullProfileManSerializer(profile, context={"request": request})
        else:
            try:
                # профиль женщины + подтянутые фото (без реакций)
                profile = await (ProfileWoman.objects.select_related("player")
                                 .prefetch_related("photos")).aget(player=target)
            except ProfileWoman.DoesNotExist:
                return Response({"error": "Анкета не найдена"}, status=status.HTTP_404_NOT_FOUND)
            serializer = FullProfileWomanSerializer(profile, context={"request": request})

        # Флаги
        is_favorite = await Favorite.objects.filter(owner=current_player, target=target).aexists()
        is_liked = is_favorite  # лайк = добавление в избранное
        is_disliked = await UserReactionDislike.objects.filter(from_player=current_player, to_player=target).aexists()

        response_data = serializer.data
        response_data.update({
            "is_favorite": is_favorite,
            "is_liked": is_liked,
            "is_disliked": is_disliked,
        })

        return Response(response_data, status=status.HTTP_200_OK)


@extend_schema_view(get=event_get_schema, post=event_post_schema, patch=event_patch_schema, delete=event_delete_schema)
class EventPlayerView(APIView):
    """CRUD для ивентов - все методы в одной вьюхе"""
    async def get(self, request, event_id=None):
        """Получить все ивенты или один конкретный"""
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            # Получаем пользователя
            player = await Player.objects.aget(tg_id=init_data["id"])
        except Player.DoesNotExist:
            return Response({"error": "Игрок не найден"}, status=status.HTTP_404_NOT_FOUND)
        try:
            if event_id:
                # Получить один ивент
                event = await Event.objects.select_related("profile").aget(id=event_id, profile=player, is_active=True)
                serializer = EventSerializer(event)
                return Response(serializer.data)
            else:
                # Получить все активные ивенты пользователя
                events = Event.objects.select_related("profile").filter(profile=player, is_active=True)
                event_list = [event async for event in events.aiterator()]
                serializer = EventSerializer(event_list, many=True)
                return Response(serializer.data)
        except Event.DoesNotExist:
            return Response({"error": "Ивент не найден"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def post(self, request):
        """Создать новый ивент"""
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            player = await Player.objects.aget(tg_id=init_data["id"])
            serializer = EventSerializer(data=request.data)
            if serializer.is_valid():
                # Сохраняем с создателем
                event = await Event.objects.acreate(profile=player, **serializer.validated_data)
                return Response(EventSerializer(event).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def patch(self, request, event_id):
        """Обновить ивент (частично)"""
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            player = await Player.objects.aget(tg_id=init_data["id"])
            event = await Event.objects.aget(id=event_id, profile=player)
            serializer = EventSerializer(event, data=request.data, partial=True)
            if serializer.is_valid():
                # обновляем объект руками через ORM
                await Event.objects.select_related("profile").filter(id=event_id, profile=player).aupdate(**serializer.validated_data)
                event = await Event.objects.select_related("profile").aget(id=event_id)
                return Response(EventSerializer(event).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Event.DoesNotExist:
            return Response({"error": "Ивент не найден или нет прав"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def delete(self, request, event_id):
        """Удалить ивент"""
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        try:
            player = await Player.objects.aget(tg_id=init_data["id"])
            event = await Event.objects.aget(id=event_id, profile=player)
            await event.adelete()
            return Response({"message": "Ивент удален"})
        except Event.DoesNotExist:
            return Response({"error": "Ивент не найден или нет прав"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema_view(get=opposite_gender_events_get_schema)
class OppositeGenderEventsView(APIView):
    """Получить ивенты противоположного пола с фильтрами по возрасту, городу и верификации"""

    async def get(self, request, event_id=None):
        init_data = availability_init_data(request)
        if not init_data:
            return Response({"error": "Не авторизован"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            # Получаем текущего пользователя
            current_player = await Player.objects.aget(tg_id=init_data["id"])

            # Если передан event_id - возвращаем один конкретный ивент
            if event_id:
                try:
                    # Предзагружаем профиль и связанные данные
                    event = await Event.objects.select_related(
                        "profile",
                        "profile__woman_profile",
                        "profile__man_profile"
                    ).prefetch_related(
                        "profile__woman_profile__photos",
                        "profile__man_profile__photos"
                    ).aget(
                        id=event_id,
                        is_active=True,
                        profile__gender="Woman" if current_player.gender == "Man" else "Man"
                    )

                    # Создаем данные для ответа
                    serializer = EventSerializer(event)
                    response_data = serializer.data

                    # Добавляем профиль создателя
                    profile = event.profile
                    if profile.gender == "Woman" and hasattr(profile, 'woman_profile'):
                        creator_data = FullProfileWomanSerializer(profile.woman_profile).data
                    elif profile.gender == "Man" and hasattr(profile, 'man_profile'):
                        creator_data = FullProfileManSerializer(profile.man_profile).data
                    else:
                        creator_data = None

                    response_data['creator_profile'] = creator_data
                    return Response(response_data)

                except Event.DoesNotExist:
                    return Response({"error": "Ивент не найден"}, status=status.HTTP_404_NOT_FOUND)

            # Определяем противоположный пол
            opposite_gender = "Woman" if current_player.gender == "Man" else "Man"

            # Базовый запрос с предзагрузкой всех данных
            events_query = (Event.objects.select_related(
                "profile",
                "profile__woman_profile",
                "profile__man_profile"
            ).prefetch_related(
                "profile__woman_profile__photos",
                "profile__man_profile__photos"
            ).filter(
                is_active=True,
                profile__gender=opposite_gender
            ).exclude(profile=current_player))

            # Фильтр по городу (если передан)
            city = request.GET.get('city')
            if city and city.strip():
                events_query = events_query.filter(city__iexact=city.strip())

            # Фильтр по минимальному возрасту (по умолчанию 18)
            min_age_filter = request.GET.get('min_age', '18')
            try:
                min_age = int(min_age_filter)
                events_query = events_query.filter(min_age__gte=min_age)
            except ValueError:
                events_query = events_query.filter(min_age__gte=18)

            # Фильтр по максимальному возрасту (по умолчанию 99)
            max_age_filter = request.GET.get('max_age', '99')
            try:
                max_age = int(max_age_filter)
                events_query = events_query.filter(max_age__lte=max_age)
            except ValueError:
                events_query = events_query.filter(max_age__lte=99)

            # Фильтр по верификации - только если явно запрошены верифицированные
            verification_filter = request.GET.get('verification')
            if verification_filter and verification_filter.lower() in ['true', '1', 'yes']:
                events_query = events_query.filter(profile__verification=True)

            # Пагинация
            page = int(request.GET.get('page', 1))
            page_size = 10
            if page < 1:
                page = 1

            # Считаем общее количество
            total_count = await events_query.acount()
            total_pages = max(1, math.ceil(total_count / page_size)) if total_count > 0 else 0

            if total_count == 0:
                return Response({
                    "results": [],
                    "page": 1,
                    "page_size": page_size,
                    "total_count": 0,
                    "total_pages": 0,
                    "has_prev": False,
                    "has_next": False,
                    "prev_page": None,
                    "next_page": None
                }, status=status.HTTP_200_OK)

            if page > total_pages:
                page = total_pages

            # Сортировка по дате создания (сначала новые) и пагинация
            events_query = events_query.order_by('-created_at')
            start = (page - 1) * page_size
            end = start + page_size

            # Получаем список ивентов для текущей страницы
            events_list = []
            async for event in events_query[start:end].aiterator():
                events_list.append(event)

            # Сериализуем данные
            events_data = []
            for event in events_list:
                event_serializer = EventSerializer(event)
                event_data = event_serializer.data

                # Добавляем профиль создателя
                profile = event.profile
                if profile.gender == "Woman" and hasattr(profile, 'woman_profile'):
                    creator_data = FullProfileWomanSerializer(profile.woman_profile).data
                elif profile.gender == "Man" and hasattr(profile, 'man_profile'):
                    creator_data = FullProfileManSerializer(profile.man_profile).data
                else:
                    creator_data = None

                event_data['creator_profile'] = creator_data
                events_data.append(event_data)

            return Response({
                "results": events_data,
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
                "prev_page": page - 1 if page > 1 else None,
                "next_page": page + 1 if page < total_pages else None
            }, status=status.HTTP_200_OK)

        except Player.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@reaction_to_the_questionnaire
class UserLikeView(APIView):
    """Ручка для лайков/дизлайков пользователей"""
    async def post(self, request):
        init_data = availability_init_data(request)
        try:
            from_player = await Player.objects.aget(tg_id=init_data["id"])
            to_player_tg_id = request.data.get("to_player_tg_id")
            reaction_type = request.data.get("reaction_type")

            # ВАЛИДАЦИЯ
            if not reaction_type or reaction_type not in ['like', 'dislike']:
                return Response({
                    "error": "reaction_type обязателен и должен быть 'like' или 'dislike'"
                }, status=status.HTTP_400_BAD_REQUEST)

            if not to_player_tg_id:
                return Response({"error": "tg_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                to_player = await Player.objects.aget(tg_id=to_player_tg_id)
            except Player.DoesNotExist:
                return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

            if from_player.tg_id == to_player.tg_id:
                return Response({"error": "Нельзя реагировать на себя"}, status=status.HTTP_400_BAD_REQUEST)

            # ПРОВЕРЯЕМ ТЕКУЩУЮ РЕАКЦИЮ
            existing_favorite = await Favorite.objects.filter(
                owner=from_player,
                target=to_player
            ).aexists()

            existing_dislike = await UserReactionDislike.objects.filter(
                from_player=from_player,
                to_player=to_player
            ).aexists()

            # ЛОГИКА TOGGLE: ЕСЛИ УЖЕ ЕСТЬ РЕАКЦИЯ - УБИРАЕМ ЕЁ
            if reaction_type == 'like':
                if existing_favorite:
                    # УБИРАЕМ ЛАЙК
                    await Favorite.objects.filter(owner=from_player, target=to_player).adelete()
                    to_player.likes_count -= 1
                    message = "Лайк убран"
                    removed = True
                else:
                    # СТАВИМ ЛАЙК (предварительно убирая дизлайк если был)
                    if existing_dislike:
                        await UserReactionDislike.objects.filter(
                            from_player=from_player,
                            to_player=to_player
                        ).adelete()
                        to_player.dislikes_count -= 1

                    await Favorite.objects.aupdate_or_create(
                        owner=from_player,
                        target=to_player,
                        defaults={}
                    )
                    to_player.likes_count += 1
                    message = "Лайк поставлен"
                    removed = False

            else:  # dislike
                if existing_dislike:
                    # УБИРАЕМ ДИЗЛАЙК
                    await UserReactionDislike.objects.filter(
                        from_player=from_player,
                        to_player=to_player
                    ).adelete()
                    to_player.dislikes_count -= 1
                    message = "Дизлайк убран"
                    removed = True
                else:
                    # СТАВИМ ДИЗЛАЙК (предварительно убирая лайк если был)
                    if existing_favorite:
                        await Favorite.objects.filter(
                            owner=from_player,
                            target=to_player
                        ).adelete()
                        to_player.likes_count -= 1

                    dislike = UserReactionDislike(
                        from_player=from_player,
                        to_player=to_player
                    )
                    await dislike.asave()
                    to_player.dislikes_count += 1
                    message = "Дизлайк поставлен"
                    removed = False

            await to_player.asave(update_fields=['likes_count', 'dislikes_count'])

            return Response({
                "message": message,
                "removed": removed,
                "stats": {
                    "likes_count": to_player.likes_count,
                    "dislikes_count": to_player.dislikes_count,
                    "like_ratio": to_player.like_ratio
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@yookassa
class CreatePaymentView(APIView):
    """Оплата платной подписки"""
    async def post(self, request):
        # Проверяем авторизацию через Telegram
        init_data = availability_init_data(request)
        tg_id = init_data.get("id")  # Извлекаем id игрока
        data = request.data
        product_id = data.get("product_id")  # Извлекаем id продукта из запроса
        return_url = data.get("return_url", "https://rndvu.rozari.info/")  # Извлекаем url для редиректа после оплаты
        # Получаем продукт и игрока
        try:
            player = await Player.objects.aget(tg_id=tg_id)
            product = await Product.objects.aget(id=product_id)
            # Создаём платеж в Юкассе
            payment_data = await create_yookassa_payment(
                amount=product.price,  # Стоимость продукта для оплаты
                return_url=return_url, # Куда вернется пользователь после оплаты
                description=f"Оплата {product.name}",  # Описание платежа
                metadata={"tg_id": tg_id, "product_id": product.id})  # Дополнительные данные для webhook
            # Создаем запись в БД с настоящим payment_id
            await Purchase.objects.acreate(player=player, product=product, payment_id=payment_data["id"], is_successful=False)
            # Возвращаем клиенту ссылку на оплату и id платежа
            return Response({
                "payment_url": payment_data["confirmation"]["confirmation_url"],
                "payment_id": payment_data["id"],})
        except Player.DoesNotExist:
            return Response({"error": "Player not found"}, status=404)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)


@update_verification
class UpdateVerificationView(GenericAPIView):
    """Обновление флага для варификация пользователя"""
    serializer_class = UpdateVerificationSerializer
    async def patch(self, request):
        init_data = availability_init_data(request)
        try:
            player = await Player.objects.aget(tg_id=init_data["id"])
            player.verification = True  # Устанавливаем флаг в True
            await player.asave()  # Сохраняем изменения
            return Response({"verification": True})
        except Player.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=404)


@product_list
class ProductListView(APIView):
    """Получаем все платные продукты"""
    async def get(self, request):
        init_data = availability_init_data(request)
        if not init_data:
            return Response({"error": "telegram_user not found"}, status=400)
        products = [product async for product in Product.objects.all().order_by('id')]
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
