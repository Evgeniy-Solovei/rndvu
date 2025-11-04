from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, IntegerField, CharField, TextField, ForeignKey, CASCADE

from core_rndvu.validators import validate_birth_date, validate_photo_size


class Player(models.Model):
    """Модель игрока"""
    GENDER_CHOICES = [('Man', 'Мужчина'), ('Woman', 'Женщина')]
    tg_id = models.PositiveBigIntegerField(unique=True, verbose_name="Telegram ID")
    first_name = models.CharField(max_length=50, verbose_name="Имя игрока", blank=True, null=True)
    username = models.CharField(max_length=100, verbose_name="Nickname игрока", blank=True, null=True)
    language_code = models.CharField(max_length=30, verbose_name="Язык пользователя", default="ru")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name="Пол пользователя", blank=True, null=True)
    city = models.IntegerField(null=True, blank=True, verbose_name="ID города из GeoNames")
    alpha2 = models.IntegerField(null=True, blank=True, verbose_name="Код страны из GeoNames")
    registration_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации игрока")
    hide_age_in_profile = models.BooleanField(default=True, verbose_name="Показывать возраст да/нет")
    is_active = models.BooleanField(default=True, verbose_name="Активный профиль да/нет")
    likes_count = models.IntegerField(default=0, verbose_name="Количество лайков профиля")
    dislikes_count = models.IntegerField(default=0, verbose_name="Количество дизлайков профиля")
    paid_subscription = models.BooleanField(default=False, verbose_name="Платная подписка/нет")
    count_days_paid_subscription = models.PositiveBigIntegerField(blank=True, null=True,
                                                                  verbose_name="Остаток дней платной подписки")
    subscription_end_date = models.DateField(null=True, blank=True, verbose_name="Дата окончания подписки")
    verification = models.BooleanField(default=False, verbose_name="Подтверждение профиля")
    link_tg = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ссылка на Telegram")


    class Meta:
        indexes = [models.Index(fields=["tg_id"])]
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        if self.username:
            return f"{self.tg_id} ({self.first_name})"
        return str(self.tg_id)

    @property
    def like_ratio(self):
        """Процентное соотношение лайков"""
        total = self.likes_count + self.dislikes_count
        if total == 0:
            return 0
        return round((self.likes_count / total) * 100, 1)

    def save(self, *args, **kwargs):
        # Автоматически создаем ссылку при сохранении
        if self.tg_id:
            self.link_tg = f"https://t.me/{self.tg_id}"
        super().save(*args, **kwargs)


class UserReactionDislike(models.Model):
    """Модель для отслеживания дизлайков пользователей"""
    from_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='given_dislikes')
    to_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='received_dislikes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['from_player', 'to_player']  # один дизлайк на пару пользователей
        verbose_name = "Дизлайк пользователя"
        verbose_name_plural = "Дизлайки пользователей"

    def __str__(self):
        return f"{self.from_player.tg_id} -> {self.to_player.tg_id} (дизлайк)"


class ProfileMan(models.Model):
    """Модель профиля игрока мужчины"""
    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name="man_profile", verbose_name="Владелец анкеты")
    birth_date = models.DateField(verbose_name="Дата рождения", validators=[validate_birth_date], blank=True, null=True)
    about = models.TextField(verbose_name="О себе", max_length=2000, blank=True, null=True)

    class Meta:
        verbose_name = "Мужская анкета"
        verbose_name_plural = "Мужские анкеты"

    def __str__(self):
        if self.player.username:
            return f"{self.player.tg_id} ({self.player.first_name})"
        return str(self.player.tg_id)


