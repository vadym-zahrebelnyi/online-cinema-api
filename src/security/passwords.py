from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=14, deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using the configured cryptographic scheme.

    Args:
        password (str): The plain text password provided by the user.

    Returns:
        str: The hashed string suitable for database storage.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored hash.

    Args:
        plain_password (str): The password provided during login.
        hashed_password (str): The hash stored in the database.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)
