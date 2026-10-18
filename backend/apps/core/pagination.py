from rest_framework.pagination import PageNumberPagination


class CatalogPagination(PageNumberPagination):
    """Catalogs: ?page=&page_size= (24 by default, 60 at most)."""

    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 60
