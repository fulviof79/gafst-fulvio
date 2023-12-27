# ----- Django imports -------------------------------------------------------------
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, FileExtensionValidator
from django.db import models
from django.contrib.auth.models import User
from django.utils.datetime_safe import date
from django.utils.translation import gettext_lazy as _

from gafst import settings

# ----- Core imports ---------------------------------------------------------------
from .enums import RoleEnum, JSEnum, ExamEnum, ChangeModelStatus, CompetitionRegistrationStatus, CompetitionStatus, \
    RuleCondition, RuleOption
from .utils import is_license_no_unique_within_club
from .validators import BirthdateValidator, validate_image_size


# id field is automatically added by Django, if no primary key is defined


# ---- PermissionsSupport ----------------------------------------------------------
class PermissionsSupport(models.Model):
    """This model is used to add permissions to the User model"""

    class Meta:
        managed = False  # No database table creation or deletion  \
        # operations will be performed for this model.

        default_permissions = ()  # disable "add", "change", "delete"
        # and "view" default permissions

        permissions = (
            ("fstb_admin_permissions", "Have FSTB Admin Permissions"),
            ("club_admin_permissions", "Have Club Admin Permissions"),
        )


# ---- Member -----------------------------------------------------------------------
class BaseMember(models.Model):
    photo = models.ImageField(
        upload_to=settings.MEMBERS_PHOTOS_DIR,
        verbose_name=_("photo"),
        blank=True,
        null=True,
        validators=[
            validate_image_size,
            FileExtensionValidator(["png", "jpg", "jpeg"]),
        ],
    )
    name = models.CharField(max_length=150, verbose_name=_("name"))
    surname = models.CharField(max_length=150, verbose_name=_("surname"))
    house_number = models.CharField(max_length=50, verbose_name=_("house number"))
    street = models.CharField(max_length=100, verbose_name=_("street"))
    city = models.CharField(max_length=100, verbose_name=_("city"))
    zip_code = models.CharField(max_length=20, verbose_name=_("zip code"))
    date_of_birth = models.DateField(
        default=date.today,
        validators=[BirthdateValidator(min_age=2, max_age=200)],
        verbose_name=_("date of birth"),
    )
    nationality = models.CharField(max_length=2, verbose_name=_("nationality"))
    affiliation_year = models.PositiveIntegerField(verbose_name=_("affiliation year"))
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)

    roles = models.ManyToManyField("Role", blank=False, verbose_name=_("roles"))
    exams = models.ManyToManyField("Exam", blank=True, verbose_name=_("exams"))
    js = models.ManyToManyField("JS", blank=True, verbose_name=_("js"))

    class Meta:
        abstract = True

    @property
    def has_club_membership(self):
        return self.current_membership is not None

    @property
    def current_membership(self):
        return Membership.objects.filter(
            member=self, transfer_date__isnull=True
        ).first()

    def __str__(self):
        return f"{self.name} {self.surname}"


class Member(BaseMember):
    pass


# ---- Club -------------------------------------------------------------------------
class Club(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("name"))
    affiliation_year = models.PositiveIntegerField(verbose_name=_("affiliation year"))
    license_no = models.PositiveIntegerField(
        unique=True,
        validators=[MaxValueValidator(99)],
        verbose_name=_("license number"),
    )
    discharge_date = models.DateField(
        null=True, blank=True, verbose_name=_("discharge date")
    )
    possible_resume_date = models.DateField(
        null=True, blank=True, verbose_name=_("possible resume date")
    )
    members = models.ManyToManyField(
        Member, through="Membership", verbose_name=_("members")
    )

    @property
    def full_license_no(self):
        return f"{self.license_no:02d}-000"

    @classmethod
    def remaining_license_no(cls):
        used_license_nos = Club.objects.values_list("license_no", flat=True)
        remaining_license_numbers = set(range(1, 100)) - set(used_license_nos)
        remaining_license_numbers = [
            (num, f"{str(num).zfill(2)}-000") for num in remaining_license_numbers
        ]
        return remaining_license_numbers

    def __str__(self):
        return self.name


# ---- Team --------------------------------------------------------------------------
class Team(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("name"))
    photo = models.ImageField(
        upload_to=settings.MEMBERS_PHOTOS_DIR,
        verbose_name=_("photo"),
        blank=True,
        null=True,
        validators=[
            validate_image_size,
            FileExtensionValidator(["png", "jpg", "jpeg"]),
        ],
    )
    members = models.ManyToManyField("Member", blank=False, verbose_name=_("members"))
    club = models.ForeignKey(Club, on_delete=models.CASCADE, null=True)
    description = models.TextField(max_length=10000, verbose_name=_("description"), null=True)

    def __str__(self):
        return self.name


# ---- Membership -------------------------------------------------------------------
LICENSE_NO_FOR_CLUB_ALREADY_USED_ERROR_MESSAGE = _(
    "The license number is already used in this club."
)
MEMBERSHIP_MODEL_NAME = "Membership"


