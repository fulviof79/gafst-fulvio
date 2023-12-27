from django.core.management.base import BaseCommand
from django.db import connections

from core.utils import run_command


class Command(BaseCommand):
    help = "Reset the database and populate with default data"

    def handle(self, *args, **kwargs):
        self.stdout.write("Resetting the database...")
        self.reset_database()

        self.apply_migrations()
        self.insert_defaults()

        self.stdout.write(
            self.style.SUCCESS(
                "Database reset and populated with default data successfully."
            )
        )

    @staticmethod
    def reset_database():
        connection = connections["default"]
        db_name = connection.settings_dict["NAME"]

        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            cursor.execute(f"CREATE DATABASE {db_name}")

    def apply_migrations(self):
        self.stdout.write(self.style.SUCCESS("Applying migrations..."))
        run_command("python manage.py makemigrations")
        run_command("python manage.py migrate")

    def insert_defaults(self):
        self.stdout.write(self.style.SUCCESS("Inserting default data..."))
        run_command("python manage.py insert_defaults")
