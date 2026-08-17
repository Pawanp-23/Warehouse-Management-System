class InsufficientStockError(Exception):
    def __init__(self, available_quantity: int, requested_quantity: int):
        self.available_quantity = available_quantity
        self.requested_quantity = requested_quantity
        super().__init__("Insufficient stock")


class DuplicateCommandError(Exception):
    pass
