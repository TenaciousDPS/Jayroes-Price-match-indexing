import pathlib
import dataclasses
import enum
import collections

JAYROES_MEMBER_NUM = "06969"
CHANGE_RECORD_CODE = "PC1"

@dataclasses.dataclass
class Field[T]:
    position: tuple[int, int] | int
    typ: T | None = None
    description: str | None = None

class FileHeaderField(enum.Enum):
    record_type = Field((1,3), description="Should be H01, indicating file header.")
    file_type = Field((4, 10), description="Should be PRCCHGS, a price change file.")
    member_number = Field((11, 16), description="First 5 bytes numeric, right justified, zero filled. Suffix alpha char or space.")
    date = Field((17, 24), description="YYYYMMDD")
    time = Field((25, 30), description="HHMMSS")
    version_no = Field((31, 34), description="Identifies version number. Should be 01.1")
    filler = Field((35, 80), description="Spaces")

# TODO: type conversions
class RecordField(enum.Enum):
    record_code = Field((1,3), "Should be PC1, indicating price change record.")
    member_num = Field((4,9), "Format 99999X. Zero padded, suffix alpha character or space.")
    sku = Field((10,15), description="Do it Best Corp. SKU")
    product_code = Field((16,29), "Right justified, zero filled. If unavailable, spaces. 8 digit EAN, 12 digit UPC, 13 digit EAN, or 14 digit SCC.")
    item_price_change = Field((30,37), "New member cost for this item. This will be the highest cost for the item.")
    unit_of_measure = Field((38,39), "Alpha Unit of Mesage for which this price applies.")
    item_type = Field(40, "I = IMCS, G = Generic. Indicates whether generic or personalied according to member's IMCS file.")
    price_status_code = Field(41, "N = Price change is due to a permanent increase, P = Promotional pricing for upcoming sale (see Suggested Retail Field), I = IMCS maintenance update pricing record. V = Lower cost high margin (retail price unchanged)")
    effective_date = Field((42,49), "YYYYMMDD. Date the Price Change becomes effective. If Price Status Code is not P, this field contains the date Price Change was effective.")
    promo_status_code = Field(50, "Code that states whether this item is on a promotion or not. Space = no, 6 = yes.")
    reorder_start_date = Field((51,58), "YYYYMMDD. Reoder start date of the promotion as specified by the member. Date the member can start ordering the items at sale cost. 0 if not promotion.")
    reorder_end_date = Field((59,66), "YYYYMMDD. The end date of the sale/promotion as specified by the member. The actual date the members no longer get the sale cost.")
    sale_start_date = Field((67,74), "YYYYMMDD. Date the promotion becomes effective at the pont-of-sale as agreed upon by Do it Best Corp and the member.")
    sale_code = Field((75,76), "XX (two chars). Do it Best Corp sale code.")
    sale_end_date = Field((77,84), "YYMMDD. Date the promotion will terminate at the pont-of-sale as agreed upon between Do it Best Corp and the member.")
    member_cost_option = Field(85, "C = Classic option, V = Vision option. Whether to use Classic costing or Vision costing.")
    mult_3 = Field((86,90), "9(5). Smallest order Mult, usually each. If this field is zero, then not sold in this multiple.")
    cost_3 = Field((91,98), "9(5)V999. The Mult 3 member cost. Zero is valid for some items.")
    mult_2 = Field((99,103), "9(5). Second largest order Mult. Usually the inner pack. If zero, then not sold in this multiple.")
    cost_2 = Field((104,111), "9(5)V999. The mult 2 member cost. Zero is valid for some items.")
    mult_1 = Field((112,116), "9(5). Largest order Mult, usually the case or pallet quantity. If zero, then not sold in this multiple.")
    cost_1 = Field((117,124), "9(5)V999. The Mult 1 member cost. Zero is valid for some items.")
    member_retail = Field((125,131), "9(5)V99. Member retail = a retail or margin code exists in the IMCS file. Member Selling Unit Retail = the IMCS Aux. Retail Switch = 'Y'. 0000000 = Member is not on IMCS or there is not IMCS retail.")
    gross_margin = Field((132,136), "+99.9 or -99.9. Negative margins are valid.")
    suggested_retail = Field((137,143), "9(5)V99. Do it Best suggested retail, based on the purchasing unit. If 'Price Status Code' contains 'P', this field will contain the Suggested Promotional Retail")
    suggested_aux_retail = Field((144,150), "9(5)V99. Auxiliary retail (AKA selling retail). If Suggested Aux Retail is zeros, then see 'Suggested Retail' for the consumer retail for this member.")
    suggested_margin = Field((151,154), "S99V9")
    private1 = Field((155,161), "Do it Best Corp use only")
    private2 = Field((162,165), "Do it Best Corp use only")
    mbr_aux_retail_switch = Field(166, "N = No, retail is based on purchasing unit. Y = Yes, retail is aux retail or selling unit retail. If member is on IMCS, then this switch identifies the underlying unit of measure for the Member Specified Retail field.")
    aux_unit = Field((167,168), "Two char descriptive alpha code which indicates the selling unit of measure. Normally use on price tickets and/or bin tags. On POS systems, usually called Stocking or selling unit of measure. If Aux Unit is spaces, default selling unit to the purchasing unit, which is in the Unit field.")
    aux_quantity = Field((169,173), "9(5). Auxiliary quantity (AKA selling quantity). The selling unit quantity that it takes to make one purchasing unit in the smallest multiple available. If aux quantity is zeros, then the consumer selling quantity is based upon the purchasing unit.")
    status_code = Field(174, description="N = normal, 1 = Item to be discontinued in near future, 2 = Probably out of stock (usually seasonal items), 3 = Discontinued, 9 = New Item")
    personal_sku = Field((175,183), description="Member's personal SKU number, if used, that corresponds to DoB's SKU. If unused, contains spaces.")
    filler = Field((184,200), description='Spaces, ignore.')


