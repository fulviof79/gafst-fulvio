from subprocess import PIPE
from unittest.mock import patch, Mock, MagicMock

from django.contrib.auth.models import User, Group, AnonymousUser
from django.core.management import call_command
from django.test import TestCase
from django.utils.datetime_safe import datetime

from core.enums import GroupEnum
from core.models import Member, Club, Membership, MemberChange, MembershipChange
from core.utils import (
    run_command,
    get_years_map,
    get_nationality_acronym_map,
    is_license_no_unique_within_club,
    save_membership,
    is_user_fstb_admin,
    is_user_club_admin,
    get_user_member,
    get_user_club,
)


class RunCommandTests(TestCase):
    @patch("core.utils.Popen")
    def test_run_command(self, MockPopen):
        process_mock = Mock()
        process_mock.communicate.return_value = (b" output", b"")
        process_mock.returncode = 0
        MockPopen.return_value = process_mock

        run_command("echo Hello")

        # Assert that Popen was called
        MockPopen.assert_called_once()

        # Asserts
        process_mock.communicate.assert_called_with(
            b"input data that is passed to subprocess' stdin"
        )
        MockPopen.assert_called_with(
            "echo Hello", shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE
        )

    @patch("subprocess.Popen")
    def test_run_command_failure(self, mock_popen):
        # Mock the Popen instance for a failing command
        mock_process = mock_popen.return_value
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"error data")

        # Call the function and assert the exception
        with self.assertRaises(Exception) as context:
            run_command("mock_command")

        # Asserts
        error_message = str(context.exception)
        self.assertIn("Error running command:", error_message)
        self.assertIn("mock_command", error_message)


class MapGettersTests(TestCase):
    def test_get_years_map(self):
        years_map = get_years_map()
        current_year = datetime.now().year
        self.assertTrue((current_year, str(current_year)) in years_map)

    def test_get_nationality_acronym_map(self):
        acronyms_map = get_nationality_acronym_map()
        self.assertTrue(("US", "US") in acronyms_map)


