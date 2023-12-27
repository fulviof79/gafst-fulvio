from django.core.management import call_command
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Group, AnonymousUser
from django.urls import reverse

from core.views import MembersCardsView, ClubsCardsView


class AdminLoginRequiredMixinTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Insert a user for testing
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='testpass'
        )

        self.url = reverse('members_view')

    def test_no_authenticated_user(self):
        request = self.factory.get(self.url)
        request.user = AnonymousUser()
        response = MembersCardsView.as_view()(request)

        # 302 Found - Redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_authenticated_user_not_in_group(self):
        request = self.factory.get(self.url)
        request.user = self.user
        response = MembersCardsView.as_view()(request)

        # 403 Forbidden - You don't have permission to access this page
        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_in_fstb_admin(self):
        self.user.groups.add(Group.objects.get(name='FSTB Admin'))

        request = self.factory.get(self.url)
        request.user = self.user
        response = MembersCardsView.as_view()(request)

        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_in_club_admin(self):
        self.user.groups.add(Group.objects.get(name='Club Admin'))

        request = self.factory.get(self.url)
        request.user = self.user
        response = MembersCardsView.as_view()(request)

        self.assertEqual(response.status_code, 200)


class FstbAdminLoginRequiredMixinTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        # Insert default data that includes the FSTB Admin and Club Admin group
        call_command("insert_defaults")

        # Insert a user for testing
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='testpass'
        )

        self.url = reverse('clubs_view')

    def test_no_authenticated_user(self):
        request = self.factory.get(self.url)
        request.user = AnonymousUser()
        response = ClubsCardsView.as_view()(request)

        # 302 Found - Redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_authenticated_user_not_in_group(self):
        request = self.factory.get(self.url)
        request.user = self.user
        response = ClubsCardsView.as_view()(request)

        # 403 Forbidden - You don't have permission to access this page
        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_in_fstb_admin(self):
        self.user.groups.add(Group.objects.get(name='FSTB Admin'))

        request = self.factory.get(self.url)
        request.user = self.user
        response = ClubsCardsView.as_view()(request)

        self.assertEqual(response.status_code, 200)

