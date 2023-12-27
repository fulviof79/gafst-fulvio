# ----- generic imports ---------------------------------------------------------
import json

from django import forms

# ----- django imports ----------------------------------------------------------
from django.views.generic import (
    TemplateView,
    ListView,
    CreateView,
    UpdateView,
    FormView,
)

# auth
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.views import LoginView as BaseLoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User

# translation
from django.utils.translation import gettext_lazy as _
import django.utils.translation as translation

# generic
from django.shortcuts import get_object_or_404, render
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.views import View

# ----- core imports ------------------------------------------------------------
from .constants import (
    CHANGED_EVENT,
    SHOW_MESSAGE,
    TABLE_ID,
    TABLE_ITEM_REMOVE_URL,
    TABLE_ITEM_EDIT_URL,
    TABLE_ITEM_ADD_URL,
    ADDED_MESSAGE,
    DELETED_MESSAGE,
    ADD_EDIT_TEMPLATE,
    UPDATED_MESSAGE,
    APPROVED_MESSAGE, TABLE_ITEM_DETAIL_URL,
)

from .enums import ChangeModelStatus

from .models import (
    Member,
    Club,
    Membership,
    get_remaining_memberships_by_club,
    Role,
    MemberChange,
    Competition, Team, CompetitionRegistration, Division, Discipline, YearRule,
)

from .forms import (
    ClubForm,
    MembershipForm,
    RoleForm,
    MemberMembershipForm,
    CompetitionForm,
    InscribedMemberForm, TeamForm, CompetitionRegistrationForm, DivisionForm, DisciplinesForm, YearRuleForm,
)

from .mixins import AdminLoginRequiredMixin, FstbAdminLoginRequiredMixin

from .utils import (
    save_membership,
    is_user_fstb_admin,
    is_user_club_admin,
    get_user_club,
    approve_member_changes,
    decline_member_changes, check_min_member, check_max_member, calculate_age, check_ages,
)


# ----- Utils -----------------------------------------------------------------
def get_success_response(self, instance, message_format, extra_event=""):
    changed_event = CHANGED_EVENT.format(self.model.__name__.lower())
    message = message_format.format(model=instance)

    return HttpResponse(
        status=204,
        headers={
            "HX-Trigger": json.dumps(
                {
                    changed_event: None,
                    SHOW_MESSAGE: message,
                    extra_event: None,
                }
            )
        },
    )


# ----- Home ------------------------------------------------------------------
class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"


# ----- Registration ---------------------------------------------------------
class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("login")


class LoginView(BaseLoginView):
    form_class = AuthenticationForm
    template_name = "registration/login.html"
    success_url = reverse_lazy("home")


# ----- Generic views --------------------------------------------------------
class CardTemplateView(TemplateView):
    model = None
    card_title = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.model is None or self.card_title is None:
            raise ImproperlyConfigured(
                _(
                    "DataTableListView requires a model and card_title attribute to be set."
                )
            )

        model_name = self.model.__name__.lower()

        context["list_changed_event"] = CHANGED_EVENT.format(model_name)
        context["card_title"] = _(self.card_title)
        context["card_body_url"] = reverse_lazy(
            f"{self.model._meta.verbose_name_plural.lower()}"
        )

        return context


class DatatableListView(ListView):
    def get_context_data(self, **kwargs):
        if self.model is None:
            raise ImproperlyConfigured(
                _("DataTableListView requires a model attribute to be set.")
            )

        context = super().get_context_data(**kwargs)

        model_name = self.model.__name__.lower()
        context["table_id"] = TABLE_ID.format(model_name)
        context["table_item_remove_url"] = TABLE_ITEM_REMOVE_URL.format(model_name)
        context["table_item_edit_url"] = TABLE_ITEM_EDIT_URL.format(model_name)
        context["table_item_detail_url"] = TABLE_ITEM_DETAIL_URL.format(model_name)
        context["table_item_add_url"] = TABLE_ITEM_ADD_URL.format(model_name)
        return context


class DatatableCreateView(CreateView):
    modal_title = None

    def form_valid(self, form):
        instance = form.save()
        return get_success_response(self, instance, ADDED_MESSAGE)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["modal_title"] = _(self.modal_title)
        return context


class DatatableDeleteView(View):
    model = None

    def post(self, request, pk):
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        instance.delete()
        return get_success_response(self, instance, DELETED_MESSAGE)

    def get_queryset(self):
        if self.model is None:
            raise ImproperlyConfigured(
                _("DataTableDeleteView requires a model attribute to be set.")
            )

        return self.model.objects.all()


