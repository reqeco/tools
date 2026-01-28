import sys
from pathlib import Path

import xlrd

from common import (
    cell_float,
    cell_str,
    collect_record_ranges,
    excel_date_to_iso,
    reproject_wkt,
    save_records,
    split_parcels,
)


def parse_xls(filepath: str) -> list[dict]:
    wb = xlrd.open_workbook(filepath)
    sh = wb.sheet_by_index(0)
    datemode = wb.datemode

    records = []
    for nr_rej, r_start, r_end in collect_record_ranges(sh):
        rec = parse_record(sh, nr_rej, r_start, r_end, datemode)
        records.append(rec)

    return records


def parse_record(sh, nr_rej: int, r_start: int, r_end: int, datemode: int) -> dict:
    v = lambda r, c: sh.cell_value(r, c)
    r0 = r_start  # main row

    rec = {
        "registry_id": nr_rej,
        "historical_contamination": cell_str(v(r0, 1)),
        "area_ha": cell_float(v(r0, 2)),
        "status": cell_str(v(r0, 3)),
        "location": {
            "voivodeship": cell_str(v(r0, 4)),
            "county": cell_str(v(r0, 5)),
            "municipality": cell_str(v(r0, 6)),
            "address": cell_str(v(r0, 7)),
            "precinct": cell_str(v(r0, 8)),
            "parcel_numbers": split_parcels(v(r0, 9)),
            "coordinates_ewkt": reproject_wkt(cell_str(v(r0, 10))),
            "site_description": cell_str(v(r0, 11)),
        },
        "occurrence_time": {
            "date": excel_date_to_iso(v(r0, 12), datemode),
            "from": excel_date_to_iso(v(r0, 13), datemode),
            "to": excel_date_to_iso(v(r0, 14), datemode),
            "description": cell_str(v(r0, 15)),
        },
        "land_owner": cell_str(v(r0, 21)),
        "economic_activity": {
            "former": cell_str(v(r0, 22)),
            "current": cell_str(v(r0, 23)),
        },
    }

    # --- 1:N collections ---
    land_holders = []
    contaminants = []
    decisions = []
    remediation_obligees = []

    # Administrative proceedings (singular fields from main row)
    admin_proceedings = {
        "initiation_date": excel_date_to_iso(v(r0, 29), datemode),
        "legal_basis": cell_str(v(r0, 30)),
        "case_reference": cell_str(v(r0, 31)),
    }

    # Appeal (singular - max 1)
    appeal = None

    # Court proceedings (singular - max 1)
    court_proceedings = None

    # Remediation singular fields
    rem_exempted = None
    rem_liability = None
    rem_entity_type = None
    rem_planned_start = None
    rem_planned_end = None
    rem_actual_end = None
    rem_method = None
    rem_description = None
    rem_ecological_effect = None
    rem_effect_assessment = None

    for r in range(r_start, r_end):
        # --- Land holders (col 16-20) ---
        holder_name = cell_str(v(r, 16))
        if holder_name:
            land_holders.append({
                "name": holder_name,
                "address": cell_str(v(r, 17)),
                "entity_type": cell_str(v(r, 18)),
                "parcels": split_parcels(v(r, 19)),
                "economic_activity_code": cell_str(v(r, 20)),
            })

        # --- Contaminants (col 24-28) ---
        substance = cell_str(v(r, 26))
        soil_group = cell_str(v(r, 24))
        depth = cell_str(v(r, 25))
        if substance or soil_group or depth:
            contaminants.append({
                "soil_group": soil_group,
                "depth": depth,
                "substance": substance,
                "concentration": cell_str(v(r, 27)),
                "area_ha": cell_float(v(r, 28)),
            })

        # --- Decisions (col 32-37) ---
        dec_date = v(r, 32)
        dec_ref = cell_str(v(r, 33))
        dec_authority = cell_str(v(r, 34))
        if dec_date or dec_ref or dec_authority:
            decisions.append({
                "issue_date": excel_date_to_iso(dec_date, datemode),
                "reference": dec_ref,
                "issuing_authority": dec_authority,
                "legal_basis": cell_str(v(r, 35)),
                "complaint_to_wsa": cell_str(v(r, 36)),
                "overturned_by_court": cell_str(v(r, 37)),
            })

        # --- Appeal (col 38-46) - take first non-empty ---
        if appeal is None:
            appeal_date = v(r, 38)
            appeal_reason = cell_str(v(r, 39))
            appeal_dec_ref = cell_str(v(r, 40))
            if appeal_date or appeal_reason or appeal_dec_ref:
                appeal = {
                    "date": excel_date_to_iso(appeal_date, datemode),
                    "reason": appeal_reason,
                    "appealed_decision_reference": appeal_dec_ref,
                    "resolution_reference": cell_str(v(r, 41)),
                    "appellant_name": cell_str(v(r, 42)),
                    "appellant_address": cell_str(v(r, 43)),
                    "resolution_date": excel_date_to_iso(v(r, 44), datemode),
                    "reviewing_authority": cell_str(v(r, 45)),
                    "resolution_content": cell_str(v(r, 46)),
                }

        # --- Court proceedings (col 47-53) - take first non-empty ---
        if court_proceedings is None:
            court_date = v(r, 47)
            court_ref = cell_str(v(r, 48))
            if court_date or court_ref:
                court_proceedings = {
                    "issue_date": excel_date_to_iso(court_date, datemode),
                    "case_number": court_ref,
                    "challenged_decision_reference": cell_str(v(r, 49)),
                    "ruling_type": cell_str(v(r, 50)),
                    "verdict": cell_str(v(r, 51)),
                    "court": cell_str(v(r, 52)),
                    "cassation_appeal_to_nsa": cell_str(v(r, 53)),
                }

        # --- Remediation (col 54-66) ---
        if cell_str(v(r, 54)):
            rem_exempted = cell_str(v(r, 54))

        # Obligees (col 55-59) - multiple possible
        obligee_name = cell_str(v(r, 57))
        obligee_liability = cell_str(v(r, 55))
        obligee_entity = cell_str(v(r, 56))
        if obligee_name or obligee_liability or obligee_entity:
            if obligee_liability:
                rem_liability = obligee_liability
            if obligee_entity:
                rem_entity_type = obligee_entity

            if obligee_name:
                remediation_obligees.append({
                    "liability": obligee_liability or rem_liability,
                    "entity_type": obligee_entity or rem_entity_type,
                    "name": obligee_name,
                    "address": cell_str(v(r, 58)),
                    "economic_activity_code": cell_str(v(r, 59)),
                })

        # Remediation details (singular, take first non-empty)
        if rem_planned_start is None and v(r, 60):
            rem_planned_start = excel_date_to_iso(v(r, 60), datemode)
        if rem_planned_end is None and v(r, 61):
            rem_planned_end = excel_date_to_iso(v(r, 61), datemode)
        if rem_actual_end is None and v(r, 62):
            rem_actual_end = excel_date_to_iso(v(r, 62), datemode)
        if rem_method is None and cell_str(v(r, 63)):
            rem_method = cell_str(v(r, 63))
        if rem_description is None and cell_str(v(r, 64)):
            rem_description = cell_str(v(r, 64))
        if rem_ecological_effect is None and cell_str(v(r, 65)):
            rem_ecological_effect = cell_str(v(r, 65))
        if rem_effect_assessment is None and cell_str(v(r, 66)):
            rem_effect_assessment = cell_str(v(r, 66))

    # Also capture obligees that have only liability+entity but no name
    if not remediation_obligees and (rem_liability or rem_entity_type):
        remediation_obligees.append({
            "liability": rem_liability,
            "entity_type": rem_entity_type,
            "name": None,
            "address": None,
            "economic_activity_code": None,
        })

    admin_proceedings["decisions"] = decisions
    admin_proceedings["appeal"] = appeal

    # Check if remediation has any data
    has_rem = any([
        rem_exempted, remediation_obligees, rem_planned_start, rem_planned_end,
        rem_actual_end, rem_method, rem_description, rem_ecological_effect,
        rem_effect_assessment,
    ])

    rec["land_holders"] = land_holders
    rec["contaminants"] = contaminants
    rec["administrative_proceedings"] = admin_proceedings
    rec["court_proceedings"] = court_proceedings
    rec["remediation"] = {
        "exempted": rem_exempted,
        "obligees": remediation_obligees,
        "planned_start": rem_planned_start,
        "planned_end": rem_planned_end,
        "actual_end": rem_actual_end,
        "method": rem_method,
        "description": rem_description,
        "ecological_effect": rem_ecological_effect,
        "effect_assessment": rem_effect_assessment,
    } if has_rem else None

    # Notes - collect from all rows
    notes_parts = []
    for r in range(r_start, r_end):
        u = cell_str(v(r, 67))
        if u:
            notes_parts.append(u)
    rec["notes"] = " ".join(notes_parts) if notes_parts else None

    return rec


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "data/raw/contamination/zanieczyszczenia_śląskie.xls"
    input_path = Path(input_file)

    if not input_path.exists():
        print(f"Plik nie istnieje: {input_path}")
        sys.exit(1)

    print(f"Parsowanie: {input_path.name}")
    records = parse_xls(str(input_path))
    print(f"Znaleziono {len(records)} rekordów")

    out_dir = Path("data/json/contamination")
    save_records(records, out_dir)
    print(f"Zapisano {len(records)} plików JSON do {out_dir}/")

    # Quick stats
    total_subst = sum(len(r["contaminants"]) for r in records)
    total_holders = sum(len(r["land_holders"]) for r in records)
    total_dec = sum(len(r["administrative_proceedings"]["decisions"]) for r in records)
    with_rem = sum(1 for r in records if r["remediation"])
    print(f"\nStatystyki:")
    print(f"  Contaminants:               {total_subst}")
    print(f"  Land holders:               {total_holders}")
    print(f"  Administrative decisions:    {total_dec}")
    print(f"  Records with remediation:   {with_rem}")


if __name__ == "__main__":
    main()
