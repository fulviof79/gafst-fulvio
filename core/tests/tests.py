from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Member


# class HomepageTests(TestCase):
#     def test_url_exists_at_correct_location(self):
#         response = self.client.get("/")
#         self.assertEqual(response.status_code, 200)
#
#     def test_homepage(self):  # new
#         response = self.client.get(reverse("home"))
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, "home.html")
#
#     @classmethod
#     def setUpTestData(cls):
#         cls.user = User.objects.create(username="testuser")
#         cls.member = Member.objects.create(
#             first_name="John",
#             last_name="Doe",
#             house_number="123",
#             street="Main Street",
#             city="City",
#             zip_code="12345",
#             date_of_birth="2000-01-01",
#             nationality="US",
#             affiliation_year=2022,
#             id_user=cls.user,
#         )
#
#     def test_member_creation(self):
#         self.assertIsInstance(self.member, Member)
#         self.assertEqual(self.member.first_name, "John")
#         self.assertEqual(self.member.last_name, "Doe")
#         self.assertEqual(self.member.house_number, "123")
#         self.assertEqual(self.member.street, "Main Street")
#         self.assertEqual(self.member.city, "City")
#         self.assertEqual(self.member.zip_code, "12345")
#         self.assertEqual(str(self.member.date_of_birth), "2000-01-01")
#         self.assertEqual(self.member.nationality, "US")
#         self.assertEqual(self.member.affiliation_year, 2022)
#         self.assertEqual(self.member.id_user, self.user)
#
#     def test_member_str(self):
#         member = Member.objects.get(id=1)
#         expected_object_name = f"{member.first_name} {member.last_name}"
#         self.assertEqual(expected_object_name, str(member))
#
#
# class AboutpageTests(TestCase):
#     def test_url_exists_at_correct_location(self):
#         response = self.client.get("/about/")
#         self.assertEqual(response.status_code, 200)
#
#     def test_aboutpage(self):  # new
#         response = self.client.get(reverse("about"))
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, "about.html")
