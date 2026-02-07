from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.orders.models import OrderDB, OrderItemDB, OrderStatusEnum

from .filters import PaymentFilter
from .models import PaymentDB, PaymentItemDB, PaymentStatusEnum


class PaymentCRUD:
    async def create_payment(
        self, db: AsyncSession, order: OrderDB, user_id: int
    ) -> PaymentDB:
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
        payment = await db.get(PaymentDB, payment_id)
        if payment:
            payment.external_payment_id = session_id
            await db.commit()
            await db.refresh(payment)
        return payment

    async def _get_payment_with_lock(
        self, db: AsyncSession, payment_id: int
    ) -> PaymentDB | None:
        stmt = (
            select(PaymentDB)
            .where(PaymentDB.id == payment_id)
            .with_for_update()
            .options(selectinload(PaymentDB.order))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def confirm_payment(self, db: AsyncSession, payment: PaymentDB) -> PaymentDB:
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
        payment.status = PaymentStatusEnum.REFUND_REQUESTED
        await db.commit()

        return await self._reload_payment_with_items(db, payment.id)

    async def refund_payment(self, db: AsyncSession, payment: PaymentDB) -> PaymentDB:
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
        stmt = select(PaymentDB).options(
            selectinload(PaymentDB.payment_items)
            .selectinload(PaymentItemDB.order_item)
            .selectinload(OrderItemDB.movie)
        )

        stmt = payment_filter.filter(stmt)
        stmt = payment_filter.sort(stmt)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, db: AsyncSession, payment_id: int) -> PaymentDB | None:
        return await db.get(PaymentDB, payment_id)


payment_crud = PaymentCRUD()
