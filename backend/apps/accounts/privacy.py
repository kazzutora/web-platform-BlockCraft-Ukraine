"""The player's data: export it all as JSON, or leave (anonymize or delete everything)."""

from django.db import transaction
from django.utils import timezone

from .models import User


def _target(row) -> dict:
    from apps.core import kinds

    try:
        kind = kinds.kind_for_content_type(row.content_type_id)
    except LookupError:
        return {"kind": None, "id": str(row.object_id)}
    target = row.target
    return {"kind": kind.name, "id": kind.identifier(target) if target else str(row.object_id)}


def export(user: User) -> dict:
    """Everything we keep about the player, readable without our site (GDPR-style export)."""
    from apps.library.models import Collection, Download, Favorite
    from apps.moderation.models import Report
    from apps.notifications.models import Notification
    from apps.servers.models import Server
    from apps.skins.models import Skin
    from apps.social.models import Comment, Like, Review

    profile, settings = user.game_profile, user.settings
    return {
        "exported_at": timezone.now().isoformat(),
        "account": {
            "email": user.email,
            "nickname": user.nickname,
            "bio": user.bio,
            "mc_nickname": user.mc_nickname,
            "is_private": user.is_private,
            "role": user.role,
            "date_joined": user.date_joined.isoformat(),
            "avatar": user.avatar.url if user.avatar else None,
        },
        "game_profile": {
            "game_version": profile.game_version,
            "loader": profile.loader,
            "edition": profile.edition,
            "interests": profile.interests,
        },
        "settings": {
            "theme": settings.theme,
            "language": settings.language,
            "notify_prefs": settings.notify_prefs,
            "who_can_comment": settings.who_can_comment,
            "collections_visible": settings.collections_visible,
        },
        "favorites": [
            {**_target(f), "saved_at": f.created_at.isoformat()}
            for f in Favorite.objects.filter(user=user).prefetch_related("target")
        ],
        "likes": [
            _target(like) for like in Like.objects.filter(user=user).prefetch_related("target")
        ],
        "collections": [
            {
                "title": c.title,
                "description": c.description,
                "visibility": c.visibility,
                "items": [
                    {**_target(i), "note": i.note} for i in c.items.prefetch_related("target")
                ],
            }
            for c in Collection.objects.filter(owner=user)
        ],
        "reviews": [
            {**_target(r), "stars": r.stars, "text": r.text, "created_at": r.created_at.isoformat()}
            for r in Review.objects.filter(user=user).prefetch_related("target")
        ],
        "comments": [
            {**_target(c), "body": c.body, "created_at": c.created_at.isoformat()}
            for c in Comment.objects.filter(user=user, is_deleted=False).prefetch_related("target")
        ],
        "skins": [
            {"id": s.pk, "title": s.title, "status": s.status, "texture": s.file.url}
            for s in Skin.objects.filter(author=user)
        ],
        "servers": [
            {"slug": s.slug, "name": s.name, "address": s.address, "status": s.status}
            for s in Server.objects.filter(author=user)
        ],
        "downloads": [
            {
                "mod": d.project.slug,
                "game_version": d.game_version,
                "loader": d.loader,
                "at": d.created_at.isoformat(),
            }
            for d in Download.objects.filter(user=user).select_related("project")
        ],
        "reports": [
            {"reason": r.reason, "comment": r.comment, "status": r.status}
            for r in Report.objects.filter(reporter=user)
        ],
        "notifications": [
            {"type": n.type, "payload": n.payload, "at": n.created_at.isoformat()}
            for n in Notification.objects.filter(user=user)
        ],
    }


def _sign_out_everywhere(user: User) -> None:
    from allauth.account.models import EmailAddress
    from allauth.socialaccount.models import SocialAccount

    EmailAddress.objects.filter(user=user).delete()
    SocialAccount.objects.filter(user=user).delete()


@transaction.atomic
def anonymize(user: User) -> None:
    """The content stays (skins, servers, reviews, comments) under a placeholder name;
    everything that identifies the person goes."""
    from apps.notifications.models import Notification
    from apps.skins.models import Skin

    _sign_out_everywhere(user)
    if user.avatar:
        user.avatar.delete(save=False)
    Notification.objects.filter(user=user).delete()
    Skin.objects.filter(author=user, is_current=True).update(is_current=False)
    user.email = f"deleted-{user.pk}@deleted.invalid"
    user.nickname = f"deleted_{user.pk}"
    user.bio = ""
    user.mc_nickname = ""
    user.is_private = True
    user.is_active = False
    user.set_unusable_password()
    user.save()


@transaction.atomic
def delete(user: User) -> None:
    """Everything goes; counters of other people's objects are fixed afterwards."""
    from apps.library.models import Favorite
    from apps.social.models import Comment, Like, Review
    from apps.social.services import recount_targets

    rows = [
        *Favorite.objects.filter(user=user).values_list("content_type_id", "object_id"),
        *Like.objects.filter(user=user).values_list("content_type_id", "object_id"),
        *Review.objects.filter(user=user).values_list("content_type_id", "object_id"),
        # Replies of others to this player's comments go with them
        *Comment.objects.filter(user=user).values_list("content_type_id", "object_id"),
    ]
    _sign_out_everywhere(user)
    if user.avatar:
        user.avatar.delete(save=False)
    user.delete()
    recount_targets(set(rows))
