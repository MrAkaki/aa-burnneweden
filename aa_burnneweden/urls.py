from django.urls import path

from . import views

app_name = "aa_burnneweden"

urlpatterns = [
    path("", views.index, name="index"),
    path("main/", views.main_view, name="main_view"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("runner/", views.contracts_runner, name="contracts_runner"),
    path("staff/", views.contracts_staff, name="contracts_staff"),
    path("<int:pk>/", views.contract_detail, name="contract_detail"),
    path("<int:pk>/complete/", views.contract_complete, name="contract_complete"),
    path("<int:pk>/cancel/", views.contract_cancel, name="contract_cancel"),
    path("<int:pk>/reject/", views.contract_reject, name="contract_reject"),
    path("<int:pk>/reassign/", views.contract_reassign, name="contract_reassign"),
    path("sync/", views.puller_sync, name="puller_sync"),
    path("puller/add-character/", views.puller_add_character, name="puller_add_character"),
    path("puller/remove-character/", views.puller_remove_character, name="puller_remove_character"),
    path("discord-settings/", views.discord_settings, name="discord_settings"),
    path("admin/config/", views.admin_config, name="admin_config"),
    path("admin/sync/", views.admin_sync, name="admin_sync"),
    path("corp-sso/post-auth/", views.corp_sso_post_auth, name="corp_sso_post_auth"),
]
