"""Error catalog: definitions attached to every ``ErrorCode``.

Mirrors ``@omnixys/contracts-ts`` ``error-definition.ts``. The catalog defines
the stable public contract (summary, default message, HTTP status, retryability)
plus the metadata keys that are safe to expose per code.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Final

from omnixys_graphql.contracts.error_code import ErrorCode

__all__ = [
    "ERROR_CATALOG_VERSION",
    "ErrorDefinition",
    "get_error_definition",
    "get_public_error_metadata",
    "is_known_error_code",
]

ERROR_CATALOG_VERSION: Final[str] = "1.0.0"


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    code: str
    summary: str
    default_message: str
    http_status: int
    retryable: bool
    public_metadata_keys: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "summary": self.summary,
            "defaultMessage": self.default_message,
            "httpStatus": self.http_status,
            "retryable": self.retryable,
            "publicMetadataKeys": list(self.public_metadata_keys),
        }


def _definition(
    summary: str,
    default_message: str,
    http_status: int,
    *,
    retryable: bool = False,
) -> ErrorDefinition:
    return ErrorDefinition(
        code="",
        summary=summary,
        default_message=default_message,
        http_status=http_status,
        retryable=retryable,
    )


def _internal_definition(summary: str) -> ErrorDefinition:
    return _definition(summary, "An unexpected error occurred.", 500)


def _inferred_definition(code: str) -> ErrorDefinition:
    summary = _title_case(code) + "."

    if code.endswith("_NOT_FOUND"):
        return _definition(summary, "The requested resource was not found.", 404)
    if "ACCESS_DENIED" in code or "FORBIDDEN" in code or code == ErrorCode.UNAUTHORIZED_TENANT:
        return _definition(summary, "Access to the requested resource is denied.", 403)
    if (
        "ALREADY" in code
        or "CONFLICT" in code
        or "DUPLICATE" in code
        or code == ErrorCode.SEAT_OCCUPIED
    ):
        return _definition(summary, "The request conflicts with the current state.", 409)
    if "UNAVAILABLE" in code or code in {
        ErrorCode.KAFKA_UNAVAILABLE,
        ErrorCode.CACHE_UNAVAILABLE,
        ErrorCode.MINIO_UNAVAILABLE,
    }:
        return _definition(
            summary,
            "A required service is temporarily unavailable.",
            503,
            retryable=True,
        )
    if (
        "INVALID" in code
        or "EXPIRED" in code
        or "REVOKED" in code
        or "REQUIRED" in code
        or "MISSING" in code
        or "CLOSED" in code
        or "STATE" in code
        or "LIMIT_REACHED" in code
        or "CAPACITY_EXCEEDED" in code
    ):
        return _definition(summary, "The request cannot be processed.", 400)
    return _definition(summary, "The request could not be completed.", 500)


def _title_case(code: str) -> str:
    words = code.lower().split("_")
    words[0] = words[0].capitalize()
    return " ".join(words)


_PUBLIC_METADATA_KEYS: dict[str, tuple[str, ...]] = {
    ErrorCode.VALIDATION_ERROR: ("field", "fields", "constraint"),
    ErrorCode.AUTHENTICATION_INPUT_INVALID: ("field", "fields"),
    ErrorCode.AUTHENTICATION_PASSWORD_POLICY: ("field",),
    ErrorCode.AUTHENTICATION_USER_ALREADY_EXISTS: ("field",),
    ErrorCode.USER_NOT_FOUND: ("userId", "identifier"),
    ErrorCode.USER_ALREADY_EXISTS: ("field",),
    ErrorCode.USERNAME_ALREADY_EXISTS: ("field",),
    ErrorCode.USER_EMAIL_ALREADY_EXISTS: ("field",),
    ErrorCode.EVENT_NOT_FOUND: ("eventId",),
    ErrorCode.EVENT_CLOSED: ("eventId",),
    ErrorCode.EVENT_ACCESS_DENIED: ("eventId",),
    ErrorCode.EVENT_MEMBER_NOT_FOUND: ("eventId", "userId"),
    ErrorCode.EVENT_TIMELINE_NOT_FOUND: ("eventId", "timelineIds"),
    ErrorCode.EVENT_MEDIA_NOT_FOUND: ("mediaId",),
    ErrorCode.EVENT_MEDIA_VARIANT_NOT_FOUND: ("mediaId",),
    ErrorCode.SEAT_NOT_FOUND: ("seatId",),
    ErrorCode.SEAT_OCCUPIED: ("seatId", "sectionId"),
    ErrorCode.SEAT_ALREADY_RESERVED: ("seatId",),
    ErrorCode.SEAT_CAPACITY_EXCEEDED: ("sectionId", "capacity", "requested"),
    ErrorCode.SEAT_ASSIGNMENT_NOT_FOUND: ("seatId", "userId"),
    ErrorCode.SECTION_NOT_FOUND: ("sectionId",),
    ErrorCode.TABLE_NOT_FOUND: ("tableId",),
    ErrorCode.LAYOUT_VERSION_NOT_FOUND: ("layoutVersionId",),
    ErrorCode.INVITATION_NOT_FOUND: ("invitationId",),
    ErrorCode.INVITATION_LIMIT_REACHED: ("eventId", "limit"),
    ErrorCode.TICKET_NOT_FOUND: ("ticketId",),
    ErrorCode.TICKET_ALREADY_SCANNED: ("ticketId",),
    ErrorCode.TICKET_ALREADY_REDEEMED: ("ticketId",),
    ErrorCode.NOTIFICATION_NOT_FOUND: ("notificationId",),
    ErrorCode.NOTIFICATION_CHANNEL_UNAVAILABLE: ("channel",),
    ErrorCode.TEMPLATE_NOT_FOUND: ("templateId", "key"),
    ErrorCode.SHOPPING_CART_NOT_FOUND: ("shoppingCartId",),
    ErrorCode.SHOPPING_CART_ITEM_NOT_FOUND: ("shoppingCartId", "inventoryId"),
    ErrorCode.SHOPPING_CART_QUANTITY_INVALID: ("field", "minimum"),
    ErrorCode.TENANT_HEADER_MISSING: ("tenantId",),
    ErrorCode.TENANT_HEADER_INVALID: ("tenantId",),
    ErrorCode.TENANT_NOT_FOUND: ("tenantId",),
    ErrorCode.TENANT_DISABLED: ("tenantId", "status"),
    ErrorCode.TENANT_MEMBERSHIP_NOT_FOUND: ("tenantId", "userId"),
    ErrorCode.TENANT_MEMBERSHIP_DENIED: ("tenantId", "userId", "reason"),
    ErrorCode.TENANT_MEMBERSHIP_INACTIVE: ("tenantId", "userId", "status"),
    ErrorCode.TENANT_SERVICE_UNAVAILABLE: ("tenantId", "userId", "reason"),
    ErrorCode.TENANT_CONTEXT_UNVERIFIED: ("tenantId",),
}

_EXPLICIT_DEFINITIONS: dict[str, ErrorDefinition] = {
    ErrorCode.INVALID_CREDENTIALS: _definition(
        "Authentication failed.",
        "The supplied credentials are invalid.",
        401,
    ),
    ErrorCode.UNAUTHENTICATED: _definition(
        "Authentication required.",
        "Authentication is required.",
        401,
    ),
    ErrorCode.UNAUTHORIZED: _definition(
        "Authentication required.",
        "Authentication is required.",
        401,
    ),
    ErrorCode.FORBIDDEN: _definition(
        "Access denied.",
        "You are not allowed to perform this operation.",
        403,
    ),
    ErrorCode.ACCESS_DENIED: _definition(
        "Access denied.",
        "You are not allowed to access this resource.",
        403,
    ),
    ErrorCode.VALIDATION_ERROR: _definition(
        "Validation failed.",
        "The supplied input is invalid.",
        400,
    ),
    ErrorCode.NOT_FOUND: _definition(
        "Resource not found.",
        "The requested resource was not found.",
        404,
    ),
    ErrorCode.CONFLICT: _definition(
        "Request conflict.",
        "The request conflicts with the current state.",
        409,
    ),
    ErrorCode.INTERNAL_SERVER_ERROR: _definition(
        "Internal service error.",
        "An unexpected error occurred.",
        500,
    ),
    ErrorCode.SERVICE_UNAVAILABLE: _definition(
        "Service unavailable.",
        "The service is temporarily unavailable.",
        503,
        retryable=True,
    ),
    ErrorCode.DEPENDENCY_UNAVAILABLE: _definition(
        "Dependency unavailable.",
        "A dependent service is temporarily unavailable.",
        503,
        retryable=True,
    ),
    ErrorCode.NETWORK_ERROR: _definition(
        "Network request failed.",
        "A dependent service could not be reached.",
        503,
        retryable=True,
    ),
    ErrorCode.RATE_LIMIT_EXCEEDED: _definition(
        "Rate limit exceeded.",
        "Too many requests.",
        429,
        retryable=True,
    ),
    ErrorCode.IDENTITY_PROVIDER_UNAVAILABLE: _definition(
        "Identity provider unavailable.",
        "The identity provider is temporarily unavailable.",
        503,
        retryable=True,
    ),
    ErrorCode.IDENTITY_PROVIDER_CLIENT_CONFIGURATION_INVALID: _definition(
        "Identity provider client configuration is invalid.",
        "Authentication is temporarily unavailable.",
        500,
    ),
    ErrorCode.IDENTITY_PROVIDER_ADMIN_CREDENTIALS_INVALID: _definition(
        "Identity provider administrator authentication failed.",
        "Identity provider administrator credentials are invalid.",
        401,
    ),
    ErrorCode.IDENTITY_PROVIDER_ADMIN_FORBIDDEN: _definition(
        "Identity provider administrator access denied.",
        "The identity provider administrator lacks the required permissions.",
        403,
    ),
    ErrorCode.IDENTITY_PROVIDER_RATE_LIMITED: _definition(
        "Identity provider rate limit exceeded.",
        "The identity provider is temporarily rate limited.",
        429,
        retryable=True,
    ),
    ErrorCode.IDENTITY_PROVIDER_RESPONSE_INVALID: _definition(
        "Identity provider response is invalid.",
        "The identity provider returned an invalid response.",
        502,
        retryable=True,
    ),
    ErrorCode.IDENTITY_PROVIDER_REQUEST_REJECTED: _definition(
        "Identity provider rejected the request.",
        "The identity provider rejected the request.",
        400,
    ),
    ErrorCode.AUTHENTICATION_PASSWORD_POLICY: _definition(
        "Password policy validation failed.",
        "The password does not meet the policy requirements.",
        400,
    ),
    ErrorCode.AUTHENTICATION_UNAUTHORIZED: _definition(
        "Authentication operation forbidden.",
        "You are not authorized to perform this authentication operation.",
        403,
    ),
    ErrorCode.AUTHENTICATION_INTERNAL_ERROR: _internal_definition(
        "Authentication service error.",
    ),
    ErrorCode.ANALYTICS_API_KEY_REQUIRED: _definition(
        "Analytics API key required.",
        "An analytics API key is required.",
        401,
    ),
    ErrorCode.ANALYTICS_API_KEY_INVALID: _definition(
        "Analytics API key invalid.",
        "The analytics API key is invalid.",
        401,
    ),
    ErrorCode.ANALYTICS_API_KEY_EXPIRED: _definition(
        "Analytics API key expired.",
        "The analytics API key has expired.",
        401,
    ),
    ErrorCode.ANALYTICS_API_KEY_REVOKED: _definition(
        "Analytics API key revoked.",
        "The analytics API key has been revoked.",
        401,
    ),
    ErrorCode.ANALYTICS_SCOPE_FORBIDDEN: _definition(
        "Analytics scope denied.",
        "The analytics API key lacks the required scope.",
        403,
    ),
    ErrorCode.SHOPPING_CART_QUANTITY_INVALID: _definition(
        "Shopping cart quantity invalid.",
        "The shopping cart quantity is invalid.",
        400,
    ),
    ErrorCode.ANALYTICS_INTERNAL_ERROR: _internal_definition("Analytics service error."),
    ErrorCode.BLOG_INTERNAL_ERROR: _internal_definition("Blog service error."),
    ErrorCode.EVENT_INTERNAL_ERROR: _internal_definition("Event service error."),
    ErrorCode.GATEWAY_INTERNAL_ERROR: _internal_definition("Gateway error."),
    ErrorCode.INVITATION_INTERNAL_ERROR: _internal_definition("Invitation service error."),
    ErrorCode.NOTIFICATION_INTERNAL_ERROR: _internal_definition("Notification service error."),
    ErrorCode.PROFILE_INTERNAL_ERROR: _internal_definition("Profile service error."),
    ErrorCode.SEAT_INTERNAL_ERROR: _internal_definition("Seat service error."),
    ErrorCode.SHOPPING_CART_INTERNAL_ERROR: _internal_definition("Shopping cart service error."),
    ErrorCode.TICKET_INTERNAL_ERROR: _internal_definition("Ticket service error."),
    ErrorCode.USER_INTERNAL_ERROR: _internal_definition("User service error."),
    ErrorCode.TENANT_HEADER_MISSING: _definition(
        "Tenant header missing.",
        "A tenant context is required for this operation.",
        400,
    ),
    ErrorCode.TENANT_HEADER_INVALID: _definition(
        "Tenant header invalid.",
        "The supplied tenant identifier is invalid.",
        400,
    ),
    ErrorCode.TENANT_NOT_FOUND: _definition(
        "Tenant not found.",
        "The requested tenant does not exist.",
        404,
    ),
    ErrorCode.TENANT_DISABLED: _definition(
        "Tenant disabled.",
        "The requested tenant is not active.",
        403,
    ),
    ErrorCode.TENANT_MEMBERSHIP_NOT_FOUND: _definition(
        "Tenant membership not found.",
        "No membership exists for this user in the tenant.",
        403,
    ),
    ErrorCode.TENANT_MEMBERSHIP_DENIED: _definition(
        "Tenant membership denied.",
        "The user has no active membership in the tenant.",
        403,
    ),
    ErrorCode.TENANT_MEMBERSHIP_INACTIVE: _definition(
        "Tenant membership inactive.",
        "The user's membership in the tenant is not active.",
        403,
    ),
    ErrorCode.TENANT_SERVICE_UNAVAILABLE: _definition(
        "Tenant service unavailable.",
        "The tenant service is temporarily unavailable.",
        503,
        retryable=True,
    ),
    ErrorCode.TENANT_CONTEXT_UNVERIFIED: _internal_definition("Tenant context unverified."),
}


def _build_catalog() -> dict[str, ErrorDefinition]:
    catalog: dict[str, ErrorDefinition] = {}
    for code in ErrorCode:
        explicit = _EXPLICIT_DEFINITIONS.get(code)
        if explicit is None:
            explicit = _inferred_definition(code.value)
        catalog[code.value] = replace(
            explicit,
            code=code.value,
            public_metadata_keys=_PUBLIC_METADATA_KEYS.get(code, ()),
        )
    return catalog


ERROR_DEFINITIONS: dict[str, ErrorDefinition] = _build_catalog()


def get_error_definition(code: str) -> ErrorDefinition:
    """Return the definition for ``code`` or a generic internal-error default."""
    found = ERROR_DEFINITIONS.get(code)
    if found is not None:
        return found
    return ErrorDefinition(
        code=code,
        summary="Internal service error.",
        default_message="An unexpected error occurred.",
        http_status=500,
        retryable=False,
    )


def is_known_error_code(code: str) -> bool:
    """Return ``True`` when ``code`` has a definition in the catalog."""
    return code in ERROR_DEFINITIONS


def get_public_error_metadata(code: str, metadata: dict[str, object] | None) -> dict[str, object]:
    """Filter ``metadata`` down to the keys that are safe to expose for ``code``."""
    if not metadata:
        return {}
    allowed = set(get_error_definition(code).public_metadata_keys)
    return {key: value for key, value in metadata.items() if key in allowed}
