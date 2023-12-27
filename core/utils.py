# ----- generic imports ---------------------------------------------------------
from datetime import datetime
from unittest.mock import Mock

import pycountry
from subprocess import Popen, PIPE

# ----- Django Imports --------------------------------------------------------
from django.utils.timezone import now

# ----- Core Imports ----------------------------------------------------------
from .enums import GroupEnum, ChangeModelStatus, RuleCondition


# ---- Commands ---------------------------------------------------------------
def run_command(command):
    process = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)

    output, err = process.communicate(b"input data that is passed to subprocess' stdin")

    print(output.decode("utf-8") + "\n")

    if process.returncode != 0:
        error_decoded = err.decode("utf-8")
        raise Exception(f"Error running command: {command}\n{error_decoded}")


# ---- Maps Getters -----------------------------------------------------------
def get_years_map():
    current_year = datetime.now().year
    years_list = list(range(current_year, 1960, -1))
    # make compatible with protocol "_FieldChoices"
    years_list = [(year, f"{str(year)}") for year in years_list]
    return years_list


def get_nationality_acronym_map():
    nationalities = [
        (country.alpha_2, country.alpha_2) for country in pycountry.countries
    ]
    return nationalities


# ---- Validators -------------------------------------------------------------
def is_license_no_unique_within_club(membership, club, license_no, excluded_ids=None):
    from core.models import MEMBERSHIP_MODEL_NAME

    if excluded_ids is None:
        excluded_ids = []

    if membership == MEMBERSHIP_MODEL_NAME:
        return not (
            club.membership_set.filter(
                club=club, transfer_date__isnull=True, license_no=license_no
            )
            .exclude(id__in=excluded_ids)
            .exists()
        )
    else:
        return True


# ---- Getters -------------------------------------------------------------
def is_user_fstb_admin(user):
    if not user or not user.is_authenticated:
        return False

    return user.groups.filter(name=GroupEnum.FSTB_ADMIN.value).exists()


def is_user_club_admin(user):
    if not user or not user.is_authenticated:
        return False

    return user.groups.filter(name=GroupEnum.CLUB_ADMIN.value).exists()


def get_user_member(user):
    if not user or not user.is_authenticated:
        return None

    from core.models import Member

    return Member.objects.filter(user=user).first()


def get_user_club(user):
    if not user or not user.is_authenticated or not is_user_club_admin(user):
        return None

    from core.models import Club

    return Club.objects.filter(membership__member__user=user).first()


def get_team_club(user):
    if not user or not user.is_authenticated or not is_user_club_admin(user):
        return None

    from core.models import Club
    from .models import Team

    club = Club.objects.filter(membership__member__user=user).first()

    return Team.objects.filter(club=club).all()


# ---- Create/Update Models ---------------------------------------------------
def create_member_change(member, applicant):
    from core.models import MemberChange

    member_change = MemberChange.objects.create(
        photo=member.photo,
        name=member.name,
        surname=member.surname,
        house_number=member.house_number,
        street=member.street,
        city=member.city,
        zip_code=member.zip_code,
        date_of_birth=member.date_of_birth,
        nationality=member.nationality,
        affiliation_year=member.affiliation_year,
        member=member.member,
        applicant=applicant,
    )

    member_change.roles.set(member.roles.all())
    member_change.exams.set(member.exams.all())
    member_change.js.set(member.js.all())

    return member_change


def save_membership(self, member, new_club, new_license_no):
    from core.models import Membership, MembershipChange, Member

    is_fstb_admin_logged = is_user_fstb_admin(self.request.user)
    current_membership = (
        member.current_membership
        if isinstance(member, Member) or not member.member or isinstance(member, Mock)
        else member.member.current_membership
    )

    if not current_membership:  # create new membership
        if is_fstb_admin_logged:
            return Membership.objects.create(
                member=member, club=new_club, license_no=new_license_no
            )
        else:
            return MembershipChange.objects.create(
                member=member,
                club=new_club,
                license_no=new_license_no,
                # Change model fields
                applicant=self.request.user,
            )

    elif current_membership.club == new_club:  # update membership
        if is_fstb_admin_logged:
            current_membership.license_no = new_license_no
            current_membership.save()
            return current_membership
        else:
            return MembershipChange.objects.create(
                member=member,
                club=current_membership.club,
                license_no=new_license_no,
                # Change model fields
                membership=current_membership,
                applicant=self.request.user,
            )

    elif current_membership.club != new_club:  # transfer membership
        if is_fstb_admin_logged:
            current_membership.transfer_date = now()
            current_membership.save()

            return Membership.objects.create(
                member=member, club=new_club, license_no=new_license_no
            )
        else:
            current_membership.transfer_date = now()
            current_membership.applicant = self.request.user
            current_membership.save()

            new_member_change = create_member_change(member, self.request.user)

            return MembershipChange.objects.create(
                member=new_member_change,
                club=new_club,
                license_no=new_license_no,
                # Change model fields
                applicant=self.request.user,
            )


