class CartException(Exception):
    """
    Base exception for all cart-related errors.
    """

    pass


class MovieAlreadyInCartError(CartException):
    """
    Raised when attempting to add a movie that is already in the cart.
    """

    def __init__(self):
        super().__init__("Movie is already in the cart")


class MovieAlreadyOwnedError(CartException):
    """
    Raised when a user tries to add a movie they have already purchased.
    """

    def __init__(self):
        super().__init__("You have already purchased this movie")


class CartItemNotFoundError(CartException):
    """
    Raised when attempting to operate on a cart item that does not exist.
    """

    def __init__(self):
        super().__init__("Item not found in cart")


class MovieNotFoundError(CartException):
    """
    Raised when the requested movie ID does not exist in the database.
    """

    def __init__(self):
        super().__init__("Movie not found")
