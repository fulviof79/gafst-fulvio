import json
from datetime import datetime

from django.contrib.auth.models import User, AnonymousUser, Group
from django.core.management import call_command
from django.http import HttpResponse
from django.test import TestCase, RequestFactory
from unittest.mock import Mock, patch, MagicMock
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from core.constants import DELETED_MESSAGE, UPDATED_MESSAGE
from core.enums import RoleEnum, GroupEnum, ChangeModelStatus
from core.forms import (
    MemberMembershipForm,
    ON_CREATING_MEMBER_WITH_CLUB_MEMBERSHIP__USER_GROUP_NOT_SELECTED_ERROR,
    ON_CREATING_MEMBER_WITH_CLUB_ADMIN_USER__USER_NOT_SELECTED_ERROR,
    ON_CREATING_MEMBER_WITH_CLUB_ADMIN_USER__CLUB_NOT_SELECTED_ERROR, CompetitionForm,
)
from core.models import Club, Member, Membership, Role, MemberChange, MembershipChange, Team, Competition
from core.views import (
    CardTemplateView,
    get_success_response,
    ADDED_MESSAGE,
    SHOW_MESSAGE,
    DatatableListView,
    DatatableCreateView,
    DatatableDeleteView,
    DatatableUpdateView,
    HomeView,
    MemberListView,
)


# ----- Test Utils -------------------------------------------------------------
class TestGetSuccessResponse(TestCase):
    def setUp(self):
        self.view = Mock(model=Mock(__name__="Member"))
        self.instance = Mock(__str__=Mock(return_value="Gina Doe"))
        self.message_format = ADDED_MESSAGE

    def test_get_success_response(self):
        expected_changed_event = "memberListChanged"
        expected_message = "Gina Doe added"

        response = get_success_response(self.view, self.instance, self.message_format)

        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 204)

        response_headers = json.loads(response["HX-Trigger"])
        self.assertEqual(None, response_headers[expected_changed_event])
        self.assertEqual(expected_message, response_headers[SHOW_MESSAGE])


# ----- Test Generic Views --------------------------------------------------
class TestCardTemplateView(TestCase):
    def setUp(self):
        self.view = CardTemplateView()

        # set language to english
        self.view.request = Mock(LANGUAGE_CODE="en")

    def test_get_context_data(self):
        # Mock the view attributes
        self.view.model = Mock(
            __name__="Member", _meta=Mock(verbose_name_plural="Members")
        )
        self.view.card_title = "Members"

        context_data = self.view.get_context_data()

        self.assertIn("list_changed_event", context_data)
        self.assertIn("card_title", context_data)
        self.assertIn("card_body_url", context_data)

        self.assertEqual(context_data["card_title"], _("Members"))
        self.assertEqual(
            context_data["card_body_url"],
            "/en/members/",
        )
        self.assertEqual(
            context_data["list_changed_event"],
            "memberListChanged",
        )

    def test_get_context_data_missing_attributes(self):
        with self.assertRaises(ImproperlyConfigured):
            self.view.get_context_data()


class TestDatatableListView(TestCase):
    def setUp(self):
        self.view = DatatableListView()

        # Every test needs access to the request factory.
        self.factory = RequestFactory()

        # Create an instance of a GET request.
        self.request = self.factory.get("members/")

        # Set the request on the view.
        self.view.request = self.request

    def test_get_context_data_with_model(self):
        # Mock the view attributes
        self.view.model = Mock(__name__="Member")

        # Get context_data data
        self.view.get(self.request)
        context_data = self.view.get_context_data()

        # Asserts
        self.assertIn("table_id", context_data)
        self.assertIn("table_item_remove_url", context_data)
        self.assertIn("table_item_edit_url", context_data)
        self.assertIn("table_item_add_url", context_data)

        self.assertEqual(context_data["table_id"], "member_list")
        self.assertEqual(
            context_data["table_item_remove_url"],
            "remove_member",
        )
        self.assertEqual(
            context_data["table_item_edit_url"],
            "edit_member",
        )
        self.assertEqual(
            context_data["table_item_add_url"],
            "add_member",
        )

    def test_get_context_data_without_model(self):
        with self.assertRaises(ImproperlyConfigured):
            self.view.get_context_data()


class DatatableCreateViewTest(TestCase):
    def setUp(self):
        self.view = DatatableCreateView()

        # Every test needs access to the request factory.
        self.factory = RequestFactory()

    @patch("core.views.get_success_response", return_value=HttpResponse(status=204))
    @patch("core.forms.MemberForm")
    def test_form_valid(self, MemberFormMock, get_success_response_mock):
        # Create an instance of a Post request.
        self.request = self.factory.post("members/create/")
        self.view.request = self.request

        # Mock the view attributes
        self.view.model = Mock(__name__="Member")
        self.view.modal_title = "Add Member"

        # Call form_valid
        response = self.view.form_valid(MemberFormMock)

        # Asserts
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 204)

        MemberFormMock.save.assert_called_once_with()
        get_success_response_mock.is_called_once_with(
            self.view, MemberFormMock, ADDED_MESSAGE
        )

    @patch("core.forms.MemberForm")
    def test_get_context_data(self, MemberFormMock):
        # Create request
        self.request = self.factory.get("members/create/")
        self.view.request = self.request

        # Mock the view attributes
        self.view.model = Mock(__name__="Member")
        self.view.modal_title = "Add Member"
        self.view.form_class = MemberFormMock
        self.view.template_name = "datatable/member_create_form.html"

        # Get context_data data
        self.view.get(self.request)
        context_data = self.view.get_context_data()

        # Asserts
        self.assertIn("modal_title", context_data)

        self.assertEqual(context_data["modal_title"], "Add Member")


class TestDatatableDeleteView(TestCase):
    def setUp(self):
        self.view = DatatableDeleteView()
        self.factory = RequestFactory()

    @patch("core.views.get_object_or_404")
    @patch("core.views.get_success_response", return_value=HttpResponse(status=204))
    def test_valid_delete(self, mock_get_success_response, mock_get_object_or_404):
        mock_instance = Mock()
        mock_instance.delete = Mock()
        mock_get_object_or_404.return_value = mock_instance

        # Mock the model and its `objects.all()` method.
        mock_model = MagicMock()
        self.view.model = mock_model

        request = self.factory.post(
            "/fake-delete/"
        )  # URL doesn't matter here due to the mocks.
        response = self.view.post(request, pk=1)

        # Asserts
        mock_get_object_or_404.assert_called_once_with(mock_model.objects.all(), pk=1)
        mock_instance.delete.assert_called_once()
        mock_get_success_response.assert_called_once_with(
            self.view, mock_instance, DELETED_MESSAGE
        )

        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 204)

    def test_without_model(self):
        request = self.factory.post("/fake-delete/")

        with self.assertRaises(ImproperlyConfigured) as context:
            self.view.post(request, pk=1)

        self.assertIn(
            _("DataTableDeleteView requires a model attribute to be set."),
            str(context.exception),
        )


