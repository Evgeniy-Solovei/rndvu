import os
from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageOps


def optimize_image(uploaded_file, max_side=1280, quality=80):
    """
    Сжимаем пользовательское фото для быстрой отдачи:
    - поворачиваем по EXIF
    - ограничиваем большую сторону до max_side
    - конвертируем в JPEG с заданным quality
    Возвращает новый InMemoryUploadedFile или исходник, если он меньше.
    """
    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
    except Exception:
        uploaded_file.seek(0)
        return uploaded_file

    try:
        image = ImageOps.exif_transpose(image)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        width, height = image.size
        max_current_side = max(width, height)
        if max_current_side > max_side:
            scale = max_side / max_current_side
            new_size = (int(width * scale), int(height * scale))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        buffer = BytesIO()
        image.save(buffer, format="JPEG", optimize=True, quality=quality)
        buffer.seek(0)

        new_name = f"{os.path.splitext(uploaded_file.name)[0]}.jpg"
        optimized_file = InMemoryUploadedFile(
            file=buffer,
            field_name=getattr(uploaded_file, "field_name", None),
            name=new_name,
            content_type="image/jpeg",
            size=buffer.getbuffer().nbytes,
            charset=getattr(uploaded_file, "charset", None),
        )
        # Если после оптимизации файл не уменьшился — используем оригинал
        if hasattr(uploaded_file, "size") and optimized_file.size >= uploaded_file.size:
            uploaded_file.seek(0)
            return uploaded_file
        return optimized_file
    except Exception:
        uploaded_file.seek(0)
        return uploaded_file
