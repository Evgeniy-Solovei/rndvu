from adrf.fields import SerializerMethodField
from adrf.serializers import ModelSerializer, Serializer
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from core_rndvu.models import *

# Импортируем LANGUAGE_CHOICES из models
from core_rndvu.models import LANGUAGE_CHOICES


class PlayerSerializer(ModelSerializer):
    """Сериализатор модели Player"""
    gender_choices = SerializerMethodField()
    like_ratio = serializers.FloatField(read_only=True)
    main_photo = SerializerMethodField()

    class Meta:
        model = Player
        fields = "__all__"
        read_only_fields = ['like_ratio', 'main_photo']

    @extend_schema_field(list[OpenApiTypes.OBJECT])
    def get_gender_choices(self, obj):
        return [
            {"value": value, "label": label}
            for value, label in Player._meta.get_field("gender").choices
        ]

    def _extract_main_photo(self, photos_queryset):
        photos_list = list(photos_queryset)
        main = next((p for p in photos_list if p.main_photo), None) or (photos_list[0] if photos_list else None)
        return main

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_main_photo(self, obj):
        if obj.gender == "Woman" and hasattr(obj, "woman_profile"):
            main = self._extract_main_photo(obj.woman_profile.photos.all())
            return WomanPhotoSerializer(main).data if main else None
        if obj.gender == "Man" and hasattr(obj, "man_profile"):
            main = self._extract_main_photo(obj.man_profile.photos.all())
            return ManPhotoSerializer(main).data if main else None
        return None


class PlayerFovariteSerializer(ModelSerializer):
    """Сериализатор модели Player"""
    gender_choices = SerializerMethodField()
    like_ratio = serializers.FloatField(read_only=True)
    photos = SerializerMethodField()
    birth_date = SerializerMethodField()

    class Meta:
        model = Player
        fields = "__all__"
        read_only_fields = ['like_ratio', 'photos', 'birth_date']

    @extend_schema_field(list[OpenApiTypes.OBJECT])
    def get_gender_choices(self, obj):
        return [
            {"value": value, "label": label}
            for value, label in Player._meta.get_field("gender").choices
        ]

    @extend_schema_field(list[OpenApiTypes.OBJECT])
    def get_photos(self, obj):
        # Если женщина — берём WomanPhotoSerializer
        if obj.gender == "Woman" and hasattr(obj, "woman_profile"):
            return WomanPhotoSerializer(obj.woman_profile.photos.all(), many=True).data
        # Если мужчина — берём ManPhotoSerializer
        if obj.gender == "Man" and hasattr(obj, "man_profile"):
            return ManPhotoSerializer(obj.man_profile.photos.all(), many=True).data
        return []

    @extend_schema_field(OpenApiTypes.STR)
    def get_birth_date(self, obj):
        # Проверяем, нужно ли скрывать возраст
        if hasattr(obj, 'hide_age_in_profile') and obj.hide_age_in_profile:
            return None
        # Если женщина — берём birth_date из woman_profile
        if obj.gender == "Woman" and hasattr(obj, "woman_profile"):
            return obj.woman_profile.birth_date
        # Если мужчина — берём birth_date из man_profile
        if obj.gender == "Man" and hasattr(obj, "man_profile"):
            return obj.man_profile.birth_date
        return None



class ProfileManSerializer(ModelSerializer):
    """Сериализатор мужской анкеты"""
    class Meta:
        model = ProfileMan
        fields = '__all__'


# def calc_like_ratio(likes_count: int, dislikes_count: int) -> float:
#     """
#     Рассчитывает процент пользователей, которым понравилось фото.
#     :param likes_count: количество лайков
#     :param dislikes_count: количество дизлайков
#     :return: число от 0 до 100 (% лайков от всех реакций)
#     """
#     total = likes_count + dislikes_count
#     if total == 0:
#         return 0.0
#     return round((likes_count / total) * 100, 2)


