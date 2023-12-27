# ----- Django Imports -----------------------------------------------------------------
from django.urls import path

# ----- Core Imports -------------------------------------------------------------------
from .views import (
    # ----- General Views ---------------------------
    HomeView,
    # ----- Auth Views ------------------------------
    RegisterView,
    LoginView,
    # ----- Load Elements Views ---------------------
    LicenseNoFieldView,
    # ----- Members ---------------------------------
    MemberListView,
    MembersCardsView,
    MemberCreateView,
    MemberDeleteView,
    MemberUpdateView,
    # ----- Member Changes --------------------------
    MemberChangesListView,
    MemberChangeApproveView,
    MemberChangeDeclineView,
    # ----- Clubs -----------------------------------
    ClubListView,
    ClubsCardsView,
    ClubCreateView,
    ClubDeleteView,
    ClubUpdateView,
    # ----- Memberships -----------------------------
    MembershipListView,
    MembershipsCardsView,
    MembershipDeleteView,
    JoinClubView,
    TransferClubView,
    # ----- Roles -----------------------------------
    RoleListView,
    RolesCardsView,
    RoleCreateView,
    RoleDeleteView,
    RoleUpdateView,
    # ----- Competitions ----------------------------
    CompetitionsCardsView,
    CompetitionsListView,
    CompetitionsCreateView,
    CompetitionsDeleteView,
    CompetitionsUpdateView,
    CompetitionsInscribeMember,
    # ----- Teams------- ----------------------------
    TeamsCardsView, TeamsListView, TeamsCreateView, TeamsDeleteView, TeamsUpdateView,
    # ----- Competitions Registration ---------------
    CompetitionRegistrationsCardsView, CompetitionRegistrationListView, CompetitionRegistrationCreateView,
    CompetitionRegistrationDeleteView, CompetitionRegistrationUpdateView, OpenCompetitionsCardsView,
    OpenCompetitionsListView, CompetitionsDetailView, ValidCompetitionRegistrationsCardsView,
    ValidCompetitionRegistrationDetailView, ValidCompetitionRegistrationListView, DivisionCardsView, DivisionListView,
    DivisionCreateView, DivisionUpdateView, DivisionDeleteView, DisciplinesCardsView, DisciplinesListView,
    DisciplinesCreateView, DisciplinesDeleteView, DisciplinesUpdateView, YearRuleCardsView, YearRulesListView,
    YearRuleCreateView, YearRuleDeleteView, YearRuleUpdateView, LoadDisciplinesView, LoadDivisionsView,
    GetNotPassedRulesView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("accounts/register/", RegisterView.as_view(), name="register"),
    path("accounts/login/", LoginView.as_view(), name="login"),
    path("accounts/logout/", LoginView.as_view(), name="logout"),
    # ----- Members -------------------------------------------------------------
    path("members/view", MembersCardsView.as_view(), name="members_view"),
    path("members/", MemberListView.as_view(), name="members"),
    path("members/create/", MemberCreateView.as_view(), name="add_member"),
    path("members/<int:pk>/remove/", MemberDeleteView.as_view(), name="remove_member"),
    path("members/<int:pk>/edit", MemberUpdateView.as_view(), name="edit_member"),
    # ----- Clubs ---------------------------------------------------------------
    path("clubs/view", ClubsCardsView.as_view(), name="clubs_view"),
    path("clubs/", ClubListView.as_view(), name="clubs"),
    path("clubs/create/", ClubCreateView.as_view(), name="add_club"),
    path("clubs/<int:pk>/remove/", ClubDeleteView.as_view(), name="remove_club"),
    path("clubs/<int:pk>/edit", ClubUpdateView.as_view(), name="edit_club"),
    # ----- Memberships ---------------------------------------------------------
    path("memberships/view", MembershipsCardsView.as_view(), name="memberships_view"),
    path("memberships/", MembershipListView.as_view(), name="memberships"),
    path(
        "memberschips/changes/", MemberChangesListView.as_view(), name="members_changes"
    ),
    path(
        "memberschips/changes/<int:pk>/approve",
        MemberChangeApproveView.as_view(),
        name="member_change_approve",
    ),
    path(
        "memberschips/changes/<int:pk>/decline",
        MemberChangeDeclineView.as_view(),
        name="member_change_decline",
    ),
    path(
        "memberships/<int:pk>/remove/",
        MembershipDeleteView.as_view(),
        name="remove_membership",
    ),
    path(
        "memberships/<int:pk>/join_club/",
        JoinClubView.as_view(),
        name="membership_join_club",
    ),
    path(
        "memberships/load_license_no_field",
        LicenseNoFieldView.as_view(),
        name="load_license_no_field",
    ),
    path(
        "memberships/<int:pk>/transfer_club",
        TransferClubView.as_view(),
        name="membership_transfer_club",
    ),
    # ----- Roles ---------------------------------------------------------------
    path("roles/view", RolesCardsView.as_view(), name="roles_view"),
    path("roles/", RoleListView.as_view(), name="roles"),
    path("roles/create/", RoleCreateView.as_view(), name="add_role"),
    path("roles/<int:pk>/remove/", RoleDeleteView.as_view(), name="remove_role"),
    path("roles/<int:pk>/edit", RoleUpdateView.as_view(), name="edit_role"),
    # ----- Competitions --------------------------------------------------------
    path("competitions/view", CompetitionsCardsView.as_view(), name="competitions_view"),
    path("competitions/", CompetitionsListView.as_view(), name="competitions"),
    path("competitions/open/view", OpenCompetitionsCardsView.as_view(), name="competitions_open_view"),
    path("competitions/open", OpenCompetitionsListView.as_view(), name="competitions_open"),
    path("competitions/create/", CompetitionsCreateView.as_view(), name="add_competition"),
    path("competitions/<int:pk>/remove/", CompetitionsDeleteView.as_view(), name="remove_competition"),
    path("competitions/<int:pk>/edit", CompetitionsUpdateView.as_view(), name="edit_competition"),
    path("competitions/<int:pk>/detail", CompetitionsDetailView.as_view(), name="detail_competition"),
    path("competitions/<int:pk>/inscribe_member", CompetitionsInscribeMember.as_view(), name="inscribe_member"),
    # ----- Teams --------------------------------------------------------
    path(
        "teams/view", TeamsCardsView.as_view(), name="teams_view"
    ),
    path("teams/", TeamsListView.as_view(), name="teams"),
    path(
        "teams/create/", TeamsCreateView.as_view(), name="add_team"
    ),
    path(
        "teams/<int:pk>/remove/",
        TeamsDeleteView.as_view(),
        name="remove_team",
    ),
    path(
        "teams/<int:pk>/edit",
        TeamsUpdateView.as_view(),
        name="edit_team",
    ),
    # ----- CompetitionsRegistration ------------------------------------
    path(
        "competition-registration/view", CompetitionRegistrationsCardsView.as_view(),
        name="competition_registrations_view"
    ),
    path("competition-registration/", CompetitionRegistrationListView.as_view(), name="competition registrations"),
    path(
        "competition-registration/create/", CompetitionRegistrationCreateView.as_view(),
        name="add_competitionregistration"
    ),
    path(
        "competition-registration/<int:pk>/remove/",
        CompetitionRegistrationDeleteView.as_view(),
        name="remove_competitionregistration",
    ),
    path(
        "competition-registration/<int:pk>/edit",
        CompetitionRegistrationUpdateView.as_view(),
        name="edit_competitionregistration",
    ),
    path("valid-competition-registration/view", ValidCompetitionRegistrationsCardsView.as_view(),
         name="valid_competition_registrations_view"),
    path("valid-competition-registration", ValidCompetitionRegistrationListView.as_view(),
         name="valid_competition_registrations"),
    path("valid-competition-registration/<int:pk>/detail", ValidCompetitionRegistrationDetailView.as_view(),
         name="detail_competitionregistration"),
    path(
        "competition-registration/load_disciplines",
        LoadDisciplinesView.as_view(),
        name="load_disciplines",
    ),
    path(
        "competition-registration/load_divisions",
        LoadDivisionsView.as_view(),
        name="load_divisions",
    ),
    path(
        "check_rules",
        GetNotPassedRulesView.as_view(),
        name="check_rules",
    ),
    # ----- Rules --------------------------------------------------------
    path(
        "divisions/view", DivisionCardsView.as_view(), name="divisions_view"
    ),
    path("divisions/", DivisionListView.as_view(), name="divisions"),
    path(
        "divisions/create/", DivisionCreateView.as_view(), name="add_division"
    ),
    path(
        "divisions/<int:pk>/remove/",
        DivisionDeleteView.as_view(),
        name="remove_division",
    ),
    path(
        "divisions/<int:pk>/edit",
        DivisionUpdateView.as_view(),
        name="edit_division",
    ),
    # ----- Year Rules --------------------------------------------------------
    path(
        "year-rules/view", YearRuleCardsView.as_view(), name="year_rules_view"
    ),
    path("year-rules/", YearRulesListView.as_view(), name="year rules"),
    path(
        "year-rules/create/", YearRuleCreateView.as_view(), name="add_yearrule"
    ),
    path(
        "year-rules/<int:pk>/remove/",
        YearRuleDeleteView.as_view(),
        name="remove_yearrule",
    ),
    path(
        "year-rules/<int:pk>/edit",
        YearRuleUpdateView.as_view(),
        name="edit_yearrule",
    ),
    # ----- Disciplines --------------------------------------------------------
    path(
        "disciplines/view", DisciplinesCardsView.as_view(), name="disciplines_view"
    ),
    path("disciplines/", DisciplinesListView.as_view(), name="disciplines"),
    path(
        "disciplines/create/", DisciplinesCreateView.as_view(), name="add_discipline"
    ),
    path(
        "disciplines/<int:pk>/remove/",
        DisciplinesDeleteView.as_view(),
        name="remove_discipline",
    ),
    path(
        "disciplines/<int:pk>/edit",
        DisciplinesUpdateView.as_view(),
        name="edit_discipline",
    ),
]
