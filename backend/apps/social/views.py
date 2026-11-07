from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.core import kinds
from apps.core.schema import error_responses
from apps.core.throttling import WriteScopedRateThrottle

from . import selectors, services
from .models import Review, ReviewVote
from .serializers import (
    ReviewSerializer,
    ReviewsPageSerializer,
    ReviewsQuerySerializer,
    ReviewUpsertSerializer,
    ReviewVoteSerializer,
)

REVIEWS_PAGE_SIZE = 10


class _ReadOpen(APIView):
    """GET for everyone, writes for signed-in users with a write-only throttle scope."""

    throttle_classes = [AnonRateThrottle, WriteScopedRateThrottle]

    def get_permissions(self):
        return [AllowAny()] if self.request.method == "GET" else [IsAuthenticated()]


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
