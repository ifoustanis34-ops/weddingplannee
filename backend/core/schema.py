from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object


class CookieJWTScheme(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]
    target_class = "accounts.authentication.CookieJWTAuthentication"
    name = "cookieJWT"

    def get_security_definition(self, auto_schema):  # type: ignore[no-untyped-def]
        return build_bearer_security_scheme_object(
            header_name="Authorization", token_prefix="Bearer"  # noqa: S106
        )
