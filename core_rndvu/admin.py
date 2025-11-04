from django.contrib import admin
from core_rndvu.models import *


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели Player."""
    list_display = [field.name for field in Player._meta.fields]
    search_fields = ['tg_id', 'first_name', 'username']  # Для autocomplete в BlacklistUserAdmin


@admin.register(ProfileMan)
class ProfileManAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели ProfileMan."""
    list_display = [field.name for field in ProfileMan._meta.fields]


@admin.register(ManPhoto)
class ManPhotoAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели ManPhoto."""
    list_display = [field.name for field in ManPhoto._meta.fields]


@admin.register(ProfileWoman)
class ProfileWomanAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели ProfileWoman."""
    list_display = [field.name for field in ProfileWoman._meta.fields]


@admin.register(WomanPhoto)
class WomanPhotoAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели WomanPhoto."""
    list_display = [field.name for field in WomanPhoto._meta.fields]


@admin.register(UserReactionDislike)
class UserReactionDislikeAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели UserReactionDislike."""
    list_display = [field.name for field in UserReactionDislike._meta.fields]


# @admin.register(PhotoReaction)
# class PhotoReactionAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели PhotoReaction."""
#     list_display = [field.name for field in PhotoReaction._meta.fields]


@admin.register(Sympathy)
class SympathyAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели Sympathy."""
    list_display = [field.name for field in Sympathy._meta.fields]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели Favorite."""
    list_display = [field.name for field in Favorite._meta.fields]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели Event."""
    list_display = [field.name for field in Event._meta.fields]


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели Purchase."""
    list_display = [field.name for field in Purchase._meta.fields]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели Product."""
    list_display = [field.name for field in Product._meta.fields]


@admin.register(BlacklistUser)
class BlacklistUserAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели BlacklistUser."""
    list_display = [field.name for field in BlacklistUser._meta.fields]
    # list_display = ['player', 'reason', 'blocked_at']
    # list_filter = ['blocked_at']
    # search_fields = ['player__tg_id', 'player__first_name', 'player__username', 'reason']
    # readonly_fields = ['blocked_at']
    # autocomplete_fields = ['player']  # Для удобного поиска пользователя
