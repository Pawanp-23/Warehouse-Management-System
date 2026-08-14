from enum import StrEnum


class StockStatus(StrEnum):
    RECEIVING = "RECEIVING"
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    DAMAGED = "DAMAGED"


class ReceiptStatus(StrEnum):
    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"


class OrderStatus(StrEnum):
    NEW = "NEW"
    RESERVED = "RESERVED"
    EXCEPTION = "EXCEPTION"
