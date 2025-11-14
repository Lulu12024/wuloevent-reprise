
"""
Created on November 03, 2025

@author:
    Beaudelaire LAHOUME, alias root-lr
"""

from rest_framework.pagination import PageNumberPagination

class SellerStatSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = 'p'

    # def get_paginated_response(self, data):
    #     return super().get_paginated_response(data)
