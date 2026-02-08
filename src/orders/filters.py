from datetime import datetime

from fastapi_filter.contrib.sqlalchemy import Filter

from .models import OrderDB, OrderStatusEnum


class OrderFilter(Filter):
    user_id: int | None = None
    status: OrderStatusEnum | None = None

    created_at__gte: datetime | None = None
    created_at__lte: datetime | None = None

    order_by: list[str] = ["-created_at"]

    class Constants(Filter.Constants):
        model = OrderDB
