import secrets


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token.

    Args:
        length: Length of the token (default: 32)

    Returns:
        str: Securely generated token.
    """
    return secrets.token_urlsafe(length)