def create_member(member_change):
    from core.models import Member

    member = Member.objects.create(
        photo=member_change.photo,
        name=member_change.name,
        surname=member_change.surname,
        house_number=member_change.house_number,
        street=member_change.street,
        city=member_change.city,
        zip_code=member_change.zip_code,
        date_of_birth=member_change.date_of_birth,
        nationality=member_change.nationality,
        affiliation_year=member_change.affiliation_year,
    )

    member.roles.set(member_change.roles.all())
    member.exams.set(member_change.exams.all())
    member.js.set(member_change.js.all())

    return member


def update_member(member, member_change):
    member.photo = member_change.photo
    member.name = member_change.name
    member.surname = member_change.surname
    member.house_number = member_change.house_number
    member.street = member_change.street
    member.city = member_change.city
    member.zip_code = member_change.zip_code
    member.date_of_birth = member_change.date_of_birth
    member.nationality = member_change.nationality
    member.affiliation_year = member_change.affiliation_year
    member.save()

    member.roles.set(member_change.roles.all())
    member.exams.set(member_change.exams.all())
    member.js.set(member_change.js.all())


def create_membership(membership_change, related_member):
    from core.models import Membership

    return Membership.objects.create(
        member=related_member,
        club=membership_change.club,
        license_no=membership_change.license_no,
        transfer_date=membership_change.transfer_date,
    )


def update_membership(membership, membership_change):
    membership.club = membership_change.club

    if not membership.license_no == membership_change.license_no:
        membership.license_no = membership_change.license_no

    membership.transfer_date = membership_change.transfer_date
    membership.save()


def approve_membership_changes(membership_change, related_member):
    if membership_change.membership:
        update_membership(membership_change.membership, membership_change)

    else:
        create_membership(membership_change, related_member)


def get_all_member_changes_pending_created_before_member_change(member_change):
    from core.models import MemberChange

    return MemberChange.objects.filter(
        member=member_change.member,
        status=ChangeModelStatus.PENDING.value,
        created_at__lte=member_change.created_at,
    )


def approve_member_changes(member_change):
    current_membership_change = None
    related_member = None

    # -- Manage member_changes ---------------------------------------------
    if member_change.member:
        update_member(member_change.member, member_change)
        current_membership_change = member_change.membership_change
        related_member = member_change.member

    else:
        new_member = create_member(member_change)
        current_membership_change = member_change.membership_change
        related_member = new_member

    # -- Manage membership_changes -----------------------------------------
    if current_membership_change:
        approve_membership_changes(current_membership_change, related_member)

    member_changes = get_all_member_changes_pending_created_before_member_change(
        member_change
    )

    for member_change in member_changes:
        member_change.status = ChangeModelStatus.APPROVED.value
        member_change.save()

        member_change.current_membership.status = ChangeModelStatus.APPROVED.value
        member_change.current_membership.save()


def decline_member_changes(member_change):
    member_changes = get_all_member_changes_pending_created_before_member_change(
        member_change
    )

    for member_change in member_changes:
        member_change.status = ChangeModelStatus.DECLINED.value
        member_change.save()

        member_change.current_membership.status = ChangeModelStatus.DECLINED.value
        member_change.current_membership.save()


# -------- Registration rules --------------
def check_min_member(min_members, members):
    return min_members > len(members)


def check_max_member(max_members, members):
    return max_members < len(members)


def check_ages(year_rules, members):
    errors = []
    ages = []

    for member in members:
        current_age = calculate_age(member.date_of_birth)
        ages.append(current_age)
        for rule in year_rules:

            if rule.condition == RuleCondition.EQUAL.value:
                if current_age != rule.value:
                    errors.append((member.name, " age is not equal to ", rule.value))

            if rule.condition == RuleCondition.GREATER.value:
                if current_age <= rule.value:
                    errors.append((member.name, " age is not greater than ", rule.value))

            if rule.condition == RuleCondition.LESS_THAN.value:
                if current_age >= rule.value:
                    errors.append((member.name, " age is not less than ", rule.value))

            if rule.condition == RuleCondition.GREATER_OR_EQUAL.value:
                if current_age < rule.value:
                    errors.append((member.name, " age is not greate or equal to ", rule.value))

            if rule.condition == RuleCondition.LESS_THAN_OR_EQUAL.value:
                if current_age > rule.value:
                    errors.append((member.name, " age is not less than or equal to ", rule.value))

            if rule.condition == RuleCondition.NOT_EQUAL.value:
                if current_age == rule.value:
                    errors.append((member.name, " age is not different to ", rule.value))
    return errors

def calculate_age(date_of_birth):
    today_date = datetime.now()

    actual_age = today_date.year - date_of_birth.year

    # Controlla se il compleanno è già passato quest'anno
    if today_date.month < date_of_birth.month or (
            today_date.month == date_of_birth.month and today_date.day < date_of_birth.day):
        actual_age -= 1  # Sottrai un anno se il compleanno non è ancora passato

    print("Hai", actual_age, "anni")
    return actual_age
