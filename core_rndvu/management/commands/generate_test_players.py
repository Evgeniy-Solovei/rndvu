import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from core_rndvu.models import *


class Command(BaseCommand):
    help = "Генерация тестовых анкет игроков"

    def handle(self, *args, **kwargs):
        # Сначала почистим старые тестовые данные
        Player.objects.filter(username__startswith="testuser").delete()

        # Фейковое фото (одинаковое для всех)
        from PIL import Image
        import io

        image = Image.new("RGB", (200, 200), (255, 0, 0))  # Красная картинка-заглушка
        image_file = io.BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)
        photo_content = ContentFile(image_file.read(), name="test.jpg")

        # Создаём мужские профили
        for i in range(20):
            player = Player.objects.create(
                tg_id=1000000 + i,
                first_name=f"TestMan{i}",
                username=f"testuser_man{i}",
                gender="Man",
                city=random.choice(["Москва", "СПб", "Казань", "Екатеринбург"]),
                likes_count=random.randint(0, 50),
                dislikes_count=random.randint(0, 20),
            )
            profile = ProfileMan.objects.create(
                player=player,
                birth_date=date.today() - timedelta(days=random.randint(20*365, 40*365)),
                about="Я тестовый мужчина, люблю спорт и игры.",
            )
            ManPhoto.objects.create(
                profile=profile,
                image=photo_content,
                main_photo=True
            )

        # Создаём женские профили
        for i in range(20):
            player = Player.objects.create(
                tg_id=2000000 + i,
                first_name=f"TestWoman{i}",
                username=f"testuser_woman{i}",
                gender="Woman",
                city=random.choice(["Москва", "СПб", "Новосибирск", "Сочи"]),
                likes_count=random.randint(0, 50),
                dislikes_count=random.randint(0, 20),
            )
            profile = ProfileWoman.objects.create(
                player=player,
                birth_date=date.today() - timedelta(days=random.randint(18*365, 35*365)),
                height=random.randint(155, 180),
                weight=random.randint(45, 70),
                bust_size=random.randint(80, 100),
                waist_size=random.randint(55, 75),
                hips_size=random.randint(85, 105),
                interests="Путешествия, книги, музыка",
                about="Я тестовая девушка, люблю путешествовать.",
            )
            WomanPhoto.objects.create(
                profile=profile,
                image=photo_content,
                main_photo=True
            )

        self.stdout.write(self.style.SUCCESS("✅ 20 мужских и 20 женских профилей созданы"))
