from rest_framework.pagination import PageNumberPagination


class ConsolePagination(PageNumberPagination):
    """Numbered pages: the console jumps through hundreds of agencies and accounts."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
