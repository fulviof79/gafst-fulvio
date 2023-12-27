from datetime import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from django.contrib.auth.models import User
from django.utils.datetime_safe import date

from core.enums import RoleEnum
from core.models import (
    Member,
    Membership,
    Role,
    Club,
    Exam,
    JS,
    get_remaining_memberships_by_club, Team, Competition,
)


# ---- general tests ----------------------------------------------------------
def test_no_user():
    member = Member(
        name="John",
        surname="Doe",
        house_number="123",
        street="Test Street",
        city="Test City",
        zip_code="12345",
        date_of_birth="1990-01-01",
        nationality="USA",
        affiliation_year=2023,
    )
    # If validation passes, the test will pass
    member.full_clean()


# ---- Test Member Model -----------------------------------------------------
class MemberModelTest(TestCase):
    def setUp(self):
        # Create a User instance
        self.user = User.objects.create(username="testuser", password="12345")

        # Create Role instance
        self.role = Role.objects.create(name="Test Role")

    def test_max_length(self):
        member = Member(
            name="a" * 150,
            surname="b" * 150,
            house_number="c" * 50,
            street="d" * 100,
            city="e" * 100,
            zip_code="f" * 20,
            date_of_birth=date.today().replace(year=date.today().year - 200),
            nationality="CH",
            affiliation_year=2023,
        )
        # If validation passes, the test will pass
        member.full_clean()

    def test_min_length(self):
        member = Member(
            name="a",
            surname="a",
            house_number="a",
            street="a",
            city="a",
            zip_code="a",
            date_of_birth=date.today().replace(year=date.today().year - 2),
            nationality="a",
            affiliation_year=2023,
        )
        # If validation passes, the test will pass
        member.full_clean()

    def test_max_affiliation_year(self):
        member = Member(
            name="John",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=date.today().year,  # Assume this is our maximum year
        )
        # If validation passes, the test will pass
        member.full_clean()

    def test_no_role(self):
        member = Member.objects.create(
            name="John",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2023,
        )
        self.assertEqual(member.roles.count(), 0)

    def test_max_roles(self):
        member = Member.objects.create(
            name="John",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2023,
        )
        roles = [
            Role.objects.create(name=f"Role {i}") for i in range(1000)
        ]  # Assume 1000 is max roles
        member.roles.set(roles)
        self.assertEqual(member.roles.count(), 1000)


class MemberModelPropertyTest(TestCase):
    def setUp(self):
        # Create a User instance
        self.user = User.objects.create(username="testuser", password="12345")

        # Create two Member instances, one with a membership and one without
        self.member_with_membership = Member.objects.create(
            name="John",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
        )
        self.member_with_membership.roles.set(
            Role.objects.filter(name=RoleEnum.ATHLETE.value)
        )

        self.club = Club.objects.create(
            name="Test Club",
            affiliation_year=2020,
            license_no=1,
        )

        self.membership = Membership.objects.create(
            member=self.member_with_membership,
            club=self.club,
            license_no=1,
        )

        # Member without membership
        self.member_without_membership = Member.objects.create(
            name="Jane",
            surname="Doe",
            house_number="456",
            street="Another Street",
            city="Another City",
            zip_code="67890",
            date_of_birth="1991-02-02",
            nationality="US",
            affiliation_year=2021,
        )
        self.member_without_membership.roles.set(
            Role.objects.filter(name=RoleEnum.ATHLETE.value)
        )

        # Create a Member instances, that will be transferred to a new club
        self.member_to_transfer = Member.objects.create(
            name="Jhonny",
            surname="Stanga",
            house_number="456",
            street="Another Street",
            city="Another City",
            zip_code="67890",
            date_of_birth="1991-02-02",
            nationality="US",
            affiliation_year=2021,
        )

        # The member will be transferred to this club
        self.club2 = Club.objects.create(
            name="Test Club 2",
            affiliation_year=2020,
            license_no=2,
        )

        # Create a Membership instance
        self.membership_transferred = Membership.objects.create(
            member=self.member_to_transfer,
            club=self.club,
            transfer_date="2021-01-01",
            license_no=2,
        )

        self.new_membership = Membership.objects.create(
            member=self.member_to_transfer,
            club=self.club2,
            license_no=1,
        )

    def test_has_club_membership(self):
        # Test that has_club_membership returns True for a member with a membership
        self.assertTrue(self.member_with_membership.has_club_membership)

        # Test that has_club_membership returns False for a member without a membership
        self.assertFalse(self.member_without_membership.has_club_membership)

        # Test that has_club_membership returns True for a member that is transferred to a new club
        self.assertTrue(self.member_to_transfer.has_club_membership)

    def test_current_membership(self):
        # Test that current_membership returns the current membership for a member with a membership
        self.assertEqual(
            self.member_with_membership.current_membership,
            self.membership,
        )

        # Test that current_membership returns None for a member without a membership
        self.assertIsNone(self.member_without_membership.current_membership)

        # Test that current_membership returns the current membership for a member that is transferred to a new club
        self.assertEqual(
            self.member_to_transfer.current_membership,
            self.new_membership,
        )


