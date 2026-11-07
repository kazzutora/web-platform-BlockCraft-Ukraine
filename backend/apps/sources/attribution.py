"""`source: {name, url}` of every catalog object: where it lives and links back (CLAUDE.md)."""

from typing import TypedDict

from rest_framework import serializers

from . import registry


class SourceRef(TypedDict):
    name: str
    url: str


class SourceRefSerializer(serializers.Serializer):
    name = serializers.CharField()
    url = serializers.URLField(help_text="The object's own page at the source.")


def source_ref(key: str, url: str) -> SourceRef:
    return {"name": registry.get(key).name, "url": url}
