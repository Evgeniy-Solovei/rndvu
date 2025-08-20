from django.contrib import admin
from core_rndvu.models import *


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели Player."""
    list_display = [field.name for field in Player._meta.fields]


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


@admin.register(PhotoReaction)
class PhotoReactionAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели PhotoReaction."""
    list_display = [field.name for field in PhotoReaction._meta.fields]


@admin.register(Sympathy)
class SympathyAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели Sympathy."""
    list_display = [field.name for field in Sympathy._meta.fields]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели Favorite."""
    list_display = [field.name for field in Favorite._meta.fields]
