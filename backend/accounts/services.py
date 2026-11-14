from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from core import ratelimit
from core.exceptions import BusinessError
from organizations import services as organization_services
from organizations.models import Organization

from .models import Membership, TeamInvitation, User

VERIFY_EMAIL_SALT = "accounts.verify-email"
VERIFY_EMAIL_MAX_AGE = 3 * 24 * 3600

LOGIN_LIMIT, LOGIN_WINDOW = 5, 15 * 60  # 5 attempts per 15 min (CLAUDE.md §11)
SIGNUP_WINDOW = 3600
RESET_LIMIT, RESET_WINDOW = 5, 3600


@dataclass(frozen=True)
class SignupData:
    company_name: str
    city: str
    country: str
    weddings_per_year: int | None
    full_name: str
    email: str
    phone: str
    password: str
    slug: str
    plan: str
    weddings_enabled: bool = False


def _validate_password(password: str, user: User | None = None) -> None:
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise BusinessError(
            "invalid", "Choisissez un mot de passe plus sûr.", {"password": list(exc.messages)}
        ) from exc


def signup(data: SignupData, *, ip: str | None) -> tuple[User, Organization]:
    """Create organization, owner and default data in one transaction (CLAUDE.md §5)."""
    ratelimit.hit("signup", ip or "unknown", limit=settings.SIGNUP_RATE_LIMIT, window=SIGNUP_WINDOW)

    email = data.email.strip().lower()
    slug_check = organization_services.check_slug(data.slug)
    if not slug_check.available:
        raise BusinessError(
            "slug_unavailable", slug_check.reason or "", {"slug": [slug_check.reason or ""]}
        )
    if User.objects.filter(email=email).exists():
        raise BusinessError(
            "email_taken",
            "Un compte existe déjà avec cet email. "
            "Connectez-vous ou réinitialisez le mot de passe.",
            {"email": ["Email déjà utilisé."]},
        )
    candidate = User(email=email, full_name=data.full_name)
    _validate_password(data.password, candidate)

    try:
        with transaction.atomic():
            organization = organization_services.create_organization(
                name=data.company_name.strip(),
                slug=slug_check.slug,
                city=data.city.strip(),
                country=data.country,
                weddings_per_year=data.weddings_per_year,
                plan=data.plan,
                weddings_enabled=data.weddings_enabled,
            )
            user = User.objects.create_user(
                email=email,
                password=data.password,
                full_name=data.full_name.strip(),
                phone=data.phone.strip(),
            )
            Membership.objects.create(
                user=user,
                organization=organization,
                role=Membership.Role.OWNER,
                joined_at=timezone.now(),
            )
    except IntegrityError as exc:  # concurrent signup on the same slug or email
        raise BusinessError(
            "signup_conflict", "Cette adresse ou cet email vient d’être pris. Réessayez."
        ) from exc

    request_email_verification(user)
    return user, organization


def login(email: str, password: str, *, ip: str | None) -> User:
    email = email.strip().lower()
    ratelimit.hit("login", f"{ip}:{email}", limit=LOGIN_LIMIT, window=LOGIN_WINDOW)
    user = authenticate(username=email, password=password)
    if user is None:
        raise BusinessError(
            "invalid_credentials", "Email ou mot de passe incorrect.", status_code=401
        )
    ratelimit.reset("login", f"{ip}:{email}", window=LOGIN_WINDOW)
    # « Dernière connexion » of the platform console.
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    return user


def active_memberships(user: User) -> list[Membership]:
    return list(
        user.memberships.filter(is_active=True, organization__is_active=True)
        .select_related("organization")
        .order_by("organization__name")
    )


# --- Email verification -------------------------------------------------------------------


def make_email_token(user: User) -> str:
    return signing.dumps({"u": str(user.pk), "e": user.email}, salt=VERIFY_EMAIL_SALT)


def request_email_verification(user: User) -> None:
    from .tasks import send_verification_email

    if user.is_verified:
        return
    transaction.on_commit(lambda: send_verification_email.delay(str(user.pk)))


def verify_email(token: str) -> User:
    invalid = BusinessError(
        "invalid_token", "Ce lien n’est plus valide. Demandez un nouvel email de vérification."
    )
    try:
        payload = signing.loads(token, salt=VERIFY_EMAIL_SALT, max_age=VERIFY_EMAIL_MAX_AGE)
    except signing.BadSignature as exc:
        raise invalid from exc
    user = User.objects.filter(pk=payload.get("u"), email=payload.get("e")).first()
    if user is None:
        raise invalid
    if not user.is_verified:
        user.is_verified = True
        user.save(update_fields=["is_verified"])
    return user


