"""
Module: orders.exceptions

This module defines custom exceptions related to order processing in the
online cinema system. These exceptions can be raised to indicate specific
error conditions when working with orders, order items, and the shopping cart.

Exceptions:
    - OrderNotFoundError: Raised when an order is not found in the database.
    - OrderCreateError: Raised when there is an error creating a new order.
    - OrderUpdateError: Raised when updating an order fails.
    - OrderDeleteError: Raised when deleting an order fails.
    - MovieNotAvailableError: Raised when a movie is not available for purchase.
    - CartIsEmptyError: Raised when an operation requires items in the cart but it is empty.
    - OrderAlreadyPendingError: Raised when attempting to create a new order while there is already a pending one.
"""

class OrderNotFoundError(Exception):
    """Raised when an order is not found in the database."""
    pass


class OrderCreateError(Exception):
    """Raised when there is an error creating a new order."""
    pass


class OrderUpdateError(Exception):
    """Raised when updating an order fails."""
    pass


class OrderDeleteError(Exception):
    """Raised when deleting an order fails."""
    pass


class MovieNotAvailableError(Exception):
    """Raised when a movie is not available for purchase."""
    pass


class CartIsEmptyError(Exception):
    """Raised when an operation requires items in the cart but it is empty."""
    pass


class OrderAlreadyPendingError(Exception):
    """Raised when attempting to create a new order while there is already a pending one."""
    pass
