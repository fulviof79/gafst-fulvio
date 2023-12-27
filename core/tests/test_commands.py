from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch, MagicMock, PropertyMock

from core.enums import RoleEnum, ExamEnum, JSEnum, GroupEnum
from core.management.commands.insert_defaults import insert_defaults_by_enum
from core.models import Role, Exam, JS


class InsertDefaultsTest(TestCase):
    @patch("core.models.Role.objects.get_or_create")
    def test_insert_defaults_by_enum(self, mock_get_or_create):
        """
        Test that the get_or_create method is called for each item in the enum
        """
        # Create mock enum items with a 'value' property
        item_names = ["item1", "item2", "item3"]
        mock_enum_items = []

        for name in item_names:
            mock_item = MagicMock(spec=["value"])
            type(mock_item).value = PropertyMock(return_value=name)
            mock_enum_items.append(mock_item)

        # Create a mock enum that is iterable
        mock_enum = MagicMock()
        mock_enum.__iter__.return_value = iter(mock_enum_items)

        # Call the function
        insert_defaults_by_enum(Role, mock_enum)

        # Check that get_or_create was called for each item in the enum
        mock_get_or_create.assert_any_call(name="item1")
        mock_get_or_create.assert_any_call(name="item2")
        mock_get_or_create.assert_any_call(name="item3")

        # Ensure the get_or_create function was called three times
        self.assertEqual(mock_get_or_create.call_count, 3)


class TestCommands(TestCase):
    @patch("core.management.commands.insert_defaults.insert_defaults_by_enum")
    def test_insert_defaults(self, mock_insert):
        """
        Test that the insert_defaults_by_enum function is called with the correct arguments
        """
        # Call the management command
        call_command("insert_defaults")

        # Check that the insert_defaults_by_enum function was called with the correct arguments
        mock_insert.assert_any_call(Role, RoleEnum)
        mock_insert.assert_any_call(Exam, ExamEnum)
        mock_insert.assert_any_call(JS, JSEnum)

        #  Check that 2 groups were created
        self.assertEqual(Group.objects.count(), 2)

        # Ensure the insert_defaults_by_enum function was called 3 times
        self.assertEqual(mock_insert.call_count, 3)
