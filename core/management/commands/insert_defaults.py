from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

from core.models import Role, Exam, JS
from core.enums import RoleEnum, ExamEnum, JSEnum, GroupEnum


def insert_defaults_by_enum(model, enum):
    for e in enum:
        model.objects.get_or_create(name=e.value)


class Command(BaseCommand):
    help = "Insert default roles and exams"

    def handle(self, *args, **options):
        insert_defaults_by_enum(Role, RoleEnum)
        self.stdout.write(self.style.SUCCESS("Successfully populated Role table"))

        insert_defaults_by_enum(Exam, ExamEnum)
        self.stdout.write(self.style.SUCCESS("Successfully populated Exam table"))

        insert_defaults_by_enum(JS, JSEnum)
        self.stdout.write(self.style.SUCCESS("Successfully populated JS table"))

        # permissions
        fstb_admin_permissions = Permission.objects.get(
            codename="fstb_admin_permissions"
        )
        club_admin_permissions = Permission.objects.get(
            codename="club_admin_permissions"
        )

        # insert default groups and related permission for django auth, based on GroupEnum
        fstb_admin_group = Group.objects.create(name=GroupEnum.FSTB_ADMIN.value)
        fstb_admin_group.permissions.set([fstb_admin_permissions])
        fstb_admin_group.permissions.set([club_admin_permissions])

        club_admin_group = Group.objects.create(name=GroupEnum.CLUB_ADMIN.value)
        club_admin_group.permissions.set([club_admin_permissions])

        self.stdout.write(
            self.style.SUCCESS("Successfully populated Group table for django auth")
        )
