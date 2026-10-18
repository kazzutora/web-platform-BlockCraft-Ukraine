from urllib.parse import parse_qs, urlparse

from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.core import kinds
from apps.core.schema import error_responses
from apps.core.throttling import WriteScopedRateThrottle

from . import selectors, services
from .models import Comment, Like, Review, ReviewVote
from .serializers import (
    CommentCreateSerializer,
    CommentSerializer,
    CommentsPageSerializer,
    CommentsQuerySerializer,
    CommentUpdateSerializer,
    LikeStateSerializer,
    ReviewSerializer,
    ReviewsPageSerializer,
    ReviewsQuerySerializer,
    ReviewUpsertSerializer,
    ReviewVoteSerializer,
    TargetQuerySerializer,
)

REVIEWS_PAGE_SIZE = 10


class _ReadOpen(APIView):
    """GET for everyone, writes for signed-in users with a write-only throttle scope."""

    throttle_classes = [AnonRateThrottle, WriteScopedRateThrottle]

    def get_permissions(self):
        return [AllowAny()] if self.request.method == "GET" else [IsAuthenticated()]


class LikeView(APIView):
    permission_classes = [IsAuthenticated]

    def _state(self, kind: kinds.Kind, target) -> Response:
        target.refresh_from_db(fields=["likes_count"])
        liked = Like.objects.filter(
            user=self.request.user, content_type=kind.content_type, object_id=target.pk
        ).exists()
        return Response(
            LikeStateSerializer(
                {
                    "kind": kind.name,
                    "id": kind.identifier(target),
                    "liked": liked,
                    "likes_count": target.likes_count,
                }
            ).data
        )

    @extend_schema(
        operation_id="likes_add",
        request=TargetQuerySerializer,
        responses={200: LikeStateSerializer, **error_responses(400, 401, 404)},
    )
    def post(self, request: Request) -> Response:
        data = TargetQuerySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        kind, target = services.like(
            user=request.user,
            kind=data.validated_data["kind"],
            identifier=data.validated_data["id"],
        )
        return self._state(kind, target)

    @extend_schema(
        operation_id="likes_remove",
        parameters=[TargetQuerySerializer],
        responses={200: LikeStateSerializer, **error_responses(400, 401, 404)},
    )
    def delete(self, request: Request) -> Response:
        # DELETE carries {kind, id} in the query string: request bodies are not portable
        data = TargetQuerySerializer(data=request.query_params)
        data.is_valid(raise_exception=True)
        kind, target = services.unlike(
            user=request.user,
            kind=data.validated_data["kind"],
            identifier=data.validated_data["id"],
        )
        return self._state(kind, target)


def _with_my_vote(queryset, viewer):
    if not viewer.is_authenticated:
        return queryset
    return queryset.annotate(
        my_vote=Subquery(
            ReviewVote.objects.filter(user=viewer, review=OuterRef("pk")).values("is_helpful")[:1]
        )
    )