class BaseMembership(models.Model):
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, verbose_name=_("member")
    )
    club = models.ForeignKey(Club, on_delete=models.CASCADE, verbose_name=_("club"))
    license_no = models.PositiveIntegerField(
        validators=[MaxValueValidator(999)], verbose_name=_("license number")
    )
    transfer_date = models.DateField(
        null=True, blank=True, verbose_name=_("transfer date")
    )

    class Meta:
        abstract = True

    @property
    def full_license_no(self):
        return f"{self.club.license_no:02d}-{self.license_no:03d}"

    @classmethod
    def remaining_license_no(cls):
        used_license_nos = Membership.objects.values_list("license_no", flat=True)
        remaining_license_numbers = set(range(1, 999)) - set(used_license_nos)
        remaining_license_numbers = [
            (num, f"01-{str(num).zfill(3)}") for num in remaining_license_numbers
        ]
        return remaining_license_numbers

    def __str__(self):
        return f"{self.member} - {self.club}"

    def clean(self):
        # Check if the license_no is unique within the club.
        if not is_license_no_unique_within_club(
                type(self).__name__, self.club, self.license_no, [self.id]
        ):
            raise ValidationError(LICENSE_NO_FOR_CLUB_ALREADY_USED_ERROR_MESSAGE)

    def save(self, *args, **kwargs):
        self.full_clean()  # Perform model validation!
        super().save(*args, **kwargs)


class Membership(BaseMembership):
    pass


# ---- Role ----------------------------------------------------------------------
class Role(models.Model):
    name = models.CharField(max_length=50, verbose_name=_("name"))

    def __str__(self):
        return self.name


# ---- Exam -------------------------------------------------------------------
class Exam(models.Model):
    name = models.CharField(
        max_length=50,
        choices=ExamEnum.choices(),
        default=ExamEnum.HONOR.value,
        unique=True,
        verbose_name=_("name"),
    )

    def __str__(self):
        return self.name


# ---- JS -------------------------------------------------------------------
class JS(models.Model):
    name = models.CharField(
        max_length=50,
        choices=JSEnum.choices(),
        default=JSEnum.MONITOR_JS.value,
        verbose_name=_("name"),
    )

    def __str__(self):
        return self.name


# ---- Change Modals --------------------------------------------------------------
class ChangeModel(models.Model):
    # Required at Creation
    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="%(class)s_applicant",
    )

    # Set later After Creation
    responder = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="%(class)s_responder",
    )

    # Auto Created at Creation
    status = models.CharField(
        max_length=10,
        choices=ChangeModelStatus.choices(),
        default=ChangeModelStatus.PENDING.value,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class MemberChange(BaseMember, ChangeModel):
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="member_changes",
        null=True,
        blank=True,
    )

    @property
    def current_membership(self):
        return MembershipChange.objects.filter(member=self).first()

    pass


class MembershipChange(BaseMembership, ChangeModel):
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="membership_changes",
        null=True,
        blank=True,
    )

    member = models.OneToOneField(
        MemberChange,
        on_delete=models.CASCADE,
        related_name="membership_change",
        null=True,
        blank=True,
    )

    pass


# ---- Competition -------------------------------------------------------------------
class Competition(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("name"))
    due_date = models.DateTimeField(default=date.today, verbose_name=_("due_date"))
    creation_date = models.DateField(default=date.today, verbose_name=_("creation_date"))
    status = models.CharField(
        max_length=50,
        choices=CompetitionStatus.choices(),
        default=CompetitionStatus.OPEN.value,
        unique=False,
        verbose_name=_("status"),
    )
    description = models.TextField(max_length=10000, verbose_name=_("description"), null=True)

    def __str__(self):
        return self.name


# ---- Disciplines -------------------------------------------------------
class Discipline(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("name"))
    description = models.TextField(max_length=10000, verbose_name=_("description"), null=True)
    min_members_number = models.IntegerField(default=6, verbose_name=_("min_members_number"), null=True)
    max_members_number = models.IntegerField(default=6, verbose_name=_("max_members_number"), null=True)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name


# ---- Rule -------------------------------------------------------
class Division(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("name"))
    description = models.TextField(max_length=10000, verbose_name=_("description"), null=True)
    exams = models.ManyToManyField("Exam", blank=True, verbose_name=_("exams"))
    year_rules = models.ManyToManyField("YearRule", blank=True, verbose_name=_("year_rules"))
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name


# ---- Year Rule -------------------------------------------------------
class YearRule(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("name"))
    option = models.CharField(
        max_length=50,
        choices=RuleOption.choices(),
        unique=False,
        verbose_name=_("option"),
    )
    condition = models.CharField(
        max_length=50,
        choices=RuleCondition.choices(),
        unique=False,
        verbose_name=_("condition"),
    )
    value = models.FloatField(verbose_name=_("value"))
    description = models.TextField(max_length=10000, verbose_name=_("description"), null=True)

    def __str__(self):
        return self.name


# ---- CompetitionRegistration -------------------------------------------------------
class CompetitionRegistration(models.Model):
    status = models.CharField(
        max_length=50,
        choices=CompetitionRegistrationStatus.choices(),
        default=CompetitionRegistrationStatus.DRAFT.value,
        unique=False,
        verbose_name=_("status"),
    )
    creation_date = models.DateField(default=date.today, verbose_name=_("creation_date"))
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, null=True)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, null=True)
    division = models.ForeignKey(Division, on_delete=models.CASCADE, null=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True)

    club = models.ForeignKey(Club, on_delete=models.CASCADE, null=True)


# ---- Functions -------------------------------------------------------------------
def get_remaining_memberships_by_club(club):
    club_license_no = club.license_no
    used_club_membership_license_nos = Membership.objects.filter(
        club=club, transfer_date__isnull=True
    ).values_list("license_no", flat=True)
    remaining_club_membership_license_nos = set(range(1, 999)) - set(
        used_club_membership_license_nos
    )
    remaining_club_membership_license_nos = [
        (
            num,
            "{:02d}-{:03d}".format(club_license_no, num),
        )
        for num in remaining_club_membership_license_nos
    ]
    return remaining_club_membership_license_nos
