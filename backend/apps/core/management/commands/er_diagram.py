"""ER diagram of our apps in Mermaid (`erDiagram`): renders on GitHub, needs no Graphviz."""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models

OUR_APPS = [
    "accounts",
    "mods",
    "skins",
    "servers",
    "library",
    "social",
    "moderation",
    "notifications",
]
# Shown as a relation to `object`, which stands for «any registered kind»
GENERIC = {"content_type", "object_id"}
TYPES = {
    models.AutoField: "int",
    models.BigAutoField: "bigint",
    models.BooleanField: "bool",
    models.CharField: "varchar",
    models.SlugField: "varchar",
    models.EmailField: "varchar",
    models.URLField: "varchar",
    models.TextField: "text",
    models.IntegerField: "int",
    models.PositiveIntegerField: "int",
    models.PositiveSmallIntegerField: "smallint",
    models.PositiveBigIntegerField: "bigint",
    models.FloatField: "float",
    models.DateTimeField: "timestamp",
    models.JSONField: "json",
    models.FileField: "file",
    models.ImageField: "file",
}


def _type(field: models.Field) -> str:
    if field.is_relation:
        return "bigint"
    if field.get_internal_type() == "ArrayField":
        return "array"
    for cls in type(field).__mro__:
        if cls in TYPES:
            return TYPES[cls]
    return field.get_internal_type().removesuffix("Field").lower()


class Command(BaseCommand):
    help = "Print the ER diagram of the project's models as Mermaid."

    def handle(self, *args, **options) -> None:
        lines = ["erDiagram"]
        relations = []
        for model in apps.get_models():
            meta = model._meta
            if meta.app_label not in OUR_APPS or meta.auto_created:
                continue
            name = meta.object_name
            lines.append(f"    {name} {{")
            for field in meta.concrete_fields:
                if field.name in GENERIC and field.name == "object_id":
                    continue
                if field.name == "content_type":
                    relations.append(f'    {name} }}o--|| ANY_KIND : "content_type + object_id"')
                    lines.append(f"        int {field.name} FK")
                    continue
                key = " PK" if field.primary_key else " FK" if field.is_relation else ""
                lines.append(f"        {_type(field)} {field.name}{key}")
                if field.is_relation and field.related_model is not None:
                    target = field.related_model._meta
                    if target.app_label in OUR_APPS:
                        cardinality = "||--||" if field.one_to_one else "}o--||"
                        relations.append(
                            f'    {name} {cardinality} {target.object_name} : "{field.name}"'
                        )
            for field in meta.many_to_many:
                target = field.related_model._meta
                if target.app_label in OUR_APPS:
                    relations.append(f'    {name} }}o--o{{ {target.object_name} : "{field.name}"')
            lines.append("    }")
        lines.append("    ANY_KIND {")
        lines.append('        string kind "mod, skin, server, collection"')
        lines.append("    }")
        self.stdout.write("\n".join([*lines, *sorted(set(relations))]))
