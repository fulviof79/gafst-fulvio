import os

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from core.utils import run_command


class Command(BaseCommand):
    help = "Deploy the application"

    PROJECT_NAME = "gafst"
    SETTINGS_FILE_PATH = os.path.join(PROJECT_NAME, "settings.py")
    PRODUCTION_SETTINGS_FILE_PATH = os.path.join(PROJECT_NAME, "production_settings.py")
    REQUIREMENTS_FILE = "requirements.txt"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "Deploying the application...\n"
                + "- remember to run this command in the right virtual environment"
                + "\n- remember to fetch and pull the latest changes from the git repository"
                + "\n- remember that this will modify the settings.py file"
                + "\n\nPRESS ENTER TO CONTINUE"
            )
        )

        input()

        try:
            self.install_requirements()
            self.collect_static_files()
            self.setup_production_settings()
            self.setup_db()
            self.create_superuser()

        except Exception as e:
            raise CommandError(str(e))

    def install_requirements(self):
        self.stdout.write(self.style.SUCCESS("Install Requirements..."))
        run_command(f"pip install -r {self.REQUIREMENTS_FILE}")

    def collect_static_files(self):
        self.stdout.write(self.style.SUCCESS("Collect Static Files..."))
        call_command('collectstatic', interactive=False, clear=True)

    def setup_production_settings(self):
        self.stdout.write(self.style.SUCCESS("Setup Production Settings..."))
        prod_setting = self.PRODUCTION_SETTINGS_FILE_PATH
        local_setting = self.SETTINGS_FILE_PATH
        print('prod: ', prod_setting)
        print('local: ', local_setting)
        run_command(
            f"cp {self.PRODUCTION_SETTINGS_FILE_PATH} {self.SETTINGS_FILE_PATH}"
        )

    def setup_db(self):
        reset_database = input(
            self.style.WARNING("Do you want to reset the database? (y/n) ")
        )
        if reset_database.lower() == "y":
            run_command("python manage.py reset_database")

    def create_superuser(self):
        create_superuser = input(
            self.style.WARNING("Do you want to create a superuser account? (y/n) ")
        )
        if create_superuser.lower() == "y":
            connection = connections["default"]
            db_name = connection.settings_dict["NAME"]

            call_command("createsuperuser")
