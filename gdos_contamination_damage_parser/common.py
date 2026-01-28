import json
import re
import sys
from pathlib import Path

import xlrd
from pyproj import Transformer

# Lazy-initialized transformers for reprojection to EPSG:2180
_transformers: dict[int, Transformer] = {}


def _get_transformer(source_srid: int) -> Transformer:
    if source_srid not in _transformers:
        _transformers[source_srid] = Transformer.from_crs(
            f"EPSG:{source_srid}", "EPSG:2180", always_xy=True
        )
    return _transformers[source_srid]


def _detect_srid(wkt: str) -> tuple[int, str]:
    """Detect SRID from EWKT prefix or coordinate range. Returns (srid, bare_wkt)."""
    m = re.match(r"SRID=(\d+);(.*)", wkt, re.DOTALL)
    if m:
        return int(m.group(1)), m.group(2)

    # Detect from first coordinate pair
    cm = re.search(r"[\(\s,]([\d]+\.?[\d]*)\s+([\d]+\.?[\d]*)", wkt)
    if cm:
        try:
            x = float(cm.group(1).rstrip("."))
            y = float(cm.group(2).rstrip("."))
        except ValueError:
            return 2180, wkt

        if 1500000 < x < 2700000 and 6200000 < y < 7300000:
            return 3857, wkt
        if x > 3000000:
            # PL-2000 zones: zone = first digit of X
            zone_digit = int(str(int(x))[0])
            srid_map = {5: 2176, 6: 2177, 7: 2178, 8: 2179}
            return srid_map.get(zone_digit, 2180), wkt

    return 2180, wkt


def _transform_coords(x: float, y: float, source_srid: int) -> tuple[float, float]:
    t = _get_transformer(source_srid)
    return t.transform(x, y)


def reproject_wkt(wkt: str) -> str:
    """Reproject WKT/EWKT to EPSG:2180 and return as EWKT with SRID=2180 prefix."""
    if not wkt:
        return wkt

    source_srid, bare_wkt = _detect_srid(wkt)

    # Fix trailing dots on numbers (e.g. "690680.244682326." -> "690680.244682326")
    bare_wkt = re.sub(r"(\d)\.\s", r"\1 ", bare_wkt)
    bare_wkt = re.sub(r"(\d)\.\)", r"\1)", bare_wkt)

    if source_srid == 2180:
        # Already correct, just ensure EWKT prefix
        return f"SRID=2180;{bare_wkt}"

    # Replace all coordinate pairs in the WKT
    def replace_coord(match):
        try:
            x = float(match.group(1).rstrip("."))
            y = float(match.group(2).rstrip("."))
            nx, ny = _transform_coords(x, y, source_srid)
            return f"{nx:.2f} {ny:.2f}"
        except (ValueError, Exception):
            return match.group(0)

    transformed = re.sub(
        r"([\d]+\.?[\d]*)\s+([\d]+\.?[\d]*)",
        replace_coord,
        bare_wkt,
    )
    return f"SRID=2180;{transformed}"


def excel_date_to_iso(value, datemode=0):
    """Convert Excel serial date to ISO 8601 string."""
    if not value:
        return None
    try:
        y, m, d, h, mi, s = xlrd.xldate_as_tuple(float(value), datemode)
        return f"{y:04d}-{m:02d}-{d:02d}"
    except (ValueError, TypeError):
        return str(value).strip() if value else None


def cell_str(value):
    """Return cleaned string or None."""
    if value is None or value == "":
        return None
    s = str(value).replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()
    return s if s else None


def cell_float(value):
    """Return float or None."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def split_parcels(raw):
    """Split parcel numbers string into a list."""
    if not raw:
        return []
    return [d.strip() for d in str(raw).replace("\n", ",").split(",") if d.strip()]


def collect_record_ranges(sh) -> list[tuple[int, int, int]]:
    """Group rows by Nr rej. (col 0). Returns list of (nr_rej, row_start, row_end)."""
    record_ranges: list[tuple[int, int, int]] = []
    current_start = None
    current_nr = None

    for r in range(3, sh.nrows):
        nr = sh.cell_value(r, 0)
        if nr:
            if current_start is not None:
                record_ranges.append((current_nr, current_start, r))
            current_nr = int(nr)
            current_start = r
    if current_start is not None:
        record_ranges.append((current_nr, current_start, sh.nrows))

    return record_ranges


def save_records(records: list[dict], out_dir: Path):
    """Save each record as individual JSON file named by registry_id."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for rec in records:
        nr = rec["registry_id"]
        out_file = out_dir / f"{nr}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