class TestDatatableUpdateView(TestCase):
    def setUp(self):
        self.view = DatatableUpdateView()
        self.factory = RequestFactory()

    @patch("core.views.get_success_response", return_value=HttpResponse())
    def test_form_valid(self, mock_get_success_response):
        mock_form = MagicMock()
        mock_instance = Mock()
        mock_form.save.return_value = mock_instance

        response = self.view.form_valid(mock_form)

        mock_form.save.assert_called_once()
        mock_get_success_response.assert_called_once_with(
            self.view, mock_instance, UPDATED_MESSAGE
        )
        self.assertEqual(response.status_code, 200)

    @patch("core.views.get_object_or_404")
    def test_get_object(self, mock_get_object_or_404):
        mock_instance = Mock()
        mock_get_object_or_404.return_value = mock_instance

        self.view.kwargs = {"pk": 1}

        result = self.view.get_object()

        mock_get_object_or_404.assert_called_once_with(self.view.model, pk=1)
        self.assertEqual(result, mock_instance)

    @patch("core.views.UpdateView.get_context_data")
    def test_get_context_data(self, super_get_context_data):
        mock_context = {}
        super_get_context_data.return_value = mock_context

        self.view.modal_title = "Update Member"

        result_context = self.view.get_context_data()

        super_get_context_data.assert_called_once()
        self.assertIn("modal_title", result_context)
        self.assertEqual(result_context["modal_title"], _("Update Member"))


# ----- Test Views -------------------------------------------------------------
class TestHomeView(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Every test needs access to the request factory.
        self.factory = RequestFactory()

        # User used for authentication
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )

    def test_details(self):
        # Create an instance of a GET request.
        request = self.factory.get("")

        # Recall that middleware are not supported. You can simulate a
        # logged-in user by setting request.user manually.
        request.user = self.user

        # Test this view as if it were deployed at ""
        response = HomeView.as_view()(request)

        self.assertEqual(response.status_code, 200)

    def test_anonymous_user(self):
        # Create an instance of a GET request.
        request = self.factory.get("")

        # Simulate an anonymous user by setting request.user to AnonymousUser
        request.user = AnonymousUser()

        # Test this view as if it were deployed at ""
        response = HomeView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/accounts/login/?next=/")

    def test_authorized_user_without_club_admin_permissions(self):
        # login with a user that is not in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get("", follow=True)

        # The view show the template, but also includes a message
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "At this time you have not been added to administration or club administration",
            str(response.content),
        )

    def test_authorized_user_with_club_admin_permissions(self):
        # Add the user to the Club Admin group, and assigned to the request
        self.user.groups.add(Group.objects.get(name=GroupEnum.CLUB_ADMIN.value))
        self.user.save()

        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get("", follow=True)

        # The view show the template, but also includes a message
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            "At this time you have not been added to administration or club administration",
            str(response.content),
        )


# ----- Test Member Views ------------------------------------------------------
class TestMemberListView(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )

        # Prepare data
        self.club_1 = Club.objects.create(
            name="Club1",
            affiliation_year=2019,
            license_no=1,
        )
        self.club_2 = Club.objects.create(
            name="Club2",
            affiliation_year=2020,
            license_no=2,
        )

        self.member_1 = Member.objects.create(
            name="Member1",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2019,
        )
        self.member_2 = Member.objects.create(
            name="Member2",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
        )

        self.membership_1 = Membership.objects.create(
            member=self.member_1, club=self.club_1, license_no=1
        )
        self.membership_2 = Membership.objects.create(
            member=self.member_2, club=self.club_2, license_no=2
        )

        # Url used for the get request
        self.url = reverse("members")

    def test_member_list_view_renders_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        # Check that the correct template was used
        self.assertTemplateUsed(response, "datatable/member.html")

    def test_member_list_view_returns_all_members(self):
        # login with a user that is in the FSTB Admin group
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)
        members_in_context = response.context["object_list"]

        # make sure that 2 members are returned
        self.assertEqual(len(members_in_context), 2)

        # make sure that the members are in the response
        self.assertIn(self.member_1, members_in_context)
        self.assertIn(self.member_2, members_in_context)

    def test_member_list_for_club_admin(self):
        # add logged user tp member1
        self.member_1.user = self.user
        self.member_1.save()

        # login with a user that is in the Club Admin group
        self.user.groups.add(Group.objects.get(name=GroupEnum.CLUB_ADMIN.value))
        self.user.save()
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        # create transfer membership of club1
        Membership.objects.create(
            member=self.member_1, club=self.club_1, license_no=10, transfer_date=now()
        )

        response = self.client.get(self.url)
        members_in_context = response.context["object_list"]

        # make sure that 1 member is returned
        self.assertEqual(len(members_in_context), 1)

        # make sure that the member1 is in the response
        self.assertIn(self.member_1, members_in_context)