class ManPhoto(models.Model):
    """Фото мужского профиля"""
    profile = models.ForeignKey(ProfileMan, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to='men_photos/', validators=[validate_photo_size], verbose_name="Фото", blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки фото")
    main_photo = models.BooleanField(default=False, verbose_name="Главное фото анкеты")


    class Meta:
        verbose_name = "Фото мужского профиля"
        verbose_name_plural = "Фото мужских профилей"


LANGUAGE_CHOICES = [
    ('RU', 'Русский'),
    ('EN', 'Английский'),
    ('FR', 'Французский'),
    ('DE', 'Немецкий'),
    ('ES', 'Испанский'),
    ('IT', 'Итальянский'),
    ('ZH', 'Китайский'),
    ('JA', 'Японский'),
    ('AR', 'Арабский'),
    ('PT', 'Португальский')
]

class ProfileWoman(models.Model):
    """Модель профиля игрока женщины"""
    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name="woman_profile", verbose_name="Владелец анкеты")
    birth_date = models.DateField(verbose_name="Дата рождения", validators=[validate_birth_date], blank=True, null=True)
    height = models.PositiveSmallIntegerField(verbose_name="Рост (см)", validators=[MaxValueValidator(250)], blank=True, null=True)
    weight = models.PositiveSmallIntegerField(verbose_name="Вес (кг)", validators=[MaxValueValidator(200)], blank=True, null=True)
    bust_size = models.PositiveSmallIntegerField(verbose_name="Обхват груди (см)", blank=True, null=True)
    waist_size = models.PositiveSmallIntegerField(verbose_name="Обхват талии (см)", blank=True, null=True)
    hips_size = models.PositiveSmallIntegerField(verbose_name="Обхват бедер (см)", blank=True, null=True)
    languages = ArrayField(base_field=models.CharField(max_length=2, choices=LANGUAGE_CHOICES), default=list,
                           verbose_name="Языки", blank=True, null=True)
    interests = models.CharField(max_length=255, verbose_name="Интересы", blank=True, null=True)
    about = models.TextField(verbose_name="О себе", max_length=2000, blank=True, null=True)

    class Meta:
        verbose_name = "Женская анкета"
        verbose_name_plural = "Женские анкеты"

    def __str__(self):
        if self.player.username:
            return f"{self.player.tg_id} ({self.player.first_name})"
        return str(self.player.tg_id)



class WomanPhoto(models.Model):
    """Фото женского профиля"""
    profile = models.ForeignKey(ProfileWoman, on_delete=models.CASCADE, related_name="photos", verbose_name="Пользователь")
    image = models.ImageField(upload_to='women_photos/', validators=[validate_photo_size], verbose_name="Фото")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки фото")
    main_photo = models.BooleanField(default=False, verbose_name="Главное фото анкеты")

    class Meta:
        verbose_name = "Фото женского профиля"
        verbose_name_plural = "Фото женских профилей"


# class PhotoReaction(models.Model):
#     """Реакция пользователя на фото (лайк/дизлайк)"""
#     REACTION_CHOICES = [
#         ('like', 'Лайк'),
#         ('dislike', 'Дизлайк'),
#     ]
#     player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='photo_reactions', verbose_name="Пользователь поставивший реакцию")
#     # На какое фото поставлена реакция (одно из двух полей должно быть заполнено)
#     man_photo = models.ForeignKey(ManPhoto, on_delete=models.CASCADE, related_name='reactions', verbose_name="Мужское фото", null=True, blank=True)
#     woman_photo = models.ForeignKey(WomanPhoto, on_delete=models.CASCADE, related_name='reactions', verbose_name="Женское фото", null=True, blank=True)
#     reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES, verbose_name="Тип реакции")
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания реакции")
#
#     class Meta:
#         verbose_name = "Реакция на фото"
#         verbose_name_plural = "Реакции на фото"
#         # Один пользователь может поставить только одну реакцию на одно фото
#         constraints = [
#             models.UniqueConstraint(
#                 fields=['player', 'man_photo'],
#                 condition=Q(man_photo__isnull=False),
#                 name='unique_player_man_photo_reaction'
#             ),
#             models.UniqueConstraint(
#                 fields=['player', 'woman_photo'],
#                 condition=Q(woman_photo__isnull=False),
#                 name='unique_player_woman_photo_reaction'
#             ),
#         ]
#         indexes = [
#             models.Index(fields=['player', 'reaction_type']),
#             models.Index(fields=['man_photo', 'reaction_type']),
#             models.Index(fields=['woman_photo', 'reaction_type']),
#         ]
#
#     def __str__(self):
#         photo_id = self.man_photo.id if self.man_photo else self.woman_photo.id
#         return f"{self.player.tg_id} - {self.reaction_type} на фото {photo_id}"


