from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.orders.models import OrderDB, OrderItemDB, OrderStatusEnum
from src.payments.crud import PaymentCRUD
from src.payments.models import PaymentDB, PaymentStatusEnum


@pytest.fixture
def mock_db():
    db = AsyncMock()
    mock_result = MagicMock()
    db.execute.return_value = mock_result
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    return db


@pytest.fixture
def payment_crud():
    return PaymentCRUD()


@pytest.mark.asyncio
async def test_create_payment_success(payment_crud, mock_db):
    """
    Test successful creation of a payment record and its snapshot items.
    """
    user_id = 1
    item1 = OrderItemDB(id=101, price_at_order=Decimal("10.00"))
    item2 = OrderItemDB(id=102, price_at_order=Decimal("20.00"))
    order = OrderDB(id=1, total_amount=Decimal("30.00"), items=[item1, item2])

    result = await payment_crud.create_payment(mock_db, order, user_id)

    assert result.user_id == user_id
    assert result.order_id == order.id
    assert result.amount == order.total_amount
    assert result.status == PaymentStatusEnum.PENDING

    mock_db.add.assert_called()
    mock_db.add_all.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_payment_error(payment_crud, mock_db):
    """
    Test error handling during payment creation triggers rollback.
    """
    order = OrderDB(id=1, total_amount=Decimal("10.00"), items=[])
    mock_db.flush.side_effect = SQLAlchemyError("DB Error")

    with pytest.raises(SQLAlchemyError):
        await payment_crud.create_payment(mock_db, order, user_id=1)

    mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_session_id_found(payment_crud, mock_db):
    """
    Test retrieving a payment by external session ID when exists.
    """
    payment = PaymentDB(id=1, external_payment_id="sess_123")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = payment
    mock_db.execute.return_value = mock_result

    result = await payment_crud.get_by_session_id(mock_db, "sess_123")

    assert result == payment
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_session_id_not_found(payment_crud, mock_db):
    """
    Test retrieving a payment by external session ID when not found.
    """
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    result = await payment_crud.get_by_session_id(mock_db, "sess_unknown")

    assert result is None


@pytest.mark.asyncio
async def test_set_external_id_success(payment_crud, mock_db):
    """
    Test successfully linking an external gateway ID to a payment.
    """
    payment = PaymentDB(id=1, external_payment_id=None)
    mock_db.get.return_value = payment

    result = await payment_crud.set_external_id(mock_db, 1, "sess_new")

    assert result.external_payment_id == "sess_new"
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(payment)