class ValidatorTests(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group, and the default roles
        call_command("insert_defaults")

        # Create a user that is in the Club Admin group
        self.club_admin_user = User.objects.create_user(
            username="clubAdminUser", password="testpassword"
        )

        # Get the FSTB Admin group
        self.club_admin_group = Group.objects.get(name=GroupEnum.CLUB_ADMIN.value)

        # Add user to the FSTB Admin group
        self.club_admin_user.groups.add(self.club_admin_group)
        self.club_admin_user.save()

        # simulate that a user is logged in
        self.request = Mock()
        self.request.user = self.club_admin_user

    def test_is_license_no_unique_within_club(self):
        self.member_change = Member.objects.create(
            name="Member Change",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
        )

        # Create Club
        self.club_1 = Club.objects.create(
            name="Club 1",
            affiliation_year=2019,
            license_no=1,
        )

        # Create membership (member_change - club_1)
        membership = Membership.objects.create(
            member=self.member_change, club=self.club_1, license_no=1
        )

        result = is_license_no_unique_within_club(Membership, self.club_1, 2)
        self.assertTrue(result)

    def test_member_changed(self):
        # Create 2 clubs
        club_1 = Club.objects.create(
            name="Club 1",
            affiliation_year=2019,
            license_no=1,
        )

        club_2 = Club.objects.create(
            name="Club 2",
            affiliation_year=2019,
            license_no=2,
        )

        original_member = Member.objects.create(
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

        original_membership = Membership.objects.create(
            member=original_member, club=club_1, license_no=1
        )

        # Mock Member
        member_change = MemberChange.objects.create(
            name="John",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            # MemberChange fields
            applicant=self.club_admin_user,
            member=original_member,
        )

        result = is_license_no_unique_within_club(MembershipChange, club_1, 1)
        self.assertTrue(result)


class SaveMembershipTests(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group, and the default roles
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.fstb_admin_user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )

        # Get the FSTB Admin group
        self.fstb_admin_group = Group.objects.get(name=GroupEnum.FSTB_ADMIN.value)

        # Add user to the FSTB Admin group
        self.fstb_admin_user.groups.add(self.fstb_admin_group)
        self.fstb_admin_user.save()

        # simulate that a user is logged in
        self.request = Mock()
        self.request.user = self.fstb_admin_user

    @patch("core.utils.now")
    @patch("core.models.Membership.objects.create")
    @patch.object(Member, "current_membership", new_callable=MagicMock)
    def test_save_new_membership(self, mock_current_membership, mock_create, mock_now):
        # Mock Member
        member = Mock()
        member.current_membership = mock_current_membership.return_value = None

        # Mock Club
        mock_club = Mock()
        mock_club.name = "club"
        mock_club.license_no = 1

        # Call the function
        result = save_membership(self, member, mock_club, 1)

        # Asserts
        self.assertEqual(result, mock_create.return_value)
        mock_create.assert_called_once_with(member=member, club=mock_club, license_no=1)
        mock_now.assert_not_called()

    def test_update_membership(self):
        # Mock Member
        member = Mock()
        member.current_membership = Mock()
        member.current_membership.club = "club"

        # Call the function
        result = save_membership(self, member, "club", 2)

        # Asserts
        self.assertEqual(result, member.current_membership)
        self.assertEqual(member.current_membership.license_no, 2)
        member.current_membership.save.assert_called_once()

    @patch("core.utils.now")
    @patch("core.models.Membership.objects.create")
    def test_transfer_membership(self, mock_create, mock_now):
        # Mock Member
        member = Mock()
        member.current_membership = Mock()
        member.current_membership.club = "old_club"

        # Call the function
        result = save_membership(self, member, "new_club", 3)

        # Asserts
        self.assertEqual(result, mock_create.return_value)
        mock_now.assert_called_once_with()
        member.current_membership.save.assert_called_once_with()
        mock_create.assert_called_once_with(
            member=member, club="new_club", license_no=3
        )


class SaveMembershipClubAdminTests(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group, and the default roles
        call_command("insert_defaults")

        # Create a user that is in the Club Admin group
        self.club_admin_user = User.objects.create_user(
            username="clubAdminUser", password="testpassword"
        )

        # Get the FSTB Admin group
        self.club_admin_group = Group.objects.get(name=GroupEnum.CLUB_ADMIN.value)

        # Add user to the FSTB Admin group
        self.club_admin_user.groups.add(self.club_admin_group)
        self.club_admin_user.save()

        # simulate that a user is logged in
        self.request = Mock()
        self.request.user = self.club_admin_user

        self.member_change = MemberChange.objects.create(
            name="Member Change",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.club_admin_user,
        )

        # Create Club
        self.club_1 = Club.objects.create(
            name="Club 1",
            affiliation_year=2019,
            license_no=1,
        )

    def test_save_new_membership_and_member(self):
        # Call the function
        result = save_membership(self, self.member_change, self.club_1, 1)

        # Asserts
        self.assertEqual(result, self.member_change.current_membership)
        self.assertEqual(self.member_change.current_membership.license_no, 1)

        # Check that the member was created
        self.assertEqual(MemberChange.objects.count(), 1)

        # Check that the membership was created
        self.assertEqual(MembershipChange.objects.count(), 1)

    def test_update_membership(self):
        original_member = Member.objects.create(
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

        original_membership = Membership.objects.create(
            member=original_member, club=self.club_1, license_no=1
        )

        # Mock Member
        member_change = MemberChange.objects.create(
            name="John",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            # MemberChange fields
            applicant=self.club_admin_user,
            member=original_member,
        )

        # Call the function
        result = save_membership(self, member_change, self.club_1, 2)

        # Check that the member was created
        self.assertEqual(MemberChange.objects.count(), 2)
        self.assertTrue(MemberChange.objects.filter(member=original_member).exists())

        # Check that the membership was created
        self.assertEqual(MembershipChange.objects.count(), 1)

    def test_transfer_member(self):
        original_member = Member.objects.create(
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

        original_membership = Membership.objects.create(
            member=original_member, club=self.club_1, license_no=1
        )

        # Mock Member
        member_change = MemberChange.objects.create(
            name="John",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            # MemberChange fields
            applicant=self.club_admin_user,
            member=original_member,
        )

        # Create MembershipChange
        membership_change = MembershipChange.objects.create(
            member=member_change,
            club=self.club_1,
            license_no=1,
            membership=original_membership,
            applicant=self.club_admin_user,
        )

        # Create second club
        club_2 = Club.objects.create(
            name="Club 2",
            affiliation_year=2019,
            license_no=2,
        )

        # Call the function
        result = save_membership(self, member_change, club_2, 1)

        # Check that the member was created
        self.assertEqual(MemberChange.objects.count(), 3)
        self.assertTrue(MemberChange.objects.filter(member=original_member).exists())

        # Check that the membership was created
        self.assertEqual(MembershipChange.objects.count(), 2)
        self.assertTrue(
            MemberChange.objects.filter(member__membership__club=self.club_1).exists()
        )
        self.assertTrue(MembershipChange.objects.filter(club=club_2).exists())
        self.assertEqual(result, MembershipChange.objects.filter(club=club_2).first())


# ----- test getters -----------------------------------------------------------
class IsUserFstbAdminTests(TestCase):
    def test_is_user_fstb_admin(self):
        user = User.objects.create_user(username="user", password="12345")
        user.groups.add(Group.objects.create(name=GroupEnum.FSTB_ADMIN.value))

        # login with a user that is Club Admin
        self.logged_in = self.client.login(username="user", password="12345")

        result = is_user_fstb_admin(user)
        self.assertTrue(result)

    def test_anonymous_user(self):
        anonymous_user = AnonymousUser()
        result = is_user_fstb_admin(anonymous_user)
        self.assertFalse(result)

    def test_null_user(self):
        result = is_user_fstb_admin(None)
        self.assertFalse(result)


class IsUserClubAdminTests(TestCase):
    def test_is_user_fstb_admin(self):
        user = User.objects.create_user(username="user", password="12345")
        user.groups.add(Group.objects.create(name=GroupEnum.CLUB_ADMIN.value))

        # login with a user that is Club Admin
        self.logged_in = self.client.login(username="user", password="12345")

        result = is_user_club_admin(user)
        self.assertTrue(result)

    def test_anonymous_user(self):
        anonymous_user = AnonymousUser()
        result = is_user_fstb_admin(anonymous_user)
        self.assertFalse(result)

    def test_null_user(self):
        result = is_user_fstb_admin(None)
        self.assertFalse(result)


class TestClubAdminGetters(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group, and the default roles
        call_command("insert_defaults")

        # Create a user that is in the Club Admin group
        self.club_admin_user = User.objects.create_user(
            username="clubAdminUser", password="testpassword"
        )

        # Get the Club Admin group
        self.club_admin_group = Group.objects.get(name=GroupEnum.CLUB_ADMIN.value)

        # Add user to the Club Admin group
        self.club_admin_user.groups.add(self.club_admin_group)
        self.club_admin_user.save()

        # Create member with user association
        self.member_with_user = Member.objects.create(
            name="member_with_user",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            user=self.club_admin_user,
        )

        # Create a club
        self.club = Club.objects.create(
            name="Club of the user",
            affiliation_year=2019,
            license_no=1,
        )

        # Create membership (member_with_user - club)
        Membership.objects.create(
            member=self.member_with_user, club=self.club, license_no=1
        )

    def test_get_user_member(self):
        # login with a user that is Club Admin
        self.logged_in = self.client.login(
            username="clubAdminUser", password="testpassword"
        )

        result = get_user_member(self.club_admin_user)
        self.assertEqual(self.member_with_user, result)

    def test_get_user_club(self):
        # login with a user that is Club Admin
        self.logged_in = self.client.login(
            username="clubAdminUser", password="testpassword"
        )

        result = get_user_club(self.club_admin_user)
        self.assertEqual(self.club, result)

    def test_anonymous_user(self):
        anonymous_user = AnonymousUser()

        member = get_user_member(anonymous_user)
        self.assertEqual(None, member)

        club = get_user_club(anonymous_user)
        self.assertEqual(None, club)

    def test_user_not_club_admin(self):
        user = User.objects.create_user(username="user", password="12345")
        user.groups.add(Group.objects.filter(name=GroupEnum.FSTB_ADMIN.value).first())

        member = get_user_member(user)
        self.assertEqual(None, member)

        club = get_user_club(user)
        self.assertEqual(None, club)

    def test_null_user(self):
        member = get_user_member(None)
        self.assertEqual(None, member)

        club = get_user_club(None)
        self.assertEqual(None, club)
