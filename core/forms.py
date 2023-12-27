# ----- Django imports --------------------------------------------------------
from django import forms
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.core.validators import FileExtensionValidator
from django.urls import reverse
from django.utils import formats
from django.utils.datetime_safe import date
from django.forms import ChoiceField, SelectMultiple
from django.utils.translation import gettext_lazy as _

# ----- Core imports --------------------------------------------------------
from .enums import RoleEnum, GroupEnum, CompetitionStatus, CompetitionRegistrationStatus, RuleOption, RuleCondition
from .models import Member, Club, Membership, Role, Exam, JS, Competition, Team, CompetitionRegistration, Division, \
    YearRule, Discipline
from .utils import get_years_map, get_nationality_acronym_map
from .validators import validator_membership_license_no, validate_image_size


class LicenseNoChoiceField(ChoiceField):
    def validate(self, value):
        validator_membership_license_no(value)


class CustomSelectMultipleWidget(SelectMultiple):
    template_name = "widgets/custom_multi_select.html"  # Path to your custom template


class MemberForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(), required=True)

    surname = forms.CharField(widget=forms.TextInput(), required=True)

    house_number = forms.CharField(widget=forms.TextInput(), required=True)

    street = forms.CharField(widget=forms.TextInput(), required=True)

    city = forms.CharField(widget=forms.TextInput(), required=True)

    zip_code = forms.CharField(widget=forms.TextInput(), required=True)

    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}, format=None),
        required=True,
        label=_("Date of birth"),
    )

    nationality = forms.ChoiceField(choices=[], label=_("Nationality"))

    affiliation_year = forms.ChoiceField(choices=[], label=_("Affiliation year"))

    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=CustomSelectMultipleWidget(),
        required=True,
        initial=[Role.objects.filter(name=RoleEnum.ATHLETE.value)],
        label=_("Roles"),
    )

    exams = forms.ModelMultipleChoiceField(
        queryset=Exam.objects.all(),
        widget=CustomSelectMultipleWidget(),
        required=False,
        initial=[],
        label=_("Exams"),
    )

    js = forms.ModelMultipleChoiceField(
        queryset=JS.objects.all(),
        widget=CustomSelectMultipleWidget(),
        required=False,
        initial=[],
        label=_("JS"),
    )

    class Meta:
        model = Member
        fields = [
            "name",
            "surname",
            "house_number",
            "street",
            "city",
            "zip_code",
            "date_of_birth",
            "nationality",
            "affiliation_year",
            "user",
            "roles",
            "exams",
            "js",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["date_of_birth"].initial = formats.localize_input(
            date.today().replace(year=date.today().year - 2)
        )
        self.fields["nationality"].choices = get_nationality_acronym_map()
        self.fields["nationality"].initial = "CH"
        self.fields["affiliation_year"].choices = get_years_map()
        self.fields["roles"].initial = Role.objects.filter(name=RoleEnum.ATHLETE.value)


class ClubForm(forms.ModelForm):
    license_no = forms.ChoiceField(choices=[], label=_("License number"))
    affiliation_year = forms.ChoiceField(choices=[], label=_("Affiliation year"))

    class Meta:
        model = Club
        fields = [
            "name",
            "affiliation_year",
            "license_no",
            "discharge_date",
            "possible_resume_date",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["license_no"].choices = Club.remaining_license_no()
        self.fields["affiliation_year"].choices = get_years_map()


class MembershipForm(forms.ModelForm):
    license_no = LicenseNoChoiceField(
        choices=[],
        validators=[validator_membership_license_no],
        label=_("Member License number"),
    )

    club_select = forms.ModelChoiceField(
        queryset=Club.objects.all(),
        label=_("Join a club"),
    )

    class Meta:
        model = Membership
        fields = [
            "license_no",
            "club",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["club"] = forms.ModelChoiceField(
            queryset=Club.objects.all(),
            label=_("Add new club"),
            widget=forms.Select(
                attrs={
                    "hx-get": reverse("load_license_no_field"),
                    "hx-target": "#license_no_container",
                }
            ),
        )

    def clean_license_no(self):
        value = self.cleaned_data["license_no"]
        validator_membership_license_no(value)
        return value


# ----- Role Form --------------------------------------------------------------
class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = [
            "name",
        ]


# ----- MemberMembershipForm ---------------------------------------------------

ON_CREATING_MEMBER_WITH_CLUB_ADMIN_USER__CLUB_NOT_SELECTED_ERROR = _(
    "Club Admin group must be associated with a club. So you must select a club."
)
ON_CREATING_MEMBER_WITH_CLUB_ADMIN_USER__USER_NOT_SELECTED_ERROR = _(
    "If an user group is selected you need to select also a user. So you must select a user."
)
ON_CREATING_MEMBER_WITH_CLUB_MEMBERSHIP__USER_GROUP_NOT_SELECTED_ERROR = _(
    "User must be associated with at least one group. So you must select a user group."
)
ON_CREATING_MEMBER_WITH_CLUB_ADMIN_USER__USER_IS_SUPERUSER = _(
    "A Superuser can't have the permission different From FSTB admin. You must select FSTB Admin Group"
)


class MemberMembershipForm(forms.Form):
    # Fields from MemberForm
    photo = forms.ImageField(
        required=False,
        label=_("Photo"),
        validators=[
            validate_image_size,
            FileExtensionValidator(["png", "jpg", "jpeg"]),
        ],
    )
    name = forms.CharField(widget=forms.TextInput(), required=True, label=_("Name"))
    surname = forms.CharField(
        widget=forms.TextInput(), required=True, label=_("Surname")
    )
    house_number = forms.CharField(
        widget=forms.TextInput(), required=True, label=_("House Number")
    )
    street = forms.CharField(widget=forms.TextInput(), required=True, label=_("Street"))
    city = forms.CharField(widget=forms.TextInput(), required=True, label=_("City"))
    zip_code = forms.CharField(
        widget=forms.TextInput(), required=True, label=_("Zip Code")
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        required=True,
        label=_("Date of birth"),
    )
    nationality = forms.ChoiceField(choices=[], label=_("Nationality"))
    affiliation_year = forms.ChoiceField(choices=[], label=_("Affiliation year"))
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all().order_by("name"),
        widget=CustomSelectMultipleWidget(),
        required=True,
        label=_("Roles"),
    )
    exams = forms.ModelMultipleChoiceField(
        queryset=Exam.objects.all(),
        widget=CustomSelectMultipleWidget(),
        required=False,
        label=_("Exams"),
    )
    js = forms.ModelMultipleChoiceField(
        queryset=JS.objects.all(),
        widget=CustomSelectMultipleWidget(),
        required=False,
        label=_("JS"),
    )

    # Fields from MembershipForm
    license_no = LicenseNoChoiceField(
        choices=[],
        validators=[validator_membership_license_no],
        label=_("Member License number"),
        required=False,
        widget=forms.Select(attrs={"required": False}),
    )
    club_select = forms.ModelChoiceField(
        queryset=Club.objects.all(),
        label=_("Join a club"),
        required=False,
        widget=forms.Select(attrs={"required": False}),
    )

    members_users_with_user = Member.objects.filter(user__isnull=False).values_list(
        "user", flat=True
    )

    users_without_member = User.objects.exclude(id__in=members_users_with_user)

    user_select = forms.ModelChoiceField(
        queryset=users_without_member,
        label="Select a User",
        required=False,
    )

    group_select = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        label="Select Group(s)",
        required=False,
        widget=CustomSelectMultipleWidget(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialization for MemberForm
        self.fields["date_of_birth"].initial = formats.localize_input(
            date.today().replace(year=date.today().year - 2)
        )
        self.fields["nationality"].choices = get_nationality_acronym_map()
        self.fields["nationality"].initial = "CH"
        self.fields["affiliation_year"].choices = get_years_map()
        self.fields["roles"].initial = Role.objects.filter(name=RoleEnum.ATHLETE.value)

        # Initialization for MembershipForm
        self.fields["club_select"] = forms.ModelChoiceField(
            queryset=Club.objects.all(),
            label=_("Add new club"),
            required=False,
            widget=forms.Select(
                attrs={
                    "required": False,
                    "hx-get": reverse("load_license_no_field"),
                    "hx-target": "#license_no_container",
                }
            ),
        )

    def clean(self):
        # If A Superuser is selected, then FSTB Admin must be selected
        if (
                self.cleaned_data["user_select"]
                and self.cleaned_data["user_select"].is_superuser
                and Group.objects.get(name=GroupEnum.FSTB_ADMIN.value)
                not in self.cleaned_data["group_select"]
        ):
            raise forms.ValidationError(
                ON_CREATING_MEMBER_WITH_CLUB_ADMIN_USER__USER_IS_SUPERUSER
            )

        # If Club Admin is selected, then a Club must be selected
        if (
                Group.objects.get(name=GroupEnum.CLUB_ADMIN.value)
                in self.cleaned_data["group_select"]
        ):
            if self.cleaned_data["club_select"] is None:
                raise forms.ValidationError(
                    ON_CREATING_MEMBER_WITH_CLUB_ADMIN_USER__CLUB_NOT_SELECTED_ERROR
                )
            elif self.cleaned_data["user_select"] is None:
                raise forms.ValidationError(
                    ON_CREATING_MEMBER_WITH_CLUB_ADMIN_USER__USER_NOT_SELECTED_ERROR
                )

        # If and user is selected, then a group must be selected
        if self.cleaned_data["user_select"] is not None:
            if len(self.cleaned_data["group_select"]) == 0:
                raise forms.ValidationError(
                    ON_CREATING_MEMBER_WITH_CLUB_MEMBERSHIP__USER_GROUP_NOT_SELECTED_ERROR
                )


# ----- Competition Form -------------------------------------------------------
class CompetitionForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(), required=True, label=_("Name"))
    due_date = forms.DateTimeField(
        input_formats=['%d-%m-%Y %H:%M'],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label=_("Due date"),
    )
    status = forms.ChoiceField(
        choices=CompetitionStatus.choices(),
        label=_("Status"),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label=_("Description"), required=False)

    def clean(self):
        cleaned_data = super(CompetitionForm, self).clean()

        for key, value in cleaned_data.items():
            if not value and key in self.initial:
                cleaned_data[key] = self.initial[key]

        return cleaned_data

    class Meta:
        model = Competition
        fields = [
            "name",
            "due_date",
            "status",
            "description",
        ]


# ----- Team Form -------------------------------------------------------
ON_CREATING_TEAM_WITH_CLUB_ADMIN_USER__CLUB_NOT_SELECTED_ERROR = _(
    "Club Admin team must be associated with a club. So you must select a club."
)


class TeamForm(forms.ModelForm):
    photo = forms.ImageField(
        required=False,
        label=_("Photo"),
        validators=[
            validate_image_size,
            FileExtensionValidator(["png", "jpg", "jpeg"]),
        ],
    )
    name = forms.CharField(widget=forms.TextInput(), required=True, label=_("Name"))
    members = forms.ModelMultipleChoiceField(
        queryset=Member.objects.filter(),
        widget=CustomSelectMultipleWidget(),
        required=True,
        label=_("Members"),
    )
    club = forms.ModelChoiceField(
        queryset=Club.objects.all(),
        label=_("Club"),
        required=True,
        widget=forms.Select(),
    )
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label=_("Description"), required=False)

    def clean(self):
        cleaned_data = super(TeamForm, self).clean()

        for key, value in cleaned_data.items():
            if not value and key in self.initial:
                cleaned_data[key] = self.initial[key]

        return cleaned_data

    class Meta:
        model = Team
        fields = [
            "photo",
            "name",
            "members",
            "club",
            "description"
        ]


# ----- CompetitionRegistration Form -------------------------------------------------------
class CompetitionRegistrationForm(forms.ModelForm):
    competition = forms.ModelChoiceField(
        queryset=Competition.objects.filter(status='Open'),
        required=True,
        label=_("Competition"),
        widget=forms.Select(attrs={"required": True}),
    )
    team = forms.ModelChoiceField(
        queryset=Team.objects.all(),
        required=True,
        label=_("Team"),
        widget=forms.Select(attrs={"required": True}),
    )
    club = forms.ModelChoiceField(
        queryset=Club.objects.all(),
        required=False,
        label=_("Club"),
        widget=forms.Select(attrs={"required": False}),
    )
    status = forms.ChoiceField(
        choices=CompetitionRegistrationStatus.choices(),
        label="Status",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["competition"] = forms.ModelChoiceField(
            queryset=Competition.objects.filter(status='Open'),
            label=_("Select competition"),
            widget=forms.Select(
                attrs={
                    "hx-get": reverse("load_disciplines"),
                    "hx-target": "#discipline_container",
                }
            ),
        )

    def clean_discipline(self):
        discipline = self.cleaned_data.get('discipline')
        if not discipline:
            raise forms.ValidationError("Questo campo è obbligatorio")
        return discipline

    class Meta:
        model = CompetitionRegistration
        fields = [
            "competition",
            "discipline",
            "division",
            "team",
            "club",
            "status",
        ]


class InscribedMemberForm(forms.Form):
    competition_select = forms.ModelChoiceField(
        queryset=Competition.objects.all(),
        label=_("Select a competition"),
        required=True,
    )

    member_select = forms.ModelChoiceField(
        queryset=Member.objects.all(),
        required=True,
        label=_("Select a Member"),
    )

    def clean(self):
        birthdate = self.cleaned_data["member_select"].date_of_birth
        min_age = 10

        # verify if member have the right age
        if birthdate > date.today().replace(year=date.today().year - min_age):
            raise forms.ValidationError(f"Member must be at least {min_age} years old")


# ----- Disciplines Form -------------------------------------------------------
class DisciplinesForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(), required=True, label=_("Name"))
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label=_("Description"), required=False)
    min_members_number = forms.IntegerField(widget=forms.NumberInput(), required=False,
                                            label=_("Minimum number members"))
    max_members_number = forms.IntegerField(widget=forms.NumberInput(), required=False,
                                            label=_("Maximum number members"))
    competition = forms.ModelChoiceField(
        queryset=Competition.objects.all(),
        label=_("Competition"),
        required=False,
        widget=forms.Select(),
    )

    class Meta:
        model = Division
        fields = [
            "name",
            "description",
            "min_members_number",
            "max_members_number",
            "competition",
        ]


