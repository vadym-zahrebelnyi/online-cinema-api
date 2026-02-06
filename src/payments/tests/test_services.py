from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from stripe import (
    APIConnectionError,
    AuthenticationError,
    InvalidRequestError,
    RateLimitError,
    SignatureVerificationError,
)

from src.payments.exceptions import (
    PaymentConfigurationError,
    PaymentConnectionError,
    PaymentValidationError,
    PaymentWebhookError,
)
from src.payments.schemas import PaymentGatewayCreateSchema
from src.payments.services import StripeGateway


@pytest.fixture
def payment_data():
    return PaymentGatewayCreateSchema(
        order_id=123,
        user_id=456,
        amount=Decimal("10.50"),
        currency="usd",
        email="test@example.com",
    )


@pytest.fixture
def gateway():
    return StripeGateway()


@pytest.mark.asyncio
async def test_create_checkout_session_success(gateway, payment_data):
    mock_session = MagicMock()
    mock_session.url = "https://stripe.com/pay/123"
    mock_session.id = "cs_test_123"

    with patch(
        "stripe.checkout.Session.create_async", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_session

        result = await gateway.create_checkout_session(payment_data)

        assert result.url == "https://stripe.com/pay/123"
        assert result.session_id == "cs_test_123"

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["line_items"][0]["price_data"]["unit_amount"] == 1050


@pytest.mark.asyncio
async def test_create_session_invalid_request_error(gateway, payment_data):
    """Test handling of 400 Bad Request from Stripe"""
    with patch(
        "stripe.checkout.Session.create_async", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = InvalidRequestError(
            "Invalid currency", param="currency"
        )

        with pytest.raises(PaymentValidationError) as exc:
            await gateway.create_checkout_session(payment_data)

        assert "Invalid currency" in str(exc.value)


@pytest.mark.asyncio
async def test_create_session_auth_error(gateway, payment_data):
    """Test handling of invalid API key"""
    with patch(
        "stripe.checkout.Session.create_async", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = AuthenticationError("Invalid API Key")

        with pytest.raises(PaymentConfigurationError):
            await gateway.create_checkout_session(payment_data)


@pytest.mark.asyncio
async def test_create_session_rate_limit_error(gateway, payment_data):
    """Test handling of Too Many Requests"""
    with patch(
        "stripe.checkout.Session.create_async", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = RateLimitError("Too many requests")

        with pytest.raises(PaymentConnectionError) as exc:
            await gateway.create_checkout_session(payment_data)

        assert "busy" in str(exc.value)


@pytest.mark.asyncio
async def test_create_session_connection_error(gateway, payment_data):
    """Test handling of network downtime"""
    with patch(
        "stripe.checkout.Session.create_async", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = APIConnectionError("Connection timeout")

        with pytest.raises(PaymentConnectionError):
            await gateway.create_checkout_session(payment_data)


@pytest.mark.asyncio
async def test_validate_webhook_success(gateway):
    payload = b'{"id": "evt_123"}'
    signature = "valid_signature"

    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {"type": "checkout.session.completed"}

        event = await gateway.validate_webhook(payload, signature)

        assert event["type"] == "checkout.session.completed"
        mock_construct.assert_called_once()


@pytest.mark.asyncio
async def test_validate_webhook_invalid_signature(gateway):
    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.side_effect = SignatureVerificationError(
            "Bad sig", sig_header="x"
        )

        with pytest.raises(PaymentWebhookError) as exc:
            await gateway.validate_webhook(b"payload", "bad_sig")

        assert "Invalid webhook signature" in str(exc.value)


@pytest.mark.asyncio
async def test_validate_webhook_invalid_payload(gateway):
    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.side_effect = ValueError("Bad JSON")

        with pytest.raises(PaymentWebhookError) as exc:
            await gateway.validate_webhook(b"bad_json", "sig")

        assert "Invalid payload" in str(exc.value)
