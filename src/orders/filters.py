"""
Module: orders.filters

This module contains filters for querying orders in the online cinema system
using FastAPI-Filter with SQLAlchemy integration.

Classes:
    - OrderFilter: Filter class for querying orders based on user, status,
      creation date range, and ordering.
"""

from datetime import datetime

from fastapi_filter.contrib.sqlalchemy import Filter

from .models import OrderDB, OrderStatusEnum


class OrderFilter(Filter):
    """
    Filter for querying OrderDB instances.

    Attributes:
        user_id (int | None): Filter orders by the ID of the user who placed them.
        status (OrderStatusEnum | None): Filter orders by their status
            (e.g., pending, paid, cancelled).
        created_at__gte (datetime | None): Filter orders created on or after this datetime.
        created_at__lte (datetime | None): Filter orders created on or before this datetime.
        order_by (list[str]): Fields to order the results by. Default is ["-created_at"]
            (descending by creation date).

    Usage:
        Filter orders with optional parameters. For example:
            filter = OrderFilter(user_id=123, status=OrderStatusEnum.PAID)
            results = await filter.filter(queryset)
    """
    user_id: int | None = None
    status: OrderStatusEnum | None = None

    created_at__gte: datetime | None = None
    created_at__lte: datetime | None = None

    order_by: list[str] = ["-created_at"]

    class Constants(Filter.Constants):
        """
        Constants for the filter class.

        Attributes:
            model: The SQLAlchemy model to which this filter applies.
        """
        model = OrderDB
