# ----- Django imports ----------------------------------------------------------
from django.utils.datetime_safe import date
from django.core.exceptions import ValidationError
from django.core.validators import BaseValidator


class BirthdateValidator(BaseValidator):
    message = "Invalid date of birth."
    code = "invalid_date_of_birth"

    def __init__(self, min_age, max_age):
        self.min_age = min_age
        self.max_age = max_age

    def __call__(self, value):
        if value is None:
            return

        today = date.today()
        age = (
            today.year
            - value.year
            - ((today.month, today.day) < (value.month, value.day))
        )
        if age < self.min_age or age > self.max_age:
            raise ValidationError(self.message, code=self.code)


def validator_membership_license_no(value):
    if value is "":
        return


def validate_image_size(image):
    file_size = image.size
    max_size = 1024 * 1024  # 1 MB
    if file_size > max_size:
        raise ValidationError("Max size of file is 1 MB")