class MemberCreateViewTest(TestCase):
    def setUp(self):
        # Url for requests
        self.url = reverse("add_member")

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

        # login with a user that is FSTB Admin
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        # Create a club
        self.club = Club.objects.create(
            name="Club1",
            affiliation_year=2019,
            license_no=1,
        )

    def test_member_create_view_reachable(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_member_create_with_valid_data(self):
        data = {
            "name": "John",
            "surname": "Doe",
            "house_number": "123",
            "street": "Test Street",
            "city": "Test City",
            "zip_code": "12345",
            "date_of_birth": "2000-01-01",
            "nationality": "US",
            "affiliation_year": 2020,
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            "exams": [],
            "js": [],
            "club_select": self.club.id,
            "license_no": 1,
        }
        response = self.client.post(self.url, data)

        # Assuming a redirect after a successful creation
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Member.objects.filter(name="John").exists())

    def test_member_create_with_invalid_data(self):
        data = {
            # Name is intentionally missing
            "surname": "Doe",
            "house_number": "123",
            "street": "Test Street",
            "city": "Test City",
            "zip_code": "12345",
            "date_of_birth": "2000-01-01",
            "nationality": "US",
            "affiliation_year": 2020,
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            "exams": [],
            "js": [],
            "club_select": self.club.id,
            "license_no": 1,
        }
        response = self.client.post(self.url, data)

        # verify that the form is not valid
        self.assertEqual(response.status_code, 200)

        # verify form is a MemberMembershipForm and is not valid
        form = response.context["form"]
        self.assertIsInstance(form, MemberMembershipForm)
        self.assertFalse(form.is_valid())

    def test_add_member_with_club_admin_but_no_club_selected(self):
        data = {
            "name": "John",
            "surname": "Doe",
            "house_number": "123",
            "street": "Test Street",
            "city": "Test City",
            "zip_code": "12345",
            "date_of_birth": "2000-01-01",
            "nationality": "US",
            "affiliation_year": 2020,
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            "exams": [],
            "js": [],
            # "club_select": self.club.id,
            # "license_no": 1,
            "user_select": self.fstb_admin_user.id,
            "group_select": Group.objects.get(name=GroupEnum.CLUB_ADMIN.value).id,
        }
        response = self.client.post(self.url, data)

        # verify that the form is not valid
        self.assertEqual(response.status_code, 200)

        # verify that a message is returned
        self.assertIn(
            str(ON_CREATING_MEMBER_WITH_CLUB_ADMIN_USER__CLUB_NOT_SELECTED_ERROR),
            str(response.content),
        )

    def test_add_member_with_club_admin_and_no_user_selected(self):
        data = {
            "name": "John",
            "surname": "Doe",
            "house_number": "123",
            "street": "Test Street",
            "city": "Test City",
            "zip_code": "12345",
            "date_of_birth": "2000-01-01",
            "nationality": "US",
            "affiliation_year": 2020,
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            "exams": [],
            "js": [],
            "club_select": self.club.id,
            "license_no": 1,
            # "user_select": self.user.id,
            "group_select": Group.objects.get(name=GroupEnum.CLUB_ADMIN.value).id,
        }
        response = self.client.post(self.url, data)

        # verify that the form is not valid
        self.assertEqual(response.status_code, 200)

        # verify that a message is returned
        self.assertIn(
            str(ON_CREATING_MEMBER_WITH_CLUB_ADMIN_USER__USER_NOT_SELECTED_ERROR),
            str(response.content),
        )

    def test_add_member_with_selected_user_but_no_group_selected(self):
        data = {
            "name": "John",
            "surname": "Doe",
            "house_number": "123",
            "street": "Test Street",
            "city": "Test City",
            "zip_code": "12345",
            "date_of_birth": "2000-01-01",
            "nationality": "US",
            "affiliation_year": 2020,
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            "exams": [],
            "js": [],
            "club_select": self.club.id,
            "license_no": 1,
            "user_select": self.fstb_admin_user.id,
            # "group_select": Group.objects.get(name=GroupEnum.CLUB_ADMIN.value).id,
        }
        response = self.client.post(self.url, data)

        # verify that the form is not valid
        self.assertEqual(response.status_code, 200)

        # verify that a message is returned
        self.assertIn(
            str(ON_CREATING_MEMBER_WITH_CLUB_MEMBERSHIP__USER_GROUP_NOT_SELECTED_ERROR),
            str(response.content),
        )


