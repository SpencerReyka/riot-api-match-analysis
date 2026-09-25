from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import PublicAnalysisRequestForm, RiotAPIKeyForm, RiotIDForm
from .models import AnalysisRequest, RiotAccount
from .public_requests import AnalysisQueueFull, submit_analysis_request
from .rate_limits import PublicRateLimitExceeded, requester_hash
from .riot import RiotAPIError, RiotClient
from .secrets import SecretStorageError, riot_api_key_status, set_riot_api_key
from .services import analyze_account, sync_account


@require_GET
@never_cache
def landing(request):
    return render(request, "stats/landing.html", {"form": PublicAnalysisRequestForm()})


@require_POST
@never_cache
def request_analysis(request):
    if not settings.RIOT_PUBLIC_REQUESTS_ENABLED:
        return render(
            request,
            "stats/landing.html",
            {
                "form": PublicAnalysisRequestForm(request.POST),
                "submission_error": (
                    "Public requests are staged until an approved Riot production key is active."
                ),
            },
            status=503,
        )

    form = PublicAnalysisRequestForm(request.POST)
    if not form.is_valid():
        return render(request, "stats/landing.html", {"form": form}, status=400)
    try:
        result = submit_analysis_request(
            game_name=form.cleaned_data["game_name"],
            tag_line=form.cleaned_data["tag_line"],
            requester_hash=requester_hash(request),
        )
    except PublicRateLimitExceeded as exc:
        response = render(
            request,
            "stats/landing.html",
            {"form": form, "submission_error": str(exc)},
            status=429,
        )
        response["Retry-After"] = "600"
        return response
    except AnalysisQueueFull as exc:
        response = render(
            request,
            "stats/landing.html",
            {"form": form, "submission_error": str(exc)},
            status=503,
        )
        response["Retry-After"] = "60"
        return response
    return redirect("analysis-request-status", request_id=result.request.id)


@require_GET
@never_cache
def analysis_request_status(request, request_id):
    request_row = get_object_or_404(
        AnalysisRequest.objects.select_related("account"), pk=request_id
    )
    analysis = None
    matches = None
    if request_row.status == AnalysisRequest.Status.COMPLETE and request_row.account:
        analysis = analyze_account(request_row.account)
        matches = request_row.account.participations.select_related("match").order_by(
            "-match__game_start"
        )
    response = render(
        request,
        "stats/request_status.html",
        {"analysis_request": request_row, "analysis": analysis, "matches": matches},
    )
    response["Cache-Control"] = "no-store"
    if request_row.status in (
        AnalysisRequest.Status.QUEUED,
        AnalysisRequest.Status.PROCESSING,
    ):
        response["Retry-After"] = "5"
        response["Refresh"] = "5"
    return response


@staff_member_required
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


@staff_member_required
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
