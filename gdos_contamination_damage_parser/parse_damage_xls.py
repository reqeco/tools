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


def parse_damage_xls(filepath: str) -> list[dict]:
    wb = xlrd.open_workbook(filepath)
    sh = wb.sheet_by_index(0)
    datemode = wb.datemode

    records = []
    for nr_rej, r_start, r_end in collect_record_ranges(sh):
        rec = parse_damage_record(sh, nr_rej, r_start, r_end, datemode)
        records.append(rec)

    return records


def parse_damage_record(sh, nr_rej: int, r_start: int, r_end: int, datemode: int) -> dict:
    v = lambda r, c: sh.cell_value(r, c)
    r0 = r_start

    rec = {
        "registry_id": nr_rej,
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
        "land_surface_holder": cell_str(v(r0, 19)),
        "land_owner": cell_str(v(r0, 20)),
        "remediation_obligee": cell_str(v(r0, 21)),
        "environmental_component": cell_str(v(r0, 22)),
        "event_description": cell_str(v(r0, 23)),
        "total_area_ha": cell_float(v(r0, 24)),
    }

    # --- 1:N collections ---
    reporters = []
    responsible_entities = []
    contaminants = []
    water_changes = []
    protected_species_list = []
    protected_habitats = []
    decisions = []
    appeals = []

    # Singular fields from first non-empty row
    proceedings_status = None
    initiation_date = None
    detection_date = None
    court_proceedings = None

    # Remedial actions (singular)
    action_planned_start = None
    action_planned_end = None
    action_actual_end = None
    action_method = None
    action_description = None
    action_ecological_effect = None
    action_effect_assessment = None

    # Cost financing (singular)
    cost_recovery = None
    cost_source = None
    cost_covered_by_obligee = None
    cost_enforcement = None
    cost_financial_security = None
    cost_non_recovery_reason = None

    for r in range(r_start, r_end):
        # --- Reporters (col 1-3) ---
        reporter_name = cell_str(v(r, 1))
        if reporter_name:
            reporters.append({
                "name": reporter_name,
                "address": cell_str(v(r, 2)),
                "legal_form": cell_str(v(r, 3)),
            })

        # --- Responsible entities (col 16-18) ---
        resp_name = cell_str(v(r, 16))
        if resp_name:
            responsible_entities.append({
                "name": resp_name,
                "address": cell_str(v(r, 17)),
                "economic_activity_code": cell_str(v(r, 18)),
            })

        # --- Soil contaminants (col 25-29) ---
        substance = cell_str(v(r, 27))
        soil_group = cell_str(v(r, 25))
        depth = cell_str(v(r, 26))
        if substance or soil_group or depth:
            contaminants.append({
                "soil_group": soil_group,
                "depth": depth,
                "substance": substance,
                "concentration": cell_str(v(r, 28)),
                "area_ha": cell_float(v(r, 29)),
            })

        # --- Water changes (col 30-32) ---
        water_type = cell_str(v(r, 30))
        water_changes_desc = cell_str(v(r, 31))
        water_substance = cell_str(v(r, 32))
        if water_type or water_changes_desc or water_substance:
            water_changes.append({
                "water_type": water_type,
                "changes": water_changes_desc,
                "substance": water_substance,
            })

        # --- Protected species (col 33) ---
        species = cell_str(v(r, 33))
        if species:
            protected_species_list.append(species)

        # --- Protected habitats (col 34-35) ---
        natura2000 = cell_str(v(r, 34))
        other_habitat = cell_str(v(r, 35))
        if natura2000 or other_habitat:
            protected_habitats.append({
                "natura_2000": natura2000,
                "other": other_habitat,
            })

        # --- Administrative proceedings singular fields ---
        if proceedings_status is None and cell_str(v(r, 36)):
            proceedings_status = cell_str(v(r, 36))
        if initiation_date is None and v(r, 37):
            initiation_date = excel_date_to_iso(v(r, 37), datemode)
        if detection_date is None and v(r, 38):
            detection_date = excel_date_to_iso(v(r, 38), datemode)

        # --- Decisions (col 39-44) ---
        dec_date = v(r, 39)
        dec_ref = cell_str(v(r, 40))
        dec_authority = cell_str(v(r, 41))
        if dec_date or dec_ref or dec_authority:
            decisions.append({
                "issue_date": excel_date_to_iso(dec_date, datemode),
                "reference": dec_ref,
                "issuing_authority": dec_authority,
                "legal_basis": cell_str(v(r, 42)),
                "complaint_to_wsa": cell_str(v(r, 43)),
                "overturned_by_court": cell_str(v(r, 44)),
            })

        # --- Appeals (col 45-53) ---
        appeal_date = v(r, 45)
        appeal_reason = cell_str(v(r, 46))
        appeal_dec_ref = cell_str(v(r, 47))
        if appeal_date or appeal_reason or appeal_dec_ref:
            appeals.append({
                "date": excel_date_to_iso(appeal_date, datemode),
                "reason": appeal_reason,
                "appealed_decision_reference": appeal_dec_ref,
                "resolution_reference": cell_str(v(r, 48)),
                "appellant_name": cell_str(v(r, 49)),
                "appellant_address": cell_str(v(r, 50)),
                "resolution_date": excel_date_to_iso(v(r, 51), datemode),
                "reviewing_authority": cell_str(v(r, 52)),
                "resolution_content": cell_str(v(r, 53)),
            })

        # --- Court proceedings (col 54-60) - take first non-empty ---
        if court_proceedings is None:
            court_date = v(r, 54)
            court_ref = cell_str(v(r, 55))
            if court_date or court_ref:
                court_proceedings = {
                    "issue_date": excel_date_to_iso(court_date, datemode),
                    "case_number": court_ref,
                    "challenged_decision_reference": cell_str(v(r, 56)),
                    "ruling_type": cell_str(v(r, 57)),
                    "verdict": cell_str(v(r, 58)),
                    "court": cell_str(v(r, 59)),
                    "cassation_appeal_to_nsa": cell_str(v(r, 60)),
                }

        # --- Remedial actions (col 61-67) ---
        if action_planned_start is None and v(r, 61):
            action_planned_start = excel_date_to_iso(v(r, 61), datemode)
        if action_planned_end is None and v(r, 62):
            action_planned_end = excel_date_to_iso(v(r, 62), datemode)
        if action_actual_end is None and v(r, 63):
            action_actual_end = excel_date_to_iso(v(r, 63), datemode)
        if action_method is None and cell_str(v(r, 64)):
            action_method = cell_str(v(r, 64))
        if action_description is None and cell_str(v(r, 65)):
            action_description = cell_str(v(r, 65))
        if action_ecological_effect is None and cell_str(v(r, 66)):
            action_ecological_effect = cell_str(v(r, 66))
        if action_effect_assessment is None and cell_str(v(r, 67)):
            action_effect_assessment = cell_str(v(r, 67))

        # --- Cost financing (col 68-73) ---
        if cost_recovery is None and cell_str(v(r, 68)):
            cost_recovery = cell_str(v(r, 68))
        if cost_source is None and cell_str(v(r, 69)):
            cost_source = cell_str(v(r, 69))
        if cost_covered_by_obligee is None and cell_str(v(r, 70)):
            cost_covered_by_obligee = cell_str(v(r, 70))
        if cost_enforcement is None and cell_str(v(r, 71)):
            cost_enforcement = cell_str(v(r, 71))
        if cost_financial_security is None and cell_str(v(r, 72)):
            cost_financial_security = cell_str(v(r, 72))
        if cost_non_recovery_reason is None and cell_str(v(r, 73)):
            cost_non_recovery_reason = cell_str(v(r, 73))

    rec["reporters"] = reporters
    rec["responsible_entities"] = responsible_entities
    rec["contaminants"] = contaminants

    # Water changes
    rec["water_changes"] = water_changes if water_changes else None

    # Protected species (deduplicate)
    rec["protected_species"] = list(dict.fromkeys(protected_species_list)) if protected_species_list else None

    # Protected habitats
    rec["protected_habitats"] = protected_habitats if protected_habitats else None

    # Administrative proceedings
    rec["administrative_proceedings"] = {
        "status": proceedings_status,
        "initiation_date": initiation_date,
        "detection_date": detection_date,
        "decisions": decisions,
        "appeals": appeals,
    }

    rec["court_proceedings"] = court_proceedings

    # Remedial actions
    has_actions = any([
        action_planned_start, action_planned_end, action_actual_end,
        action_method, action_description, action_ecological_effect,
        action_effect_assessment,
    ])
    rec["remedial_actions"] = {
        "planned_start": action_planned_start,
        "planned_end": action_planned_end,
        "actual_end": action_actual_end,
        "method": action_method,
        "description": action_description,
        "ecological_effect": action_ecological_effect,
        "effect_assessment": action_effect_assessment,
    } if has_actions else None

    # Cost financing
    has_costs = any([
        cost_recovery, cost_source, cost_covered_by_obligee,
        cost_enforcement, cost_financial_security, cost_non_recovery_reason,
    ])
    rec["cost_financing"] = {
        "recovery": cost_recovery,
        "source": cost_source,
        "covered_by_obligee": cost_covered_by_obligee,
        "enforcement": cost_enforcement,
        "financial_security": cost_financial_security,
        "non_recovery_reason": cost_non_recovery_reason,
    } if has_costs else None

    # Notes (col 74)
    notes_parts = []
    for r in range(r_start, r_end):
        u = cell_str(v(r, 74))
        if u:
            notes_parts.append(u)
    rec["notes"] = " ".join(notes_parts) if notes_parts else None

    return rec


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "data/raw/damage/szkody_śląskie.xls"
    input_path = Path(input_file)

    if not input_path.exists():
        print(f"Plik nie istnieje: {input_path}")
        sys.exit(1)

    print(f"Parsowanie: {input_path.name}")
    records = parse_damage_xls(str(input_path))
    print(f"Znaleziono {len(records)} rekordów")

    out_dir = Path("data/json/damage")
    save_records(records, out_dir)
    print(f"Zapisano {len(records)} plików JSON do {out_dir}/")

    # Quick stats
    total_subst = sum(len(r["contaminants"]) for r in records)
    total_resp = sum(len(r["responsible_entities"]) for r in records)
    total_dec = sum(len(r["administrative_proceedings"]["decisions"]) for r in records)
    total_appeals = sum(len(r["administrative_proceedings"]["appeals"]) for r in records)
    with_water = sum(1 for r in records if r["water_changes"])
    with_species = sum(1 for r in records if r["protected_species"])
    with_actions = sum(1 for r in records if r["remedial_actions"])
    with_costs = sum(1 for r in records if r["cost_financing"])
    print(f"\nStatystyki:")
    print(f"  Contaminants:               {total_subst}")
    print(f"  Responsible entities:        {total_resp}")
    print(f"  Administrative decisions:    {total_dec}")
    print(f"  Appeals:                     {total_appeals}")
    print(f"  Records with water changes:  {with_water}")
    print(f"  Records with prot. species:  {with_species}")
    print(f"  Records with remedial act.:  {with_actions}")
    print(f"  Records with cost financing: {with_costs}")


if __name__ == "__main__":
    main()
