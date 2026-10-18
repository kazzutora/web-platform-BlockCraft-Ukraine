from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.schema import error_responses

from . import selectors, services
from .serializers import (
    AvatarUploadSerializer,
    GameProfileSerializer,
    MeSerializer,
    MeUpdateSerializer,
    OnboardingSerializer,
    PublicProfileSerializer,
    UserSettingsSerializer,
)


def _me(request: Request) -> Response:
    user = request.user
    user.refresh_from_db()
    return Response(MeSerializer(user).data)


@method_decorator(ensure_csrf_cookie, name="get")
class CsrfView(APIView):
    """Sets the `csrftoken` cookie that the browser sends back in `X-CSRFToken`."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(operation_id="csrf", responses={204: None}, tags=["auth"])
    def get(self, request: Request) -> Response:
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="me_retrieve", responses={200: MeSerializer, **error_responses(401)}
    )
    def get(self, request: Request) -> Response:
        return Response(MeSerializer(request.user).data)

    @extend_schema(
        operation_id="me_update",
        request=MeUpdateSerializer,
        responses={200: MeSerializer, **error_responses(400, 401)},
    )
    def patch(self, request: Request) -> Response:
        serializer = MeUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_account(user=request.user, data=serializer.validated_data)
        return _me(request)


class MeGameProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="me_game_profile_retrieve",
        responses={200: GameProfileSerializer, **error_responses(401)},
    )
    def get(self, request: Request) -> Response:
        return Response(GameProfileSerializer(request.user.game_profile).data)

    @extend_schema(
        operation_id="me_game_profile_update",
        request=GameProfileSerializer,
        responses={200: GameProfileSerializer, **error_responses(400, 401)},
    )
    def patch(self, request: Request) -> Response:
        serializer = GameProfileSerializer(
            request.user.game_profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        profile = services.update_game_profile(user=request.user, data=serializer.validated_data)
        return Response(GameProfileSerializer(profile).data)


class OnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="me_onboarding",
        request=OnboardingSerializer,
        responses={200: GameProfileSerializer, **error_responses(400, 401)},
    )
    def post(self, request: Request) -> Response:
        serializer = OnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = services.complete_onboarding(user=request.user, data=serializer.validated_data)
        return Response(GameProfileSerializer(profile).data)


class MeSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="me_settings_retrieve",
        responses={200: UserSettingsSerializer, **error_responses(401)},
    )
    def get(self, request: Request) -> Response:
        return Response(UserSettingsSerializer(request.user.settings).data)

    @extend_schema(
        operation_id="me_settings_update",
        request=UserSettingsSerializer,
        responses={200: UserSettingsSerializer, **error_responses(400, 401)},
    )
    def patch(self, request: Request) -> Response:
        serializer = UserSettingsSerializer(request.user.settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        settings = services.update_settings(user=request.user, data=serializer.validated_data)
        return Response(UserSettingsSerializer(settings).data)


class MeAvatarView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    throttle_scope = "uploads"

    @extend_schema(
        operation_id="me_avatar_upload",
        request={"multipart/form-data": AvatarUploadSerializer},
        responses={200: MeSerializer, **error_responses(400, 401)},
    )
    def put(self, request: Request) -> Response:
        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.set_avatar(user=request.user, upload=serializer.validated_data["avatar"])
        return _me(request)

    @extend_schema(
        operation_id="me_avatar_delete", responses={200: MeSerializer, **error_responses(401)}
    )
    def delete(self, request: Request) -> Response:
        services.remove_avatar(user=request.user)
        return _me(request)


class UserProfileView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="users_retrieve",
        responses={200: PublicProfileSerializer, **error_responses(404)},
    )
    def get(self, request: Request, nickname: str) -> Response:
        owner = selectors.get_profile_user(nickname=nickname)
        full = selectors.can_view_full_profile(viewer=request.user, owner=owner)
        return Response(PublicProfileSerializer.from_user(owner, full=full).data)
