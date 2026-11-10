"""`Resolution` on the wire (tech.md 9.4). Explanations are texts of the frontend by code."""

from rest_framework import serializers

from apps.core.game import Loader
from apps.mods.models import Project, ProjectType

from .services import Resolved
from .types import Item, ItemStatus, Reason, Status

WARNING_CODES = [
    "version_mismatch",
    "optifine_manual",
    "beta_only",
    "unknown_dependency",
    "pinned_other_game",
]


class TargetSerializer(serializers.Serializer):
    game_version = serializers.CharField()
    loader = serializers.ChoiceField(choices=Loader.choices)


class ProjectRefSerializer(serializers.Serializer):
    slug = serializers.CharField()
    title = serializers.CharField()
    icon_url = serializers.CharField(allow_blank=True)
    project_type = serializers.ChoiceField(choices=ProjectType.choices)
    hidden = serializers.BooleanField(
        help_text="A moderator took it out of the catalog: no page and no download here."
    )


class VersionRefSerializer(serializers.Serializer):
    id = serializers.CharField()
    version_number = serializers.CharField()
    version_type = serializers.ChoiceField(choices=["release", "beta", "alpha"])
    file_name = serializers.CharField()
    file_size = serializers.IntegerField()


class ResolutionItemSerializer(serializers.Serializer):
    project = ProjectRefSerializer()
    version = VersionRefSerializer(allow_null=True)
    reason = serializers.ChoiceField(choices=[reason.value for reason in Reason])
    required_by = serializers.ListField(child=serializers.CharField(), help_text="Slugs.")
    status = serializers.ChoiceField(choices=[status.value for status in ItemStatus])
    nearest_game_versions = serializers.ListField(child=serializers.CharField())


class ConflictSerializer(serializers.Serializer):
    a = serializers.CharField()
    b = serializers.CharField()
    declared_by = serializers.CharField()


class SuggestionSerializer(serializers.Serializer):
    project_id = serializers.CharField(help_text="Modrinth id; may be outside our catalog.")
    project = ProjectRefSerializer(allow_null=True)
    suggested_by = serializers.CharField()


class CompatWarningSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=WARNING_CODES)
    params = serializers.DictField(child=serializers.CharField())


class ResolutionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[status.value for status in Status])
    target = TargetSerializer()
    items = ResolutionItemSerializer(many=True)
    conflicts = ConflictSerializer(many=True)
    suggestions = SuggestionSerializer(many=True)
    missing = serializers.ListField(
        child=serializers.CharField(),
        help_text="Being imported; ask again in a few seconds (status `incomplete`).",
    )
    unavailable = serializers.ListField(
        child=serializers.CharField(),
        help_text="Required, but Modrinth does not have them either (status `errors`).",
    )
    warnings = CompatWarningSerializer(many=True)


def _project(row: Project | None, fallback) -> dict:
    if row is not None:
        return {
            "slug": row.slug,
            "title": row.title,
            "icon_url": row.icon_url,
            "project_type": row.project_type,
            "hidden": row.is_hidden,
        }
    return {
        "slug": fallback.slug,
        "title": fallback.title,
        "icon_url": fallback.icon_url,
        "project_type": fallback.project_type,
        "hidden": False,
    }


def _item(item: Item, rows: dict[str, Project]) -> dict:
    version = item.version
    return {
        "project": _project(rows.get(item.project.id), item.project),
        "version": None
        if version is None
        else {
            "id": version.id,
            "version_number": version.version_number,
            "version_type": version.version_type,
            "file_name": version.file_name,
            "file_size": version.file_size,
        },
        "reason": item.reason.value,
        "required_by": item.required_by,
        "status": item.status.value,
        "nearest_game_versions": list(item.nearest_game_versions),
    }


