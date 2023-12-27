# ----- Django imports -------------------------------------
from django.contrib import admin

# ----- Core Imports ---------------------------------------
from .models import Member


admin.site.register(Member)
