# GDOS Contamination & Damage Parser

Parses data from GDOS (General Directorate for Environmental Protection) registries, converting XLS files to site-centric JSON records.

## Usage

```bash
# Parse all files for a given dataset
poetry run python main.py contamination
poetry run python main.py damage

# Parse a specific file
poetry run python main.py contamination data/raw/contamination/zanieczyszczenia_śląskie.xls
```

## Project structure

```
data/raw/contamination/     16 XLS source files (zanieczyszczenia_*.xls)
data/raw/damage/            16 XLS source files (szkody_*.xls)
data/json/contamination/    1938 JSON output files
data/json/damage/           1174 JSON output files
common.py                   shared utility functions
parse_contamination_xls.py  contamination parser
parse_damage_xls.py         damage parser
main.py                     CLI entry point
```

## Datasets

### Contamination (zanieczyszczenia)

Registry of historical soil contamination sites. 16 files (one per voivodeship), 68 columns, 1938 unique records. Registry IDs are globally unique across all voivodeships.

### Damage (szkody)

Registry of environmental damage and threats. 16 files (one per voivodeship), 75 columns, 1174 unique records. Two records (ID 1573 and 2092) appear in multiple voivodeships (cross-border events) — identical data, deduplicated on save.

The two datasets have independent ID numbering and separate schemas.

## XLS file structure

Both file types follow the same master-detail row pattern:

- **Rows 0-2**: headers (3 levels, with merged cells)
- **Row 3+**: data
- A row with column 0 filled (`Nr rej.`) starts a new record
- Subsequent rows without `Nr rej.` are continuations of the same record (1:N relationships)

### Contamination — XLS columns (68)

| Column | Field | Cardinality |
|--------|-------|-------------|
| 0 | Registry ID | record key |
| 1 | Historical contamination | 1:1 |
| 2 | Area [ha] | 1:1 |
| 3 | Status | 1:1 |
| 4-11 | Location (voivodeship, county, municipality, address, precinct, parcels, coordinates, description) | 1:1 |
| 12-15 | Occurrence time (date, from, to, description) | 1:1 |
| 16-20 | Land holders (name, address, entity type, parcels, PKD code) | **1:N** |
| 21 | Land owner | 1:1 |
| 22-23 | Economic activity (former, current) | 1:1 |
| 24-28 | Contaminants (soil group, depth, substance, concentration, area) | **1:N** |
| 29-31 | Administrative proceedings (initiation date, legal basis, case reference) | 1:1 |
| 32-37 | Decisions (date, reference, authority, legal basis, WSA complaint, overturned) | **1:N** |
| 38-46 | Appeal (date, reason, decision ref, resolution, appellant, authority, content) | 1:1 |
| 47-53 | Court proceedings (date, case number, challenged decision, ruling type, verdict, court, cassation) | 1:1 |
| 54 | Remediation — exemption | 1:1 |
| 55-59 | Remediation obligees (liability, entity type, name, address, PKD code) | **1:N** |
| 60-66 | Remediation (planned start/end, actual end, method, description, effect, assessment) | 1:1 |
| 67 | Notes | 1:1 (collected from all rows) |

### Damage — XLS columns (75)

| Column | Field | Cardinality |
|--------|-------|-------------|
| 0 | Registry ID | record key |
| 1-3 | Reporters (name, address, legal form) | **1:N** |
| 4-11 | Location (voivodeship, county, municipality, address, precinct, parcels, coordinates, description) | 1:1 |
| 12-15 | Occurrence time (date, from, to, description) | 1:1 |
| 16-18 | Responsible entities (name, address, PKD code) | **1:N** |
| 19 | Land surface holder | 1:1 |
| 20 | Land owner | 1:1 |
| 21 | Remediation obligee | 1:1 |
| 22 | Environmental component | 1:1 |
| 23 | Event description | 1:1 |
| 24 | Total area [ha] | 1:1 |
| 25-29 | Soil contamination (soil group, depth, substance, concentration, area) | **1:N** |
| 30-32 | Water state changes (water type, changes, substance) | **1:N** |
| 33 | Protected species | **1:N** |
| 34-35 | Protected habitats (Natura 2000, other) | **1:N** |
| 36 | Proceedings status | 1:1 |
| 37 | Initiation date | 1:1 |
| 38 | Detection date | 1:1 |
| 39-44 | Decisions (date, reference, authority, legal basis, WSA complaint, overturned) | **1:N** |
| 45-53 | Appeals (date, reason, decision ref, resolution, appellant, address, resolution date, authority, content) | **1:N** |
| 54-60 | Court proceedings (date, case number, challenged decision, ruling type, verdict, court, cassation) | 1:1 |
| 61-67 | Remedial actions (planned start/end, actual end, method, description, effect, assessment) | 1:1 |
| 68-73 | Cost financing (recovery, source, covered by obligee, enforcement, financial security, non-recovery reason) | 1:1 |
| 74 | Notes | 1:1 (collected from all rows) |

