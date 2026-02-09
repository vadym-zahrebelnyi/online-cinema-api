from datetime import datetime

from fastapi_filter.contrib.sqlalchemy import Filter

from .models import PaymentDB, PaymentStatusEnum


class PaymentFilter(Filter):
    """
    Filter class for querying payments with specific criteria.

    This class integrates with FastAPI-Filter to provide dynamic filtering capabilities
    on the PaymentDB model. It supports filtering by user, status, and date ranges,
    as well as sorting.

    Attributes:
        user_id (int | None): Filter by the unique identifier of the user who made the payment.
        status (PaymentStatusEnum | None): Filter by the current status of the payment
            (e.g., 'successful', 'pending').
        created_at__gte (datetime | None): Filter for payments created on or after this timestamp
            (inclusive start date).
        created_at__lte (datetime | None): Filter for payments created on or before this timestamp
            (inclusive end date).
        order_by (list[str]): List of fields to sort the results by. Defaults to descending
            order of creation date ('-created_at').
    """
    user_id: int | None = None
    status: PaymentStatusEnum | None = None

    created_at__gte: datetime | None = None  # date_from
    created_at__lte: datetime | None = None  # date_to

    order_by: list[str] = ["-created_at"]

    class Constants(Filter.Constants):
        """
        Configuration constants for the filter.

        Attributes:
            model (Type[PaymentDB]): The SQLAlchemy model that this filter applies to.
        """
        model = PaymentDB