def resolution_data(resolved: Resolved) -> dict:
    """Plain data for `ResolutionSerializer`; the engine's dataclasses are not models."""
    result, rows = resolved.resolution, resolved.projects
    data = {
        "status": result.status.value,
        "target": {"game_version": result.target.game_version, "loader": result.target.loader},
        "items": [_item(item, rows) for item in result.items],
        "conflicts": [{"a": c.a, "b": c.b, "declared_by": c.declared_by} for c in result.conflicts],
        "suggestions": [
            {
                "project_id": s.project,
                "project": _project(rows[s.project], None) if s.project in rows else None,
                "suggested_by": s.suggested_by,
            }
            for s in result.suggestions
        ],
        "missing": result.missing,
        "unavailable": result.unavailable,
        "warnings": [
            {"code": w.code, "params": {k: str(v) for k, v in w.params.items()}}
            for w in result.warnings
        ],
    }
    return ResolutionSerializer(data).data


class InstallQuerySerializer(serializers.Serializer):
    game_version = serializers.CharField(required=False, allow_blank=True, max_length=32)
    loader = serializers.ChoiceField(choices=Loader.choices, required=False, allow_blank=True)


class ResolveItemSerializer(serializers.Serializer):
    slug = serializers.CharField(max_length=96)
    version_id = serializers.CharField(max_length=16, required=False, allow_blank=True)


class ResolveRequestSerializer(serializers.Serializer):
    game_version = serializers.CharField(max_length=32)
    loader = serializers.ChoiceField(choices=Loader.choices)
    # The engine refuses more than 300 with `pack_too_large`; this only bounds the body
    items = ResolveItemSerializer(many=True, allow_empty=False, max_length=1000)


class HashedFileSerializer(serializers.Serializer):
    hash = serializers.RegexField(r"^[0-9a-fA-F]{40}$", help_text="SHA-1 counted in the browser.")
    name = serializers.CharField(max_length=300, allow_blank=True, required=False, default="")


class IdentifyRequestSerializer(serializers.Serializer):
    algorithm = serializers.ChoiceField(choices=["sha1"], default="sha1")
    files = HashedFileSerializer(many=True, allow_empty=False, max_length=2000)


class KnownFileSerializer(serializers.Serializer):
    hash = serializers.CharField()
    name = serializers.CharField(allow_blank=True)
    project = ProjectRefSerializer()
    version = VersionRefSerializer()
    game_versions = serializers.ListField(child=serializers.CharField())
    loaders = serializers.ListField(child=serializers.CharField())


class UnknownFileSerializer(serializers.Serializer):
    hash = serializers.CharField()
    name = serializers.CharField(allow_blank=True)


class IdentifyResponseSerializer(serializers.Serializer):
    known = KnownFileSerializer(many=True)
    unknown = UnknownFileSerializer(many=True)
    guess = TargetSerializer(allow_null=True, help_text="«Схоже, це 1.21.1 · Fabric».")
    fitting = serializers.IntegerField(help_text="Identified mods that fit the guess.")
    identified = serializers.IntegerField(help_text="Identified mods (resource packs excluded).")
    source_unavailable = serializers.BooleanField()


class UpdatesRequestSerializer(IdentifyRequestSerializer):
    game_version = serializers.CharField(max_length=32)
    loader = serializers.ChoiceField(choices=Loader.choices)


class UpdateSerializer(serializers.Serializer):
    hash = serializers.CharField()
    project = ProjectRefSerializer()
    current = VersionRefSerializer()
    latest = VersionRefSerializer(allow_null=True, help_text="null — not ported to the target.")
    status = serializers.ChoiceField(choices=["up_to_date", "update", "not_ported"])


class UpdatesResponseSerializer(serializers.Serializer):
    target = TargetSerializer()
    files = UpdateSerializer(many=True)
    source_unavailable = serializers.BooleanField()


def version_ref(row) -> dict:
    return {
        "id": row.modrinth_version_id,
        "version_number": row.version_number,
        "version_type": row.version_type,
        "file_name": row.file_name,
        "file_size": row.file_size,
    }


def project_ref(row) -> dict:
    return _project(row, None)