class DatatableUpdateView(UpdateView):
    model = Member
    form_class = None
    modal_title = None

    def form_valid(self, form):
        instance = form.save()
        return get_success_response(self, instance, UPDATED_MESSAGE)

    def get_object(self, queryset=None):
        pk = self.kwargs.get("pk")
        return get_object_or_404(self.model, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["modal_title"] = _(self.modal_title)
        context["is_update"] = True
        return context


# ----- Load Elements Views -----------------------------------------------
class LicenseNoFieldView(AdminLoginRequiredMixin, TemplateView):
    template_name = "datatable/structure/select_field.html"

    def get(self, request, *args, **kwargs):
        club_id = request.GET.get("club_select")

        # if club_id is empty, return no template
        if not club_id:
            return HttpResponse()

        club = Club.objects.filter(pk=club_id).first()

        form = MembershipForm()
        form.fields["license_no"].choices = get_remaining_memberships_by_club(club)

        context = super().get_context_data(**kwargs)
        context["form"] = form
        context["container_ccs_classes"] = "col-12"

        return render(
            request,
            self.template_name,
            context,
        )


# ----- Member views ----------------------------------------------------------
class MembersCardsView(AdminLoginRequiredMixin, CardTemplateView):
    translation.activate(translation.get_language())
    model = Member
    template_name = "admin/cards/members.html"
    card_title = _("Members")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["member_changes_card_title"] = _("Member Changes")
        context["member_changes_url"] = reverse_lazy("members_changes")
        context["member_changes_list_changed_event"] = CHANGED_EVENT.format(
            MemberChange.__name__.lower()
        )

        return context


class MemberListView(AdminLoginRequiredMixin, DatatableListView):
    model = Member
    template_name = "datatable/member.html"

    def get_queryset(self):
        logged_user = self.request.user
        if is_user_fstb_admin(logged_user):
            return Member.objects.prefetch_related("membership_set__club")
        else:
            club_to_admin = get_user_club(logged_user)

            return Member.objects.filter(
                membership__club=club_to_admin,
                membership__transfer_date__isnull=True,
            ).prefetch_related("membership_set__club")


class MemberCreateView(AdminLoginRequiredMixin, FormView):
    template_name = "datatable/member_create_form.html"
    form_class = MemberMembershipForm
    model = Member
    modal_title = _("Add Member")
    club_select_label = _("Select Club")

    def form_valid(self, form):
        member = (
            self.create_member(form)
            if is_user_fstb_admin(self.request.user)
            else self.create_member_change(form)
        )
        self.create_member_membership(form, member)

        # if the logged user is a FSTB Admin, can link member to user with a specific group
        self.set_user_and_specific_group(form, member)

        return get_success_response(
            self,
            member,
            ADDED_MESSAGE,
            extra_event=CHANGED_EVENT.format(Member.__name__.lower()),
        )

    @staticmethod
    def create_member(form):
        # Save the data related to Member
        member = Member.objects.create(
            photo=form.cleaned_data["photo"],
            name=form.cleaned_data["name"],
            surname=form.cleaned_data["surname"],
            house_number=form.cleaned_data["house_number"],
            street=form.cleaned_data["street"],
            city=form.cleaned_data["city"],
            zip_code=form.cleaned_data["zip_code"],
            date_of_birth=form.cleaned_data["date_of_birth"],
            nationality=form.cleaned_data["nationality"],
            affiliation_year=form.cleaned_data["affiliation_year"],
        )

        # Now, set the many-to-many relationships
        member.roles.set(form.cleaned_data["roles"])
        member.exams.set(form.cleaned_data["exams"])
        member.js.set(form.cleaned_data["js"])

        return member

    def create_member_change(self, form):
        # Save the data related to Member
        member = MemberChange.objects.create(
            photo=form.cleaned_data["photo"],
            name=form.cleaned_data["name"],
            surname=form.cleaned_data["surname"],
            house_number=form.cleaned_data["house_number"],
            street=form.cleaned_data["street"],
            city=form.cleaned_data["city"],
            zip_code=form.cleaned_data["zip_code"],
            date_of_birth=form.cleaned_data["date_of_birth"],
            nationality=form.cleaned_data["nationality"],
            affiliation_year=form.cleaned_data["affiliation_year"],
            applicant=self.request.user,  # set the applicant of the change to the logged user
        )

        # Now, set the many-to-many relationships
        member.roles.set(form.cleaned_data["roles"])
        member.exams.set(form.cleaned_data["exams"])
        member.js.set(form.cleaned_data["js"])

        return member

    def create_member_membership(self, form, member):
        # Save the data related to Membership
        selected_club = (
            form.cleaned_data["club_select"]
            if is_user_fstb_admin(self.request.user)
            else get_user_club(self.request.user)
        )

        if selected_club:
            license_no = form.cleaned_data["license_no"]
            return save_membership(self, member, selected_club, license_no)

    @staticmethod
    def set_user_and_specific_group(form, member):
        # Save the related User and User Group if they are selected
        if form.cleaned_data["user_select"]:
            selected_user = form.cleaned_data["user_select"]

            if form.cleaned_data["group_select"] and not selected_user.is_superuser:
                selected_user.groups.set(form.cleaned_data["group_select"])
                selected_user.save()

            member.user = selected_user
            member.save()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Modify form fields labels
        form.fields["club_select"].label = _(self.club_select_label)

        form.fields["license_no"].choices = []
        form.fields["license_no"].initial = None

        logged_user = self.request.user
        if is_user_club_admin(logged_user):
            logged_user_club = get_user_club(logged_user)

            # make club_select field disabled and set the initial value to the club of the logged user
            form.fields["club_select"].widget.attrs["disabled"] = True
            form.fields["club_select"].initial = logged_user_club
            form.fields["license_no"].choices = get_remaining_memberships_by_club(
                logged_user_club
            )

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["modal_title"] = _("Add Member")
        return context


class MemberDeleteView(AdminLoginRequiredMixin, DatatableDeleteView):
    model = Member

    def post(self, request, pk):
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        instance.delete()

        # remove the user from any authorization
        if instance.user:
            instance.user.groups.clear()
            instance.user.save()

        return get_success_response(self, instance, DELETED_MESSAGE)


class MemberUpdateView(AdminLoginRequiredMixin, FormView):
    model = Member
    form_class = MemberMembershipForm
    modal_title = _("Update Member")
    club_select_label = _("Select Club")
    template_name = ADD_EDIT_TEMPLATE.format("member")

    def form_valid(self, form):
        # get selected object to update
        member = self.get_object()

        # update the Member fields
        member = (
            self.update_member_fields(form, member)
            if is_user_fstb_admin(self.request.user)
            else self.register_member_change(form, member)
        )

        self.update_membership_fields(form, member)

        # if the logged user is a FSTB Admin, can update user fields
        if is_user_fstb_admin(self.request.user):
            self.update_user_fields(form, member)

        return get_success_response(self, member, UPDATED_MESSAGE)

    @staticmethod
    def update_member_fields(form, member):
        # Update the Member fields
        member.photo = form.cleaned_data["photo"]
        member.name = form.cleaned_data["name"]
        member.surname = form.cleaned_data["surname"]
        member.house_number = form.cleaned_data["house_number"]
        member.street = form.cleaned_data["street"]
        member.city = form.cleaned_data["city"]
        member.zip_code = form.cleaned_data["zip_code"]
        member.date_of_birth = form.cleaned_data["date_of_birth"]
        member.nationality = form.cleaned_data["nationality"]
        member.affiliation_year = form.cleaned_data["affiliation_year"]
        member.save()

        # set the many-to-many relationships
        member.roles.set(form.cleaned_data["roles"])
        member.exams.set(form.cleaned_data["exams"])
        member.js.set(form.cleaned_data["js"])

        return member

    def register_member_change(self, form, member):
        member_change = MemberChange.objects.create(
            photo=form.cleaned_data["photo"],
            name=form.cleaned_data["name"],
            surname=form.cleaned_data["surname"],
            house_number=form.cleaned_data["house_number"],
            street=form.cleaned_data["street"],
            city=form.cleaned_data["city"],
            zip_code=form.cleaned_data["zip_code"],
            date_of_birth=form.cleaned_data["date_of_birth"],
            nationality=form.cleaned_data["nationality"],
            affiliation_year=form.cleaned_data["affiliation_year"],
            applicant=self.request.user,
            member=member,
        )

        member_change.roles.set(form.cleaned_data["roles"])
        member_change.exams.set(form.cleaned_data["exams"])
        member_change.js.set(form.cleaned_data["js"])

        return member_change

    def update_membership_fields(self, form, member):
        club = (
            form.cleaned_data["club_select"]
            if is_user_fstb_admin(self.request.user)
            else get_user_club(self.request.user)
        )
        if club:
            license_no = form.cleaned_data["license_no"]
            save_membership(self, member, club, license_no)

    @staticmethod
    def update_user_fields(form, member):
        # Get related user
        current_user = member.user
        user_updated = form.cleaned_data["user_select"]

        # Save the related User and User Group if they are selected
        if user_updated:
            if current_user and not current_user.is_superuser:
                current_user.groups.set(form.cleaned_data["group_select"])
                current_user.save()

            else:
                if not user_updated.is_superuser:
                    user_updated.groups.set(form.cleaned_data["group_select"])
                    user_updated.save()

                member.user = user_updated
                member.save()
        else:
            member.user = None
            member.save()

            if current_user and not current_user.is_superuser:
                current_user.groups.clear()
                current_user.save()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        self.set_initial_member_fields(form)
        self.set_initial_membership_fields(form)

        if is_user_fstb_admin(self.request.user):
            self.set_initial_user_fields(form)

        return form

    def set_initial_member_fields(self, form):
        # get selected object to update
        member = self.get_object()

        # Set the initial values for Member fields
        form.fields["photo"].initial = member.photo
        form.fields["name"].initial = member.name
        form.fields["surname"].initial = member.surname
        form.fields["house_number"].initial = member.house_number
        form.fields["street"].initial = member.street
        form.fields["city"].initial = member.city
        form.fields["zip_code"].initial = member.zip_code
        form.fields["date_of_birth"].initial = member.date_of_birth
        form.fields["nationality"].initial = member.nationality
        form.fields["affiliation_year"].initial = member.affiliation_year
        form.fields["roles"].initial = member.roles.all()
        form.fields["exams"].initial = member.exams.all()
        form.fields["js"].initial = member.js.all()

    def set_initial_membership_fields(self, form):
        # get selected object to update
        member = self.get_object()

        # Modify form fields labels
        form.fields["club_select"].label = _(self.club_select_label)

        # Get related club
        club = member.current_membership.club if member.current_membership else None

        # Set initial values for Membership fields
        if club:
            form.fields["club_select"].initial = club

            choices = get_remaining_memberships_by_club(club)
            sorted_choices = sorted(
                choices
                + [
                    (
                        member.current_membership.license_no,
                        member.current_membership.full_license_no,
                    )
                ],
                key=lambda x: x[0],
            )
            form.fields["license_no"].choices = sorted_choices

            form.fields["license_no"].initial = member.current_membership.license_no

        if is_user_club_admin(self.request.user):
            form.fields["club_select"].widget.attrs["disabled"] = True

    def set_initial_user_fields(self, form):
        # get selected object to update
        member = self.get_object()

        # get related user and user group
        user = member.user

        if user:
            # change the queryset of the user_select field to include the current user
            form.fields["user_select"].queryset = form.fields[
                                                      "user_select"
                                                  ].queryset | User.objects.filter(id=user.id)

            form.fields["user_select"].initial = user.id
            form.fields["group_select"].initial = user.groups.all()

    def get_object(self, queryset=None):
        # Return the related Member object
        pk = self.kwargs.get("pk")
        return get_object_or_404(self.model, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["modal_title"] = _(self.modal_title)
        return context


# ----- Member Change Views ---------------------------------------------------
class MemberChangesListView(AdminLoginRequiredMixin, ListView):
    model = MemberChange
    template_name = "datatable/member_changes.html"

    def get_queryset(self):
        logged_user = self.request.user
        if is_user_fstb_admin(logged_user):
            member_change_unique_members = (
                MemberChange.objects.filter(status=ChangeModelStatus.PENDING.value)
                .values("member")
                .distinct()
            )

            members = []
            for member in member_change_unique_members:
                members.append(
                    MemberChange.objects.order_by("-created_at")
                    .filter(member=member["member"])
                    .first()
                )

            return members

        # else:
        #     club_to_admin = get_user_club(logged_user)
        #
        #     members_changes_memberships_changes = MemberChange.objects.filter(
        #         membership_change__club=club_to_admin,
        #         membership_change__transfer_date__isnull=True,
        #     )
        #
        #     members_changes_memberships = MemberChange.objects.filter(
        #         membership_set__club=club_to_admin,
        #         membership_set__transfer_date__isnull=True,
        #     )
        #
        #     return members_changes_memberships_changes | members_changes_memberships

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        model_name = self.model.__name__.lower()
        context["table_id"] = TABLE_ID.format(model_name)
        context["member_change_decline_url"] = "member_change_decline"
        context["member_change_approve_url"] = "member_change_approve"
        return context


class MemberChangeApproveView(FstbAdminLoginRequiredMixin, View):
    model = MemberChange

    def post(self, request, pk):
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        approve_member_changes(instance)
        return get_success_response(
            self,
            instance,
            APPROVED_MESSAGE,
            extra_event=CHANGED_EVENT.format(Member.__name__.lower()),
        )

    @staticmethod
    def get_queryset():
        return MemberChange.objects.all()


class MemberChangeDeclineView(FstbAdminLoginRequiredMixin, View):
    model = MemberChange

    def post(self, request, pk):
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        decline_member_changes(instance)
        return get_success_response(
            self,
            instance,
            APPROVED_MESSAGE,
            extra_event=CHANGED_EVENT.format(Member.__name__.lower()),
        )

    @staticmethod
    def get_queryset():
        return MemberChange.objects.all()


# ----- Club -----------------------------------------------------------------
class ClubsCardsView(FstbAdminLoginRequiredMixin, CardTemplateView):
    model = Club
    template_name = "admin/cards/clubs.html"
    card_title = _("Clubs")


class ClubListView(FstbAdminLoginRequiredMixin, DatatableListView):
    model = Club
    template_name = "datatable/club.html"


class ClubCreateView(FstbAdminLoginRequiredMixin, DatatableCreateView):
    template_name = "datatable/club_create_form.html"
    form_class = ClubForm
    model = Club
    modal_title = _("Add Club")


class ClubDeleteView(FstbAdminLoginRequiredMixin, DatatableDeleteView):
    model = Club


class ClubUpdateView(FstbAdminLoginRequiredMixin, DatatableUpdateView):
    model = Club
    form_class = ClubForm
    modal_title = _("Update Club")
    template_name = ADD_EDIT_TEMPLATE.format("club")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Add selected club license_no to the choices
        club = self.get_object()
        remaining_license_choices = Club.remaining_license_no()
        remaining_license_choices.append((club.license_no, club.full_license_no))
        sorted_choices = sorted(
            remaining_license_choices, key=lambda x: x[0]
        )  # Sort by license number
        form.fields["license_no"].choices = sorted_choices

        return form


# ----- Memberships -----------------------------------------------------------------
class MembershipsCardsView(AdminLoginRequiredMixin, CardTemplateView):
    model = Membership
    template_name = "admin/cards/memberships.html"
    card_title = _("Memberships")


class MembershipListView(AdminLoginRequiredMixin, DatatableListView):
    model = Membership
    template_name = "datatable/membership.html"

    def get_queryset(self):
        logged_user = self.request.user
        if is_user_fstb_admin(logged_user):
            return Member.objects.prefetch_related("membership_set__club")
        else:
            club_to_admin = get_user_club(logged_user)

            return Member.objects.filter(
                membership__club=club_to_admin,
                membership__transfer_date__isnull=True,
            ).prefetch_related("membership_set__club")


class MembershipDeleteView(AdminLoginRequiredMixin, DatatableDeleteView):
    model = Membership


class JoinClubView(AdminLoginRequiredMixin, DatatableUpdateView):
    model = Membership
    form_class = MembershipForm
    modal_title = _("Join a Club")
    template_name = "datatable/membership_join_club_form.html"
    club_select_label = _("Select Club")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Modify form configuration
        form.fields["club_select"].label = _(self.club_select_label)

        return form

    def get_object(self, queryset=None):
        pk = self.kwargs.get("pk")
        return get_object_or_404(Member, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["member"] = self.get_object()
        return context

    def form_valid(self, form):
        member = self.get_object()
        club = form.cleaned_data["club"]
        license_no = form.cleaned_data["license_no"]

        # Create a new membership object
        membership = save_membership(self, member, club, license_no)

        return get_success_response(self, membership, _("New Membership: {model}"))


class TransferClubView(AdminLoginRequiredMixin, DatatableUpdateView):
    model = Membership

    form_class = MembershipForm
    modal_title = _("Transfer Club")
    template_name = "datatable/membership_transfer_club_form.html"
    club_select_label = _("Transfer to Club")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Modify form configuration
        form.fields["club_select"].label = _(self.club_select_label)

        return form

    def get_object(self, queryset=None):
        pk = self.kwargs.get("pk")
        return get_object_or_404(Member, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["member"] = self.get_object()
        return context

    def form_valid(self, form):
        member = self.get_object()
        club = form.cleaned_data["club"]
        license_no = form.cleaned_data["license_no"]

        membership = save_membership(self, member, club, license_no)

        return get_success_response(self, membership, _("Transfer: {model}"))


# ----- Roles views -----------------------------------------------------------
class RolesCardsView(FstbAdminLoginRequiredMixin, CardTemplateView):
    model = Role
    template_name = "admin/cards/roles.html"
    card_title = _("Roles")


class RoleListView(FstbAdminLoginRequiredMixin, DatatableListView):
    model = Role
    template_name = "datatable/roles.html"


class RoleCreateView(FstbAdminLoginRequiredMixin, DatatableCreateView):
    template_name = "datatable/role_create_form.html"
    form_class = RoleForm
    model = Role
    modal_title = _("Add Role")


class RoleDeleteView(FstbAdminLoginRequiredMixin, DatatableDeleteView):
    model = Role


class RoleUpdateView(FstbAdminLoginRequiredMixin, DatatableUpdateView):
    model = Role
    form_class = RoleForm
    modal_title = _("Update Role")
    template_name = ADD_EDIT_TEMPLATE.format("role")


# ----- Competitions views ----------------------------------------------------
class CompetitionsCardsView(FstbAdminLoginRequiredMixin, CardTemplateView):
    model = Competition
    template_name = "admin/cards/competitions.html"
    card_title = _("Competitions")


class OpenCompetitionsCardsView(AdminLoginRequiredMixin, CardTemplateView):
    model = Competition
    template_name = "admin/cards/open_competitions.html"
    card_title = _("Open competitions")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["card_body_url"] = reverse_lazy(
            "competitions_open"
        )

        return context


class CompetitionsListView(FstbAdminLoginRequiredMixin, DatatableListView):
    model = Competition
    template_name = "datatable/competitions.html"


class OpenCompetitionsListView(AdminLoginRequiredMixin, DatatableListView):
    model = Competition
    template_name = "datatable/open_competitions.html"

    def get_queryset(self):
        return Competition.objects.filter(status="Open")


class CompetitionsCreateView(FstbAdminLoginRequiredMixin, DatatableCreateView):
    template_name = "datatable/competition_create_form.html"
    form_class = CompetitionForm
    model = Competition
    modal_title = _("Add Competition")

    def form_valid(self, form):
        competition = (
            self.create_competition(form)
        )

        competition.save()
        instance = competition

        return get_success_response(
            self,
            instance,
            ADDED_MESSAGE
        )

    @staticmethod
    def create_competition(form):
        # Save the data related to the new Competition
        competition = Competition.objects.create(
            name=form.cleaned_data["name"],
            due_date=form.cleaned_data["due_date"],
            description=form.cleaned_data["description"],
            status=form.cleaned_data["status"]
        )

        return competition


class CompetitionsDeleteView(FstbAdminLoginRequiredMixin, DatatableDeleteView):
    model = Competition


class CompetitionsUpdateView(FstbAdminLoginRequiredMixin, DatatableUpdateView):
    model = Competition
    form_class = CompetitionForm
    modal_title = _("Update Competition")
    template_name = ADD_EDIT_TEMPLATE.format("competition")


class CompetitionsDetailView(AdminLoginRequiredMixin, DatatableUpdateView):
    template_name = "datatable/competition_detail_form.html"
    form_class = CompetitionForm
    model = Competition
    modal_title = _("Competition detail")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["name"].disabled = True
        form.fields["due_date"].disabled = True
        form.fields["status"].disabled = True
        form.fields["description"].disabled = True

        return form


class CompetitionsInscribeMember(FstbAdminLoginRequiredMixin, FormView):
    model = Competition
    form_class = InscribedMemberForm
    modal_title = _("Inscribe Member")
    template_name = "datatable/competition_inscribe_member_form.html"

    def get_object(self, queryset=None):
        pk = self.kwargs.get("pk")
        return get_object_or_404(Competition, pk=pk)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["competition_select"].initial = self.get_object()

        return form

    def form_valid(self, form):
        member = form.cleaned_data["member_select"]
        competition = form.cleaned_data["competition_select"]

        member.competitions.add(competition)

        return get_success_response(self, member, _("Inscribed Member: {model}"))


# ----- Teams views ----------------------------------------------------
class TeamsCardsView(AdminLoginRequiredMixin, CardTemplateView):
    model = Team
    template_name = "admin/cards/teams.html"
    card_title = _("Teams")


class TeamsListView(AdminLoginRequiredMixin, DatatableListView):
    model = Team
    template_name = "datatable/teams.html"

    def get_queryset(self):
        logged_user = self.request.user
        if is_user_fstb_admin(logged_user):
            return Team.objects.all()
        else:
            club_to_admin = get_user_club(logged_user)

            return Team.objects.filter(
                club=club_to_admin,
            ).all()


class TeamsCreateView(AdminLoginRequiredMixin, DatatableCreateView):
    template_name = "datatable/team_create_form.html"
    form_class = TeamForm
    model = Team
    modal_title = _("Team")
    club_select_label = _("Select Club")

    def form_valid(self, form):
        logged_user = self.request.user

        logged_user_club = None
        if is_user_club_admin(logged_user):
            logged_user_club = get_user_club(logged_user)

        team = (
            self.create_team(form, logged_user_club)
        )

        team.save()
        instance = team

        return get_success_response(
            self,
            instance,
            ADDED_MESSAGE
        )

    @staticmethod
    def create_team(form, club=None):
        if club is None:
            club = form.cleaned_data["club"]

        # min_member_club_create_not_reached = form.cleaned_data["members"].count() < form.cleaned_data[
        #     "min_members_number"]

        # Save the data related to the new Team
        team = Team.objects.create(
            photo=form.cleaned_data["photo"],
            name=form.cleaned_data["name"],
            description=form.cleaned_data["description"],
            club=club,
        )

        # Now, set the many-to-many relationships
        team.members.set(form.cleaned_data["members"])

        return team

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        form.fields["club"].label = _(self.club_select_label)

        logged_user = self.request.user

        if is_user_club_admin(logged_user):
            logged_user_club = get_user_club(logged_user)
            # make club_select field disabled and set the initial value to the club of the logged user
            form.fields["club"].initial = logged_user_club
            form.fields["club"].disabled = True
            form.fields["members"].queryset = (Member.objects.filter(
                membership__club=logged_user_club,
                membership__transfer_date__isnull=True)
                                               .prefetch_related("membership_set__club"))

        return form


class TeamsDeleteView(AdminLoginRequiredMixin, DatatableDeleteView):
    model = Team


class TeamsUpdateView(AdminLoginRequiredMixin, DatatableUpdateView):
    model = Team
    form_class = TeamForm
    modal_title = _("Update team")
    template_name = ADD_EDIT_TEMPLATE.format("team")
    club_select_label = _("Select Club")

    def form_valid(self, form):
        logged_user = self.request.user
        _team = self.get_object()

        logged_user_club = None
        if is_user_club_admin(logged_user):
            logged_user_club = get_user_club(logged_user)

        team = (
            self.update_team(form, _team, logged_user_club)
        )

        team.save()
        instance = team

        return get_success_response(
            self,
            instance,
            UPDATED_MESSAGE
        )

    @staticmethod
    def update_team(form, team, logged_user_club=None):
        club = None
        if logged_user_club is not None:
            club = logged_user_club
        else:
            club = form.cleaned_data["club"]

        team.photo = form.cleaned_data["photo"]
        team.name = form.cleaned_data["name"]
        team.description = form.cleaned_data["description"]
        team.club = club

        team.members.set(form.cleaned_data["members"])

        team.save()

        return team

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        form.fields["club"].label = _(self.club_select_label)

        logged_user = self.request.user

        if is_user_club_admin(logged_user):
            logged_user_club = get_user_club(logged_user)
            # make club_select field disabled and set the initial value to the club of the logged user
            form.fields["club"].initial = logged_user_club
            form.fields["club"].disabled = True
            form.fields["members"].queryset = (Member.objects.filter(
                membership__club=logged_user_club,
                membership__transfer_date__isnull=True)
                                               .prefetch_related("membership_set__club"))

        return form


# ----- CompetitionRegistration views ----------------------------------
class CompetitionRegistrationsCardsView(AdminLoginRequiredMixin, CardTemplateView):
    model = CompetitionRegistration
    template_name = "admin/cards/competition_registration.html"
    card_title = _("Competition subscriptions")


class CompetitionRegistrationListView(AdminLoginRequiredMixin, DatatableListView):
    model = CompetitionRegistration
    template_name = "datatable/competition_registration.html"

    def get_queryset(self):
        logged_user = self.request.user
        if is_user_fstb_admin(logged_user):
            return CompetitionRegistration.objects.all()
        else:
            club_to_admin = get_user_club(logged_user)

            return CompetitionRegistration.objects.filter(
                team__club=club_to_admin,
            ).all()


class CompetitionRegistrationCreateView(AdminLoginRequiredMixin, DatatableCreateView):
    template_name = "datatable/competition_registration_create_form.html"
    form_class = CompetitionRegistrationForm
    model = CompetitionRegistration
    modal_title = _("Subscribe team to competition")

    def form_valid(self, form):
        registration = (
            self.create_registration(form)
        )

        registration.save()
        instance = registration

        return get_success_response(
            self,
            instance,
            ADDED_MESSAGE
        )

    @staticmethod
    def create_registration(form):

        discipline = form.cleaned_data["discipline"]
        division = form.cleaned_data["division"]
        team = form.cleaned_data['team']
        club = Club.objects.filter(pk=team.club.pk).first()
        status = form.cleaned_data['status']
        members = Member.objects.filter(team=team)

        if discipline.min_members_number is not None:
            if check_min_member(discipline.min_members_number, members):
                status = "Draft"

        if discipline.max_members_number is not None:
            if check_max_member(discipline.max_members_number, members):
                status = "Draft"

        if division is not None:
            year_rules = YearRule.objects.filter(division__year_rules__division=division)
            errors = check_ages(year_rules, members)
            if len(errors) > 0:
                status = "Draft"

        # Save the data related to the new Registration
        registration = CompetitionRegistration.objects.create(
            competition=form.cleaned_data["competition"],
            team=team,
            status=status,
            discipline=discipline,
            division=division,
            club=club
        )

        return registration

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        form.fields["discipline"].choices = []
        form.fields["discipline"].initial = None
        form.fields["division"].choices = []
        form.fields["division"].initial = None

        logged_user = self.request.user

        if is_user_club_admin(logged_user):
            logged_user_club = get_user_club(logged_user)
            form.fields["team"].queryset = (Team.objects.filter(
                club=logged_user_club)).all()

        return form


class GetNotPassedRulesView(AdminLoginRequiredMixin, TemplateView):
    template_name = "datatable/structure/warning_box.html"

    def get(self, request, *args, **kwargs):
        discipline_id = request.GET.get("discipline")
        division_id = request.GET.get("division")
        team_id = request.GET.get("team")

        discipline = Discipline.objects.filter(pk=discipline_id).first()
        division = Division.objects.filter(pk=division_id).first()
        team = Team.objects.filter(pk=team_id).first()

        members = Member.objects.filter(team=team)

        rules = []

        if discipline.min_members_number is not None:
            if check_min_member(discipline.min_members_number, members):
                rules.append("min_error_message")

        if discipline.max_members_number is not None:
            if check_max_member(discipline.max_members_number, members):
                rules.append("max_error_message")

        if division is not None:
            year_rules = YearRule.objects.filter(division__year_rules__division=division)
            errors = check_ages(year_rules, members)

            for error in errors:
                rules.append(error[0] + error[1] + str(error[2]))

        form = CompetitionRegistrationForm()
        context = super().get_context_data(**kwargs)
        context["form"] = form
        context["container_ccs_classes"] = "col-12"
        context["rules"] = rules

        return render(
            request,
            self.template_name,
            context,
        )


class LoadDisciplinesView(AdminLoginRequiredMixin, TemplateView):
    template_name = "datatable/structure/discipline_select_field.html"

    def get(self, request, *args, **kwargs):
        competition_id = request.GET.get("competition")

        # if competition_id is empty, return no template
        if not competition_id:
            return HttpResponse()

        competition = Competition.objects.filter(pk=competition_id).first()

        form = CompetitionRegistrationForm()
        disciplines = Discipline.objects.filter(competition=competition).all()
        choices_list = [('', '---------')]
        choices_list += [(discipline.id, discipline.name) for discipline in disciplines]

        form.fields["discipline"].choices = choices_list
        form.fields["discipline"].required = False

        context = super().get_context_data(**kwargs)
        context["form"] = form
        context["container_ccs_classes"] = "col-12"

        return render(
            request,
            self.template_name,
            context,
        )


class LoadDivisionsView(AdminLoginRequiredMixin, TemplateView):
    template_name = "datatable/structure/division_select_field.html"

    def get(self, request, *args, **kwargs):
        discipline_id = request.GET.get("discipline")

        # if discipline_id is empty, return no template
        if not discipline_id:
            return HttpResponse()

        _discipline = Discipline.objects.filter(pk=discipline_id).first()
        competition = Competition.objects.filter(pk=_discipline.competition_id).first()

        disciplines = Discipline.objects.filter(competition=competition).all()
        choices_list_discipline = [('', '---------')]
        choices_list_discipline += [(discipline.id, discipline.name) for discipline in disciplines]
        print("choices", choices_list_discipline)

        form = CompetitionRegistrationForm()
        divisions = Division.objects.filter(discipline=_discipline).all()
        choices_list = [('', '---------')]
        choices_list += [(division.id, division.name) for division in divisions]

        form.fields["discipline"].choices = choices_list_discipline
        form.fields["discipline"].required = False
        form.fields["division"].choices = choices_list
        form.fields["division"].required = False

        context = super().get_context_data(**kwargs)
        context["form"] = form
        context["container_ccs_classes"] = "col-12"

        return render(
            request,
            self.template_name,
            context,
        )


class CompetitionRegistrationDeleteView(AdminLoginRequiredMixin, DatatableDeleteView):
    model = CompetitionRegistration


class CompetitionRegistrationUpdateView(AdminLoginRequiredMixin, DatatableUpdateView):
    model = CompetitionRegistration
    form_class = CompetitionRegistrationForm
    modal_title = _("Update registration")
    template_name = ADD_EDIT_TEMPLATE.format("competition_registration")

    def form_valid(self, form):
        registration = (
            self.update_registration(form, self.get_object())
        )

        registration.save()
        instance = registration

        return get_success_response(
            self,
            instance,
            ADDED_MESSAGE
        )

    @staticmethod
    def update_registration(form, registration):
        # Update the registration fields
        registration.competition = form.cleaned_data["competition"]
        registration.discipline = form.cleaned_data["discipline"]
        registration.division = form.cleaned_data["division"]
        registration.team = form.cleaned_data["team"]
        registration.club = form.cleaned_data["club"]
        status = form.cleaned_data["status"]
        members = Member.objects.filter(team=registration.team)

        if registration.discipline.min_members_number is not None:
            if check_min_member(registration.discipline.min_members_number, members):
                status = "Draft"

        if registration.discipline.max_members_number is not None:
            if check_max_member(registration.discipline.max_members_number, members):
                status = "Draft"

        if registration.division is not None:
            year_rules = YearRule.objects.filter(division__year_rules__division=registration.division)
            errors = check_ages(year_rules, members)
            if len(errors) > 0:
                status = "Draft"

        registration.status = status
        registration.save()

        return registration

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        form.fields["competition"].disabled = True

        form.fields["discipline"].disabled = True

        form.fields["division"].disabled = True

        form.fields["team"].disabled = True

        form.fields["club"].disabled = True

        logged_user = self.request.user

        if is_user_club_admin(logged_user):
            logged_user_club = get_user_club(logged_user)
            form.fields["team"].queryset = (Team.objects.filter(
                club=logged_user_club)).all()

        return form


class ValidCompetitionRegistrationsCardsView(AdminLoginRequiredMixin, CardTemplateView):
    model = CompetitionRegistration
    template_name = "admin/cards/competition_registration.html"
    card_title = _("Registered teams")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["card_body_url"] = reverse_lazy(
            "valid_competition_registrations"
        )

        return context


class ValidCompetitionRegistrationListView(AdminLoginRequiredMixin, DatatableListView):
    model = CompetitionRegistration
    template_name = "datatable/valid_competition_registration.html"

    def get_queryset(self):
        return CompetitionRegistration.objects.filter(status="Registered")


class ValidCompetitionRegistrationDetailView(FstbAdminLoginRequiredMixin, DatatableUpdateView):
    template_name = "datatable/valid_competition_registration_detail_form.html"
    form_class = CompetitionRegistrationForm
    model = CompetitionRegistration
    modal_title = _("Team subscription information")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["team"].disabled = True
        form.fields["club"].disabled = True
        form.fields["competition"].disabled = True
        form.fields["status"].disabled = True

        return form


# ----- Rule views ----------------------------------------------------
class DivisionCardsView(FstbAdminLoginRequiredMixin, CardTemplateView):
    model = Division
    template_name = "admin/cards/rules.html"
    card_title = _("Divisions")


class DivisionListView(FstbAdminLoginRequiredMixin, DatatableListView):
    model = Division
    template_name = "datatable/rules.html"


class DivisionCreateView(FstbAdminLoginRequiredMixin, DatatableCreateView):
    template_name = "datatable/rule_create_form.html"
    form_class = DivisionForm
    model = Division
    modal_title = _("Add Division")

    def form_valid(self, form):
        division = (
            self.create_division(form)
        )

        division.save()
        instance = division

        return get_success_response(
            self,
            instance,
            ADDED_MESSAGE
        )

    @staticmethod
    def create_division(form):
        # Save the data related to the new Rule
        division = Division.objects.create(
            name=form.cleaned_data["name"],
            description=form.cleaned_data["description"],
            discipline=form.cleaned_data["discipline"]
        )

        # Now, set the many-to-many relationships
        division.exams.set(form.cleaned_data["exams"])
        division.year_rules.set(form.cleaned_data["year_rules"])

        return division


class DivisionDeleteView(FstbAdminLoginRequiredMixin, DatatableDeleteView):
    model = Division


class DivisionUpdateView(FstbAdminLoginRequiredMixin, DatatableUpdateView):
    model = Division
    form_class = DivisionForm
    modal_title = _("Update division")
    template_name = ADD_EDIT_TEMPLATE.format("rule")

    def form_valid(self, form):
        # get selected object to update
        rule = self.get_object()

        form_rule = (
            self.update_division(form, rule)
        )

        form_rule.save()
        instance = form_rule

        return get_success_response(
            self,
            instance,
            UPDATED_MESSAGE
        )

    @staticmethod
    def update_division(form, division):
        # Update the Rule fields
        division.name = form.cleaned_data["name"]
        division.description = form.cleaned_data["description"]
        division.discipline = form.cleaned_data["discipline"]
        division.save()

        # set the many-to-many relationships
        division.exams.set(form.cleaned_data["exams"])
        division.year_rules.set(form.cleaned_data["year_rules"])

        return division


# ----- Year Rule views ----------------------------------------------------
class YearRuleCardsView(FstbAdminLoginRequiredMixin, CardTemplateView):
    model = YearRule
    template_name = "admin/cards/year_rules.html"
    card_title = _("Age Rules")


class YearRulesListView(FstbAdminLoginRequiredMixin, DatatableListView):
    model = YearRule
    template_name = "datatable/year_rules.html"


class YearRuleCreateView(FstbAdminLoginRequiredMixin, DatatableCreateView):
    template_name = "datatable/year_rule_create_form.html"
    form_class = YearRuleForm
    model = YearRule
    modal_title = _("Rule")

    def form_valid(self, form):
        rule = (
            self.create_rule(form)
        )

        rule.save()
        instance = rule

        return get_success_response(
            self,
            instance,
            ADDED_MESSAGE
        )

    @staticmethod
    def create_rule(form):
        # Save the data related to the new Rule
        rule = YearRule.objects.create(
            name=form.cleaned_data["name"],
            option=form.cleaned_data["option"],
            condition=form.cleaned_data["condition"],
            value=form.cleaned_data["value"],
            description=form.cleaned_data["description"],
        )

        return rule


class YearRuleDeleteView(FstbAdminLoginRequiredMixin, DatatableDeleteView):
    model = YearRule


class YearRuleUpdateView(FstbAdminLoginRequiredMixin, DatatableUpdateView):
    model = YearRule
    form_class = YearRuleForm
    modal_title = _("Update year rule")
    template_name = ADD_EDIT_TEMPLATE.format("year_rule")

    def form_valid(self, form):
        # get selected object to update
        rule = self.get_object()

        form_rule = (
            self.update_rule(form, rule)
        )

        form_rule.save()
        instance = form_rule

        return get_success_response(
            self,
            instance,
            UPDATED_MESSAGE
        )

    @staticmethod
    def update_rule(form, rule):
        # Update the Rule fields
        rule.name = form.cleaned_data["name"]
        rule.option = form.cleaned_data["option"]
        rule.condition = form.cleaned_data["condition"]
        rule.value = form.cleaned_data["value"]
        rule.description = form.cleaned_data["description"]
        rule.save()

        return rule


# ----- Disciplines views ----------------------------------------------------
class DisciplinesCardsView(FstbAdminLoginRequiredMixin, CardTemplateView):
    model = Discipline
    template_name = "admin/cards/disciplines.html"
    card_title = _("Disciplines")


class DisciplinesListView(FstbAdminLoginRequiredMixin, DatatableListView):
    model = Discipline
    template_name = "datatable/disciplines.html"


class DisciplinesCreateView(FstbAdminLoginRequiredMixin, DatatableCreateView):
    template_name = "datatable/disciplines_create_form.html"
    form_class = DisciplinesForm
    model = Discipline
    modal_title = _("Add Disciplines")

    def form_valid(self, form):
        disciplines = (
            self.create_disciplines(form)
        )

        disciplines.save()
        instance = disciplines

        return get_success_response(
            self,
            instance,
            ADDED_MESSAGE
        )

    @staticmethod
    def create_disciplines(form):
        # Save the data related to the new Disciplines
        disciplines = Discipline.objects.create(
            name=form.cleaned_data["name"],
            description=form.cleaned_data["description"],
            min_members_number=form.cleaned_data["min_members_number"],
            max_members_number=form.cleaned_data["max_members_number"],
            competition=form.cleaned_data["competition"],
        )

        return disciplines


class DisciplinesDeleteView(FstbAdminLoginRequiredMixin, DatatableDeleteView):
    model = Discipline


class DisciplinesUpdateView(FstbAdminLoginRequiredMixin, DatatableUpdateView):
    model = Discipline
    form_class = DisciplinesForm
    modal_title = _("Update disciplines")
    template_name = ADD_EDIT_TEMPLATE.format("disciplines")

    def form_valid(self, form):
        # get selected object to update
        disciplines = self.get_object()

        form_disciplines = (
            self.update_disciplines(form, disciplines)
        )

        form_disciplines.save()
        instance = form_disciplines

        return get_success_response(
            self,
            instance,
            UPDATED_MESSAGE
        )

    @staticmethod
    def update_disciplines(form, disciplines):
        # Update the Disciplines fields
        disciplines.name = form.cleaned_data["name"]
        disciplines.description = form.cleaned_data["description"]
        disciplines.min_members_number = form.cleaned_data["min_members_number"]
        disciplines.max_members_number = form.cleaned_data["max_members_number"]
        disciplines.competition = form.cleaned_data["competition"]
        disciplines.save()

        return disciplines