@pytest.mark.asyncio
async def test_set_external_id_not_found(payment_crud, mock_db):
    """
    Test setting external ID returns None if payment does not exist.
    """
    mock_db.get.return_value = None

    result = await payment_crud.set_external_id(mock_db, 999, "sess_new")

    assert result is None
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_external_id_error(payment_crud, mock_db):
    """
    Test error handling during external ID update triggers rollback.
    """
    mock_db.get.side_effect = SQLAlchemyError("DB Error")

    with pytest.raises(SQLAlchemyError):
        await payment_crud.set_external_id(mock_db, 1, "sess_new")

    mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_payment_success(payment_crud, mock_db):
    """
    Test confirming a payment transitions status to SUCCESSFUL and Order to PAID.
    """
    order = OrderDB(id=10, status=OrderStatusEnum.PENDING)
    payment = PaymentDB(id=1, status=PaymentStatusEnum.PENDING)
    payment.order = order

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = payment
    mock_db.execute.return_value = mock_result

    result = await payment_crud.confirm_payment(mock_db, payment)

    assert result.status == PaymentStatusEnum.SUCCESSFUL
    assert order.status == OrderStatusEnum.PAID
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_payment_idempotency(payment_crud, mock_db):
    """
    Test that confirming an already successful payment performs no action.
    """
    payment = PaymentDB(id=1, status=PaymentStatusEnum.SUCCESSFUL)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = payment
    mock_db.execute.return_value = mock_result

    result = await payment_crud.confirm_payment(mock_db, payment)

    assert result.status == PaymentStatusEnum.SUCCESSFUL
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_payment_not_found_lock(payment_crud, mock_db):
    """
    Test confirm payment returns original object if lock acquisition fails.
    """
    payment = PaymentDB(id=1, status=PaymentStatusEnum.PENDING)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    result = await payment_crud.confirm_payment(mock_db, payment)

    assert result == payment
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_payment_error(payment_crud, mock_db):
    """
    Test error handling during confirmation triggers rollback.
    """
    payment = PaymentDB(id=1)
    mock_db.execute.side_effect = SQLAlchemyError("DB Error")

    with pytest.raises(SQLAlchemyError):
        await payment_crud.confirm_payment(mock_db, payment)

    mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_payment_success(payment_crud, mock_db):
    """
    Test canceling a payment updates status and reloads items.
    """
    payment = PaymentDB(id=1, status=PaymentStatusEnum.PENDING)
    mock_result_lock = MagicMock()
    mock_result_lock.scalar_one_or_none.return_value = payment
    mock_result_reload = MagicMock()
    mock_result_reload.scalar_one.return_value = payment
    mock_db.execute.side_effect = [mock_result_lock, mock_result_reload]

    result = await payment_crud.cancel_payment(mock_db, payment)

    assert result.status == PaymentStatusEnum.CANCELED
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_payment_error(payment_crud, mock_db):
    """
    Test error handling during cancellation triggers rollback.
    """
    payment = PaymentDB(id=1)
    mock_db.execute.side_effect = SQLAlchemyError("DB Error")

    with pytest.raises(SQLAlchemyError):
        await payment_crud.cancel_payment(mock_db, payment)

    mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_refund_payment_success(payment_crud, mock_db):
    """
    Test refunding a payment transitions status to REFUNDED and Order to CANCELLED.
    """
    order = OrderDB(id=10, status=OrderStatusEnum.PAID)
    payment = PaymentDB(id=1, status=PaymentStatusEnum.SUCCESSFUL)
    payment.order = order

    mock_result_lock = MagicMock()
    mock_result_lock.scalar_one_or_none.return_value = payment
    mock_result_reload = MagicMock()
    mock_result_reload.scalar_one.return_value = payment
    mock_db.execute.side_effect = [mock_result_lock, mock_result_reload]

    await payment_crud.refund_payment(mock_db, payment)

    assert payment.status == PaymentStatusEnum.REFUNDED
    assert order.status == OrderStatusEnum.CANCELLED
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refund_payment_error(payment_crud, mock_db):
    """
    Test error handling during refund triggers rollback.
    """
    payment = PaymentDB(id=1)
    mock_db.execute.side_effect = SQLAlchemyError("DB Error")

    with pytest.raises(SQLAlchemyError):
        await payment_crud.refund_payment(mock_db, payment)

    mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_payments(payment_crud, mock_db):
    """
    Test retrieving payment history for a user.
    """
    payments = [PaymentDB(id=1), PaymentDB(id=2)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = payments
    mock_db.execute.return_value = mock_result

    result = await payment_crud.get_user_payments(mock_db, user_id=1)

    assert len(result) == 2
    assert result == payments


@pytest.mark.asyncio
async def test_get_all_payments_filtered(payment_crud, mock_db):
    """
    Test retrieving filtered payments for admin view.
    """
    filters = MagicMock()
    filters.filter.side_effect = lambda stmt: stmt
    filters.sort.side_effect = lambda stmt: stmt

    payments = [PaymentDB(id=1)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = payments
    mock_db.execute.return_value = mock_result

    result = await payment_crud.get_all_payments_filtered(mock_db, filters)

    assert result == payments
    filters.filter.assert_called_once()
    filters.sort.assert_called_once()


@pytest.mark.asyncio
async def test_get_payment_details(payment_crud, mock_db):
    """
    Test retrieving full payment details with deep relationships.
    """
    payment = PaymentDB(id=1)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = payment
    mock_db.execute.return_value = mock_result

    result = await payment_crud.get_payment_details(mock_db, payment_id=1)

    assert result == payment
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_refund_requested(payment_crud, mock_db):
    """
    Test marking a payment as refund requested updates status and reloads.
    """
    payment = PaymentDB(id=1, status=PaymentStatusEnum.SUCCESSFUL)
    mock_result_reload = MagicMock()
    mock_result_reload.scalar_one.return_value = payment
    mock_db.execute.return_value = mock_result_reload

    await payment_crud.mark_refund_requested(mock_db, payment)

    assert payment.status == PaymentStatusEnum.REFUND_REQUESTED
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_refund_requested_error(payment_crud, mock_db):
    """
    Test error handling during refund request triggers rollback.
    """
    payment = PaymentDB(id=1)
    mock_db.commit.side_effect = SQLAlchemyError("DB Error")

    with pytest.raises(SQLAlchemyError):
        await payment_crud.mark_refund_requested(mock_db, payment)

    mock_db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_id_found(payment_crud, mock_db):
    """
    Test retrieving a payment by ID when it exists.
    """
    payment = PaymentDB(id=1)
    mock_db.get.return_value = payment

    result = await payment_crud.get_by_id(mock_db, 1)

    assert result == payment
    mock_db.get.assert_awaited_once_with(PaymentDB, 1)


@pytest.mark.asyncio
async def test_get_by_id_not_found(payment_crud, mock_db):
    """
    Test retrieving a payment by ID when it does not exist.
    """
    mock_db.get.return_value = None

    result = await payment_crud.get_by_id(mock_db, 999)

    assert result is None
