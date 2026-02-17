from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.accounts.models import UserDB
from src.orders.models import OrderDB, OrderStatusEnum
from src.payments.models import PaymentDB, PaymentStatusEnum
from src.payments.schemas import PaymentGatewayResponseSchema
from src.payments.services import PaymentService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_gateway():
    gateway = AsyncMock()
    gateway.create_checkout_session.return_value = PaymentGatewayResponseSchema(
        session_id="sess_123", url="http://checkout.url"
    )
    return gateway


@pytest.fixture
def payment_service(mock_db, mock_gateway):
    return PaymentService(mock_db, mock_gateway)


@pytest.mark.asyncio
async def test_create_checkout_session_success(payment_service, mock_db, mock_gateway):
    """
    Test successful creation of a checkout session.
    Verifies that the order is validated, payment is created in DB,
    and gateway session data is returned.
    """
    user = UserDB(id=1, email="user@test.com")
    order = OrderDB(id=10, user_id=1, status=OrderStatusEnum.PENDING)
    payment = PaymentDB(id=100, amount=Decimal("50.00"))

    with (
        patch(
            "src.payments.services.order_crud.get_order_with_items"
        ) as mock_get_order,
        patch(
            "src.payments.services.payment_crud.create_payment"
        ) as mock_create_payment,
        patch("src.payments.services.payment_crud.set_external_id") as mock_set_ext_id,
    ):
        mock_get_order.return_value = order
        mock_create_payment.return_value = payment

        result = await payment_service.create_checkout_session(user, 10)

        assert result.session_id == "sess_123"
        assert str(result.url) == "http://checkout.url/"

        mock_create_payment.assert_awaited_once_with(
            mock_db, order=order, user_id=user.id
        )
        mock_gateway.create_checkout_session.assert_awaited_once()
        mock_set_ext_id.assert_awaited_once_with(mock_db, 100, "sess_123")


@pytest.mark.asyncio
async def test_create_checkout_session_order_not_found(payment_service):
    """
    Test checkout session creation fails if the order does not exist.
    """
    user = UserDB(id=1)

    with patch(
        "src.payments.services.order_crud.get_order_with_items"
    ) as mock_get_order:
        mock_get_order.return_value = None

        with pytest.raises(ValueError, match="Order not found"):
            await payment_service.create_checkout_session(user, 999)


@pytest.mark.asyncio
async def test_create_checkout_session_permission_error(payment_service):
    """
    Test checkout session creation fails if the user does not own the order.
    """
    user = UserDB(id=1)
    order = OrderDB(id=10, user_id=2, status=OrderStatusEnum.PENDING)

    with patch(
        "src.payments.services.order_crud.get_order_with_items"
    ) as mock_get_order:
        mock_get_order.return_value = order

        with pytest.raises(PermissionError, match="Not authorized"):
            await payment_service.create_checkout_session(user, 10)


@pytest.mark.asyncio
async def test_create_checkout_session_already_paid(payment_service):
    """
    Test checkout session creation fails if the order is already paid.
    """
    user = UserDB(id=1)
    order = OrderDB(id=10, user_id=1, status=OrderStatusEnum.PAID)

    with patch(
        "src.payments.services.order_crud.get_order_with_items"
    ) as mock_get_order:
        mock_get_order.return_value = order

        with pytest.raises(ValueError, match="Order is already paid"):
            await payment_service.create_checkout_session(user, 10)


@pytest.mark.asyncio
async def test_process_webhook_checkout_completed(
    payment_service, mock_gateway, mock_db
):
    """
    Test processing of 'checkout.session.completed' webhook event.
    Verifies that the payment is confirmed and a confirmation email is sent.
    """
    event_payload = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "sess_123", "payment_intent": "pi_999"}},
    }
    mock_gateway.validate_webhook.return_value = event_payload

    user = UserDB(id=1, email="test@test.com")
    payment = PaymentDB(
        id=100,
        status=PaymentStatusEnum.PENDING,
        user=user,
        amount=Decimal("100.00"),
        order_id=50,
    )

    with (
        patch(
            "src.payments.services.payment_crud.get_by_session_id"
        ) as mock_get_payment,
        patch("src.payments.services.payment_crud.set_external_id") as mock_set_ext,
        patch("src.payments.services.payment_crud.confirm_payment") as mock_confirm,
        patch(
            "src.payments.services.send_payment_confirmation_email_task.delay"
        ) as mock_email_task,
    ):
        mock_get_payment.return_value = payment
        mock_confirm.return_value = payment

        result = await payment_service.process_webhook(b"payload", "sig")

        assert result == {"status": "ok"}

        mock_set_ext.assert_awaited_once_with(mock_db, 100, "pi_999")
        mock_confirm.assert_awaited_once_with(mock_db, payment)
        mock_email_task.assert_called_once_with(
            email="test@test.com", amount="100.00", order_id=50
        )


