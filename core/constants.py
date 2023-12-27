# ----- Django imports --------------------------------------------------------
from django.utils.translation import gettext_lazy as _

# ----- Constants -------------------------------------------------------------
CHANGED_EVENT = "{}ListChanged"

SHOW_MESSAGE = "showMessage"
ADDED_MESSAGE = _("{model} added")
UPDATED_MESSAGE = _("{model} updated")
DELETED_MESSAGE = _("{model} deleted")

APPROVED_MESSAGE = _("{model} approved")
DECLINED_MESSAGE = _("{model} declined")

TABLE_ID = "{}_list"
TABLE_ITEM_EDIT_URL = "edit_{}"
TABLE_ITEM_DETAIL_URL = "detail_{}"
TABLE_ITEM_REMOVE_URL = "remove_{}"
TABLE_ITEM_ADD_URL = "add_{}"

ADD_EDIT_TEMPLATE = "datatable/{}_create_form.html"
