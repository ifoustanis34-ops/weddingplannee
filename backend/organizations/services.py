from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from core.exceptions import BusinessError

from .models import Organization

RESERVED_SLUGS = frozenset(
    {"www", "app", "api", "admin", "static", "mail", "support", "docs", "status"}
)
SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,30}[a-z0-9])$")
TRIAL_DAYS = 14
ORG_CACHE_TIMEOUT = 300  # 5 minutes (CLAUDE.md §5)


@dataclass(frozen=True)
class SlugCheck:
    slug: str
    available: bool
    reason: str | None = None


def _slug_cache_key(slug: str) -> str:
    return f"tenant:slug:{slug}"


def check_slug(slug: str) -> SlugCheck:
    slug = slug.strip().lower()
    if not SLUG_PATTERN.match(slug):
        return SlugCheck(
            slug,
            False,
            "De 3 à 32 caractères : lettres minuscules, chiffres et tirets, "
            "sans tiret au début ni à la fin.",
        )
    if slug in RESERVED_SLUGS:
        return SlugCheck(slug, False, "Cette adresse est réservée. Choisissez-en une autre.")
    if Organization.objects.filter(slug=slug).exists():
        return SlugCheck(slug, False, "Cette adresse est déjà utilisée.")
    return SlugCheck(slug, True)


def suggest_slug(name: str) -> str:
    """Propose an available slug derived from the company name (``maison-elegance-2``...)."""
    base = slugify(name)[:28].strip("-") or "agence"
    if len(base) < 3:
        base = f"{base}-events"
    candidate = base
    suffix = 2
    while not check_slug(candidate).available:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def get_active_organization_by_slug(slug: str) -> Organization | None:
    """Tenant lookup cached 5 min in Redis (db 1). Invalidated by ``invalidate_organization``."""
    key = _slug_cache_key(slug)
    organization: Organization | None = cache.get(key)
    if organization is None:
        organization = Organization.objects.filter(slug=slug, is_active=True).first()
        if organization is not None:
            cache.set(key, organization, ORG_CACHE_TIMEOUT)
    return organization


def invalidate_organization(organization: Organization, *, old_slug: str | None = None) -> None:
    cache.delete(_slug_cache_key(organization.slug))
    if old_slug and old_slug != organization.slug:
        cache.delete(_slug_cache_key(old_slug))


def create_organization(
    *,
    name: str,
    slug: str,
    city: str,
    country: str,
    weddings_per_year: int | None = None,
    plan: str = Organization.Plan.PRO,
    weddings_enabled: bool = False,
) -> Organization:
    """Create a company space with its 14-day Pro trial (called inside the signup transaction)."""
    organization = Organization.objects.create(
        name=name,
        slug=slug,
        city=city,
        country=country.upper(),
        weddings_per_year=weddings_per_year,
        weddings_enabled=weddings_enabled,
        plan=plan,
        trial_ends_at=timezone.now() + timedelta(days=TRIAL_DAYS),
    )
    bootstrap_organization(organization)
    return organization


def bootstrap_organization(organization: Organization) -> None:
    """Default data of a new space.

    Document numbering starts lazily (``organizations.numbering``).
    """
    from catalog.defaults import create_sample_catalog
    from core.tenant import tenant_context
    from events.defaults import ensure_standard_tasks
    from finance.defaults import ensure_expense_categories
    from stock.defaults import ensure_item_categories

    with tenant_context(organization):
        create_sample_catalog()
        ensure_standard_tasks()
        ensure_expense_categories()
        ensure_item_categories()


UPDATABLE_FIELDS = (
    "name",
    "city",
    "country",
    "currency",
    "timezone",
    "legal_mentions",
    "quote_prefix",
    "quote_validity_days",
    "weddings_per_year",
    "alert_digest",
    "deposit_kept_on_cancel",
    "weddings_enabled",
)


@transaction.atomic
def update_organization(organization: Organization, data: dict[str, Any]) -> dict[str, Any]:
    """Apply settings changes and return the diff for the audit log."""
    changes: dict[str, Any] = {}
    old_slug = organization.slug
    for field in UPDATABLE_FIELDS:
        if field in data and getattr(organization, field) != data[field]:
            changes[field] = {"from": getattr(organization, field), "to": data[field]}
            setattr(organization, field, data[field])
    # The space address: same rules as at sign-up; links with the old address stop working.
    slug = (data.get("slug") or "").strip().lower()
    if slug and slug != organization.slug:
        check = check_slug(slug)
        if not check.available:
            raise BusinessError(
                "slug_unavailable", check.reason or "", {"slug": [check.reason or ""]}
            )
        changes["slug"] = {"from": organization.slug, "to": slug}
        organization.slug = slug
    if changes:
        organization.save(update_fields=[*changes.keys(), "updated_at"])
        invalidate_organization(organization, old_slug=old_slug)
    return changes


@transaction.atomic
def change_plan(organization: Organization, code: str) -> dict[str, Any]:
    """During the trial the agency picks its offer freely; afterwards it needs a payment,
    which is not integrated yet (CLAUDE.md §2: never promise what is not built)."""
    from accounts.models import Membership

    from .models import SubscriptionPlan

    plan = SubscriptionPlan.objects.filter(code=code, is_active=True).first()
    if plan is None:
        raise BusinessError("invalid", "Offre inconnue.", {"plan": ["Offre inconnue."]})
    if plan.code == organization.plan:
        return {}
    if not organization.is_in_trial(timezone.now()):
        raise BusinessError(
            "plan_change_unavailable",
            "Le paiement en ligne n’est pas encore disponible : contactez l’équipe Wedivo "
            "pour changer d’offre après l’essai.",
        )
    members = Membership.objects.filter(organization=organization, is_active=True).count()
    if (
        not settings.ALL_FEATURES_INCLUDED
        and plan.max_users is not None
        and members > plan.max_users
    ):
        raise BusinessError(
            "plan_limit",
            f"L’offre {plan.name} permet {plan.max_users} utilisateur"
            f"{'s' if plan.max_users > 1 else ''} : désactivez des membres avant de la choisir.",
        )
    changes = {"plan": {"from": organization.plan, "to": plan.code}}
    organization.plan = plan.code
    organization.save(update_fields=["plan", "updated_at"])
    invalidate_organization(organization)
    return changes
