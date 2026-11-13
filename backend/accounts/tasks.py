from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import User

RETRY = {"autoretry_for": (Exception,), "retry_backoff": True, "max_retries": 3}


@shared_task(queue="emails", **RETRY)  # type: ignore[untyped-decorator]
def send_verification_email(user_id: str) -> None:
    from .services import make_email_token

    user = User.objects.filter(pk=user_id, is_verified=False).first()
    if user is None:  # already verified or deleted: nothing to do (idempotent)
        return
    link = f"{settings.FRONTEND_URL}/verifier-email?token={make_email_token(user)}"
    send_mail(
        subject="Confirmez votre adresse email — Wedivo",
        message=(
            f"Bonjour {user.first_name},\n\n"
            "Bienvenue sur Wedivo. Confirmez votre adresse email pour activer les envois "
            f"de devis par email :\n{link}\n\n"
            "Ce lien est valable 3 jours.\n\nL’équipe Wedivo"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


@shared_task(queue="emails", **RETRY)  # type: ignore[untyped-decorator]
def send_password_reset_email(user_id: str, uid: str, token: str) -> None:
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return
    link = f"{settings.FRONTEND_URL}/reinitialiser-mot-de-passe?uid={uid}&token={token}"
    send_mail(
        subject="Réinitialisez votre mot de passe — Wedivo",
        message=(
            f"Bonjour {user.first_name},\n\n"
            f"Pour choisir un nouveau mot de passe, ouvrez ce lien :\n{link}\n\n"
            "Si vous n’avez rien demandé, ignorez cet email.\n\nL’équipe Wedivo"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


@shared_task(queue="emails", **RETRY)  # type: ignore[untyped-decorator]
def send_team_invitation(invitation_id: str, token: str) -> None:
    from .models import TeamInvitation

    invitation = (
        TeamInvitation.objects.select_related("organization", "invited_by")
        .filter(pk=invitation_id, accepted_at__isnull=True, cancelled_at__isnull=True)
        .first()
    )
    if invitation is None:  # cancelled or already accepted: nothing to send (idempotent)
        return
    inviter = invitation.invited_by.full_name if invitation.invited_by else "Votre équipe"
    link = f"{settings.FRONTEND_URL}/invitation/{token}"
    send_mail(
        subject=f"{inviter} vous invite sur Wedivo — {invitation.organization.name}",
        message=(
            "Bonjour,\n\n"
            f"{inviter} vous invite à rejoindre l’espace « {invitation.organization.name} » "
            f"sur Wedivo, avec le rôle {invitation.get_role_display()}.\n\n"
            f"Pour accepter, ouvrez ce lien :\n{link}\n\n"
            "Ce lien est valable 7 jours.\n\nL’équipe Wedivo"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitation.email],
    )