## JSON model

### Contamination

```json
{
  "registry_id": 123,
  "historical_contamination": "tak",
  "area_ha": 0.5,
  "status": "zakończone",
  "location": {
    "voivodeship": "śląskie",
    "county": "Katowice",
    "municipality": "Katowice",
    "address": "ul. Przykładowa 1",
    "precinct": "0001",
    "parcel_numbers": ["1234/5", "1234/6"],
    "coordinates_ewkt": "SRID=2180;POLYGON((......))",
    "site_description": "teren dawnej fabryki"
  },
  "occurrence_time": {
    "date": "2010-01-15",
    "from": "2009-06-01",
    "to": "2010-01-15",
    "description": "..."
  },
  "land_owner": "Jan Kowalski",
  "economic_activity": {
    "former": "produkcja chemiczna",
    "current": "brak"
  },
  "land_holders": [
    {
      "name": "Firma Sp. z o.o.",
      "address": "ul. Inna 2",
      "entity_type": "osoba prawna",
      "parcels": ["1234/5"],
      "economic_activity_code": "20.11.Z"
    }
  ],
  "contaminants": [
    {
      "soil_group": "C",
      "depth": "od 0 do 2",
      "substance": "ołów",
      "concentration": ">600",
      "area_ha": 0.3
    }
  ],
  "administrative_proceedings": {
    "initiation_date": "2010-03-01",
    "legal_basis": "art. 101e",
    "case_reference": "WSI.512.1.2010",
    "decisions": [
      {
        "issue_date": "2011-06-09",
        "reference": "WSI.512.1.2010.MB",
        "issuing_authority": "RDOS Katowice",
        "legal_basis": "art. 15",
        "complaint_to_wsa": null,
        "overturned_by_court": null
      }
    ],
    "appeal": {
      "date": "2011-07-01",
      "reason": "...",
      "appealed_decision_reference": "WSI.512.1.2010.MB",
      "resolution_reference": "GDOS/123",
      "appellant_name": "Jan Kowalski",
      "appellant_address": "ul. Inna 2",
      "resolution_date": "2011-09-15",
      "reviewing_authority": "GDOS",
      "resolution_content": "utrzymanie w mocy"
    }
  },
  "court_proceedings": {
    "issue_date": "2012-01-10",
    "case_number": "II SA/Ka 1234/11",
    "challenged_decision_reference": "GDOS/123",
    "ruling_type": "wyrok",
    "verdict": "oddalenie skargi",
    "court": "WSA Gliwice",
    "cassation_appeal_to_nsa": null
  },
  "remediation": {
    "exempted": null,
    "obligees": [
      {
        "liability": "odpowiedzialny",
        "entity_type": "osoba prawna",
        "name": "Firma Sp. z o.o.",
        "address": "ul. Inna 2",
        "economic_activity_code": "20.11.Z"
      }
    ],
    "planned_start": "2012-06-01",
    "planned_end": "2013-12-31",
    "actual_end": "2014-03-15",
    "method": "ex-situ",
    "description": "wymiana gruntu",
    "ecological_effect": "brak przekroczeń",
    "effect_assessment": "pozytywna"
  },
  "notes": "..."
}
```

### Damage

