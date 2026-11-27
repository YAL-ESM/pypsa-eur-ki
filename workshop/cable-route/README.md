# Kabel Brasilien – Deutschland (Rolle 1)

Routen, Kosten und Machbarkeit des HVDC-Kabels von Macau/Guamaré (RN) in die Deutsche Bucht.

| Ordner | Inhalt |
|---|---|
| `skripte/` | Python-Skripte, dazu ihre Eingaben und Zwischenergebnisse: `routes.json`/`routes.npz` (berechnete Routen), `problems.json` (Text der Folien „Wichtigste Faktoren“) |
| `excel/` | `routen_vergleich.xlsx` (die drei Routen im Vergleich), `capex_opex.xlsx` (CAPEX, OPEX und Verluste je Route) |
| `folien/` | `slides.pdf` und `slides.html` (Foliensatz), dazu die Karten und Tiefenprofile als PNG |

`folien/` und `excel/` werden erzeugt. Änderungen gehören in die Skripte bzw. in `skripte/problems.json`.

## Neu erzeugen

Aus dem Repo-Verzeichnis, in dieser Reihenfolge. Schritt 1 und 2 nur, wenn sich Routen oder Karten ändern.

```bash
C=workshop/cable-route
PY=".pixi/envs/default/bin/python -I"
$PY $C/skripte/grid.py <gebco_2025_atlantic_30s.nc>                                       # 1a Raster (einmalig, nach /tmp)
$PY $C/skripte/routes.py workshop/inputs/cable_system_design.yaml $C/skripte/routes.npz   # 1b Routen -> routes.json/.npz
$PY $C/skripte/plot_maps.py <data-brazil/bathymetry_atlantic> $C/skripte/routes.npz $C/folien  # 2 Karten
$PY $C/skripte/make_slides.py $C            # 3 Folien HTML
$PY $C/skripte/make_slides_pdf.py $C        # 3 Folien PDF
$PY $C/skripte/make_capex_opex_xlsx.py $C   # 4 Excel CAPEX/OPEX
$PY $C/skripte/make_routes_xlsx.py $C       # 4 Excel Routenvergleich
```

## Vor jedem Upload

Die Einzelpreise und technischen Daten des Kabellieferanten, die Projektreferenz und die Einzelbedingungen
des Finanzierungs-Term-Sheets dürfen nicht nach Git. `skripte/check_confidential.py` prüft die
Lieferantendaten in allen Textdateien; Bilder, PDF und Excel muss man selbst ansehen.