class ReviewsView(_ReadOpen):
    throttle_scope = "reviews"

    @extend_schema(
        operation_id="reviews_list",
        parameters=[ReviewsQuerySerializer],
        responses={200: ReviewsPageSerializer, **error_responses(400, 404)},
    )
    def get(self, request: Request) -> Response:
        query = ReviewsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        kind, target = kinds.resolve(
            query.validated_data["kind"],
            query.validated_data["id"],
            viewer=request.user,
            action="review",
        )
        reviews = _with_my_vote(
            selectors.reviews_for(
                kind=kind, object_id=target.pk, sort=query.validated_data["sort"]
            ),
            request.user,
        )
        page = query.validated_data["page"]
        start = (page - 1) * REVIEWS_PAGE_SIZE
        count = reviews.count()
        results = list(reviews[start : start + REVIEWS_PAGE_SIZE])
        my_review = (
            _with_my_vote(reviews.filter(user=request.user), request.user).first()
            if request.user.is_authenticated
            else None
        )
        payload = {
            "summary": {
                "rating_avg": target.rating_avg,
                "rating_count": target.rating_count,
                "distribution": selectors.review_distribution(kind=kind, object_id=target.pk),
                "my_review": my_review,
            },
            "count": count,
            "next_page": page + 1 if start + REVIEWS_PAGE_SIZE < count else None,
            "results": results,
        }
        return Response(ReviewsPageSerializer(payload, context={"request": request}).data)

    @extend_schema(
        operation_id="reviews_upsert",
        request=ReviewUpsertSerializer,
        responses={
            200: ReviewSerializer,
            201: ReviewSerializer,
            **error_responses(400, 401, 404, 429),
        },
        description="Creates the player's review or updates it (one per object).",
    )
    def put(self, request: Request) -> Response:
        data = ReviewUpsertSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        review, created = services.upsert_review(
            user=request.user,
            kind=data.validated_data["kind"],
            identifier=data.validated_data["id"],
            stars=data.validated_data["stars"],
            text=data.validated_data.get("text", ""),
        )
        return Response(
            ReviewSerializer(review, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ReviewDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="reviews_delete", responses={204: None, **error_responses(401, 403, 404)}
    )
    def delete(self, request: Request, pk: int) -> Response:
        services.delete_review(review=get_object_or_404(Review, pk=pk), user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewVoteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="reviews_vote",
        request=ReviewVoteSerializer,
        responses={200: ReviewSerializer, **error_responses(400, 401, 404)},
    )
    def post(self, request: Request, pk: int) -> Response:
        data = ReviewVoteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        review = get_object_or_404(Review, pk=pk, status=Review.Status.PUBLISHED)
        services.vote_review(
            review=review, user=request.user, is_helpful=data.validated_data["is_helpful"]
        )
        review = _with_my_vote(
            Review.objects.select_related("user").filter(pk=pk), request.user
        ).get()
        return Response(ReviewSerializer(review, context={"request": request}).data)


class CommentCursor(CursorPagination):
    page_size = 20
    ordering = "-created_at"


def _cursor_of(link: str | None) -> str | None:
    if not link:
        return None
    return parse_qs(urlparse(link).query).get("cursor", [None])[0]


class CommentsView(_ReadOpen):
    throttle_scope = "comments"

    @extend_schema(
        operation_id="comments_list",
        parameters=[CommentsQuerySerializer],
        responses={200: CommentsPageSerializer, **error_responses(400, 404)},
        description="Top-level comments with replies; the first page also brings the pinned one.",
    )
    def get(self, request: Request) -> Response:
        query = CommentsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        kind, target = kinds.resolve(
            query.validated_data["kind"],
            query.validated_data["id"],
            viewer=request.user,
            action="comment",
        )
        comments = selectors.comments_for(kind=kind, object_id=target.pk)
        paginator = CommentCursor()
        page = paginator.paginate_queryset(comments.filter(is_pinned=False), request, view=self)
        owner = kind.owner_of(target)
        context = {"request": request, "owner_id": getattr(owner, "pk", None)}
        first_page = not query.validated_data.get("cursor")
        payload = {
            "can_comment": services.can_comment(user=request.user, kind=kind, target=target),
            "can_pin": request.user.is_authenticated
            and (getattr(owner, "pk", None) == request.user.pk or request.user.is_moderator),
            "comments_count": target.comments_count,
            "pinned": list(comments.filter(is_pinned=True)) if first_page else [],
            "results": page,
            "next_cursor": _cursor_of(paginator.get_next_link()),
        }
        return Response(CommentsPageSerializer(payload, context=context).data)

    @extend_schema(
        operation_id="comments_create",
        request=CommentCreateSerializer,
        responses={201: CommentSerializer, **error_responses(400, 401, 403, 404, 429)},
    )
    def post(self, request: Request) -> Response:
        data = CommentCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        comment = services.add_comment(
            user=request.user,
            kind=data.validated_data["kind"],
            identifier=data.validated_data["id"],
            body=data.validated_data["body"],
            parent_id=data.validated_data.get("parent"),
        )
        return Response(
            CommentSerializer(comment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CommentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="comments_update",
        request=CommentUpdateSerializer,
        responses={200: CommentSerializer, **error_responses(400, 401, 403, 404)},
    )
    def patch(self, request: Request, pk: int) -> Response:
        data = CommentUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        comment = services.edit_comment(
            comment=get_object_or_404(Comment.objects.published(), pk=pk),
            user=request.user,
            body=data.validated_data["body"],
        )
        return Response(CommentSerializer(comment, context={"request": request}).data)

    @extend_schema(
        operation_id="comments_delete", responses={204: None, **error_responses(401, 403, 404)}
    )
    def delete(self, request: Request, pk: int) -> Response:
        services.delete_comment(
            comment=get_object_or_404(Comment.objects.published(), pk=pk), user=request.user
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommentPinView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="comments_pin",
        request=None,
        responses={200: CommentSerializer, **error_responses(400, 401, 403, 404)},
        description="Pins or unpins a top-level comment; one pinned comment per object.",
    )
    def post(self, request: Request, pk: int) -> Response:
        comment = services.toggle_pin(
            comment=get_object_or_404(Comment.objects.published(), pk=pk), user=request.user
        )
        return Response(CommentSerializer(comment, context={"request": request}).data)