```json
{
  "registry_id": 2137,
  "location": {
    "voivodeship": "śląskie",
    "county": "Rybnik",
    "municipality": "Rybnik",
    "address": "ul. Przykładowa 1",
    "precinct": "0001",
    "parcel_numbers": ["1234/5"],
    "coordinates_ewkt": "SRID=2180;POLYGON((......))",
    "site_description": null
  },
  "occurrence_time": {
    "date": "2010-07-16",
    "from": "2010-07-15",
    "to": "2010-07-17",
    "description": "..."
  },
  "land_surface_holder": null,
  "land_owner": null,
  "remediation_obligee": "podmiot korzystający ze środowiska",
  "environmental_component": "powierzchnia ziemi",
  "event_description": "wyciek oleju do gruntu",
  "total_area_ha": 0.1,
  "reporters": [
    {
      "name": "Prezydent Miasta",
      "address": "ul. Główna 1",
      "legal_form": "jednostka samorządu terytorialnego"
    }
  ],
  "responsible_entities": [
    {
      "name": "Firma ABC",
      "address": "ul. Inna 2",
      "economic_activity_code": "38.11.Z"
    }
  ],
  "contaminants": [
    {
      "soil_group": "C",
      "depth": "od 0 do 2",
      "substance": "węglowodory C12-C35",
      "concentration": ">3000",
      "area_ha": null
    }
  ],
  "water_changes": [
    {
      "water_type": "wody podziemne",
      "changes": "zmiana barwy",
      "substance": "olej mineralny"
    }
  ],
  "protected_species": ["orzeł bielik"],
  "protected_habitats": [
    {
      "natura_2000": "PLH240001",
      "other": null
    }
  ],
  "administrative_proceedings": {
    "status": "zakończone postępowanie administracyjne",
    "initiation_date": "2010-07-23",
    "detection_date": "2010-07-16",
    "decisions": [
      {
        "issue_date": "2011-06-09",
        "reference": "WSI.512.43.1.2011.MB",
        "issuing_authority": "RDOS Katowice",
        "legal_basis": "art. 15",
        "complaint_to_wsa": null,
        "overturned_by_court": null
      }
    ],
    "appeals": [
      {
        "date": "2011-07-01",
        "reason": "...",
        "appealed_decision_reference": "WSI.512.43.1.2011.MB",
        "resolution_reference": "GDOS/456",
        "appellant_name": "Firma ABC",
        "appellant_address": "ul. Inna 2",
        "resolution_date": "2011-09-15",
        "reviewing_authority": "GDOS",
        "resolution_content": "utrzymanie w mocy"
      }
    ]
  },
  "court_proceedings": {
    "issue_date": "2012-01-10",
    "case_number": "II SA/Ka 5678/11",
    "challenged_decision_reference": "GDOS/456",
    "ruling_type": "wyrok",
    "verdict": "oddalenie skargi",
    "court": "WSA Gliwice",
    "cassation_appeal_to_nsa": null
  },
  "remedial_actions": {
    "planned_start": "2012-06-01",
    "planned_end": "2013-12-31",
    "actual_end": "2014-03-15",
    "method": "ex-situ",
    "description": "wymiana gruntu",
    "ecological_effect": "brak przekroczeń",
    "effect_assessment": "pozytywna"
  },
  "cost_financing": {
    "recovery": "tak",
    "source": "środki własne",
    "covered_by_obligee": "tak",
    "enforcement": null,
    "financial_security": null,
    "non_recovery_reason": null
  },
  "notes": "..."
}
```

## Coordinates

Source files contain coordinates in different CRS:
- EPSG:2180 (PUWG 1992) — majority of records
- EPSG:3857 (Web Mercator) — 85 records
- EPSG:2176 (PL-2000 zone 5) — 1 record

The parser automatically detects the CRS based on:
1. EWKT prefix (`SRID=xxxx;...`)
2. Coordinate value ranges (heuristic for 3857 and PL-2000)

All coordinates are reprojected to EPSG:2180 using pyproj and stored in EWKT format with `SRID=2180;` prefix.

## Utility functions (common.py)

| Function | Description |
|----------|-------------|
| `cell_str(value)` | Cleans string: replaces `\r\n`, `\r`, `\n` with spaces, strips whitespace. Returns `None` for empty values. |
| `cell_float(value)` | Converts to float or returns `None`. |
| `excel_date_to_iso(value, datemode)` | Converts Excel serial date to ISO 8601 (`YYYY-MM-DD`). |
| `split_parcels(raw)` | Splits parcel number strings by comma and `\n`. |
| `reproject_wkt(wkt)` | Detects source CRS and reprojects WKT to EPSG:2180 EWKT. |
| `collect_record_ranges(sh)` | Groups XLS rows by registry ID (master-detail pattern). |
| `save_records(records, out_dir)` | Saves each record as an individual JSON file named by registry ID. |

## Dependencies

- `xlrd` — reads .xls files (legacy Excel format)
- `pyproj` — coordinate system transformations