# ---- Test Club Model ----------------------------------------------------------------
class ClubModelTest(TestCase):
    def setUp(self):
        self.club1 = Club.objects.create(
            name="Club 1", affiliation_year=2020, license_no=1
        )

        self.club2 = Club.objects.create(
            name="Club 2", affiliation_year=2021, license_no=2
        )

        self.member = Member.objects.create(
            name="John",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2023,
        )

        self.membership = Membership.objects.create(
            member=self.member,
            club=self.club1,
            license_no=1,
        )

    def test_fields(self):
        self.assertEqual(self.club1.name, "Club 1")
        self.assertEqual(self.club1.affiliation_year, 2020)
        self.assertEqual(self.club1.license_no, 1)

    def test_str(self):
        self.assertEqual(str(self.club1), "Club 1")

    def test_full_license_no_property(self):
        self.assertEqual(self.club1.full_license_no, "01-000")

    def test_classmethod_remaining_license_no(self):
        remaining_license_nos = Club.remaining_license_no()
        self.assertTrue(
            (3, "03-000") in remaining_license_nos
        )  # Assuming 3 is not already used.
        self.assertFalse(
            (1, "01-000") in remaining_license_nos
        )  # As club1's license_no is 1

        # test edge case
        self.assertTrue((99, "99-000") in remaining_license_nos)


# ---- Test Membership Model ----------------------------------------------------------
class MembershipModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up non-modified objects used by all test methods
        cls.member = Member.objects.create(
            name="John",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2023,
        )  # assuming these fields exist in Member
        cls.club = Club.objects.create(
            name="Test Club",
            affiliation_year=2020,
            license_no=1,
        )  # assuming these fields exist in Club

        cls.membership = Membership.objects.create(
            member=Member.objects.all().first(),
            club=Club.objects.all().first(),
            license_no=1,
        )

    def test_full_license_no(self):
        self.assertEquals(self.membership.full_license_no, "01-001")

    def test_str(self):
        self.assertEquals(str(self.membership), "John Doe - Test Club")

    def test_license_no_unique_validator(self):
        with self.assertRaises(ValidationError):
            membership2 = Membership.objects.create(
                member=self.member,
                club=self.club,
                license_no=1,
            )

    def test_remaining_license_no(self):
        # assuming we've created a few Membership instances already
        remaining = Membership.remaining_license_no()
        self.assertIsInstance(remaining, list)  # checks if it's a list
        self.assertNotIn(
            1, [tup[0] for tup in remaining]
        )  # checks if 1 (used license_no) is not in the list


# ---- Test Role Model ----------------------------------------------------------
class RoleModelTest(TestCase):
    def test_str(self):
        role = Role.objects.create(name="Test Role")
        self.assertEquals(str(role), "Test Role")


# ---- Test JS Model -----------------------------------------------------------
class JSModelTest(TestCase):
    def test_str(self):
        js = JS.objects.create(name="Test js")
        self.assertEquals(str(js), "Test js")


# ---- Test Exam Model -----------------------------------------------------------
class ExamModelTest(TestCase):
    def test_str(self):
        exam = Exam.objects.create(name="Test exam")
        self.assertEquals(str(exam), "Test exam")


# ---- functions ----------------------------------------------------------------
class FunctionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        member = Member.objects.create(
            name="John",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2023,
        )
        club = Club.objects.create(
            name="Test Club",
            affiliation_year=2020,
            license_no=1,
        )
        Membership.objects.create(member=member, club=club, license_no=1)

    def test_get_remaining_memberships_by_club(self):
        club = Club.objects.all().first()
        remaining = get_remaining_memberships_by_club(club)
        self.assertIsInstance(remaining, list)
        self.assertNotIn(1, [tup[0] for tup in remaining])


# ---- Test Team Model ----------------------------------------------------------
class TeamModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up non-modified objects used by all test methods
        club = Club.objects.create(
            name="new club",
            affiliation_year=2023,
            license_no=1
        )

        cls.club = club

        # Create a sample team to be deleted in the test
        cls.team = Team.objects.create(
            name="new team",
            description="test",
            min_members_number=1,
            club=club,
            min_members_number_not_reached=True
        )

    def test_str(self):
        self.assertEquals(str(self.team), "new team")


# ---- Test Competition Model ----------------------------------------------------------
class CompetitionModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up non-modified objects used by all test methods
        competition = Competition.objects.create(
            name="new competition",
            due_date=datetime.today(),
            description="test",
            status="Open"
        )

        cls.competition = competition

    def test_str(self):
        self.assertEquals(str(self.competition), "new competition")
