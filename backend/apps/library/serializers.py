from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.core import kinds
from apps.mods.models import Project
from apps.mods.serializers import ProjectCardSerializer
from apps.skins.models import Skin
from apps.skins.serializers import SkinCardSerializer

from .models import Collection, CollectionItem
from .selectors import PREVIEW_ITEMS, can_edit


def thumbnail_of(target) -> str | None:
    """Image for collection previews; each kind exposes its own picture field."""
    if isinstance(target, Skin):
        image = target.preview or target.file
        return image.url if image else None
    return getattr(target, "icon_url", None) or None


class TargetSerializer(serializers.Serializer):
    """`{kind, id}`: id is a slug or a number depending on the kind."""

    kind = serializers.ChoiceField(choices=kinds.names())
    id = serializers.CharField(max_length=96)


class FavoriteStateSerializer(serializers.Serializer):
    kind = serializers.CharField()
    id = serializers.CharField()
    favorited = serializers.BooleanField()
    favorites_count = serializers.IntegerField()


class CollectionSerializer(serializers.ModelSerializer):
    owner = UserBriefSerializer(read_only=True)
    preview = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = [
            "id",
            "title",
            "description",
            "visibility",
            "owner",
            "items_count",
            "likes_count",
            "favorites_count",
            "is_setup",
            "preview",
            "can_edit",
            "is_liked",
            "is_favorited",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    def get_preview(self, collection: Collection) -> list[str]:
        items = getattr(collection, "preview_items", None)
        if items is None:
            # The detail view passes its prefetched items; anything else reads the first four
            loaded = self.context.get("items")
            items = (
                loaded[:PREVIEW_ITEMS]
                if loaded is not None
                else collection.items.all()[:PREVIEW_ITEMS]
            )
        return [url for item in items if (url := thumbnail_of(item.target))]

    def get_can_edit(self, collection: Collection) -> bool:
        request = self.context.get("request")
        return bool(request) and can_edit(request.user, collection)

    def get_is_liked(self, collection: Collection) -> bool:
        return bool(getattr(collection, "is_liked", False))

    def get_is_favorited(self, collection: Collection) -> bool:
        return bool(getattr(collection, "is_favorited", False))


class CollectionItemSerializer(serializers.ModelSerializer):
    kind = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()
    mod = serializers.SerializerMethodField()
    skin = serializers.SerializerMethodField()

    class Meta:
        model = CollectionItem
        fields = ["id", "kind", "target_id", "position", "slot", "note", "mod", "skin"]
        read_only_fields = fields

    def _kind(self, item: CollectionItem) -> kinds.Kind:
        return kinds.kind_for_content_type(item.content_type_id)

    def get_kind(self, item: CollectionItem) -> str:
        return self._kind(item).name

    def get_target_id(self, item: CollectionItem) -> str:
        return self._kind(item).identifier(item.target) if item.target else str(item.object_id)

    @extend_schema_field(ProjectCardSerializer(allow_null=True))
    def get_mod(self, item: CollectionItem) -> dict | None:
        target = item.target
        if isinstance(target, Project) and target.status == Project.Status.PUBLISHED:
            return ProjectCardSerializer(target, context=self.context).data
        return None

    @extend_schema_field(SkinCardSerializer(allow_null=True))
    def get_skin(self, item: CollectionItem) -> dict | None:
        target = item.target
        if isinstance(target, Skin) and target.status == Skin.Status.PUBLISHED:
            return SkinCardSerializer(target, context=self.context).data
        return None


class CollectionDetailSerializer(CollectionSerializer):
    items = serializers.SerializerMethodField()
    share_token = serializers.SerializerMethodField()
    editors = serializers.SerializerMethodField()

    class Meta(CollectionSerializer.Meta):
        fields = [*CollectionSerializer.Meta.fields, "items", "share_token", "editors"]
        read_only_fields = fields

    @extend_schema_field(CollectionItemSerializer(many=True))
    def get_items(self, collection: Collection) -> list[dict]:
        items = self.context.get("items", collection.items.all())
        return CollectionItemSerializer(items, many=True, context=self.context).data

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_share_token(self, collection: Collection) -> str | None:
        """Only people who can edit see the token for «за посиланням»."""
        return collection.share_token if self.get_can_edit(collection) else None

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_editors(self, collection: Collection) -> list[str]:
        if not self.get_can_edit(collection):
            return []
        return [editor.nickname for editor in collection.editors.all()]


class CollectionWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=80)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True)
    visibility = serializers.ChoiceField(choices=Collection.Visibility.choices, required=False)
    editors = serializers.ListField(
        child=serializers.CharField(max_length=24), required=False, max_length=10
    )


class AddItemSerializer(TargetSerializer):
    note = serializers.CharField(max_length=140, required=False, allow_blank=True)
    slot = serializers.ChoiceField(
        choices=CollectionItem.Slot.choices, required=False, allow_blank=True
    )


class ReorderSerializer(serializers.Serializer):
    item_ids = serializers.ListField(child=serializers.IntegerField(), max_length=500)


class MyCollectionSerializer(CollectionSerializer):
    contains = serializers.SerializerMethodField()
    item_id = serializers.SerializerMethodField()

    class Meta(CollectionSerializer.Meta):
        fields = [*CollectionSerializer.Meta.fields, "contains", "item_id"]
        read_only_fields = fields

    def get_contains(self, collection: Collection) -> bool:
        return bool(getattr(collection, "contains", False))

    def get_item_id(self, collection: Collection) -> int | None:
        """Item of the requested object in this collection, to remove it again."""
        return getattr(collection, "item_id", None)


class SavedQuerySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=kinds.names(), default="mod")
    game_version = serializers.CharField(required=False, allow_blank=True, max_length=32)


class SavedItemSerializer(serializers.Serializer):
    """One saved object; exactly one of the kind fields is filled."""

    kind = serializers.CharField()
    id = serializers.CharField()
    saved_at = serializers.DateTimeField()
    mod = ProjectCardSerializer(allow_null=True)
    skin = SkinCardSerializer(allow_null=True)
    collection = CollectionSerializer(allow_null=True)