# --- Password reset -----------------------------------------------------------------------


def request_password_reset(email: str, *, ip: str | None) -> None:
    """Always succeeds from the caller's point of view: never reveal whether an email exists."""
    from .tasks import send_password_reset_email

    ratelimit.hit("password-reset", ip or "unknown", limit=RESET_LIMIT, window=RESET_WINDOW)
    user = User.objects.filter(email=email.strip().lower(), is_active=True).first()
    if user is None:
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    transaction.on_commit(lambda: send_password_reset_email.delay(str(user.pk), uid, token))


def confirm_password_reset(uid: str, token: str, password: str) -> User:
    invalid = BusinessError(
        "invalid_token", "Ce lien a expiré ou a déjà servi. Demandez un nouveau lien."
    )
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id, is_active=True)
    except (ValueError, User.DoesNotExist, DjangoValidationError) as exc:
        raise invalid from exc
    if not default_token_generator.check_token(user, token):
        raise invalid
    _validate_password(password, user)
    user.set_password(password)
    user.save(update_fields=["password"])
    return user


# --- Team (CLAUDE.md §7.9: invitation by email with a role, role change, deactivation) -----

INVITATION_DAYS = 7


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _seat_limit(organization: Organization) -> tuple[int | None, str]:
    """Users allowed by the current offer (database), and the offer name for messages.
    Unlimited while every agency has every feature (`ALL_FEATURES_INCLUDED`)."""
    from django.conf import settings

    from organizations.models import SubscriptionPlan

    if settings.ALL_FEATURES_INCLUDED:
        return None, organization.get_plan_display()

    plan = SubscriptionPlan.objects.filter(code=organization.plan).first()
    if plan is None:
        return None, organization.get_plan_display()
    return plan.max_users, plan.name


def pending_invitations(organization: Organization) -> list[TeamInvitation]:
    now = timezone.now()
    return list(
        TeamInvitation.objects.filter(
            organization=organization,
            accepted_at__isnull=True,
            cancelled_at__isnull=True,
            expires_at__gt=now,
        )
    )


@transaction.atomic
def invite_member(
    organization: Organization, *, email: str, role: str, invited_by: User
) -> TeamInvitation:
    """Create (or renew) an invitation and email the link. The owner role is never invited."""
    from .tasks import send_team_invitation

    email = email.strip().lower()
    if role not in Membership.Role.values or role == Membership.Role.OWNER:
        raise BusinessError("invalid", "Choisissez un rôle.", {"role": ["Rôle inconnu."]})
    # Lock the organization row: two simultaneous invitations cannot exceed the seats.
    Organization.objects.select_for_update().filter(pk=organization.pk).first()
    if Membership.objects.filter(
        organization=organization, user__email=email, is_active=True
    ).exists():
        raise BusinessError(
            "already_member",
            "Cette personne fait déjà partie de l’équipe.",
            {"email": ["Déjà membre de l’espace."]},
        )
    pending = [inv for inv in pending_invitations(organization) if inv.email != email]
    seats, plan_name = _seat_limit(organization)
    members = Membership.objects.filter(organization=organization, is_active=True).count()
    if seats is not None and members + len(pending) >= seats:
        raise BusinessError(
            "plan_limit",
            f"L’offre {plan_name} permet {seats} utilisateur{'s' if seats > 1 else ''}. "
            "Choisissez une offre supérieure pour inviter un membre de plus.",
        )
    TeamInvitation.objects.filter(
        organization=organization, email=email, accepted_at__isnull=True, cancelled_at__isnull=True
    ).update(cancelled_at=timezone.now())
    token = secrets.token_urlsafe(32)
    invitation = TeamInvitation.objects.create(
        organization=organization,
        email=email,
        role=role,
        token_hash=_token_hash(token),
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(days=INVITATION_DAYS),
    )
    transaction.on_commit(lambda: send_team_invitation.delay(str(invitation.pk), token))
    return invitation


def invitation_for_token(token: str) -> TeamInvitation:
    invitation = (
        TeamInvitation.objects.select_related("organization", "invited_by")
        .filter(token_hash=_token_hash(token))
        .first()
    )
    if invitation is None or not invitation.is_pending(timezone.now()):
        raise BusinessError(
            "invalid_invitation",
            "Ce lien d’invitation n’est plus valable. Demandez une nouvelle invitation.",
            status_code=404,
        )
    if not invitation.organization.is_active:
        raise BusinessError("invalid_invitation", "Cet espace n’est plus actif.", status_code=404)
    return invitation


