class PaymentError(Exception):
    """Base class for payment exceptions."""

    pass


class PaymentValidationError(PaymentError):
    """Invalid data sent to provider (e.g. negative amount)."""

    pass


class PaymentConfigurationError(PaymentError):
    """Server-side configuration issues (API keys, etc)."""

    pass


class PaymentConnectionError(PaymentError):
    """Network issues or provider downtime."""

    pass


class PaymentWebhookError(PaymentError):
    """Invalid signature or payload in webhook."""

    pass
