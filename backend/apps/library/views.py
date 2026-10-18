from django.db.models import BooleanField, Exists, OuterRef, Value
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import kinds
from apps.core.exceptions import DomainError
from apps.core.pagination import CatalogPagination
from apps.core.schema import error_responses, paginated
from apps.mods.models import Project
from apps.mods.selectors import catalog
from apps.skins.models import Skin
from apps.skins.selectors import catalog as skins_catalog
from apps.social.models import Like

from . import selectors, services
from .models import Collection, Favorite
from .serializers import (
    AddItemSerializer,
    CollectionDetailSerializer,
    CollectionSerializer,
    CollectionWriteSerializer,
    FavoriteStateSerializer,
    MyCollectionSerializer,
    ReorderSerializer,
    SavedItemSerializer,
    SavedQuerySerializer,
    TargetSerializer,
)


def _with_collection_state(queryset, viewer):
    kind = kinds.get_kind("collection")
    if not viewer.is_authenticated:
        return queryset.annotate(
            is_liked=Value(False, output_field=BooleanField()),
            is_favorited=Value(False, output_field=BooleanField()),
        )
    target = {"content_type": kind.content_type, "object_id": OuterRef("pk")}
    return queryset.annotate(
        is_liked=Exists(Like.objects.filter(user=viewer, **target)),
        is_favorited=Exists(Favorite.objects.filter(user=viewer, **target)),
    )


class FavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def _state(self, kind: kinds.Kind, target) -> Response:
        target.refresh_from_db(fields=["favorites_count"])
        exists = Favorite.objects.filter(
            user=self.request.user, content_type=kind.content_type, object_id=target.pk
        ).exists()
        return Response(
            FavoriteStateSerializer(
                {
                    "kind": kind.name,
                    "id": kind.identifier(target),
                    "favorited": exists,
                    "favorites_count": target.favorites_count,
                }
            ).data
        )

    @extend_schema(
        operation_id="favorites_add",
        request=TargetSerializer,
        responses={200: FavoriteStateSerializer, **error_responses(400, 401, 404)},
    )
    def post(self, request: Request) -> Response:
        data = TargetSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        kind, target = services.add_favorite(
            user=request.user,
            kind=data.validated_data["kind"],
            identifier=data.validated_data["id"],
        )
        return self._state(kind, target)

    @extend_schema(
        operation_id="favorites_remove",
        parameters=[TargetSerializer],
        responses={200: FavoriteStateSerializer, **error_responses(400, 401, 404)},
    )
    def delete(self, request: Request) -> Response:
        # DELETE carries {kind, id} in the query string: request bodies are not portable
        data = TargetSerializer(data=request.query_params)
        data.is_valid(raise_exception=True)
        kind, target = services.remove_favorite(
            user=request.user,
            kind=data.validated_data["kind"],
            identifier=data.validated_data["id"],
        )
        return self._state(kind, target)