@pytest.mark.asyncio
async def test_process_webhook_refunded(payment_service, mock_gateway, mock_db):
    """
    Test processing of 'charge.refunded' webhook event.
    Verifies that the payment is refunded locally.
    """
    event_payload = {
        "type": "charge.refunded",
        "data": {"object": {"payment_intent": "pi_999"}},
    }
    mock_gateway.validate_webhook.return_value = event_payload
    payment = PaymentDB(id=100)

    with (
        patch(
            "src.payments.services.payment_crud.get_by_session_id"
        ) as mock_get_payment,
        patch("src.payments.services.payment_crud.refund_payment") as mock_refund,
    ):
        mock_get_payment.return_value = payment

        await payment_service.process_webhook(b"payload", "sig")

        mock_refund.assert_awaited_once_with(mock_db, payment)


@pytest.mark.asyncio
async def test_cancel_payment_success(payment_service, mock_db):
    """
    Test successful cancellation of a pending payment by the user.
    """
    user = UserDB(id=1)
    payment = PaymentDB(id=100, user_id=1, status=PaymentStatusEnum.PENDING)

    with (
        patch("src.payments.services.payment_crud.get_by_id") as mock_get,
        patch("src.payments.services.payment_crud.cancel_payment") as mock_cancel,
    ):
        mock_get.return_value = payment
        mock_cancel.return_value = payment

        await payment_service.cancel_payment(user, 100)

        mock_cancel.assert_awaited_once_with(mock_db, payment)


@pytest.mark.asyncio
async def test_cancel_payment_invalid_status(payment_service):
    """
    Test cancellation fails if the payment is not in PENDING state.
    """
    user = UserDB(id=1)
    payment = PaymentDB(id=100, user_id=1, status=PaymentStatusEnum.SUCCESSFUL)

    with patch("src.payments.services.payment_crud.get_by_id") as mock_get:
        mock_get.return_value = payment

        with pytest.raises(ValueError, match="Cannot cancel processed payment"):
            await payment_service.cancel_payment(user, 100)


@pytest.mark.asyncio
async def test_request_refund_success(payment_service, mock_db):
    """
    Test successful refund request by the user.
    """
    user = UserDB(id=1)
    payment = PaymentDB(id=100, user_id=1, status=PaymentStatusEnum.SUCCESSFUL)

    with (
        patch("src.payments.services.payment_crud.get_by_id") as mock_get,
        patch("src.payments.services.payment_crud.mark_refund_requested") as mock_mark,
    ):
        mock_get.return_value = payment

        await payment_service.request_refund(user, 100)

        mock_mark.assert_awaited_once_with(mock_db, payment)


@pytest.mark.asyncio
async def test_request_refund_not_allowed(payment_service):
    """
    Test refund request fails if payment was not successful.
    """
    user = UserDB(id=1)
    payment = PaymentDB(id=100, user_id=1, status=PaymentStatusEnum.PENDING)

    with patch("src.payments.services.payment_crud.get_by_id") as mock_get:
        mock_get.return_value = payment

        with pytest.raises(ValueError, match="Can only request refund for successful"):
            await payment_service.request_refund(user, 100)


@pytest.mark.asyncio
async def test_approve_refund_success(payment_service, mock_db, mock_gateway):
    """
    Test admin approval of a refund.
    Verifies interaction with the gateway and database update.
    """
    admin = UserDB(id=99)
    payment = PaymentDB(
        id=100, status=PaymentStatusEnum.REFUND_REQUESTED, external_payment_id="pi_123"
    )

    with (
        patch("src.payments.services.payment_crud.get_by_id") as mock_get,
        patch("src.payments.services.payment_crud.refund_payment") as mock_refund_db,
    ):
        mock_get.return_value = payment

        await payment_service.approve_refund(admin, 100)

        mock_gateway.refund_payment.assert_awaited_once_with("pi_123")
        mock_refund_db.assert_awaited_once_with(mock_db, payment)


@pytest.mark.asyncio
async def test_approve_refund_missing_external_id(payment_service):
    """
    Test approval fails if the payment lacks an external gateway ID.
    """
    admin = UserDB(id=99)
    payment = PaymentDB(
        id=100, status=PaymentStatusEnum.SUCCESSFUL, external_payment_id=None
    )

    with patch("src.payments.services.payment_crud.get_by_id") as mock_get:
        mock_get.return_value = payment

        with pytest.raises(ValueError, match="Missing external Stripe ID"):
            await payment_service.approve_refund(admin, 100)


@pytest.mark.asyncio
async def test_approve_refund_gateway_error(payment_service, mock_gateway):
    """
    Test that gateway errors during refund are propagated.
    """
    admin = UserDB(id=99)
    payment = PaymentDB(
        id=100, status=PaymentStatusEnum.SUCCESSFUL, external_payment_id="pi_123"
    )

    mock_gateway.refund_payment.side_effect = Exception("Stripe Error")

    with patch("src.payments.services.payment_crud.get_by_id") as mock_get:
        mock_get.return_value = payment

        with pytest.raises(Exception, match="Stripe Error"):
            await payment_service.approve_refund(admin, 100)
