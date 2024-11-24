import pathlib
import dataclasses
import logging
from typing import Iterable

import json


from .point_of_sale import read_file as read_pos_file, Product
from .supplier import read_file as read_supplier_file, PriceChangeRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Args:
    pricechange_file: pathlib.Path
    inventory_file: pathlib.Path
    outdir: pathlib.Path

    @staticmethod
    def from_cli():
        def _valid_path(filepath_str: str, isfile: bool):
            try:
                fp = pathlib.Path(filepath_str)
            except Exception as e:
                raise argparse.ArgumentTypeError(
                    f"{filepath_str} is not a filepath."
                ) from e
            if not fp.exists():
                raise argparse.ArgumentTypeError(f"{filepath_str} does not exist.")
            if isfile and not fp.is_file():
                raise argparse.ArgumentTypeError(f"{filepath_str} is not a file.")
            if not isfile and not fp.is_dir():
                raise argparse.ArgumentTypeError(f"{filepath_str} is not a dir.")
            return fp

        def valid_filepath(path: str):
            return _valid_path(path, isfile=True)

        def valid_dirpath(path: str):
            return _valid_path(path, isfile=False)

        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--pricechange",
            "-p",
            help="Path to price change file",
            required=True,
            type=valid_filepath,
        )
        parser.add_argument(
            "--inventory",
            "-i",
            help="Path to inventory file",
            required=True,
            type=valid_filepath,
        )
        parser.add_argument(
            "--outdir",
            "-o",
            help="Path to verbose output folder",
            type=valid_dirpath,
            required=True,
        )
        args = parser.parse_args()
        return Args(
            pricechange_file=args.pricechange,
            inventory_file=args.inventory,
            outdir=args.outdir,
        )


def main(args: Args):
    logger.info(f"Price change file: {str(args.pricechange_file)}")
    logger.info(f"Revel inventory file: {str(args.inventory_file)}")

    pos_records = [r for r in read_pos_file(args.inventory_file)]
    logger.info("Processed Revel file...")

    change_records = [r for r in read_supplier_file(args.pricechange_file)]
    logger.info(f"Processed price change file: {str(args.inventory_file)}")

    matching_records = [f for f in match_records(change_records, pos_records)]

    write_report(args.outdir / "verbose_report.json", matching_records, verbose=True)
    logging.info(f"Created verbose report @ {str(args.outdir / 'verbose_report.json')}")

    write_report(args.outdir / "minimal_report.json", matching_records, verbose=False)
    logging.info(f"Created minimal report @ {str(args.outdir / 'minimal_report.json')}")

    missing_suggested_retail = args.outdir / "no_suggested_retail.json"
    if missing_retail := [
        m for m in matching_records if not m.pricechange_record.suggested_retail
    ]:
        logger.error(
            f"The following UPCs had no suggested retail: {[m.upc for m in missing_retail]} "
        )
        logger.error(f"See {str(missing_suggested_retail)} for specifics.")
        write_report(
            missing_suggested_retail,
            [m for m in matching_records if not m.pricechange_record.suggested_retail],
            verbose=True,
        )
        import sys

        sys.exit(1)
    else:
        missing_suggested_retail.unlink(missing_ok=True)
        logging.info("No records were missing suggested retail.")


@dataclasses.dataclass
class MatchRecord:
    pricechange_record: PriceChangeRecord
    revel_record: Product
    sku_matches: bool

    @property
    def sku(self):
        return self.revel_record.sku

    @property
    def upc(self):
        if not self.revel_record.barcode:
            return None
        return self.revel_record.barcode.lstrip("0")

    def verbose_price_info(self):
        return {
            "revel_price": {
                "cost": self.revel_record.cost,
                "price": self.revel_record.price,
            },
            "change_details": {
                "3": {
                    "mult_3": self.pricechange_record.mult_3,
                    "cost_3": self.pricechange_record.cost_3,
                },
                "2": {
                    "mult_2": self.pricechange_record.mult_3,
                    "cost_3": self.pricechange_record.cost_3,
                },
                "1": {
                    "mult_1": self.pricechange_record.mult_3,
                    "cost_1": self.pricechange_record.cost_3,
                },
                "member_retail": self.pricechange_record.member_retail,
                "suggested_retail": self.pricechange_record.suggested_retail,
                "suggested_aux_retail": self.pricechange_record.suggested_aux_retail,
                "suggested_margin": self.pricechange_record.suggested_margin,
                "aux_unit": self.pricechange_record.aux_unit,
                "aux_quantity": self.pricechange_record.aux_quantity,
                "price_status_code": self.pricechange_record.price_status_code,
                "promo_status_code": self.pricechange_record.promo_status_code,
                "item_price_change": self.pricechange_record.item_price_change,
                "unit_of_measure": self.pricechange_record.unit_of_measure,
            },
        }

    def minimal_price_info(self):
        result = {
            "revel_price": {
                "cost": self.revel_record.cost,
                "price": self.revel_record.price,
            },
            "change_details": {
                "suggested_retail": (
                    self.pricechange_record.suggested_retail.strip("0")
                    if self.pricechange_record.suggested_retail
                    else None
                ),
                "item_price_change": (
                    self.pricechange_record.item_price_change.strip("0")
                    if self.pricechange_record.item_price_change
                    else None
                ),
                "unit_of_measure": self.pricechange_record.unit_of_measure,
            },
        }
        if self.pricechange_record.suggested_aux_retail:
            result["change_details"]["suggested_aux_retail"] = (
                self.pricechange_record.suggested_aux_retail.strip("0")
                if self.pricechange_record.suggested_aux_retail
                else None
            )
        if (aux_unit := self.pricechange_record.aux_unit) and aux_unit.strip():
            result["change_details"]["aux_unit"] = self.pricechange_record.aux_unit
            result["change_details"]["aux_quantity"] = (
                self.pricechange_record.aux_quantity.strip("0")
                if self.pricechange_record.aux_quantity
                else None
            )
        return result

    @staticmethod
    def format(record: "MatchRecord", verbose: bool):
        result = {
            "upc": record.upc,
            "sku": record.sku,
            "sku_matches": record.sku_matches,
        }
        if verbose:
            return {**result, **record.verbose_price_info()}
        else:
            return {**result, **record.minimal_price_info()}


def match_records(change_records: list[PriceChangeRecord], pos_records: list[Product]):
    for cr in change_records:
        if not cr.product_code:
            continue
        if pr := next(
            (
                r
                for r in pos_records
                if r.barcode
                and str(r.barcode).lstrip("0") == str(cr.product_code).lstrip("0")
            ),
            None,
        ):
            yield MatchRecord(
                pricechange_record=cr,
                revel_record=pr,
                sku_matches=bool(
                    cr.sku and pr.sku and (cr.sku.lstrip("0") == pr.sku.lstrip("0"))
                ),
            )


def write_report(filepath: pathlib.Path, matches: Iterable[MatchRecord], verbose: bool):
    with open(filepath, "w") as f:
        json.dump([MatchRecord.format(m, verbose) for m in matches], f, indent=4)


if __name__ == "__main__":
    args = Args.from_cli()
    main(args)
