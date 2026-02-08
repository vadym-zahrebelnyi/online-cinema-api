class CartException(Exception):
    """Base cart exception"""

    pass


class MovieAlreadyInCartError(CartException):
    def __init__(self):
        super().__init__("Movie is already in the cart")


class MovieAlreadyOwnedError(CartException):
    def __init__(self):
        super().__init__("You have already purchased this movie")


class CartItemNotFoundError(CartException):
    def __init__(self):
        super().__init__("Item not found in cart")


class MovieNotFoundError(CartException):
    def __init__(self):
        super().__init__("Movie not found")
