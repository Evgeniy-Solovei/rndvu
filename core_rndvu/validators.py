from datetime import date
from django.core.exceptions import ValidationError


"""Валидатор о размере макс. размера фото"""
def validate_photo_size(value):
    limit = 20 * 1024 * 1024  # 20MB
    if value.size > limit:
        raise ValidationError('Максимальный размер файла - 20MB')

"""Валидатор для заполнения даты рождения"""
def validate_birth_date(value):
    if value > date.today():
        raise ValidationError("Дата рождения не может быть в будущем")