class ManPhotoSerializer(ModelSerializer):
    """Сериализатор фото мужского профиля"""
    # user_reaction = SerializerMethodField()
    # likes_count = SerializerMethodField()
    # dislikes_count = SerializerMethodField()
    # like_ratio = SerializerMethodField()

    class Meta:
        model = ManPhoto
        fields = ["id", "image", "uploaded_at", "main_photo"]

    # def get_user_reaction(self, obj):
    #     # Берём из префетча: Prefetch(..., to_attr="user_reactions")
    #     ur = getattr(obj, "user_reactions", None)
    #     return ur[0].reaction_type if ur else None
    #
    # def get_likes_count(self, obj):
    #     # Берём из аннотации queryset-а (см. Prefetch ниже)
    #     return getattr(obj, "likes_count", 0)
    #
    # def get_dislikes_count(self, obj):
    #     return getattr(obj, "dislikes_count", 0)
    #
    # def get_like_ratio(self, obj):
    #     return calc_like_ratio(getattr(obj, "likes_count", 0), getattr(obj, "dislikes_count", 0))


class FullProfileManSerializer(ModelSerializer):
    """Полный сериализатор мужской анкеты с фото"""
    # Связываем с сериализатором фото (many=True означает, что фото может быть несколько)
    photos = ManPhotoSerializer(many=True, read_only=True)
    # Связываем с сериализатором пользователя (read_only=True означает, что поле нельзя изменять)
    player = PlayerSerializer(read_only=True)
    
    class Meta:
        model = ProfileMan
        fields = '__all__'  # Включаем все поля модели
        extra_kwargs = {'player': {'read_only': True}}  # Поле player только для чтения


class ProfileWomanSerializer(ModelSerializer):
    """Сериализатор женской анкеты + чойчасы для языков"""
    language_choices = SerializerMethodField()

    class Meta:
        model = ProfileWoman
        fields = '__all__'
        extra_kwargs = {'player': {'read_only': True}}

    def get_language_choices(self, obj):
        return LANGUAGE_CHOICES


class WomanPhotoSerializer(ModelSerializer):
    """Сериализатор фото женского профиля"""
    # user_reaction = SerializerMethodField()
    # likes_count = SerializerMethodField()
    # dislikes_count = SerializerMethodField()
    # like_ratio = SerializerMethodField()

    class Meta:
        model = WomanPhoto
        fields = ["id", "image", "uploaded_at", "main_photo"]

    # def get_user_reaction(self, obj):
    #     ur = getattr(obj, "user_reactions", None)
    #     return ur[0].reaction_type if ur else None
    #
    # def get_likes_count(self, obj):
    #     return getattr(obj, "likes_count", 0)
    #
    # def get_dislikes_count(self, obj):
    #     return getattr(obj, "dislikes_count", 0)
    #
    # def get_like_ratio(self, obj):
    #     return calc_like_ratio(getattr(obj, "likes_count", 0), getattr(obj, "dislikes_count", 0))


class FullProfileWomanSerializer(ModelSerializer):
    """Полный сериализатор женской анкеты с фото"""
    # Связываем с сериализатором фото
    photos = WomanPhotoSerializer(many=True, read_only=True)
    # Связываем с сериализатором пользователя
    player = PlayerSerializer(read_only=True)
    # Добавляем поле с доступными языками
    language_choices = SerializerMethodField()
    
    class Meta:
        model = ProfileWoman
        fields = '__all__'  # Включаем все поля модели
        extra_kwargs = {'player': {'read_only': True}}  # Поле player только для чтения

    def get_language_choices(self, obj):
        """Возвращает список доступных языков для выбора"""
        return LANGUAGE_CHOICES


