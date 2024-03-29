from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = "page_size"

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("current_page", self.page.number),
                    ("num_pages", self.page.paginator.num_pages),
                    ("page_size", self.get_page_size(self.request)),
                    ("results", data),
                ]
            )
        )
