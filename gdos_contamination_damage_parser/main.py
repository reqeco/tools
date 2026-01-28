import argparse
import sys
from pathlib import Path

from common import save_records
from parse_contamination_xls import parse_xls
from parse_damage_xls import parse_damage_xls

DATASETS = {
    "contamination": {
        "parser": parse_xls,
        "raw_dir": Path("data/raw/contamination"),
        "json_dir": Path("data/json/contamination"),
        "glob": "*.xls",
    },
    "damage": {
        "parser": parse_damage_xls,
        "raw_dir": Path("data/raw/damage"),
        "json_dir": Path("data/json/damage"),
        "glob": "*.xls",
    },
}


def parse_files(dataset: str, files: list[Path]):
    ds = DATASETS[dataset]
    all_records = []

    for f in sorted(files):
        records = ds["parser"](str(f))
        print(f"  {f.name}: {len(records)} rekordów")
        all_records.extend(records)

    save_records(all_records, ds["json_dir"])
    print(f"\nZapisano {len(all_records)} plików JSON do {ds['json_dir']}/")


def main():
    parser = argparse.ArgumentParser(description="Parser rejestrów GDOŚ")
    parser.add_argument(
        "dataset",
        choices=list(DATASETS.keys()),
        help="zbiór danych do parsowania",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="pliki XLS do parsowania (domyślnie: wszystkie z data/raw/<dataset>/)",
    )
    args = parser.parse_args()

    ds = DATASETS[args.dataset]

    if args.files:
        files = [Path(f) for f in args.files]
        for f in files:
            if not f.exists():
                print(f"Plik nie istnieje: {f}")
                sys.exit(1)
    else:
        files = list(ds["raw_dir"].glob(ds["glob"]))
        if not files:
            print(f"Brak plików XLS w {ds['raw_dir']}/")
            sys.exit(1)

    print(f"Parsowanie: {args.dataset} ({len(files)} plików)")
    parse_files(args.dataset, files)


if __name__ == "__main__":
    main()