PriceChangeRecord = collections.namedtuple("PriceChangeRecord", [*(field.name for field in RecordField), 'line_number'])
# SKU, MEMBER_NUM <-- just to test
# PRODUCT_CODE == UPC (jayroe's is always 12 digit version)
#     - UPC and SKU (not everything has) match would be nice
# ITEM_PRICE_CHANGE <-- new cost field
# jayroes uses the smallest option (mult 3, cost 3)
# 
# pos -- "suggested retail = price"
# cost -- "jayroe's cost" item_price_change


class FileTrailerField(enum.Enum):
    record_type = Field((1, 3), "Should be T01. Trailer.")
    file_type = Field((4,10), "Should be PRCCHGS. Indicates price change")
    member_number = Field((11,16), "Member numer, same as H01 record.")
    date = Field((17,24), "YYYYMMDD")
    time = Field((25,30), "HHMMSS")
    total_records = Field((31,37), "Total record count including all levels. This includes all of the r ecords on the transmission for this specified batch. The field is left filled with zeroes.")
    filler = Field((38,80), "Spaces, ignore.")

def read_file(filepath: pathlib.Path):
    def read_field(row: str, field: Field):
        match field.position:
            case int(), int():
                return row[(field.position[0] - 1):(field.position[1])]
            case int():
                return row[field.position - 1]
            case _:
                raise ValueError(f"{field} contains invalid position {field.position}")

    def read_row(row: str, line_no: int):
        return PriceChangeRecord(**{k.name: read_field(row, k.value) for k in RecordField}, line_number=line_no)

    with filepath.open(mode='r') as file:
        for line_no, line in enumerate(file.readlines()):
            if not line.startswith(CHANGE_RECORD_CODE + JAYROES_MEMBER_NUM):
                continue
            yield read_row(line, line_no)

