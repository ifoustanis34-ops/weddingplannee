"""Platform console (super-admin, feedback 14/11/2026): every agency and every account.

Agencies, users and memberships are not tenant tables (no RLS): nothing here needs a tenant
context, except ``bootstrap_organization`` which opens its own. Every change is written to
``PlatformAuditLog``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Count, OuterRef, Q, QuerySet, Subquery
from django.db.models.functions import TruncMonth
from django.utils import timezone

from accounts.models import Membership, User
from core.exceptions import BusinessError
from organizations import services as organization_services
from organizations.models import Organization

from .models import PlatformAuditLog

Role = Membership.Role


# --- Journal -------------------------------------------------------------------------------------


def record(
    action: str,
    target: models.Model,
    *,
    actor: User,
    ip: str | None = None,
    label: str = "",
    organization: Organization | None = None,
    changes: dict[str, Any] | None = None,
) -> PlatformAuditLog:
    entry: PlatformAuditLog = PlatformAuditLog.objects.create(
        action=action,
        target_type=target._meta.label_lower,
        target_id=str(target.pk),
        target_label=label[:200],
        organization=organization,
        changes=changes or {},
        ip=ip,
        actor=actor,
    )
    return entry


def _check_password(password: str, user: User | None = None) -> None:
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise BusinessError(
            "invalid", "Choisissez un mot de passe plus sûr.", {"password": list(exc.messages)}
        ) from exc


def _clean_name(value: str, field: str = "full_name") -> str:
    name = " ".join(value.split())
    if not name:
        raise BusinessError("invalid", "Indiquez le nom.", {field: ["Champ obligatoire."]})
    return name


# --- Overview ------------------------------------------------------------------------------------


def overview(now: datetime | None = None) -> dict[str, Any]:
    now = now or timezone.now()
    month_ago = now - timedelta(days=30)
    agencies = Organization.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
        suspended=Count("id", filter=Q(is_active=False)),
        lifetime=Count("id", filter=Q(lifetime_access=True)),
        in_trial=Count(
            "id", filter=Q(is_active=True, lifetime_access=False, trial_ends_at__gt=now)
        ),
        trial_over=Count(
            "id",
            filter=Q(is_active=True, lifetime_access=False)
            & (Q(trial_ends_at__lte=now) | Q(trial_ends_at__isnull=True)),
        ),
        new_this_month=Count("id", filter=Q(created_at__gte=month_ago)),
    )
    users = User.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
        inactive=Count("id", filter=Q(is_active=False)),
        admins=Count("id", filter=Q(is_staff=True)),
        new_this_month=Count("id", filter=Q(date_joined__gte=month_ago)),
        seen_this_month=Count("id", filter=Q(last_login__gte=month_ago)),
    )
    plans = dict(
        Organization.objects.filter(is_active=True)
        .values("plan")
        .annotate(n=Count("id"))
        .values_list("plan", "n")
    )
    latest = list(
        Organization.objects.order_by("-created_at").values("id", "name", "slug", "created_at")[:5]
    )
    # Agencies where at least one active member signed in during the last 30 days.
    agencies["engaged"] = (
        Organization.objects.filter(
            is_active=True,
            memberships__is_active=True,
            memberships__user__last_login__gte=month_ago,
        )
        .distinct()
        .count()
    )
    return {
        "agencies": agencies,
        "users": users,
        "plans": [
            {"code": code, "label": label, "count": plans.get(code, 0)}
            for code, label in Organization.Plan.choices
        ],
        "latest_agencies": latest,
        "growth": _growth(now),
        "watchlist": _watchlist(now),
        "activity": list(
            PlatformAuditLog.objects.select_related("actor")
            .order_by("-created_at")
            .values("id", "action", "target_label", "created_at", "actor__full_name")[:6]
        ),
    }


def _month_start(moment: datetime, months_back: int) -> datetime:
    year, month = moment.year, moment.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    return moment.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)


def _per_month(queryset: QuerySet[Any], field: str, start: datetime) -> dict[tuple[int, int], int]:
    rows = (
        queryset.filter(**{f"{field}__gte": start})
        .annotate(month=TruncMonth(field))
        .values("month")
        .annotate(n=Count("pk"))
        .values_list("month", "n")
    )
    return {(month.year, month.month): n for month, n in rows}


def _growth(now: datetime) -> list[dict[str, Any]]:
    """New agencies and accounts per month over the last 12 months (oldest first)."""
    local = timezone.localtime(now)
    start = _month_start(local, 11)
    agencies = _per_month(Organization.objects.all(), "created_at", start)
    accounts = _per_month(User.objects.all(), "date_joined", start)
    months = []
    for back in range(11, -1, -1):
        month = _month_start(local, back)
        key = (month.year, month.month)
        months.append(
            {
                "month": month.date().isoformat(),
                "agencies": agencies.get(key, 0),
                "accounts": accounts.get(key, 0),
            }
        )
    return months


def _watchlist(now: datetime) -> list[dict[str, Any]]:
    """What needs the team: trials ending within 7 days, trials ended in the last 14 days,
    suspended agencies. Most urgent first, 8 at most."""
    owner = Membership.objects.filter(
        organization=OuterRef("pk"), role=Role.OWNER, is_active=True
    ).order_by("joined_at")
    base = Organization.objects.annotate(owner_email=Subquery(owner.values("user__email")[:1]))
    items: list[dict[str, Any]] = []
    for organization in base.filter(
        is_active=True,
        lifetime_access=False,
        trial_ends_at__gt=now,
        trial_ends_at__lte=now + timedelta(days=7),
    ).order_by("trial_ends_at")[:8]:
        items.append(_watch(organization, "trial_ending", organization.trial_ends_at))
    for organization in base.filter(
        is_active=True,
        lifetime_access=False,
        trial_ends_at__lte=now,
        trial_ends_at__gt=now - timedelta(days=14),
    ).order_by("-trial_ends_at")[:8]:
        items.append(_watch(organization, "trial_ended", organization.trial_ends_at))
    for organization in base.filter(is_active=False).order_by("-suspended_at")[:8]:
        items.append(_watch(organization, "suspended", organization.suspended_at))
    return items[:8]


def _watch(organization: Organization, kind: str, at: datetime | None) -> dict[str, Any]:
    return {
        "id": organization.id,
        "name": organization.name,
        "slug": organization.slug,
        "kind": kind,
        "at": at,
        "owner_email": getattr(organization, "owner_email", None),
    }


# --- Agencies ------------------------------------------------------------------------------------

AGENCY_STATUSES = ("active", "suspended", "lifetime", "trial", "trial_over")


def organizations(search: str = "", status: str = "") -> QuerySet[Organization]:
    owner = Membership.objects.filter(
        organization=OuterRef("pk"), role=Role.OWNER, is_active=True
    ).order_by("joined_at", "created_at")
    queryset = Organization.objects.annotate(
        members_count=Count("memberships", filter=Q(memberships__is_active=True), distinct=True),
        owner_name=Subquery(owner.values("user__full_name")[:1]),
        owner_email=Subquery(owner.values("user__email")[:1]),
    )
    search = search.strip()
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(slug__icontains=search)
            | Q(city__icontains=search)
            | Q(memberships__user__email__icontains=search)
        ).distinct()
    now = timezone.now()
    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "suspended":
        queryset = queryset.filter(is_active=False)
    elif status == "lifetime":
        queryset = queryset.filter(lifetime_access=True)
    elif status == "trial":
        queryset = queryset.filter(is_active=True, lifetime_access=False, trial_ends_at__gt=now)
    elif status == "trial_over":
        queryset = queryset.filter(is_active=True, lifetime_access=False).filter(
            Q(trial_ends_at__lte=now) | Q(trial_ends_at__isnull=True)
        )
    return queryset.order_by("-created_at")


def organization_detail(pk: Any) -> Organization:
    organization = organizations().filter(pk=pk).first()
    if organization is None:
        raise BusinessError("not_found", "Agence introuvable.", status_code=404)
    return organization


@dataclass(frozen=True)
class NewAgency:
    name: str
    slug: str
    city: str
    country: str
    plan: str
    owner_full_name: str
    owner_email: str
    owner_phone: str
    owner_password: str
    lifetime_access: bool = False
    weddings_enabled: bool = False


def create_organization(
    data: NewAgency, *, actor: User, ip: str | None
) -> tuple[Organization, User, bool]:
    """Open an agency for a customer, with its owner (new account with a temporary password,
    or an existing Wedivo account that keeps its own). Returns the agency, the owner and
    whether the account was created."""
    name = _clean_name(data.name, "name")
    check = organization_services.check_slug(data.slug)
    if not check.available:
        raise BusinessError("slug_unavailable", check.reason or "", {"slug": [check.reason or ""]})
    if data.plan not in Organization.Plan.values:
        raise BusinessError("invalid", "Offre inconnue.", {"plan": ["Offre inconnue."]})
    owner_name = _clean_name(data.owner_full_name, "owner_full_name")
    email = data.owner_email.strip().lower()
    owner = User.objects.filter(email__iexact=email).first()
    created = owner is None
    if owner is None:
        _check_password(data.owner_password)
    try:
        with transaction.atomic():
            organization = organization_services.create_organization(
                name=name,
                slug=check.slug,
                city=data.city.strip(),
                country=data.country,
                plan=data.plan,
                weddings_enabled=data.weddings_enabled,
            )
            if data.lifetime_access:
                organization.lifetime_access = True
                organization.lifetime_granted_at = timezone.now()
                organization.save(update_fields=["lifetime_access", "lifetime_granted_at"])
            if owner is None:
                owner = User.objects.create_user(
                    email=email,
                    password=data.owner_password,
                    full_name=owner_name,
                    phone=data.owner_phone.strip(),
                    is_verified=True,
                    must_change_password=True,
                )
            now = timezone.now()
            Membership.objects.create(
                user=owner, organization=organization, role=Role.OWNER, joined_at=now
            )
            record(
                "organization.created",
                organization,
                actor=actor,
                ip=ip,
                label=organization.name,
                organization=organization,
                changes={
                    "slug": organization.slug,
                    "plan": organization.plan,
                    "owner": email,
                    "new_account": created,
                    "lifetime_access": organization.lifetime_access,
                },
            )
    except IntegrityError as exc:
        raise BusinessError(
            "conflict", "Cette adresse vient d’être prise. Choisissez-en une autre."
        ) from exc
    return organization, owner, created


# Editable from the console, with the audit label of each field.
AGENCY_FIELDS = (
    "name",
    "city",
    "country",
    "plan",
    "trial_ends_at",
    "weddings_enabled",
    "admin_note",
)


@transaction.atomic
def update_organization(
    organization: Organization, data: dict[str, Any], *, actor: User, ip: str | None
) -> dict[str, Any]:
    """Plan, trial end, lifetime access, suspension, identity, private note."""
    organization = Organization.objects.select_for_update().get(pk=organization.pk)
    changes: dict[str, Any] = {}
    now = timezone.now()

    def change(field: str, value: Any) -> None:
        before = getattr(organization, field)
        if before != value:
            changes[field] = {
                "from": before.isoformat() if isinstance(before, datetime) else before,
                "to": value.isoformat() if isinstance(value, datetime) else value,
            }
            setattr(organization, field, value)

    for field in AGENCY_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if field == "name":
            value = _clean_name(value, "name")
        elif field == "country":
            value = str(value).upper()
        elif field == "plan" and value not in Organization.Plan.values:
            raise BusinessError("invalid", "Offre inconnue.", {"plan": ["Offre inconnue."]})
        change(field, value)

    if "lifetime_access" in data and data["lifetime_access"] != organization.lifetime_access:
        change("lifetime_access", bool(data["lifetime_access"]))
        organization.lifetime_granted_at = now if organization.lifetime_access else None

    if "is_active" in data and data["is_active"] != organization.is_active:
        change("is_active", bool(data["is_active"]))
        if organization.is_active:
            organization.suspended_at = None
            organization.suspension_reason = ""
        else:
            organization.suspended_at = now
            organization.suspension_reason = str(data.get("suspension_reason") or "").strip()[:240]
            changes["suspension_reason"] = organization.suspension_reason

    if not changes:
        return {}
    organization.save()
    organization_services.invalidate_organization(organization)
    action = "organization.updated"
    if "is_active" in changes:
        action = "organization.reactivated" if organization.is_active else "organization.suspended"
    elif "lifetime_access" in changes:
        action = (
            "organization.lifetime_granted"
            if organization.lifetime_access
            else "organization.lifetime_revoked"
        )
    record(
        action,
        organization,
        actor=actor,
        ip=ip,
        label=organization.name,
        organization=organization,
        changes=changes,
    )
    return changes


def organization_members(organization: Organization) -> QuerySet[Membership]:
    return (
        Membership.objects.filter(organization=organization)
        .select_related("user")
        .order_by("-is_active", "role", "user__full_name")
    )


# --- Accounts ------------------------------------------------------------------------------------

USER_STATUSES = ("active", "inactive", "admins", "never_logged_in", "no_agency")


def users(search: str = "", status: str = "", organization: str = "") -> QuerySet[User]:
    queryset = User.objects.annotate(
        agencies_count=Count("memberships", filter=Q(memberships__is_active=True), distinct=True)
    )
    search = search.strip()
    if search:
        queryset = queryset.filter(
            Q(email__icontains=search)
            | Q(full_name__icontains=search)
            | Q(phone__icontains=search)
            | Q(memberships__organization__name__icontains=search)
        ).distinct()
    if organization:
        queryset = queryset.filter(memberships__organization_id=organization).distinct()
    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)
    elif status == "admins":
        queryset = queryset.filter(is_staff=True)
    elif status == "never_logged_in":
        queryset = queryset.filter(last_login__isnull=True)
    elif status == "no_agency":
        queryset = queryset.filter(agencies_count=0)
    return queryset.prefetch_related(
        models.Prefetch(
            "memberships",
            queryset=Membership.objects.select_related("organization").order_by(
                "organization__name"
            ),
        )
    ).order_by("-date_joined")


def user_detail(pk: Any) -> User:
    user = users().filter(pk=pk).first()
    if user is None:
        raise BusinessError("not_found", "Compte introuvable.", status_code=404)
    return user


@dataclass(frozen=True)
class NewAccount:
    full_name: str
    email: str
    phone: str
    password: str
    organization_id: Any = None
    role: str = ""
    is_platform_admin: bool = False


def _organization(pk: Any) -> Organization:
    organization = Organization.objects.filter(pk=pk).first()
    if organization is None:
        raise BusinessError(
            "invalid", "Agence introuvable.", {"organization_id": ["Agence introuvable."]}
        )
    return organization


def _check_role(role: str) -> None:
    if role not in Role.values:
        raise BusinessError("invalid", "Choisissez un rôle.", {"role": ["Rôle inconnu."]})


@transaction.atomic
def create_user(data: NewAccount, *, actor: User, ip: str | None) -> tuple[User, Membership | None]:
    """A new Wedivo account (temporary password), optionally placed in an agency with a role."""
    email = data.email.strip().lower()
    full_name = _clean_name(data.full_name)
    if User.objects.filter(email__iexact=email).exists():
        raise BusinessError(
            "email_taken",
            "Un compte existe déjà avec cet email : ajoutez-le à l’agence depuis sa fiche.",
            {"email": ["Email déjà utilisé."]},
        )
    organization = _organization(data.organization_id) if data.organization_id else None
    if organization is not None:
        _check_role(data.role)
    _check_password(data.password, User(email=email, full_name=full_name))
    user = User.objects.create_user(
        email=email,
        password=data.password,
        full_name=full_name,
        phone=data.phone.strip(),
        is_verified=True,
        must_change_password=True,
        is_staff=data.is_platform_admin,
        is_superuser=data.is_platform_admin,
    )
    record(
        "user.created",
        user,
        actor=actor,
        ip=ip,
        label=email,
        organization=organization,
        changes={"is_platform_admin": data.is_platform_admin},
    )
    membership = None
    if organization is not None:
        membership = add_membership(organization, user, data.role, actor=actor, ip=ip)
    return user, membership


@transaction.atomic
def update_user(user: User, data: dict[str, Any], *, actor: User, ip: str | None) -> dict[str, Any]:
    """Name, phone, email; turn the account off or on; give or take the console."""
    user = User.objects.select_for_update().get(pk=user.pk)
    changes: dict[str, Any] = {}
    if "full_name" in data:
        name = _clean_name(data["full_name"])
        if name != user.full_name:
            changes["full_name"] = {"from": user.full_name, "to": name}
            user.full_name = name
    if "phone" in data and data["phone"].strip() != user.phone:
        changes["phone"] = {"from": user.phone, "to": data["phone"].strip()}
        user.phone = data["phone"].strip()
    if "email" in data:
        email = data["email"].strip().lower()
        if email != user.email:
            if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                raise BusinessError(
                    "email_taken", "Cet email est déjà utilisé.", {"email": ["Déjà utilisé."]}
                )
            changes["email"] = {"from": user.email, "to": email}
            user.email = email
    if "is_active" in data and data["is_active"] != user.is_active:
        if user.pk == actor.pk:
            raise BusinessError("self_locked", "Vous ne pouvez pas désactiver votre propre compte.")
        changes["is_active"] = {"from": user.is_active, "to": data["is_active"]}
        user.is_active = bool(data["is_active"])
    if "is_platform_admin" in data and data["is_platform_admin"] != user.is_staff:
        if user.pk == actor.pk:
            raise BusinessError(
                "self_locked", "Vous ne pouvez pas retirer votre propre accès à la console."
            )
        changes["is_platform_admin"] = {"from": user.is_staff, "to": data["is_platform_admin"]}
        user.is_staff = user.is_superuser = bool(data["is_platform_admin"])
    if not changes:
        return {}
    user.save()
    action = "user.updated"
    if "is_active" in changes:
        action = "user.reactivated" if user.is_active else "user.deactivated"
    elif "is_platform_admin" in changes:
        action = "user.admin_granted" if user.is_staff else "user.admin_revoked"
    record(action, user, actor=actor, ip=ip, label=user.email, changes=changes)
    return changes


def set_password(user: User, password: str, *, actor: User, ip: str | None) -> None:
    """A new temporary password, changed by the person at their next sign-in."""
    _check_password(password, user)
    user.set_password(password)
    user.must_change_password = user.pk != actor.pk
    user.save(update_fields=["password", "must_change_password"])
    record("user.password_set", user, actor=actor, ip=ip, label=user.email)


# --- Memberships ---------------------------------------------------------------------------------


def _demote_other_owners(
    organization: Organization, keep: Membership, *, actor: User, ip: str | None
) -> None:
    """One owner per agency: the previous one becomes wedding planner (transfer)."""
    for previous in (
        Membership.objects.select_related("user")
        .filter(organization=organization, role=Role.OWNER, is_active=True)
        .exclude(pk=keep.pk)
    ):
        previous.role = Role.PLANNER
        previous.save(update_fields=["role"])
        record(
            "membership.role_changed",
            previous,
            actor=actor,
            ip=ip,
            label=f"{previous.user.email} · {organization.name}",
            organization=organization,
            changes={"role": {"from": Role.OWNER, "to": Role.PLANNER}, "reason": "transfer"},
        )


def _is_last_owner(membership: Membership) -> bool:
    return (
        membership.role == Role.OWNER
        and membership.is_active
        and not Membership.objects.filter(
            organization_id=membership.organization_id, role=Role.OWNER, is_active=True
        )
        .exclude(pk=membership.pk)
        .exists()
    )


@transaction.atomic
def add_membership(
    organization: Organization, user: User, role: str, *, actor: User, ip: str | None
) -> Membership:
    """Place an existing account in an agency (or bring a former member back)."""
    _check_role(role)
    Organization.objects.select_for_update().filter(pk=organization.pk).first()
    membership = Membership.objects.filter(organization=organization, user=user).first()
    now = timezone.now()
    if membership is not None and membership.is_active:
        raise BusinessError(
            "already_member",
            "Ce compte fait déjà partie de cette agence.",
            {"email": ["Déjà membre."]},
        )
    if membership is not None:
        membership.role, membership.is_active, membership.joined_at = role, True, now
        membership.save(update_fields=["role", "is_active", "joined_at"])
    else:
        membership = Membership.objects.create(
            user=user, organization=organization, role=role, invited_at=now, joined_at=now
        )
    if role == Role.OWNER:
        _demote_other_owners(organization, membership, actor=actor, ip=ip)
    record(
        "membership.created",
        membership,
        actor=actor,
        ip=ip,
        label=f"{user.email} · {organization.name}",
        organization=organization,
        changes={"role": role},
    )
    return membership


@transaction.atomic
def update_membership(
    membership: Membership, data: dict[str, Any], *, actor: User, ip: str | None
) -> dict[str, Any]:
    membership = (
        Membership.objects.select_for_update()
        .select_related("user", "organization")
        .get(pk=membership.pk)
    )
    changes: dict[str, Any] = {}
    role = data.get("role")
    leaves_owner = (role is not None and role != Role.OWNER) or data.get("is_active") is False
    if leaves_owner and _is_last_owner(membership):
        raise BusinessError(
            "last_owner",
            "C’est le seul propriétaire de l’agence : nommez d’abord un autre propriétaire.",
        )
    if role is not None and role != membership.role:
        _check_role(role)
        changes["role"] = {"from": membership.role, "to": role}
        membership.role = role
    if "is_active" in data and data["is_active"] != membership.is_active:
        changes["is_active"] = {"from": membership.is_active, "to": data["is_active"]}
        membership.is_active = bool(data["is_active"])
    if not changes:
        return {}
    membership.save(update_fields=["role", "is_active"])
    if membership.role == Role.OWNER and membership.is_active:
        _demote_other_owners(membership.organization, membership, actor=actor, ip=ip)
    record(
        "membership.updated",
        membership,
        actor=actor,
        ip=ip,
        label=f"{membership.user.email} · {membership.organization.name}",
        organization=membership.organization,
        changes=changes,
    )
    return changes


def membership_or_404(pk: Any) -> Membership:
    membership = Membership.objects.select_related("user", "organization").filter(pk=pk).first()
    if membership is None:
        raise BusinessError("not_found", "Accès introuvable.", status_code=404)
    return membership


def journal(organization: str = "", search: str = "") -> QuerySet[PlatformAuditLog]:
    queryset = PlatformAuditLog.objects.select_related("actor", "organization")
    if organization:
        queryset = queryset.filter(organization_id=organization)
    if search.strip():
        queryset = queryset.filter(
            Q(target_label__icontains=search.strip()) | Q(action__icontains=search.strip())
        )
    return queryset.order_by("-created_at")
