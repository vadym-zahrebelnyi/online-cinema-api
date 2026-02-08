class CartException(Exception):
    pass


class MovieNotFoundException(CartException):
    pass


class MovieAlreadyInCartException(CartException):
    pass


class MovieNotInCartException(CartException):
    pass


class MovieAlreadyPurchasedException(CartException):
    pass
