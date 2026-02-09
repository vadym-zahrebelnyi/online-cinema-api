import re

import email_validator


def validate_password_strength(password: str) -> str:
    """
        Validates that a password meets the minimum security requirements.

        Checks:
        - Minimum length of 8 characters.
        - Presence of at least one uppercase letter (A-Z).
        - Presence of at least one lowercase letter (a-z).
        - Presence of at least one digit (0-9).
        - Presence of at least one special character (@$!%*?&#).

        :param password: The raw password string to validate.
        :return: The validated password string.
        :raises ValueError: If any of the security requirements are not met.
    """
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lower letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r"[@$!%*?&#]", password):
        raise ValueError(
            "Password must contain at least one special character: @, $, !, %, *, ?, #, &."
        )
    return password


def validate_email(user_email: str) -> str:
    """
        Validates and normalizes an email address.

        Uses the email-validator library to ensure the format is correct.
        Deliverability check is disabled for performance.

        :param user_email: The raw email string.
        :return: The normalized email string (e.g., lowercase).
        :raises ValueError: If the email format is invalid.
    """
    try:
        email_info = email_validator.validate_email(
            user_email, check_deliverability=False
        )
        email = email_info.normalized
    except email_validator.EmailNotValidError as error:
        raise ValueError(str(error))
    else:
        return email
