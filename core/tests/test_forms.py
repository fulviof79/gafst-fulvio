from django.core.management import call_command
from django.test import TestCase

from core.enums import RoleEnum, ExamEnum, JSEnum
from core.forms import MemberForm, ClubForm
from core.models import Role, Exam, JS


class MemberFormTest(TestCase):
    def setUp(self):
        # run insert_defaults command
        call_command("insert_defaults")

    def test_valid_form(self):
        data = {
            "name": "Alice",
            "surname": "Panna",
            "house_number": "20",
            "street": "Viale Bartolomeo",
            "city": "Minusio",
            "zip_code": "6648",
            "date_of_birth": "2021-08-16",
            "nationality": "CH",
            "affiliation_year": "2023",
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            "exams": [],
            "js": [],
        }
        form = MemberForm(data)
        self.assertTrue(form.is_valid())

    def test_missing_required_fields(self):
        # Test missing name field
        data = {
            # "name": "Alice",  # Missing this field on purpose
            "surname": "Panna",
            "house_number": "20",
            "street": "Viale Bartolomeo",
            "city": "Minusio",
            "zip_code": "6648",
            "date_of_birth": "2021-08-16",
            "nationality": "CH",
            "affiliation_year": "2023",
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
        }
        form = MemberForm(data)
        self.assertFalse(form.is_valid())

    def test_optional_fields(self):
        data = {
            "name": "Alice",
            "surname": "Panna",
            "house_number": "20",
            "street": "Viale Bartolomeo",
            "city": "Minusio",
            "zip_code": "6648",
            "date_of_birth": "2021-08-16",
            "nationality": "CH",
            "affiliation_year": "2023",
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            # "exams": [self.exam.id],  # Missing this optional field on purpose
            # "js": [self.js.id],  # Missing this optional field on purpose
        }
        form = MemberForm(data)
        self.assertTrue(form.is_valid())


class ClubFormTest(TestCase):
    def test_valid_data(self):
        valid_data_1 = {
            "name": "Bellinzona",
            "affiliation_year": 2017,
            "license_no": 1,
        }
        valid_data_2 = {
            "name": "Bellinzona",
            "affiliation_year": 2017,
            "license_no": 99,
        }
        form_1 = ClubForm(valid_data_1)
        form_2 = ClubForm(valid_data_2)

        self.assertTrue(form_1.is_valid())
        self.assertTrue(form_2.is_valid())

    def test_invalid_edge_cases(self):
        invalid_data_1 = {
            "name": "Bellinzona",
            "affiliation_year": 2017,
            "license_no": 0,
        }
        invalid_data_2 = {
            "name": "Bellinzona",
            "affiliation_year": 2017,
            "license_no": 100,
        }
        form_1 = ClubForm(invalid_data_1)
        form_2 = ClubForm(invalid_data_2)

        self.assertFalse(form_1.is_valid())
        self.assertFalse(form_2.is_valid())
        self.assertIn("license_no", form_1.errors)
        self.assertIn("license_no", form_2.errors)