# Избранное — направленное отношение между пользователями
class Favorite(models.Model):
    owner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="favorites", verbose_name="Кто добавил в избранное")
    target = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="favorited_by", verbose_name="Кого добавили в избранное")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранные"
        constraints = [
            models.UniqueConstraint(fields=["owner", "target"], name="unique_favorite_owner_target"),
            models.CheckConstraint(check=~models.Q(owner=models.F("target")), name="favorite_owner_not_target"),
        ]
        indexes = [
            models.Index(fields=["owner", "created_at"]),
            models.Index(fields=["target", "created_at"]),
        ]

    def __str__(self):
        return f"{self.owner.tg_id} ➜ {self.target.tg_id} (favorite)"


# Симпатия — направленное отношение. При взаимности формируется match
class Sympathy(models.Model):
    from_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="sympathies_out", verbose_name="От кого")
    to_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="sympathies_in", verbose_name="Кому")
    is_mutual = models.BooleanField(default=False, verbose_name="Взаимная симпатия")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Симпатия"
        verbose_name_plural = "Симпатии"
        constraints = [
            models.UniqueConstraint(fields=["from_player", "to_player"], name="unique_sympathy_from_to"),
            models.CheckConstraint(check=~models.Q(from_player=models.F("to_player")), name="sympathy_from_not_to"),
        ]
        indexes = [
            models.Index(fields=["from_player", "created_at"]),
            models.Index(fields=["to_player", "created_at"]),
            models.Index(fields=["is_mutual"]),
        ]

    def __str__(self):
        arrow = "⇆" if self.is_mutual else "→"
        return f"{self.from_player.tg_id} {arrow} {self.to_player.tg_id}"


class PassedUser(models.Model):
    """Пропущенные пользователи - когда пользователь нажал "не понравился" (skip)"""
    from_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="passed_users", verbose_name="Кто пропустил")
    to_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="passed_by_users", verbose_name="Кого пропустили")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата пропуска")

    class Meta:
        verbose_name = "Пропущенный пользователь"
        verbose_name_plural = "Пропущенные пользователи"
        constraints = [
            models.UniqueConstraint(fields=["from_player", "to_player"], name="unique_passed_from_to"),
            models.CheckConstraint(check=~models.Q(from_player=models.F("to_player")), name="passed_from_not_to"),
        ]
        indexes = [models.Index(fields=["from_player", "created_at"]), models.Index(fields=["to_player"])]

    def __str__(self):
        return f"{self.from_player.tg_id} пропустил {self.to_player.tg_id}"