class ProfileUpdateSerializer(ModelSerializer):
    """Сериализатор для обновления анкеты (PATCH/PUT)"""
    class Meta:
        model = ProfileMan  # По умолчанию мужская анкета, но будет переопределено
        fields = '__all__'  # Включаем все поля модели
        extra_kwargs = {
            'player': {'read_only': True},  # Поле player нельзя изменять
            'id': {'read_only': True}       # Поле id нельзя изменять
        }
    
    def __init__(self, *args, **kwargs):
        # Получаем модель из контекста (передается из view)
        model = kwargs.get('context', {}).get('model')
        if model:
            # Устанавливаем модель для правильной валидации полей
            self.Meta.model = model
        super().__init__(*args, **kwargs)


# class PhotoReactionSerializer(ModelSerializer):
#     """Сериализатор для реакций на фото"""
#     class Meta:
#         model = PhotoReaction
#         fields = ['id', 'player', 'man_photo', 'woman_photo', 'reaction_type', 'created_at']
#         read_only_fields = ['id', 'created_at']


class SympathySerializer(ModelSerializer):
    """Сериализатор симпатий с вложенными пользователями"""
    from_player = PlayerSerializer(read_only=True)
    to_player = PlayerSerializer(read_only=True)

    class Meta:
        model = Sympathy
        fields = ["id", "from_player", "to_player", "is_mutual", "created_at"]
        read_only_fields = ["id", "is_mutual", "created_at", "from_player", "to_player"]


def calculate_age(birth_date):
    if not birth_date:
        return None
    from datetime import date
    today = date.today()
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


class GameUserSerializer(ModelSerializer):
    """Короткая карточка пользователя для игры"""
    age = SerializerMethodField()
    photos = SerializerMethodField()

    class Meta:
        model = Player
        fields = ["id", "tg_id", "first_name", "username", "gender", "city", "is_active", "age", "photos", "hide_age_in_profile"]

    def get_age(self, obj):
        # Проверяем, нужно ли скрывать возраст
        if hasattr(obj, 'hide_age_in_profile') and obj.hide_age_in_profile:
            return None
        # birth_date может быть добавлен в queryset через annotate/select_related
        birth_date = getattr(obj, "birth_date", None)
        return calculate_age(birth_date) if birth_date else None

    def get_photos(self, obj):
        # Если женщина — берём WomanPhotoSerializer, только главное фото
        # После prefetch_related photos уже загружены в память, используем all() для получения списка
        if obj.gender == "Woman" and hasattr(obj, "woman_profile"):
            photos_list = list(obj.woman_profile.photos.all())
            # Ищем главное фото в уже загруженном списке
            main_photo = next((p for p in photos_list if p.main_photo), None)
            if main_photo:
                return [WomanPhotoSerializer(main_photo).data]
            # Если главного фото нет, возвращаем первое фото (для обратной совместимости)
            if photos_list:
                return [WomanPhotoSerializer(photos_list[0]).data]
            return []
        # Если мужчина — берём ManPhotoSerializer, только главное фото
        if obj.gender == "Man" and hasattr(obj, "man_profile"):
            photos_list = list(obj.man_profile.photos.all())
            # Ищем главное фото в уже загруженном списке
            main_photo = next((p for p in photos_list if p.main_photo), None)
            if main_photo:
                return [ManPhotoSerializer(main_photo).data]
            # Если главного фото нет, возвращаем первое фото (для обратной совместимости)
            if photos_list:
                return [ManPhotoSerializer(photos_list[0]).data]
            return []
        return []


class FavoriteSerializer(ModelSerializer):
    """Сериализатор для модели Favorite"""
    target = PlayerSerializer(read_only=True)  # отдаём всю инфу о target
    owner = SerializerMethodField()            # кастомно выводим tg_id

    class Meta:
        model = Favorite
        fields = ["id", "owner", "target", "created_at"]
        read_only_fields = ["id", "owner", "created_at", "target"]

    def get_owner(self, obj):
        return obj.owner.tg_id


class MainPhotoResponseSerializer(Serializer):
    message = serializers.CharField()
    main_photo_id = serializers.IntegerField()


