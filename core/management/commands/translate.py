from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import os

from core.utils import run_command


class Command(BaseCommand):
    help = "Creates all messages in every supported language."

    def handle(self, *args, **options):
        # The languages supported by your app, defined in your settings file.
        languages = settings.LANGUAGES

        for lang, _ in languages:
            self.stdout.write(self.style.SUCCESS(f"Processing language: {lang}"))
            run_command(f"python manage.py makemessages -d django -l {lang}")
            run_command(f"python manage.py makemessages -d djangojs -l {lang}")

        # Removing english locale directory if exists
        en_dir = os.path.join(settings.BASE_DIR, "locale", "en")
        if os.path.exists(en_dir):
            # remove recursively
            os.system(f"rm -rf {en_dir}")

        # compile messages
        self.stdout.write(self.style.SUCCESS("Compiling messages..."))
        call_command("compilemessages")

        self.stdout.write(
            self.style.SUCCESS("All messages created and translated successfully.")
        )