class Event(models.Model):
    """Ивент для пользователей"""
    DURATION_CHOICES = [
        (0, 'Время обсудим в диалоге'),
        (1, '1 час'),
        (2, '2 часа'),
        (3, '3 часа'),
        (4, '4 часа'),
        (5, '5+ часов'),
        (24, '24 часа'),
    ]

    PLACE_CHOICES = [
        ('restaurant', 'Ресторан'),
        ('cafe', 'Кофейня'),
        ('hotel', 'Отель'),
        ('apartments', 'Апартаменты'),
        ('restaurant_and_apartments', 'Ресторан и апартаменты'),
        ('yacht', 'Яхта'),
        ('villa', 'Вилла'),
        ('bath_complex', 'Банный комплекс'),
        ('private_house', 'Частный дом'),
        ('country_complex', 'Загородный комплекс'),
        ('private_sector', 'Частный сектор'),
        ('club', 'Клуб'),
        ('club_and_hotel', 'Клуб и отель'),
        ('travel_together', 'Совместная поездка'),
        ('any_place_you_wish', 'Любое место по вашему желанию'),
        ('bachelor_party', 'Мальчишник'),
        ('bachelorette_party', 'Девичник'),
        ('to_pair_with_us', 'К нам в пару'),
        ('has_not_been_selected_yet', 'Место пока не выбрано'),
    ]

    CURRENCY_CHOICES = [
        ('USD', 'usd'),
        ('USDT', 'usdt'),
        ('EU', 'eu'),
        ('RU', 'ru'),
    ]

    profile = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='created_events', verbose_name="Создатель ивента")
    city = models.IntegerField(null=True, blank=True, verbose_name="ID города из GeoNames")
    alpha2 = models.IntegerField(null=True, blank=True, verbose_name="Код страны из GeoNames")
    date = models.DateField(verbose_name="Дата ивента", blank=True, null=True)
    duration = models.IntegerField(choices=DURATION_CHOICES, verbose_name="Длительность ивента", blank=True, null=True)
    exact_time = models.TimeField(verbose_name="Точное время встречи", blank=True, null=True)
    place = models.CharField(max_length=50, choices=PLACE_CHOICES, verbose_name="Место ивента", blank=True, null=True)
    min_age = models.IntegerField(default=18, validators=[MinValueValidator(18), MaxValueValidator(99)], verbose_name="Минимальный возраст")
    max_age = models.IntegerField(default=99, validators=[MinValueValidator(18), MaxValueValidator(99)], verbose_name="Максимальный возраст")
    currency = models.CharField(max_length=60, choices=CURRENCY_CHOICES, blank=True, null=True, verbose_name='Валюта награды за ивент')
    reward = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Награда за ивент")
    description = models.TextField(verbose_name="Описание ивента", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")
    is_active = models.BooleanField(default=True, verbose_name="Активный/нет")

    class Meta:
        verbose_name = "Ивент"
        verbose_name_plural = "Ивенты"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.id}, {self.city})"


class SubscriptionType(models.TextChoices):
    """Срок подписки"""
    MONTHLY = "monthly", "1 месяц"
    YEARLY = "yearly", "1 год"


class Product(models.Model):
    """Товар, который пользователь может купить: подписка"""
    name = models.CharField(max_length=100, verbose_name="Название товара")
    subscription_type = models.CharField(max_length=20, choices=SubscriptionType.choices, verbose_name="Тип подписки",
                                         null=True, blank=True)
    duration_days = models.PositiveIntegerField(null=True, blank=True, verbose_name="Количество дней")
    price = models.PositiveIntegerField(verbose_name="Цена в рублях")

    def save(self, *args, **kwargs):
        # Автоматически устанавливаем duration_days
        if self.subscription_type == SubscriptionType.MONTHLY:
            self.duration_days = 30
        elif self.subscription_type == SubscriptionType.YEARLY:
            self.duration_days = 365

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

    def __str__(self):
        return self.name


class Purchase(models.Model):
    """Запись о покупке пользователя. Связана с пользователем (player) и продуктом (product)"""
    player = models.ForeignKey("Player", on_delete=models.CASCADE, related_name="purchases", verbose_name="Пользователь")
    product = models.ForeignKey("Product", on_delete=models.SET_NULL, null=True, verbose_name="Продукт")
    payment_id = models.CharField(max_length=100, unique=True, verbose_name="ID платежа в ЮKassa")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата покупки")
    is_successful = models.BooleanField(default=False, verbose_name="Успешно оплачено")

    class Meta:
        constraints = [models.UniqueConstraint(fields=['payment_id'], name='unique_payment')]
        verbose_name = "Оплата"
        verbose_name_plural = "Оплаты"

    def __str__(self):
        return f"{self.player.tg_id} — {self.product.name}"


class BlacklistUser(models.Model):
    """Черный список пользователей"""
    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name="blacklist_entry", verbose_name="Пользователь", null=True, blank=True)
    reason = models.TextField(verbose_name="Причина блокировки", blank=True, null=True)
    blocked_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата блокировки")

    class Meta:
        verbose_name = "Заблокированный пользователь"
        verbose_name_plural = "Заблокированные пользователи"
        ordering = ['-blocked_at']

    def get_player_tg_id(self, obj):
        return obj.player.tg_id if obj.player else "—"
    get_player_tg_id.short_description = "Telegram ID"