# ----- Rule Form -------------------------------------------------------
class DivisionForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(), required=True, label=_("Name"))
    year_rules = forms.ModelMultipleChoiceField(
        queryset=YearRule.objects.all(),
        widget=CustomSelectMultipleWidget(),
        required=False,
        initial=[],
        label=_("Age rules"),
    )
    exams = forms.ModelMultipleChoiceField(
        queryset=Exam.objects.all(),
        widget=CustomSelectMultipleWidget(),
        required=False,
        initial=[],
        label=_("Exams"),
    )
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label=_("Description"), required=False)
    discipline = forms.ModelChoiceField(
        queryset=Discipline.objects.all(),
        label=_("Discipline"),
        required=False,
        widget=forms.Select(),
    )

    class Meta:
        model = Division
        fields = [
            "name",
            "year_rules",
            "exams",
            "description",
            "discipline",
        ]


# ----- Year Rule Form -------------------------------------------------------
class YearRuleForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(), required=True, label=_("Name"))
    option = forms.ChoiceField(
        choices=RuleOption.choices(),
        required=True,
        widget=forms.Select(attrs={"required": True}),
        label=_("Option")
    )
    condition = forms.ChoiceField(
        choices=RuleCondition.choices(),
        required=True,
        widget=forms.Select(attrs={"required": True}),
        label=_("Condition")
    )
    value = forms.FloatField(widget=forms.NumberInput(), required=True, label=_("Value"))
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label=_("Description"), required=False)

    class Meta:
        model = YearRule
        fields = [
            "name",
            "option",
            "condition",
            "value",
            "description",
        ]
