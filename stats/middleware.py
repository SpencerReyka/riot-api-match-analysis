class SecurityHeadersMiddleware:
    """Apply a restrictive browser policy without breaking Django's admin UI."""

    PUBLIC_CSP = "; ".join(
        (
            "default-src 'self'",
            "base-uri 'none'",
            "connect-src 'self'",
            "font-src 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "img-src 'self' data:",
            "object-src 'none'",
            "script-src 'none'",
            "style-src 'self'",
        )
    )
    ADMIN_CSP = PUBLIC_CSP.replace("script-src 'none'", "script-src 'self'")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Content-Security-Policy"] = (
            self.ADMIN_CSP if request.path.startswith("/admin/") else self.PUBLIC_CSP
        )
        response["Permissions-Policy"] = (
            "camera=(), display-capture=(), geolocation=(), microphone=(), "
            "payment=(), usb=()"
        )
        response["Cross-Origin-Resource-Policy"] = "same-origin"
        return response
