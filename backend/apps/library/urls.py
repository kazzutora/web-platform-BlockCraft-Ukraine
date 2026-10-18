from django.urls import path

from . import views

urlpatterns = [
    path("favorites", views.FavoriteView.as_view(), name="favorites"),
    path("me/saved", views.SavedView.as_view(), name="me-saved"),
    path("me/collections", views.MyCollectionsView.as_view(), name="me-collections"),
    path("collections", views.CollectionListView.as_view(), name="collections"),
    path("collections/<int:pk>", views.CollectionDetailView.as_view(), name="collection"),
    path(
        "collections/<int:pk>/items", views.CollectionItemsView.as_view(), name="collection-items"
    ),
    path(
        "collections/<int:pk>/items/<int:item_id>",
        views.CollectionItemView.as_view(),
        name="collection-item",
    ),
    path(
        "collections/<int:pk>/reorder",
        views.CollectionReorderView.as_view(),
        name="collection-reorder",
    ),
    path("collections/<int:pk>/copy", views.CollectionCopyView.as_view(), name="collection-copy"),
]