class MemberCreateViewClubAdminTest(TestCase):
    def setUp(self):
        # Url for the post request
        self.post_url = reverse("add_member")

        # Insert default data that includes the FSTB Admin and Club Admin group, and the default roles
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.club_admin_user = User.objects.create_user(
            username="clubAdminUser", password="testpassword"
        )

        # Get the Club Admin group
        self.club_admin_group = Group.objects.get(name=GroupEnum.CLUB_ADMIN.value)

        # Add user to the Club Admin group
        self.club_admin_user.groups.add(self.club_admin_group)
        self.club_admin_user.save()

        # login with a user that is Club Admin
        self.logged_in = self.client.login(
            username="clubAdminUser", password="testpassword"
        )

        # Create member with user association
        member_with_user = Member.objects.create(
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
        Membership.objects.create(member=member_with_user, club=self.club, license_no=1)

    def test_add_member(self):
        data = {
            "name": "New Member",
            "surname": "Doe",
            "house_number": "123",
            "street": "Test Street",
            "city": "Test City",
            "zip_code": "12345",
            "date_of_birth": "2000-01-01",
            "nationality": "US",
            "affiliation_year": 2020,
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            "exams": [],
            "js": [],
            # the club is defaulted to the one of the user
            "license_no": 2,
        }
        response = self.client.post(self.post_url, data, follow=True)

        # verify that the form is valid
        self.assertEqual(response.status_code, 204)

        # verify that the member is created
        self.assertTrue(MemberChange.objects.filter(name="New Member").exists())

        # verify that the change membership is created
        self.assertEqual(MembershipChange.objects.all().count(), 1)

        # verify that the new membership is created
        self.assertTrue(
            MembershipChange.objects.filter(
                member__name="New Member", club__name="Club of the user"
            ).exists()
        )


class MemberDeleteViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        # Creating a test member
        self.member_1 = Member.objects.create(
            name="Member1",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2019,
        )

    def test_view_not_accessible(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        url = reverse("remove_member", args=[self.member_1.id])
        response = self.client.get(url)

        # 405 Method Not Allowed (Only POST is allowed)
        self.assertEqual(response.status_code, 405)

    def test_successful_deletion(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        url = reverse("remove_member", args=[self.member_1.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Member.objects.filter(id=self.member_1.id).exists())

    def test_deletion_non_existent_member(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        url = reverse("remove_member", args=[9999])  # Non-existent member ID
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_unsupported_http_method(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        url = reverse("remove_member", args=[self.member_1.id])
        # Using HTTP PUT method which is not supported
        response = self.client.put(url)

        self.assertEqual(response.status_code, 405)  # HTTP 405 Method Not Allowed


class MemberUpdateViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group, and the default roles
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )

        # Groups
        self.fstb_admin_group = Group.objects.get(name=GroupEnum.FSTB_ADMIN.value)
        self.club_admin_group = Group.objects.get(name=GroupEnum.CLUB_ADMIN.value)

        # login with a user that is in the FSTB Admin group
        self.user.groups.set([self.fstb_admin_group])
        self.user.save()
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        # Create member
        self.member_1 = Member.objects.create(
            name="Old Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
        )

        # Create member
        self.member_2 = Member.objects.create(
            name="Old Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
        )

        # Create a club
        self.club = Club.objects.create(
            name="Club1",
            affiliation_year=2019,
            license_no=1,
        )

        # Create membership
        self.membership_1 = Membership.objects.create(
            member=self.member_2, club=self.club, license_no=12
        )

    def test_view_accessible(self):
        url = reverse("edit_member", args=[self.member_1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_successful_update(self):
        url = reverse("edit_member", args=[self.member_1.id])
        data = {
            "name": "New Name",
            "surname": "Doe",
            "house_number": "123",
            "street": "Test Street",
            "city": "Test City",
            "zip_code": "12345",
            "date_of_birth": "2000-01-01",
            "nationality": "US",
            "affiliation_year": 2020,
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            "exams": [],
            "js": [],
            "club_select": self.club.id,
            "license_no": 1,
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 204)
        updated_member = Member.objects.get(id=self.member_1.id)
        self.assertEqual(updated_member.name, "New Name")

    def test_update_with_invalid_data(self):
        url = reverse("edit_member", args=[self.member_1.id])
        data = {
            # Name is intentionally missing
            "surname": "Doe",
            "house_number": "123",
            "street": "Test Street",
            "city": "Test City",
            "zip_code": "12345",
            "date_of_birth": "2000-01-01",
            "nationality": "US",
            "affiliation_year": 2020,
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            "exams": [],
            "js": [],
            "club_select": self.club.id,
            "license_no": 1,
        }
        response = self.client.post(url, data)

        self.assertEqual(
            response.status_code, 200
        )  # Should re-render the form with errors
        form = response.context["form"]
        self.assertFalse(form.is_valid())

    def test_update_non_existent_member(self):
        url = reverse("edit_member", args=[9999])  # Non-existent member ID
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_update_member_with_membership(self):
        url = reverse("edit_member", args=[self.member_2.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datatable/member_create_form.html")
        self.assertIn("form", response.context)
        self.assertIn("club_select", response.context["form"].fields)
        self.assertEqual(
            response.context["form"].fields["club_select"].initial, self.club
        )

    def test_update_member_with_user(self):
        # Create a user that is not in a group
        user_no_group = User.objects.create_user(
            username="noGroupUser", password="testpassword"
        )

        url = reverse("edit_member", args=[self.member_1.id])
        data = {
            "name": "New Name",
            "surname": "Doe",
            "house_number": "123",
            "street": "Test Street",
            "city": "Test City",
            "zip_code": "12345",
            "date_of_birth": "2000-01-01",
            "nationality": "US",
            "affiliation_year": 2020,
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            "exams": [],
            "js": [],
            # Club Membership Data
            "club_select": self.club.id,
            "license_no": 1,
            # User data
            "user_select": user_no_group.id,
            "group_select": self.fstb_admin_group.id,
        }
        response = self.client.post(url, data)

        # verify the form is valid
        self.assertEqual(response.status_code, 204)

        # get the updated member, because the member_1 object is not updated
        # that is because an object is passed by value, not by reference
        updated_member = Member.objects.get(id=self.member_1.id)

        # verify that the member is associated with the user
        self.assertEqual(updated_member.user, user_no_group)
        self.assertEqual(updated_member.user.groups.first(), self.fstb_admin_group)

    def test_update_member_removing_relation_with_user(self):
        # Set user with a group
        user_with_group = User.objects.create_user(
            username="userWithGroup", password="testpassword"
        )
        user_with_group.groups.add(self.club_admin_group)
        user_with_group.save()

        # Create member with user association
        member_with_user = Member.objects.create(
            name="Old Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            user=user_with_group,
        )

        url = reverse("edit_member", args=[member_with_user.id])
        data = {
            "name": "New Name",
            "surname": "Doe",
            "house_number": "123",
            "street": "Test Street",
            "city": "Test City",
            "zip_code": "12345",
            "date_of_birth": "2000-01-01",
            "nationality": "US",
            "affiliation_year": 2020,
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            "exams": [],
            "js": [],
            # Club Membership Data
            "club_select": self.club.id,
            "license_no": 1,
            # User data
            # "user_select": self.user.id,
            # "group_select": self.fstb_admin_group.id,
        }
        response = self.client.post(url, data)

        # verify the form is valid
        self.assertEqual(response.status_code, 204)

        # get the updated member, because the member_1 object is not updated
        # that is because an object is passed by value, not by reference
        updated_member = Member.objects.get(id=member_with_user.id)

        # verify that the member is associated with no user
        self.assertIsNone(updated_member.user)

        # the user that is no more associated with the member
        updated_user = User.objects.get(id=user_with_group.id)

        # verify that the user is not associated with any group
        self.assertFalse(updated_user.groups.exists())


class MemberUpdateViewClubAdminTest(TestCase):
    def setUp(self):
        # Url for the post request
        self.post_uri = "edit_member"

        # Insert default data that includes the FSTB Admin and Club Admin group, and the default roles
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.club_admin_user = User.objects.create_user(
            username="clubAdminUser", password="testpassword"
        )

        # Get the Club Admin group
        self.club_admin_group = Group.objects.get(name=GroupEnum.CLUB_ADMIN.value)

        # Add user to the Club Admin group
        self.club_admin_user.groups.add(self.club_admin_group)
        self.club_admin_user.save()

        # login with a user that is Club Admin
        self.logged_in = self.client.login(
            username="clubAdminUser", password="testpassword"
        )

        # Create member with user association
        member_with_user = Member.objects.create(
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
        Membership.objects.create(member=member_with_user, club=self.club, license_no=1)

        # Create member
        self.member_1 = Member.objects.create(
            name="Old Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
        )

    def test_update_member(self):
        url = reverse(self.post_uri, args=[self.member_1.id])
        data = {
            "name": "New Name",
            "surname": "Doe",
            "house_number": "123",
            "street": "Test Street",
            "city": "Test City",
            "zip_code": "12345",
            "date_of_birth": "2000-01-01",
            "nationality": "US",
            "affiliation_year": 2020,
            "roles": [Role.objects.filter(name=RoleEnum.ATHLETE.value).first().id],
            "exams": [],
            "js": [],
            # the club is defaulted to the one of the user
            "license_no": 1,
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 204)
        updated_member = MemberChange.objects.get(member=self.member_1)
        self.assertEqual(updated_member.name, "New Name")


class MemberChangesListViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group, and the default roles
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )

        # Groups
        self.fstb_admin_group = Group.objects.get(name=GroupEnum.FSTB_ADMIN.value)
        self.club_admin_group = Group.objects.get(name=GroupEnum.CLUB_ADMIN.value)

        # login with a user that is in the FSTB Admin group
        self.user.groups.set([self.fstb_admin_group])
        self.user.save()
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        # Url for the get request
        self.get_url = reverse("members_changes")

        # Create a club
        self.club_1 = Club.objects.create(
            name="Club1",
            affiliation_year=2019,
            license_no=1,
        )

        # Create Member
        self.member = Member.objects.create(
            name="Old Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
        )

        # Create Membership
        self.membership = Membership.objects.create(
            member=self.member,
            club=self.club_1,
            license_no=1,
        )

        # Create ChangeMember
        self.member_change = MemberChange.objects.create(
            name="New Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.user,
            member=self.member,
        )

        # Create ChangeMembership
        self.membership_change = MembershipChange.objects.create(
            member=self.member_change,
            club=self.club_1,
            license_no=2,
            applicant=self.user,
            membership=self.membership,
        )

        # Create 2 ChangeMember
        self.member_change_2 = MemberChange.objects.create(
            name="New Name 2",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.user,
            member=self.member,
        )

        # Create 2 ChangeMembership
        self.membership_change_2 = MembershipChange.objects.create(
            member=self.member_change_2,
            club=self.club_1,
            license_no=3,
            applicant=self.user,
            membership=self.membership,
        )

    def test_view_accessible(self):
        response = self.client.get(self.get_url)

        self.assertEqual(response.status_code, 200)

    def test_with_data(self):
        response = self.client.get(self.get_url)
        members_in_context = response.context["object_list"]

        # make sure that 2 members are returned
        self.assertEqual(len(members_in_context), 1)

        # make sure that the members are in the response
        self.assertIn(self.member_change_2, members_in_context)

    def test_shows_only_pending(self):
        # approve the first change
        self.member_change.status = ChangeModelStatus.APPROVED.value
        self.member_change.save()

        response = self.client.get(self.get_url)
        members_in_context = response.context["object_list"]

        # make sure that 1 member is returned
        self.assertEqual(len(members_in_context), 1)

        # make sure that the members are in the response
        self.assertNotIn(self.member_change, members_in_context)
        self.assertIn(self.member_change_2, members_in_context)

    def test_view_updated_new_member_change(self):
        Member.objects.all().delete()
        Membership.objects.all().delete()
        MemberChange.objects.all().delete()
        MembershipChange.objects.all().delete()

        new_member_change = MemberChange.objects.create(
            name="New Name 3",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.user,
        )

        new_membership_change = MembershipChange.objects.create(
            member=new_member_change,
            club=self.club_1,
            license_no=4,
            applicant=self.user,
        )

        member_change = MemberChange.objects.create(
            name="New Name 3",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.user,
        )

        membership_change = MembershipChange.objects.create(
            member=member_change,
            club=self.club_1,
            license_no=4,
            applicant=self.user,
        )

        response = self.client.get(self.get_url)
        members_in_context = response.context["object_list"]


class MemberChangeApproveViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group, and the default roles
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )

        # Groups
        self.fstb_admin_group = Group.objects.get(name=GroupEnum.FSTB_ADMIN.value)
        self.club_admin_group = Group.objects.get(name=GroupEnum.CLUB_ADMIN.value)

        # login with a user that is in the FSTB Admin group
        self.user.groups.set([self.fstb_admin_group])
        self.user.save()
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        # Create a club
        self.club_1 = Club.objects.create(
            name="Club1",
            affiliation_year=2019,
            license_no=1,
        )

    def test_approve_add_member(self):
        # Create ChangeMember
        self.member_change = MemberChange.objects.create(
            name="John",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.user,
        )

        # Create ChangeMembership
        self.membership_change = MembershipChange.objects.create(
            member=self.member_change,
            club=self.club_1,
            license_no=1,
            applicant=self.user,
        )

        url = reverse("member_change_approve", args=[self.member_change.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 204)
        self.assertTrue(Member.objects.filter(name="John").exists())
        self.assertTrue(Membership.objects.filter(member__name="John").exists())

    def test_approve_update_member(self):
        # Create Member
        member = Member.objects.create(
            name="Old Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
        )

        # Create Membership
        membership = Membership.objects.create(
            member=member,
            club=self.club_1,
            license_no=1,
        )

        # Create ChangeMember
        member_change = MemberChange.objects.create(
            name="New Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.user,
            member=member,
        )

        # Create ChangeMembership
        membership_change = MembershipChange.objects.create(
            member=member_change,
            club=self.club_1,
            license_no=2,
            applicant=self.user,
            membership=membership,
        )

        url = reverse("member_change_approve", args=[member_change.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 204)

        self.assertEqual(Member.objects.all().count(), 1)
        self.assertEqual(Membership.objects.all().count(), 1)

        self.assertTrue(Member.objects.filter(name="New Name").exists())
        self.assertTrue(Membership.objects.filter(member__name="New Name").exists())

    def test_approve_multiple_update_member(self):
        # Create Member
        member = Member.objects.create(
            name="Old Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
        )

        # Create Membership
        membership = Membership.objects.create(
            member=member,
            club=self.club_1,
            license_no=1,
        )

        # Create ChangeMember
        member_change = MemberChange.objects.create(
            name="New Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.user,
            member=member,
        )

        # Create ChangeMembership
        membership_change = MembershipChange.objects.create(
            member=member_change,
            club=self.club_1,
            license_no=2,
            applicant=self.user,
            membership=membership,
        )

        # Create 2 ChangeMember
        member_change_2 = MemberChange.objects.create(
            name="New Name 2",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.user,
            member=member,
        )

        # Create 2 ChangeMembership
        membership_change_2 = MembershipChange.objects.create(
            member=member_change_2,
            club=self.club_1,
            license_no=3,
            applicant=self.user,
            membership=membership,
        )

        url = reverse("member_change_approve", args=[member_change_2.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 204)

        self.assertEqual(Member.objects.all().count(), 1)
        self.assertEqual(Membership.objects.all().count(), 1)

        self.assertTrue(Member.objects.filter(name="New Name 2").exists())
        self.assertTrue(Membership.objects.filter(member__name="New Name 2").exists())

        # assert all 2 MemberChanges are approved
        self.assertEqual(
            MemberChange.objects.filter(
                status=ChangeModelStatus.APPROVED.value
            ).count(),
            2,
        )


class MemberChangeDeclinedViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group, and the default roles
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )

        # Groups
        self.fstb_admin_group = Group.objects.get(name=GroupEnum.FSTB_ADMIN.value)
        self.club_admin_group = Group.objects.get(name=GroupEnum.CLUB_ADMIN.value)

        # login with a user that is in the FSTB Admin group
        self.user.groups.set([self.fstb_admin_group])
        self.user.save()
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        # Create a club
        self.club_1 = Club.objects.create(
            name="Club1",
            affiliation_year=2019,
            license_no=1,
        )

    def test_decline_add_member(self):
        # Create ChangeMember
        self.member_change = MemberChange.objects.create(
            name="John",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.user,
        )

        # Create ChangeMembership
        self.membership_change = MembershipChange.objects.create(
            member=self.member_change,
            club=self.club_1,
            license_no=1,
            applicant=self.user,
        )

        url = reverse("member_change_decline", args=[self.member_change.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Member.objects.filter(name="John").exists())
        self.assertFalse(Membership.objects.filter(member__name="John").exists())

    def test_decline_update_member(self):
        # Create Member
        member = Member.objects.create(
            name="Old Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
        )

        # Create Membership
        membership = Membership.objects.create(
            member=member,
            club=self.club_1,
            license_no=1,
        )

        # Create ChangeMember
        member_change = MemberChange.objects.create(
            name="New Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.user,
            member=member,
        )

        # Create ChangeMembership
        membership_change = MembershipChange.objects.create(
            member=member_change,
            club=self.club_1,
            license_no=2,
            applicant=self.user,
            membership=membership,
        )

        url = reverse("member_change_decline", args=[member_change.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 204)

        self.assertEqual(Member.objects.all().count(), 1)
        self.assertEqual(Membership.objects.all().count(), 1)

        self.assertFalse(Member.objects.filter(name="New Name").exists())
        self.assertFalse(Membership.objects.filter(member__name="New Name").exists())

    def test_decline_multiple_update_member(self):
        # Create Member
        member = Member.objects.create(
            name="Old Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
        )

        # Create Membership
        membership = Membership.objects.create(
            member=member,
            club=self.club_1,
            license_no=1,
        )

        # Create ChangeMember
        member_change = MemberChange.objects.create(
            name="New Name",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.user,
            member=member,
        )

        # Create ChangeMembership
        membership_change = MembershipChange.objects.create(
            member=member_change,
            club=self.club_1,
            license_no=2,
            applicant=self.user,
            membership=membership,
        )

        # Create 2 ChangeMember
        member_change_2 = MemberChange.objects.create(
            name="New Name 2",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
            applicant=self.user,
            member=member,
        )

        # Create 2 ChangeMembership
        membership_change_2 = MembershipChange.objects.create(
            member=member_change_2,
            club=self.club_1,
            license_no=3,
            applicant=self.user,
            membership=membership,
        )

        url = reverse("member_change_decline", args=[member_change_2.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 204)

        self.assertEqual(Member.objects.all().count(), 1)
        self.assertEqual(Membership.objects.all().count(), 1)

        self.assertTrue(Member.objects.filter(name="Old Name").exists())
        self.assertTrue(Membership.objects.filter(member__name="Old Name").exists())

        # assert all 2 MemberChanges are approved
        self.assertEqual(
            MemberChange.objects.filter(
                status=ChangeModelStatus.DECLINED.value
            ).count(),
            2,
        )


# ----- Test Club Views ---------------------------------------------------
class ClubListViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        # Create sample clubs for the list view
        self.club1 = Club.objects.create(
            name="Club 1", affiliation_year=2022, license_no=6
        )
        self.club2 = Club.objects.create(
            name="Club 2", affiliation_year=2023, license_no=7
        )

    def test_club_list_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(reverse("clubs"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datatable/club.html")

    def test_club_list_view_displays_clubs(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(reverse("clubs"))

        self.assertContains(response, "Club 1")
        self.assertContains(response, "Club 2")


class ClubCreateView(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

    def test_club_create_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(reverse("add_club"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datatable/club_create_form.html")

    def test_club_create_view_successful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "name": "New Club",
            "affiliation_year": 2023,
            "license_no": 2,
        }
        response = self.client.post(reverse("add_club"), data=data)

        self.assertEqual(
            response.status_code, 204
        )  # Expecting a redirect after successful creation
        self.assertTrue(Club.objects.filter(name="New Club").exists())

    def test_club_create_view_unsuccessful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "name": "",  # Name is required, so this should fail
            "affiliation_year": 2023,
            "license_no": 3,
        }
        response = self.client.post(reverse("add_club"), data=data)

        self.assertEqual(
            response.status_code, 200
        )  # The form should be rendered again with errors
        self.assertFalse(Club.objects.filter(license_no=3).exists())


class ClubDeleteView(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        # Create a sample club to be deleted in the test
        self.club = Club.objects.create(
            name="Test Club", affiliation_year=2022, license_no=4
        )
        self.delete_url = reverse("remove_club", args=[self.club.pk])

    def test_club_delete_view_successful_delete(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.post(self.delete_url)

        self.assertEqual(
            response.status_code, 204
        )  # Expecting a redirect after successful deletion
        self.assertFalse(Club.objects.filter(pk=self.club.pk).exists())

    def test_club_delete_view_unsuccessful_delete(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        # Delete the club manually to simulate a club that doesn't exist
        self.club.delete()
        response = self.client.post(self.delete_url)
        self.assertEqual(
            response.status_code, 404
        )  # The club doesn't exist, so a 404 should be returned


class ClubUpdateView(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        # Create a sample club to be updated in the test
        self.club = Club.objects.create(
            name="Test Club", affiliation_year=2022, license_no=5
        )

        # Create url for update club view
        self.update_url = reverse("edit_club", args=[self.club.pk])

    def test_club_update_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.update_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datatable/club_create_form.html")

    def test_club_update_view_successful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "name": "Updated Club",
            "affiliation_year": 2023,
            "license_no": 5,
        }
        response = self.client.post(self.update_url, data=data)

        self.assertEqual(response.status_code, 204, msg=response.content)
        self.assertTrue(Club.objects.filter(name="Updated Club").exists())

    def test_club_update_view_unsuccessful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "name": "",  # Name is required, so this should fail
            "affiliation_year": 2023,
            "license_no": 5,
        }
        response = self.client.post(self.update_url, data=data)

        self.assertEqual(
            response.status_code, 200
        )  # The form should be rendered again with errors
        self.assertFalse(Club.objects.filter(name="Updated Club").exists())

    def test_club_update_view_nonexistent_club(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        nonexistent_update_url = reverse(
            "edit_club", args=[self.club.pk + 1]
        )  # Assuming the next ID doesn't exist
        response = self.client.get(nonexistent_update_url)
        self.assertEqual(
            response.status_code, 404
        )  # The club doesn't exist, so a 404 should be returned


# ----- Test Role Views ---------------------------------------------------
class MembershipsCardsViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        self.url = reverse("memberships_view")

    def test_memberships_cards_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/cards/memberships.html")

    def test_memberships_cards_view_displays_card_title(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Memberships")


class MembershipListViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        self.url = reverse("memberships")

        # Prepare data
        self.club_1 = Club.objects.create(
            name="Club1",
            affiliation_year=2019,
            license_no=1,
        )
        self.club_2 = Club.objects.create(
            name="Club2",
            affiliation_year=2020,
            license_no=2,
        )

        self.member_1 = Member.objects.create(
            name="Member1",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2019,
        )
        self.member_2 = Member.objects.create(
            name="Member2",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2020,
        )

        self.membership_1 = Membership.objects.create(
            member=self.member_1, club=self.club_1, license_no=1
        )
        self.membership_2 = Membership.objects.create(
            member=self.member_2, club=self.club_2, license_no=2
        )

    def test_membership_list_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datatable/membership.html")

    def test_membership_list_view_displays_memberships(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Member1")
        self.assertContains(response, "Member2")


class MembershipDeleteViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        # Create sample data
        self.member_1 = Member.objects.create(
            name="Member1",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2019,
        )
        self.club_1 = Club.objects.create(
            name="Club1",
            affiliation_year=2019,
            license_no=1,
        )
        self.membership_1 = Membership.objects.create(
            member=self.member_1, club=self.club_1, license_no=1
        )

        # Create url for delete membership view
        self.delete_url = reverse("remove_membership", args=[self.membership_1.pk])

    def test_membership_delete_view_successful_delete(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Membership.objects.filter(pk=self.membership_1.pk).exists())

    def test_membership_delete_view_unsuccessful_delete(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        # Delete the membership manually to simulate a membership that doesn't exist
        self.membership_1.delete()
        response = self.client.post(self.delete_url)

        # The membership doesn't exist, so a 404 should be returned
        self.assertEqual(response.status_code, 404)


class JoinClubViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        # Create sample data
        self.member_1 = Member.objects.create(
            name="Member1",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2019,
        )
        self.club_1 = Club.objects.create(
            name="Club1",
            affiliation_year=2019,
            license_no=1,
        )

        self.join_url = reverse("membership_join_club", args=[self.member_1.pk])

    def test_join_club_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.join_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datatable/membership_join_club_form.html")

    def test_join_club_view_successful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "club_select": self.club_1.pk,
            "license_no": 1,
        }
        response = self.client.post(self.join_url, data=data)

        # The modal should be closed and the membership should be created
        self.assertEqual(response.status_code, 204)
        self.assertTrue(
            Membership.objects.filter(member=self.member_1, club=self.club_1).exists()
        )

    def test_join_club_view_unsuccessful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "club_select": "Club3",  # Leaving club_select empty should fail
            "license_no": 1,
        }
        response = self.client.post(self.join_url, data=data)

        # The form should be rendered again with errors
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Membership.objects.filter(member=self.member_1, club=self.club_1).exists()
        )


class TransferClubViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        # Create sample data
        self.member_1 = Member.objects.create(
            name="Member1",
            surname="Doe",
            house_number="123",
            street="Test Street",
            city="Test City",
            zip_code="12345",
            date_of_birth="1990-01-01",
            nationality="US",
            affiliation_year=2019,
        )
        self.old_club = Club.objects.create(
            name="Old Club",
            affiliation_year=2019,
            license_no=1,
        )

        self.new_club = Club.objects.create(
            name="New Club",
            affiliation_year=2020,
            license_no=2,
        )

        self.membership_1 = Membership.objects.create(
            member=self.member_1, club=self.old_club, license_no=1
        )

        # Create url for transfer membership view
        self.transfer_url = reverse("membership_transfer_club", args=[self.member_1.pk])

    def test_transfer_club_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.transfer_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "datatable/membership_transfer_club_form.html"
        )

    def test_transfer_club_view_successful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "club_select": self.new_club.pk,
            "license_no": 1,
        }
        response = self.client.post(self.transfer_url, data=data)

        # The modal should be closed and the membership should be updated
        self.assertEqual(response.status_code, 204)
        self.assertTrue(
            Membership.objects.filter(member=self.member_1, club=self.new_club).exists()
        )

    def test_transfer_club_view_unsuccessful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "club_select": "Club A",  # Leaving club_select empty which should fail
            "license_no": 1,
        }
        response = self.client.post(self.transfer_url, data=data)

        # The form should be rendered again with errors
        self.assertEqual(response.status_code, 200)
        # The member should still be in the old club
        self.assertTrue(
            Membership.objects.filter(member=self.member_1, club=self.old_club).exists()
        )


class LicenseNoFieldViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        self.club = Club.objects.create(
            name="Club",
            affiliation_year=2019,
            license_no=1,
        )

        self.url = reverse("load_license_no_field")

    def test_license_no_field_view_with_valid_club_id(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url, {"club_select": self.club.pk})

        self.assertEqual(response.status_code, 200)

    def test_license_no_field_view_without_club_id(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        # Should return an empty response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    def test_license_no_field_view_generates_correct_form(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url, {"club_select": self.club.pk})

        self.assertIn(b'name="license_no"', response.content)


# ----- Test Roles Views ---------------------------------------------------
class RolesCardsViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        self.url = reverse("roles_view")

    def test_roles_cards_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/cards/roles.html")

    def test_roles_cards_view_displays_card_title(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Roles")


class RoleListViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group, and roles
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        self.url = reverse("roles")

    def test_role_list_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datatable/roles.html")

    def test_role_list_view_displays_roles(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        self.assertContains(response, RoleEnum.ATHLETE.value)
        self.assertContains(response, RoleEnum.FSTB_CC.value)


class RoleCreateViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        self.add_url = reverse("add_role")

    def test_role_create_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.add_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datatable/role_create_form.html")

    def test_role_create_view_successful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "name": "New Role",
        }
        response = self.client.post(self.add_url, data=data)

        # the modal should be closed and the role should be created
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Role.objects.filter(name="New Role").exists())

    def test_role_create_view_unsuccessful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "name": "",  # The name is required, so this should fail
        }
        response = self.client.post(self.add_url, data=data)

        # The form should be rendered again with errors
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Role.objects.filter(name="New Role").exists())


class RoleDeleteViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        # Create a sample role to be deleted in the test
        self.role = Role.objects.create(name="Test Role")

        self.delete_url = reverse("remove_role", args=[self.role.pk])

    def test_role_delete_view_successful_delete(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.post(self.delete_url)

        # The modal should be closed and the role should be deleted
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Role.objects.filter(pk=self.role.pk).exists())

    def test_role_delete_view_unsuccessful_delete(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        self.role.delete()
        response = self.client.post(self.delete_url)

        # The role doesn't exist, so a 404 should be returned
        self.assertEqual(response.status_code, 404)


class RoleUpdateViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        # Create a sample role to be deleted in the test
        self.old_role = Role.objects.create(name="Old Role")

        self.update_url = reverse("edit_role", args=[self.old_role.pk])

    def test_role_update_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.update_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datatable/role_create_form.html")

    def test_role_update_view_successful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "name": "Updated Role",
        }
        response = self.client.post(self.update_url, data=data)

        # The modal should be closed and the role should be updated
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Role.objects.filter(name="Updated Role").exists())

    def test_role_update_view_unsuccessful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "name": "",  # The name is required, so this should fail
        }
        response = self.client.post(self.update_url, data=data)

        # The form should be rendered again with errors
        self.assertEqual(response.status_code, 200)
        # The name should remain unchanged
        self.assertTrue(Role.objects.filter(name="Old Role").exists())

    def test_role_update_view_role_not_exists(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        self.old_role.delete()
        response = self.client.get(self.update_url)

        # The role doesn't exist, so a 404 should be returned
        self.assertEqual(response.status_code, 404)


# ----- Test Roles Views ---------------------------------------------------
class TeamsCardsViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        self.url = reverse("teams_view")

    def test_teams_cards_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/cards/teams.html")

    def test_teams_cards_view_displays_card_title(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Teams")


class TeamListViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group, and roles
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        self.url = reverse("teams")

    def test_team_list_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datatable/teams.html")


class TeamCreateViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        self.add_url = reverse("add_team")

    def test_team_create_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.add_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datatable/team_create_form.html")

    def test_team_create_view_unsuccessful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "name": "",  # The name is required, so this should fail
        }
        response = self.client.post(self.add_url, data=data)

        # The form should be rendered again with errors
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Role.objects.filter(name="New Team").exists())


class TeamDeleteViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        club = Club.objects.create(
            name="new club",
            affiliation_year=2023,
            license_no=1
        )

        # Create a sample team to be deleted in the test
        self.team = Team.objects.create(
            name="new team",
            description="test",
            min_members_number=1,
            club=club,
            min_members_number_not_reached=True
        )

        self.delete_url = reverse("remove_team", args=[self.team.pk])

    def test_team_delete_view_successful_delete(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.post(self.delete_url)

        # The modal should be closed and the role should be deleted
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Team.objects.filter(pk=self.team.pk).exists())

    def test_team_delete_view_unsuccessful_delete(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        self.team.delete()
        response = self.client.post(self.delete_url)

        # The role doesn't exist, so a 404 should be returned
        self.assertEqual(response.status_code, 404)


class TeamUpdateViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        club = Club.objects.create(
            name="new club",
            affiliation_year=2023,
            license_no=1
        )

        # Create a sample team to be deleted in the test
        self.old_team = Team.objects.create(
            name="old team",
            description="test",
            min_members_number=1,
            club=club,
            min_members_number_not_reached=True
        )

        self.update_url = reverse("edit_team", args=[self.old_team.pk])

    def test_role_update_view_uses_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.update_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "datatable/team_create_form.html")

    def test_update_update_view_unsuccessful_post(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        data = {
            "name": "",  # The name is required, so this should fail
        }
        response = self.client.post(self.update_url, data=data)

        # The form should be rendered again with errors
        self.assertEqual(response.status_code, 200)
        # The name should remain unchanged
        self.assertTrue(Team.objects.filter(name="old team").exists())

    def test_team_update_view_role_not_exists(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        self.old_team.delete()
        response = self.client.get(self.update_url)

        # The role doesn't exist, so a 404 should be returned
        self.assertEqual(response.status_code, 404)


# ----- Test Competition Views ------------------------------------------------------
class TestCompetitionListView(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )

        # Prepare data
        self.competition_1 = Competition.objects.create(
            name="competition 1",
            description="test",
            status="Open",
            due_date=datetime.today()
        )

        self.competition_2 = Competition.objects.create(
            name="competition 2",
            description="test",
            status="Closed",
            due_date=datetime.today()
        )

        # Url used for the get request
        self.url = reverse("competitions")

    def test_competition_list_view_renders_correct_template(self):
        # login with a user that is in the FSTB Admin group
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)

        # Check that the correct template was used
        self.assertTemplateUsed(response, "datatable/competitions.html")

    def test_competition_list_view_returns_all_competitions(self):
        # login with a user that is in the FSTB Admin group
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        response = self.client.get(self.url)
        competitions_in_context = response.context["object_list"]

        # make sure that 2 competitions are returned
        self.assertEqual(len(competitions_in_context), 2)

        # make sure that the competition are in the response
        self.assertIn(self.competition_1, competitions_in_context)
        self.assertIn(self.competition_2, competitions_in_context)


class CompetitionCreateViewTest(TestCase):
    def setUp(self):
        # Url for requests
        self.url = reverse("add_competition")

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

        # login with a user that is FSTB Admin
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

    def test_competition_create_view_reachable(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_competition_create_with_valid_data(self):
        data = {
            "name": "competition",
            "description": "test",
            "due_date": datetime.today(),
            "status": "Open"
        }
        response = self.client.post(self.url, data)

        # Assuming a redirect after a successful creation
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Competition.objects.filter(name="competition").exists())

    def test_competition_create_with_invalid_data(self):
        data = {
            # Name is intentionally missing
            "description": "test",
            "due_date": datetime.today(),
            "status": "Open"
        }
        response = self.client.post(self.url, data)

        # verify that the form is not valid
        self.assertEqual(response.status_code, 200)

        # verify form is a CompetitionForm and is not valid
        form = response.context["form"]
        self.assertIsInstance(form, CompetitionForm)
        self.assertFalse(form.is_valid())


class CompetitionDeleteViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )
        self.user.groups.add(Group.objects.get(name=GroupEnum.FSTB_ADMIN.value))
        self.user.save()

        # Creating a test Competition
        self.competition = Competition.objects.create(
            name="competition",
            description="test",
            due_date=datetime.today(),
            status="Open"
        )

    def test_view_not_accessible(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        url = reverse("remove_competition", args=[self.competition.id])
        response = self.client.get(url)

        # 405 Method Not Allowed (Only POST is allowed)
        self.assertEqual(response.status_code, 405)

    def test_successful_deletion(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        url = reverse("remove_competition", args=[self.competition.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Member.objects.filter(id=self.competition.id).exists())

    def test_deletion_non_existent_competition(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        url = reverse("remove_competition", args=[9999])  # Non-existent member ID
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_unsupported_http_method(self):
        # login with a user that is in the FSTB Admin group
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        url = reverse("remove_member", args=[self.competition.id])
        # Using HTTP PUT method which is not supported
        response = self.client.put(url)

        self.assertEqual(response.status_code, 405)  # HTTP 405 Method Not Allowed


class CompetitionUpdateViewTest(TestCase):
    def setUp(self):
        # Insert default data that includes the FSTB Admin and Club Admin group, and the default roles
        call_command("insert_defaults")

        # Create a user that is in the FSTB Admin group
        self.user = User.objects.create_user(
            username="fstbAdminUser", password="testpassword"
        )

        # Groups
        self.fstb_admin_group = Group.objects.get(name=GroupEnum.FSTB_ADMIN.value)

        # login with a user that is in the FSTB Admin group
        self.user.groups.set([self.fstb_admin_group])
        self.user.save()
        self.logged_in = self.client.login(
            username="fstbAdminUser", password="testpassword"
        )

        # Create competition
        self.competition_1 = Competition.objects.create(
            name="competition 1",
            description="test",
            due_date=datetime.today(),
            status="Open",
        )

        self.competition_2 = Competition.objects.create(
            name="competition 2",
            description="test",
            due_date=datetime.today(),
            status="Closed",
        )

    def test_view_accessible(self):
        url = reverse("edit_competition", args=[self.competition_1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_successful_update(self):
        url = reverse("edit_competition", args=[self.competition_1.id])
        data = {
            "name": "New Name",
            "description": "test",
            "due_date": datetime.today(),
            "status": "Open",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 204)
        updated_competition = Competition.objects.get(id=self.competition_1.id)
        self.assertEqual(updated_competition.name, "New Name")

    def test_update_with_invalid_data(self):
        url = reverse("edit_competition", args=[self.competition_1.id])
        data = {
            "description": "test",
            "due_date": datetime.today(),
            "status": "Open",
        }
        response = self.client.post(url, data)

        self.assertEqual(
            response.status_code, 200
        )  # Should re-render the form with errors
        form = response.context["form"]
        self.assertFalse(form.is_valid())

    def test_update_non_existent_competition(self):
        url = reverse("edit_competition", args=[9999])  # Non-existent competition ID
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
