class OrderNotFoundError(Exception):
    pass


class OrderCreateError(Exception):
    pass


class OrderUpdateError(Exception):
    pass


class OrderDeleteError(Exception):
    pass


class MovieNotAvailableError(Exception):
    pass


class CartIsEmptyError(Exception):
    pass


class OrderAlreadyPendingError(Exception):
    pass
