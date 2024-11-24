import dataclasses
import logging
import pathlib
import functools

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)

# A29 = 1,29
TABLE_START = 1, 29


def int_to_excel_column(n: int) -> str:
    """
    Converts an integer to an Excel column string (e.g., 1 -> A, 27 -> AA).
    """
    if n < 1:
        raise ValueError("Input must be a positive integer.")
    n -= 1
    if n < 26:
        return chr(n + ord("A"))
    return int_to_excel_column(n // 26) + chr(n % 26 + ord("A"))

# some stupid optimization
@functools.cache
def dataclass_field_indexes(klass):
    return {
        field.name: i
        for i, field in enumerate(dataclasses.fields(klass))
    }

@dataclasses.dataclass
class Product:
    product_class: str
    category: str
    subcategory: str
    name: str
    description: str | None
    price: int  # in cents
    cost: int  # in cents
    sku: str | None
    barcode: str | None
    active: bool

    def __post_init__(self):
        if not (self.sku or self.barcode):
            raise ValueError("Either sku or barcode must be set.")

    @staticmethod
    def from_row(row: tuple):
        record = {
            fieldname: row[index]
            for fieldname, index in dataclass_field_indexes(Product).items()
        }
        record["active"] = record["active"] == "Yes"
        record["cost"] = int(record["cost"] * 100) if record["cost"] else None
        record["price"] = int(record["price"] * 100)
        return Product(**record)


def read_file(filepath: pathlib.Path):
    workbook = openpyxl.load_workbook(filepath, read_only=True, data_only=False)
    worksheet: Worksheet = workbook.active  # type: ignore stupid library is stupid
    if not worksheet:
        raise ValueError("Could not find currently active sheet")

    cols = TABLE_START[0], TABLE_START[0] + len(dataclasses.fields(Product))
    row_num = TABLE_START[1]
    cost_index = dataclass_field_indexes(Product)["cost"]

    for row in worksheet.iter_rows(
        min_row=row_num,
        min_col=cols[0],
        max_col=cols[1],
        values_only=True,
    ):
        if not any(v is None for v in row):
            return
        yield Product.from_row(row)
        row_num += 1
