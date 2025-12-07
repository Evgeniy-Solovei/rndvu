import os

from django.core.management.base import BaseCommand

from core_rndvu.models import ManPhoto, WomanPhoto
from core_rndvu.utils.image_utils import optimize_image


class Command(BaseCommand):
    help = "Оптимизация уже загруженных фото (ресайз и JPEG) для более быстрой отдачи."

    def add_arguments(self, parser):
        parser.add_argument("--max-side", type=int, default=1280, help="Максимальная сторона итогового фото.")
        parser.add_argument("--quality", type=int, default=80, help="JPEG quality.")
        parser.add_argument("--limit", type=int, help="Ограничить количество фото на модель.")
        parser.add_argument("--dry-run", action="store_true", help="Не сохранять, только показать потенциальную экономию.")

    def handle(self, *args, **options):
        max_side = options["max_side"]
        quality = options["quality"]
        limit = options.get("limit")
        dry_run = options["dry_run"]

        total_checked = 0
        total_changed = 0

        for model in (ManPhoto, WomanPhoto):
            qs = model.objects.all().order_by("id")
            if limit:
                qs = qs[:limit]
            for photo in qs.iterator():
                total_checked += 1
                try:
                    changed = self._process_photo(photo, max_side, quality, dry_run)
                    if changed:
                        total_changed += 1
                except Exception as exc:
                    self.stderr.write(f"[{model.__name__} #{photo.id}] ошибка: {exc}")

        action = "Переcохранил" if not dry_run else "Можно переcохранить"
        self.stdout.write(f"{action}: {total_changed}/{total_checked} фото.")

    def _process_photo(self, photo, max_side, quality, dry_run):
        if not photo.image:
            return False

        photo.image.open("rb")
        try:
            original_size = getattr(photo.image, "size", None)
            optimized_file = optimize_image(photo.image.file, max_side=max_side, quality=quality)
        finally:
            try:
                photo.image.close()
            except Exception:
                pass

        # Если оптимизация не уменьшила файл — пропускаем
        new_size = getattr(optimized_file, "size", None)
        if optimized_file is photo.image.file or (original_size and new_size and new_size >= original_size):
            return False

        # Формируем имя в том же каталоге, но с .jpg
        dir_name, _ = os.path.split(photo.image.name)
        base_name = os.path.splitext(os.path.basename(photo.image.name))[0]
        new_name = f"{base_name}.jpg"
        if dir_name:
            new_name = f"{dir_name}/{new_name}"

        if dry_run:
            saved_mb = self._format_mb(original_size) if original_size else "?"
            new_mb = self._format_mb(new_size) if new_size else "?"
            self.stdout.write(f"[{photo.__class__.__name__} #{photo.id}] {saved_mb} -> {new_mb} (preview)")
            return True

        old_name = photo.image.name
        photo.image.save(new_name, optimized_file, save=False)
        photo.save(update_fields=["image"])

        if old_name != photo.image.name and photo.image.storage.exists(old_name):
            photo.image.storage.delete(old_name)

        saved_mb = (self._format_mb(original_size), self._format_mb(getattr(photo.image, "size", None)))
        self.stdout.write(f"[{photo.__class__.__name__} #{photo.id}] оптимизировано {saved_mb[0]} -> {saved_mb[1]}")
        return True

    @staticmethod
    def _format_mb(size_bytes):
        if not size_bytes:
            return "?"
        return f"{size_bytes / (1024 * 1024):.2f}MB"
