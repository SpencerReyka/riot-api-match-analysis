from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import RiotAPIKeyForm, RiotIDForm
from .models import RiotAccount
from .riot import RiotAPIError, RiotClient
from .secrets import SecretStorageError, riot_api_key_status, set_riot_api_key
from .services import analyze_account, sync_account


@require_GET
def dashboard(request):
    accounts = list(RiotAccount.objects.all())
    analyses = [analyze_account(account) for account in accounts]
    return render(
        request,
        "stats/dashboard.html",
        {"form": RiotIDForm(), "analyses": analyses},
    )


@staff_member_required
@require_POST
def add_account(request):
    form = RiotIDForm(request.POST)
    if not form.is_valid():
        accounts = list(RiotAccount.objects.all())
        return render(
            request,
            "stats/dashboard.html",
            {
                "form": form,
                "analyses": [analyze_account(account) for account in accounts],
            },
            status=400,
        )

    try:
        result = sync_account(**form.cleaned_data)
    except (RiotAPIError, ValueError) as exc:
        messages.error(request, str(exc))
        return redirect("dashboard")

    messages.success(
        request,
        f"Synced {result.account.riot_id}: {result.fetched_matches} new and "
        f"{result.cached_matches} cached matches.",
    )
    return redirect("account-detail", pk=result.account.pk)


@require_GET
def account_detail(request, pk: int):
    account = get_object_or_404(RiotAccount, pk=pk)
    analysis = analyze_account(account)
    matches = account.participations.select_related("match").order_by(
        "-match__game_start"
    )
    return render(
        request,
        "stats/account_detail.html",
        {"analysis": analysis, "matches": matches},
    )


@staff_member_required
@require_POST
def refresh_account(request, pk: int):
    account = get_object_or_404(RiotAccount, pk=pk)
    try:
        result = sync_account(
            account.game_name,
            account.tag_line,
            routing_region=account.routing_region,
            platform_region=account.platform_region,
        )
    except (RiotAPIError, ValueError) as exc:
        messages.error(request, str(exc))
    else:
        messages.success(
            request,
            f"Refresh complete: {result.fetched_matches} new and "
            f"{result.cached_matches} cached matches.",
        )
    return redirect("account-detail", pk=account.pk)


@require_GET
@never_cache
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"ok": False, "database": False}, status=503)
    return JsonResponse({"ok": True, "database": True})


@staff_member_required
@never_cache
@sensitive_post_parameters("api_key")
@require_http_methods(["GET", "POST"])
def api_settings(request):
    form = RiotAPIKeyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        api_key = form.cleaned_data["api_key"]
        try:
            RiotClient(api_key).platform_status()
            set_riot_api_key(api_key, updated_by=request.user.get_username())
        except RiotAPIError as exc:
            form.add_error("api_key", str(exc))
        except SecretStorageError:
            form.add_error(
                None,
                "Encrypted credential storage is unavailable. Contact the operator.",
            )
        else:
            messages.success(request, "Riot API key validated and replaced securely.")
            return redirect("api-settings")

    return render(
        request,
        "stats/api_settings.html",
        {"form": form, "credential_status": riot_api_key_status()},
    )
