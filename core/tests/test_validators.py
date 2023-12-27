from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.test import TestCase
from core.validators import BirthdateValidator, validator_membership_license_no


class TestBirthdateValidator(TestCase):
    def setUp(self):
        self.validator = BirthdateValidator(min_age=18, max_age=100)

    def test_validator_with_valid_age(self):
        # Calculate a birthdate that results in a valid age
        valid_birth_date = date.today() - timedelta(days=18 * 365 + 18 / 4)

        # The validator should not raise an exception for a valid age
        try:
            self.validator(valid_birth_date)
        except ValidationError:
            self.fail("DateBirthValidator raised ValidationError unexpectedly!")

    def test_validator_with_younger_age(self):
        # Calculate a birth date that results in an age that is too young
        young_birth_date = date.today() - timedelta(days=17 * 365)

        # The validator should raise an exception for an age that is too young
        with self.assertRaises(ValidationError):
            self.validator(young_birth_date)

    def test_validator_with_older_age(self):
        # Calculate a birthdate that results in an age that is too old
        old_birth_date = date.today() - timedelta(days=101 * 365 + 101 / 4)

        # The validator should raise an exception for an age that is too old
        with self.assertRaises(ValidationError):
            self.validator(old_birth_date)

    def test_validator_with_none_value(self):
        # The validator should not raise an exception when the value is None
        try:
            self.validator(None)
        except ValidationError:
            self.fail("DateBirthValidator raised ValidationError unexpectedly!")

class ValidatorMembershipLicenseNoTest(TestCase):

    def test_validator_with_empty_string(self):
        # No exception should be raised
        try:
            validator_membership_license_no("")
        except Exception as e:
            self.fail(f"validator_membership_license_no() raised {e} unexpectedly!")

    def test_validator_with_non_empty_string(self):
        # The function should just return and do nothing
        result = validator_membership_license_no("some_value")
        self.assertIsNone(result)

    def test_validator_with_none(self):
        # The function should just return and do nothing
        result = validator_membership_license_no(None)
        self.assertIsNone(result)