class SavedView(APIView):
    """The player's favorites of one kind, newest first; mods can be filtered by version."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="me_saved",
        parameters=[SavedQuerySerializer],
        responses={200: paginated(SavedItemSerializer), **error_responses(400, 401)},
    )
    def get(self, request: Request) -> Response:
        query = SavedQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        kind = kinds.get_kind(query.validated_data["kind"])
        user = request.user

        if kind.name == "mod":
            objects = catalog(user)
            game_version = query.validated_data.get("game_version")
            if game_version:
                objects = objects.filter(game_versions__contains=[game_version])
        elif kind.name == "skin":
            objects = skins_catalog(user)
        else:
            objects = _with_collection_state(selectors.listed_collections(user), user)

        favorites = selectors.favorites_of(user=user, kind=kind, object_ids=objects.values("pk"))
        paginator = CatalogPagination()
        page = paginator.paginate_queryset(favorites, request, view=self)
        by_pk = objects.in_bulk([favorite.object_id for favorite in page])
        items = []
        for favorite in page:
            target = by_pk.get(favorite.object_id)
            if target is None:
                continue
            items.append(
                {
                    "kind": kind.name,
                    "id": kind.identifier(target),
                    "saved_at": favorite.created_at,
                    "mod": target if isinstance(target, Project) else None,
                    "skin": target if isinstance(target, Skin) else None,
                    "collection": target if isinstance(target, Collection) else None,
                }
            )
        return paginator.get_paginated_response(
            SavedItemSerializer(items, many=True, context={"request": request}).data
        )


class CollectionListView(APIView):
    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "POST" else [AllowAny()]

    @extend_schema(
        operation_id="collections_list",
        parameters=[OpenApiParameter("owner", str, description="Nickname of the owner")],
        responses={200: paginated(CollectionSerializer)},
        description="Public collections; with `owner` — the ones shown on their profile.",
    )
    def get(self, request: Request) -> Response:
        queryset = _with_collection_state(
            selectors.public_collections(owner_nickname=request.query_params.get("owner", "")),
            request.user,
        )
        paginator = CatalogPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(
            CollectionSerializer(page, many=True, context={"request": request}).data
        )

    @extend_schema(
        operation_id="collections_create",
        request=CollectionWriteSerializer,
        responses={201: CollectionDetailSerializer, **error_responses(400, 401)},
    )
    def post(self, request: Request) -> Response:
        data = CollectionWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        collection = services.create_collection(
            owner=request.user,
            title=data.validated_data["title"],
            description=data.validated_data.get("description", ""),
            visibility=data.validated_data.get("visibility", Collection.Visibility.PRIVATE),
        )
        return Response(
            CollectionDetailSerializer(collection, context={"request": request, "items": []}).data,
            status=status.HTTP_201_CREATED,
        )


class CollectionAccess(APIView):
    """Shared lookups for collection endpoints; no HTTP methods of its own."""

    permission_classes = [IsAuthenticated]

    def _get(self, request: Request, pk: int) -> Collection:
        return selectors.get_collection(
            pk=pk, viewer=request.user, share_token=request.query_params.get("share_token", "")
        )

    def _editable(self, request: Request, pk: int) -> Collection:
        collection = self._get(request, pk)
        if not selectors.can_edit(request.user, collection):
            raise DomainError(code="forbidden", message="Це не твоя колекція.", status=403)
        return collection

    def _detail(self, request: Request, collection: Collection) -> Response:
        collection = _with_collection_state(
            Collection.objects.filter(pk=collection.pk), request.user
        ).get()
        items = list(selectors.items_of(collection))
        return Response(
            CollectionDetailSerializer(
                collection, context={"request": request, "items": items}
            ).data
        )


class CollectionDetailView(CollectionAccess):
    def get_permissions(self):
        return [AllowAny()] if self.request.method == "GET" else [IsAuthenticated()]

    @extend_schema(
        operation_id="collections_retrieve",
        parameters=[OpenApiParameter("share_token", str, description="Token from the share link")],
        responses={200: CollectionDetailSerializer, **error_responses(404)},
    )
    def get(self, request: Request, pk: int) -> Response:
        return self._detail(request, self._get(request, pk))

    @extend_schema(
        operation_id="collections_update",
        request=CollectionWriteSerializer(partial=True),
        responses={200: CollectionDetailSerializer, **error_responses(400, 401, 403, 404)},
    )
    def patch(self, request: Request, pk: int) -> Response:
        collection = self._editable(request, pk)
        data = CollectionWriteSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        services.update_collection(
            collection=collection, user=request.user, data=data.validated_data
        )
        return self._detail(request, collection)

    @extend_schema(
        operation_id="collections_delete",
        responses={204: None, **error_responses(401, 403, 404)},
    )
    def delete(self, request: Request, pk: int) -> Response:
        collection = self._editable(request, pk)
        services.delete_collection(collection=collection, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CollectionItemsView(CollectionAccess):
    @extend_schema(
        operation_id="collections_items_add",
        request=AddItemSerializer,
        responses={200: CollectionDetailSerializer, **error_responses(400, 401, 403, 404)},
    )
    def post(self, request: Request, pk: int) -> Response:
        collection = self._editable(request, pk)
        data = AddItemSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.add_item(
            collection=collection,
            user=request.user,
            kind=data.validated_data["kind"],
            identifier=data.validated_data["id"],
            note=data.validated_data.get("note", ""),
            slot=data.validated_data.get("slot", ""),
        )
        return self._detail(request, collection)


class CollectionItemView(CollectionAccess):
    @extend_schema(
        operation_id="collections_items_remove",
        responses={200: CollectionDetailSerializer, **error_responses(401, 403, 404)},
    )
    def delete(self, request: Request, pk: int, item_id: int) -> Response:
        collection = self._editable(request, pk)
        services.remove_item(collection=collection, item_id=item_id)
        return self._detail(request, collection)


class CollectionReorderView(CollectionAccess):
    @extend_schema(
        operation_id="collections_reorder",
        request=ReorderSerializer,
        responses={200: CollectionDetailSerializer, **error_responses(400, 401, 403, 404)},
    )
    def post(self, request: Request, pk: int) -> Response:
        collection = self._editable(request, pk)
        data = ReorderSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.reorder_items(collection=collection, item_ids=data.validated_data["item_ids"])
        return self._detail(request, collection)


class CollectionCopyView(CollectionAccess):
    @extend_schema(
        operation_id="collections_copy",
        request=None,
        parameters=[OpenApiParameter("share_token", str)],
        responses={201: CollectionDetailSerializer, **error_responses(401, 404)},
    )
    def post(self, request: Request, pk: int) -> Response:
        source = self._get(request, pk)
        copy = services.copy_collection(source=source, user=request.user)
        response = self._detail(request, copy)
        response.status_code = status.HTTP_201_CREATED
        return response


class MyCollectionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="me_collections",
        parameters=[
            OpenApiParameter("kind", str, description="With `id`: mark collections holding it"),
            OpenApiParameter("id", str),
        ],
        responses={200: MyCollectionSerializer(many=True), **error_responses(401)},
    )
    def get(self, request: Request) -> Response:
        kind_obj = object_id = None
        kind_name, identifier = request.query_params.get("kind"), request.query_params.get("id")
        if kind_name and identifier:
            kind_obj, target = kinds.resolve(kind_name, identifier, viewer=request.user)
            object_id = target.pk
        queryset = _with_collection_state(
            selectors.my_collections(user=request.user, kind=kind_obj, object_id=object_id),
            request.user,
        )
        return Response(
            MyCollectionSerializer(queryset, many=True, context={"request": request}).data
        )