@transaction.atomic
def accept_invitation(
    token: str, *, full_name: str, password: str, ip: str | None
) -> tuple[User, TeamInvitation]:
    """Join the space. An existing account proves itself with its password; a new one is created
    already verified (the emailed link proves the address)."""
    invitation = invitation_for_token(token)
    TeamInvitation.objects.select_for_update().filter(pk=invitation.pk).first()
    user = User.objects.filter(email__iexact=invitation.email).first()
    if user is not None:
        user = login(invitation.email, password, ip=ip)
    else:
        full_name = full_name.strip()
        if not full_name:
            raise BusinessError(
                "invalid", "Indiquez votre nom complet.", {"full_name": ["Champ obligatoire."]}
            )
        _validate_password(password)
        user = User.objects.create_user(
            email=invitation.email, password=password, full_name=full_name, is_verified=True
        )
    now = timezone.now()
    membership, created = Membership.objects.get_or_create(
        user=user,
        organization=invitation.organization,
        defaults={
            "role": invitation.role,
            "invited_at": invitation.created_at,
            "joined_at": now,
        },
    )
    if not created:
        membership.role = invitation.role
        membership.is_active = True
        membership.joined_at = now
        membership.save(update_fields=["role", "is_active", "joined_at"])
    invitation.accepted_at = now
    invitation.save(update_fields=["accepted_at"])
    return user, invitation


def cancel_invitation(organization: Organization, invitation_id: str) -> TeamInvitation:
    invitation = TeamInvitation.objects.filter(
        organization=organization, pk=invitation_id, accepted_at__isnull=True
    ).first()
    if invitation is None:
        raise BusinessError("not_found", "Invitation introuvable.", status_code=404)
    invitation.cancelled_at = timezone.now()
    invitation.save(update_fields=["cancelled_at"])
    return invitation


def update_member(
    organization: Organization, membership_id: str, *, role: str | None, is_active: bool | None
) -> tuple[Membership, dict[str, Any]]:
    """Change a member's role or (de)activate them. The owner's membership never changes here."""
    membership = (
        Membership.objects.select_related("user")
        .filter(organization=organization, pk=membership_id)
        .first()
    )
    if membership is None:
        raise BusinessError("not_found", "Membre introuvable.", status_code=404)
    if membership.role == Membership.Role.OWNER:
        raise BusinessError(
            "owner_locked",
            "Le rôle et l’accès du propriétaire ne se modifient pas.",
            status_code=403,
        )
    changes: dict[str, Any] = {}
    if role is not None and role != membership.role:
        if role not in Membership.Role.values or role == Membership.Role.OWNER:
            raise BusinessError("invalid", "Choisissez un rôle.", {"role": ["Rôle inconnu."]})
        changes["role"] = {"from": membership.role, "to": role}
        membership.role = role
    if is_active is not None and is_active != membership.is_active:
        changes["is_active"] = {"from": membership.is_active, "to": is_active}
        membership.is_active = is_active
    if changes:
        membership.save(update_fields=list(changes))
    return membership, changes


# --- Own profile and accounts created by the owner (feedback 13/11/2026) --------------------------


def update_profile(user: User, *, full_name: str | None, phone: str | None) -> dict[str, Any]:
    """The person changes their own name and phone (the email stays: it signs them in)."""
    changes: dict[str, Any] = {}
    if full_name is not None:
        full_name = " ".join(full_name.split())
        if not full_name:
            raise BusinessError(
                "invalid", "Indiquez votre nom complet.", {"full_name": ["Champ obligatoire."]}
            )
        if full_name != user.full_name:
            changes["full_name"] = {"from": user.full_name, "to": full_name}
            user.full_name = full_name
    if phone is not None and phone.strip() != user.phone:
        changes["phone"] = {"from": user.phone, "to": phone.strip()}
        user.phone = phone.strip()
    if changes:
        user.save(update_fields=list(changes))
    return changes