class GameUsersResponseSerializer(serializers.Serializer):
    results = GameUserSerializer(many=True)
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    total_count = serializers.IntegerField(required=False)
    has_prev = serializers.BooleanField(required=False)
    has_next = serializers.BooleanField(required=False)
    prev_page = serializers.IntegerField(required=False, allow_null=True)
    next_page = serializers.IntegerField(required=False, allow_null=True)


class SympathyResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    sympathy = SympathySerializer()


class MutualSympathyResponseSerializer(serializers.Serializer):
    mutual = SympathySerializer(many=True)


class DeleteSympathyResponseSerializer(serializers.Serializer):
    deleted = serializers.BooleanField()
    message = serializers.CharField(required=False, allow_null=True)


class FavoriteResponseSerializer(serializers.Serializer):
    created = serializers.BooleanField()
    favorite = FavoriteSerializer()


class FavoriteItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    target = PlayerSerializer()


class FavoriteListResponseSerializer(serializers.Serializer):
    results = FavoriteItemSerializer(many=True)
    count = serializers.IntegerField()


class DeleteFavoriteResponseSerializer(serializers.Serializer):
    deleted = serializers.BooleanField()


class UserLikeRequestSerializer(serializers.Serializer):
    """Схема запроса для UserLikeView"""
    to_player_tg_id = serializers.CharField(help_text="Telegram ID игрока, которому ставим реакцию")
    reaction_type = serializers.ChoiceField(
        choices=["like", "dislike"],
        help_text="Тип реакции: 'like' или 'dislike'"
    )


class UserLikeResponseStatsSerializer(serializers.Serializer):
    """Вложенная схема статистики"""
    likes_count = serializers.IntegerField()
    dislikes_count = serializers.IntegerField()
    like_ratio = serializers.FloatField()


class UserLikeResponseSerializer(serializers.Serializer):
    """Схема ответа для UserLikeView"""
    message = serializers.CharField()
    removed = serializers.BooleanField()
    stats = UserLikeResponseStatsSerializer()


class CreatePaymentRequestSerializer(serializers.Serializer):
    """Схема запроса для CreatePaymentView"""
    product_id = serializers.IntegerField(
        help_text="ID продукта для оплаты"
    )
    return_url = serializers.URLField(
        required=False,
        help_text="URL, на который пользователь вернётся после оплаты"
    )
    init_data = serializers.JSONField(
        help_text="Данные инициализации Telegram WebApp (telegram_user)"
    )


class CreatePaymentResponseSerializer(serializers.Serializer):
    """Схема ответа для CreatePaymentView"""
    payment_url = serializers.URLField(
        help_text="Ссылка на оплату YooKassa"
    )
    payment_id = serializers.CharField(
        help_text="ID платежа в YooKassa"
    )


class ErrorResponseSerializer(serializers.Serializer):
    """Схема ошибки"""
    error = serializers.CharField(help_text="Описание ошибки")


class EventSerializer(ModelSerializer):
    """Сериализатор для модели Event"""
    profile_tg_id = serializers.CharField(source="profile.tg_id", read_only=True)
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['id', 'profile', 'profile_tg_id', 'creator', 'created_at', 'updated_at', 'is_active']

    def get_fields(self):
        fields = super().get_fields()
        fields.pop('profile', None)  # выпиливаем profile
        return fields


class UpdateVerificationSerializer(ModelSerializer):
    """Сериализатор модели Player, для изменение поле варифицированной анкеты"""
    class Meta:
        model = Player
        fields = ['verification']


class UpdateShowInGameSerializer(ModelSerializer):
    """Сериализатор модели Player, для изменения поля показа в игре"""
    class Meta:
        model = Player
        fields = ['show_in_game']


class ProductSerializer(ModelSerializer):
    """Сериализатор модели Product, для предоставления информации о продуктах премиум подписки"""
    class Meta:
        model = Product
        fields = "__all__"
