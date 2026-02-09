from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.orders.models import OrderDB, OrderItemDB, OrderStatusEnum

from .filters import PaymentFilter
from .models import PaymentDB, PaymentItemDB, PaymentStatusEnum


class PaymentCRUD:
    """
    Data Access Object (DAO) for Payment-related database operations.

    This class encapsulates all database interactions regarding payments,
    including transaction creation, status updates with row-level locking
    (for concurrency safety), and complex data retrieval with relationship loading.
    """

    async def create_payment(
        self, db: AsyncSession, order: OrderDB, user_id: int
    ) -> PaymentDB:
        """
        Initialize a new payment record based on an existing order.

        This method performs two critical actions:
        1. Creates the main Payment record.
        2. Creates 'snapshot' PaymentItem records. These preserve the price
           of items *at the moment of payment initialization*, protecting
           historical data even if catalog prices change later.

        Args:
            db (AsyncSession): The database session.
            order (OrderDB): The order object containing items and total amount.
            user_id (int): The ID of the user initiating the payment.

        Returns:
            PaymentDB: The newly created and persisted payment record.
        """
        new_payment = PaymentDB(
            user_id=user_id,
            order_id=order.id,
            amount=order.total_amount,
            status=PaymentStatusEnum.PENDING,
        )
        db.add(new_payment)
        await db.flush()

        payment_items = [
            PaymentItemDB(
                payment_id=new_payment.id,
                order_item_id=item.id,
                price_at_payment=item.price_at_order,
            )
            for item in order.items
        ]

        if payment_items:
            db.add_all(payment_items)

        await db.commit()
        await db.refresh(new_payment)
        return new_payment

    async def get_by_session_id(
        self, db: AsyncSession, session_id: str
    ) -> PaymentDB | None:
        """
        Retrieve a payment by its external gateway identifier.

        Typically used during webhook processing or success page rendering
        where the gateway provides its own session ID.

        Args:
            db (AsyncSession): The database session.
            session_id (str): The unique ID provided by the payment gateway (e.g., Stripe Session ID).

        Returns:
            PaymentDB | None: The payment record with 'order' and 'user' relationships loaded,
            or None if not found.
        """
        stmt = (
            select(PaymentDB)
            .where(PaymentDB.external_payment_id == session_id)
            .options(selectinload(PaymentDB.order), selectinload(PaymentDB.user))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def set_external_id(
        self, db: AsyncSession, payment_id: int, session_id: str
    ) -> PaymentDB | None:
        """
        Link a local payment record with an external gateway ID.

        Args:
            db (AsyncSession): The database session.
            payment_id (int): The internal ID of the payment.
            session_id (str): The ID returned by the payment gateway.

        Returns:
            PaymentDB | None: The updated payment record, or None if the ID was invalid.
        """
        payment = await db.get(PaymentDB, payment_id)
        if payment:
            payment.external_payment_id = session_id
            await db.commit()
            await db.refresh(payment)
        return payment

    async def _get_payment_with_lock(
        self, db: AsyncSession, payment_id: int
    ) -> PaymentDB | None:
        """
        Retrieve a payment record with a row-level write lock (FOR UPDATE).

        This is an internal helper method used to prevent race conditions
        when multiple processes (e.g., webhooks and user actions) try to
        update the same payment status simultaneously.

        Args:
            db (AsyncSession): The database session.
            payment_id (int): The payment ID to lock.

        Returns:
            PaymentDB | None: The locked payment instance.
        """
        stmt = (
            select(PaymentDB)
            .where(PaymentDB.id == payment_id)
            .with_for_update()
            .options(selectinload(PaymentDB.order))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def confirm_payment(self, db: AsyncSession, payment: PaymentDB) -> PaymentDB:
        """
        Transition a payment to the SUCCESSFUL state.

        This operation is atomic and uses database locking. It also updates
        the associated Order status to PAID. If the payment is already
        successful, it returns immediately (idempotency).

        Args:
            db (AsyncSession): The database session.
            payment (PaymentDB): The payment object (used for ID reference).

        Returns:
            PaymentDB: The updated payment record.
        """
        locked_payment = await self._get_payment_with_lock(db, payment.id)

        if not locked_payment:
            return payment

        if locked_payment.status == PaymentStatusEnum.SUCCESSFUL:
            return locked_payment

        locked_payment.status = PaymentStatusEnum.SUCCESSFUL

        if locked_payment.order:
            locked_payment.order.status = OrderStatusEnum.PAID

        await db.commit()
        await db.refresh(locked_payment)
        return locked_payment

    async def cancel_payment(self, db: AsyncSession, payment: PaymentDB) -> PaymentDB:
        """
        Transition a payment to the CANCELED state.

        Used when a user cancels the checkout flow or the gateway reports failure.

        Args:
            db (AsyncSession): The database session.
            payment (PaymentDB): The payment object.

        Returns:
            PaymentDB: The updated payment record with items reloaded for display.
        """
        locked_payment = await self._get_payment_with_lock(db, payment.id)

        if not locked_payment:
            return payment

        locked_payment.status = PaymentStatusEnum.CANCELED
        await db.commit()
        stmt = (
            select(PaymentDB)
            .where(PaymentDB.id == payment.id)
            .options(
                selectinload(PaymentDB.payment_items)
                .selectinload(PaymentItemDB.order_item)
                .selectinload(OrderItemDB.movie)
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def mark_refund_requested(
        self, db: AsyncSession, payment: PaymentDB
    ) -> PaymentDB:
        """
        Update the payment status to REFUND_REQUESTED.

        This step usually precedes an admin review. It does not yet interact
        with the payment gateway to return funds.

        Args:
            db (AsyncSession): The database session.
            payment (PaymentDB): The payment to update.

        Returns:
            PaymentDB: The updated payment with full item details reloaded.
        """
        payment.status = PaymentStatusEnum.REFUND_REQUESTED
        await db.commit()

        return await self._reload_payment_with_items(db, payment.id)

    async def refund_payment(self, db: AsyncSession, payment: PaymentDB) -> PaymentDB:
        """
        Finalize a refund by updating the database status.

        This updates the Payment status to REFUNDED and the associated Order
        status to CANCELLED (revoking access to content). Uses row locking
        for safety.

        Args:
            db (AsyncSession): The database session.
            payment (PaymentDB): The payment to refund.

        Returns:
            PaymentDB: The updated payment record.
        """
        locked_payment = await self._get_payment_with_lock(db, payment.id)

        if not locked_payment:
            return payment

        locked_payment.status = PaymentStatusEnum.REFUNDED
        if locked_payment.order:
            locked_payment.order.status = OrderStatusEnum.CANCELLED

        await db.commit()

        return await self._reload_payment_with_items(db, payment.id)

    async def _reload_payment_with_items(
        self, db: AsyncSession, payment_id: int
    ) -> PaymentDB:
        """
        Internal helper to reload a payment with deep relationships.

        Loads: Payment -> PaymentItems -> OrderItem -> Movie.
        Required for generating detailed responses after status changes.

        Args:
            db (AsyncSession): The database session.
            payment_id (int): ID of the payment to reload.

        Returns:
            PaymentDB: The fully loaded payment object.
        """
        stmt = (
            select(PaymentDB)
            .where(PaymentDB.id == payment_id)
            .options(
                selectinload(PaymentDB.payment_items)
                .selectinload(PaymentItemDB.order_item)
                .selectinload(OrderItemDB.movie)
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def get_user_payments(
        self, db: AsyncSession, user_id: int
    ) -> Sequence[PaymentDB]:
        """
        Retrieve the complete payment history for a specific user.

        Results are ordered by creation date (newest first) and include
        details about the purchased movies.

        Args:
            db (AsyncSession): The database session.
            user_id (int): The ID of the user.

        Returns:
            Sequence[PaymentDB]: A list of payment records.
        """
        stmt = (
            select(PaymentDB)
            .where(PaymentDB.user_id == user_id)
            .order_by(desc(PaymentDB.created_at))
            .options(
                selectinload(PaymentDB.payment_items)
                .selectinload(PaymentItemDB.order_item)
                .selectinload(OrderItemDB.movie)
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_all_payments_filtered(
        self, db: AsyncSession, payment_filter: PaymentFilter
    ) -> Sequence[PaymentDB]:
        """
        Retrieve a list of payments based on dynamic filters.

        Used for admin dashboards. Supports filtering by status, dates, etc.,
        and includes eager loading of movie details for the result list.

        Args:
            db (AsyncSession): The database session.
            payment_filter (PaymentFilter): The filter object containing query parameters.

        Returns:
            Sequence[PaymentDB]: A list of filtered payment records.
        """
        stmt = select(PaymentDB).options(
            selectinload(PaymentDB.payment_items)
            .selectinload(PaymentItemDB.order_item)
            .selectinload(OrderItemDB.movie)
        )

        stmt = payment_filter.filter(stmt)
        stmt = payment_filter.sort(stmt)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_payment_details(
        self, db: AsyncSession, payment_id: int
    ) -> PaymentDB | None:
        """
        Retrieve comprehensive details for a single payment.

        This method performs a "heavy" load, fetching the payment along with:
        - All payment items and their associated movies.
        - The user profile.
        - The original order details.

        Args:
            db (AsyncSession): The database session.
            payment_id (int): The unique identifier of the payment.

        Returns:
            PaymentDB | None: The fully populated payment object, or None if not found.
        """
        stmt = (
            select(PaymentDB)
            .where(PaymentDB.id == payment_id)
            .options(
                selectinload(PaymentDB.payment_items)
                .selectinload(PaymentItemDB.order_item)
                .selectinload(OrderItemDB.movie),
                selectinload(PaymentDB.user),
                selectinload(PaymentDB.order),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, payment_id: int) -> PaymentDB | None:
        """
        Fetch a payment record by its primary key.

        This is a lightweight lookup without eager loading of relationships.

        Args:
            db (AsyncSession): The database session.
            payment_id (int): The unique identifier of the payment.

        Returns:
            PaymentDB | None: The payment record or None.
        """
        return await db.get(PaymentDB, payment_id)


payment_crud = PaymentCRUD()
