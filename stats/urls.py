from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("accounts/", views.add_account, name="add-account"),
    path("accounts/<int:pk>/", views.account_detail, name="account-detail"),
    path("accounts/<int:pk>/refresh/", views.refresh_account, name="refresh-account"),
    path("settings/riot-api/", views.api_settings, name="api-settings"),
    path("healthz", views.health, name="health"),
]
