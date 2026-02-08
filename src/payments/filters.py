from datetime import datetime

from fastapi_filter.contrib.sqlalchemy import Filter

from .models import PaymentDB, PaymentStatusEnum


class PaymentFilter(Filter):
    user_id: int | None = None
    status: PaymentStatusEnum | None = None

    created_at__gte: datetime | None = None  # date_from
    created_at__lte: datetime | None = None  # date_to

    order_by: list[str] = ["-created_at"]

    class Constants(Filter.Constants):
        model = PaymentDB
