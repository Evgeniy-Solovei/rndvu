from adrf.fields import SerializerMethodField
from adrf.serializers import ModelSerializer
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from core_rndvu.models import *

# Импортируем LANGUAGE_CHOICES из models
from core_rndvu.models import LANGUAGE_CHOICES


class PlayerSerializer(ModelSerializer):
    """Сериализатор модели Player"""
    gender_choices = SerializerMethodField()
    
    class Meta:
        model = Player
        fields = "__all__"

    @extend_schema_field(list[OpenApiTypes.OBJECT])
    def get_gender_choices(self, obj):
        return [
            {"value": value, "label": label}
            for value, label in Player._meta.get_field("gender").choices
        ]


class ProfileManSerializer(ModelSerializer):
    """Сериализатор мужской анкеты"""
    class Meta:
        model = ProfileMan
        fields = '__all__'


def calc_like_ratio(likes_count: int, dislikes_count: int) -> float:
    """
    Рассчитывает процент пользователей, которым понравилось фото.
    :param likes_count: количество лайков
    :param dislikes_count: количество дизлайков
    :return: число от 0 до 100 (% лайков от всех реакций)
    """
    total = likes_count + dislikes_count
    if total == 0:
        return 0.0
    return round((likes_count / total) * 100, 2)


class ManPhotoSerializer(ModelSerializer):
    """Сериализатор фото мужского профиля"""
    user_reaction = SerializerMethodField()
    likes_count = SerializerMethodField()
    dislikes_count = SerializerMethodField()
    like_ratio = SerializerMethodField()

    class Meta:
        model = ManPhoto
        fields = ["id", "image", "uploaded_at", "user_reaction", "likes_count", "dislikes_count", "like_ratio"]

    def get_user_reaction(self, obj):
        # Берём из префетча: Prefetch(..., to_attr="user_reactions")
        ur = getattr(obj, "user_reactions", None)
        return ur[0].reaction_type if ur else None

    def get_likes_count(self, obj):
        # Берём из аннотации queryset-а (см. Prefetch ниже)
        return getattr(obj, "likes_count", 0)

    def get_dislikes_count(self, obj):
        return getattr(obj, "dislikes_count", 0)

    def get_like_ratio(self, obj):
        return calc_like_ratio(getattr(obj, "likes_count", 0), getattr(obj, "dislikes_count", 0))


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
    user_reaction = SerializerMethodField()
    likes_count = SerializerMethodField()
    dislikes_count = SerializerMethodField()
    like_ratio = SerializerMethodField()

    class Meta:
        model = WomanPhoto
        fields = ["id", "image", "uploaded_at", "user_reaction", "likes_count", "dislikes_count", "like_ratio"]

    def get_user_reaction(self, obj):
        ur = getattr(obj, "user_reactions", None)
        return ur[0].reaction_type if ur else None

    def get_likes_count(self, obj):
        return getattr(obj, "likes_count", 0)

    def get_dislikes_count(self, obj):
        return getattr(obj, "dislikes_count", 0)

    def get_like_ratio(self, obj):
        return calc_like_ratio(getattr(obj, "likes_count", 0), getattr(obj, "dislikes_count", 0))


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


class PhotoReactionSerializer(ModelSerializer):
    """Сериализатор для реакций на фото"""
    class Meta:
        model = PhotoReaction
        fields = ['id', 'player', 'man_photo', 'woman_photo', 'reaction_type', 'created_at']
        read_only_fields = ['id', 'created_at']


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
        fields = ["id", "tg_id", "first_name", "username", "gender", "city", "is_active", "age", "photos"]

    def get_age(self, obj):
        # birth_date может быть добавлен в queryset через annotate/select_related
        birth_date = getattr(obj, "birth_date", None)
        return calculate_age(birth_date)

    def get_photos(self, obj):
        # Если женщина — берём WomanPhotoSerializer
        if obj.gender == "Woman" and hasattr(obj, "woman_profile"):
            return WomanPhotoSerializer(obj.woman_profile.photos.all(), many=True).data
        # Если мужчина — берём ManPhotoSerializer
        if obj.gender == "Man" and hasattr(obj, "man_profile"):
            return ManPhotoSerializer(obj.man_profile.photos.all(), many=True).data
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