def change_password(user: User, *, current: str, new: str) -> None:
    """Their own password: the current one first, then a safe new one, different from it."""
    # A temporary password is often pasted from a message: spaces around it do not count.
    pasted = user.must_change_password and current.strip() != current
    if not user.check_password(current) and not (pasted and user.check_password(current.strip())):
        raise BusinessError(
            "invalid",
            "Le mot de passe actuel n’est pas le bon.",
            {"current_password": ["Mot de passe incorrect."]},
        )
    if current.strip() == new.strip():
        raise BusinessError(
            "invalid",
            "Choisissez un mot de passe différent de l’actuel.",
            {"new_password": ["Identique à l’actuel."]},
        )
    try:
        validate_password(new, user)
    except DjangoValidationError as exc:
        raise BusinessError(
            "invalid", "Choisissez un mot de passe plus sûr.", {"new_password": list(exc.messages)}
        ) from exc
    user.set_password(new)
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password"])


@dataclass(frozen=True)
class NewMember:
    full_name: str
    email: str
    phone: str
    role: str
    password: str


@transaction.atomic
def create_member(
    organization: Organization, data: NewMember, *, created_by: User
) -> tuple[Membership, bool]:
    """The owner opens an account for someone of the team, without an email round trip: a
    temporary password they hand over, to be changed at first sign-in. Someone who already has a
    Wedivo account joins with their own password (the temporary one is ignored).
    Returns the membership and whether a new account was created."""
    email = data.email.strip().lower()
    if data.role not in Membership.Role.values or data.role == Membership.Role.OWNER:
        raise BusinessError("invalid", "Choisissez un rôle.", {"role": ["Rôle inconnu."]})
    full_name = " ".join(data.full_name.split())
    if not full_name:
        raise BusinessError("invalid", "Indiquez le nom.", {"full_name": ["Champ obligatoire."]})
    Organization.objects.select_for_update().filter(pk=organization.pk).first()
    existing = Membership.objects.filter(organization=organization, user__email=email).first()
    if existing is not None and existing.is_active:
        raise BusinessError(
            "already_member",
            "Cette personne fait déjà partie de l’équipe.",
            {"email": ["Déjà membre de l’espace."]},
        )
    seats, plan_name = _seat_limit(organization)
    members = Membership.objects.filter(organization=organization, is_active=True).count()
    if seats is not None and members + len(pending_invitations(organization)) >= seats:
        raise BusinessError(
            "plan_limit",
            f"L’offre {plan_name} permet {seats} utilisateur{'s' if seats > 1 else ''}. "
            "Choisissez une offre supérieure pour ajouter un membre.",
        )
    user = User.objects.filter(email__iexact=email).first()
    created = user is None
    if user is None:
        try:
            validate_password(data.password)
        except DjangoValidationError as exc:
            raise BusinessError(
                "invalid", "Choisissez un mot de passe plus sûr.", {"password": list(exc.messages)}
            ) from exc
        user = User.objects.create_user(
            email=email,
            password=data.password,
            full_name=full_name,
            phone=data.phone.strip(),
            is_verified=True,  # the owner vouches for the address; it only gates outgoing emails
        )
        user.must_change_password = True
        user.save(update_fields=["must_change_password"])
    now = timezone.now()
    if existing is not None:  # a former member comes back
        existing.role, existing.is_active, existing.joined_at = data.role, True, now
        existing.save(update_fields=["role", "is_active", "joined_at"])
        membership = existing
    else:
        membership = Membership.objects.create(
            user=user, organization=organization, role=data.role, invited_at=now, joined_at=now
        )
    TeamInvitation.objects.filter(
        organization=organization, email=email, accepted_at__isnull=True, cancelled_at__isnull=True
    ).update(cancelled_at=now)
    return membership, created


def set_member_password(
    organization: Organization, membership_id: str, password: str
) -> Membership:
    """The owner gives a member a new temporary password (forgotten, no email at hand). Only for
    accounts that belong to this space alone: never someone who also works elsewhere."""
    membership = (
        Membership.objects.select_related("user")
        .filter(organization=organization, pk=membership_id)
        .first()
    )
    if membership is None:
        raise BusinessError("not_found", "Membre introuvable.", status_code=404)
    if membership.role == Membership.Role.OWNER:
        raise BusinessError(
            "owner_locked",
            "Le propriétaire change son mot de passe depuis son profil.",
            status_code=403,
        )
    user = membership.user
    if Membership.objects.filter(user=user).exclude(organization=organization).exists():
        raise BusinessError(
            "shared_account",
            "Ce compte sert aussi dans un autre espace : la personne utilise « Mot de passe "
            "oublié » sur la page de connexion.",
        )
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise BusinessError(
            "invalid", "Choisissez un mot de passe plus sûr.", {"password": list(exc.messages)}
        ) from exc
    user.set_password(password)
    user.must_change_password = True
    user.save(update_fields=["password", "must_change_password"])
    return membership
