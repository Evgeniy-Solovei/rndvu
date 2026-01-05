from django.contrib import admin
from django.contrib.auth.models import Group, User

from core_rndvu.models import *

# Скрываем стандартные модели Django auth из админки
for model in (Group, User):
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели Player."""
    list_display = [field.name for field in Player._meta.fields]
    search_fields = ['tg_id', 'first_name', 'username']  # Для autocomplete в BlacklistUserAdmin
#
#
# @admin.register(ProfileMan)
# class ProfileManAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели ProfileMan."""
#     list_display = [field.name for field in ProfileMan._meta.fields]
#
#
# @admin.register(ManPhoto)
# class ManPhotoAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели ManPhoto."""
#     list_display = [field.name for field in ManPhoto._meta.fields]
#
#
# @admin.register(ProfileWoman)
# class ProfileWomanAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели ProfileWoman."""
#     list_display = [field.name for field in ProfileWoman._meta.fields]
#
#
# @admin.register(WomanPhoto)
# class WomanPhotoAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели WomanPhoto."""
#     list_display = [field.name for field in WomanPhoto._meta.fields]
#
#
# @admin.register(UserReactionDislike)
# class UserReactionDislikeAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели UserReactionDislike."""
#     list_display = [field.name for field in UserReactionDislike._meta.fields]


# @admin.register(PhotoReaction)
# class PhotoReactionAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели PhotoReaction."""
#     list_display = [field.name for field in PhotoReaction._meta.fields]
#
#
# @admin.register(Sympathy)
# class SympathyAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели Sympathy."""
#     list_display = [field.name for field in Sympathy._meta.fields]
#
#
# @admin.register(Favorite)
# class FavoriteAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели Favorite."""
#     list_display = [field.name for field in Favorite._meta.fields]
#
#
# @admin.register(Event)
# class EventAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели Event."""
#     list_display = [field.name for field in Event._meta.fields]
#
#
# @admin.register(Purchase)
# class PurchaseAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели Purchase."""
#     list_display = [field.name for field in Purchase._meta.fields]
#
#
# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели Product."""
#     list_display = [field.name for field in Product._meta.fields]


@admin.register(BlacklistUser)
class BlacklistUserAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели BlacklistUser."""
    list_display = [field.name for field in BlacklistUser._meta.fields]


@admin.register(SubscriptionGrant)
class SubscriptionGrantAdmin(admin.ModelAdmin):
    """Ручная выдача подписки пользователю через админку."""
    list_display = ["player", "subscription_type", "duration_days", "created_at", "applied_by"]
    search_fields = ["player__tg_id", "player__first_name", "player__username"]
    autocomplete_fields = ["player"]
    readonly_fields = ["duration_days", "created_at", "applied_by"]
    fields = ["player", "subscription_type", "duration_days", "created_at", "applied_by"]

    def _reset_subscription(self, player_ids):
        Player.objects.filter(id__in=player_ids).update(
            paid_subscription=False,
            count_days_paid_subscription=0,
            subscription_end_date=None,
        )

    def save_model(self, request, obj, form, change):
        if not change and not obj.applied_by:
            obj.applied_by = request.user
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        self._reset_subscription([obj.player_id])
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        player_ids = list(queryset.values_list("player_id", flat=True).distinct())
        if player_ids:
            self._reset_subscription(player_ids)
        super().delete_queryset(request, queryset)

#
# @admin.register(PassedUser)
# class PassedUserAdmin(admin.ModelAdmin):
#     """Регистрация в админ панели модели PassedUser."""
#     list_display = [field.name for field in PassedUser._meta.fields]
