"""Build a self-contained HTML slide deck (slides.html) from the route results and maps.

Usage: python make_slides.py <cable-route dir>
Navigation: arrow keys / space / click. Print to PDF: one slide per page.
"""
import base64
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
R = json.loads((d / "routes.json").read_text())
P = json.loads((d / "problems.json").read_text())


def img(name):
    b = base64.b64encode((d / name).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b}" alt="{name}">'


def de(x, nd=0):
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


land = {"cost_Touros": "Touros/Natal", "cost_Pecem": "Pecém", "cost_SaoLuis": "São Luís"}
lens = [R[k]["length_km"] for k in land]
tots = [R[k]["total_bn"] for k in land]
A, B, C = R["cost_Touros"], R["shallow"], R["cost_Pecem"]
budget = 31.4

slides = []

slides.append(f"""
<section class="title">
  <h1>HVDC-Kabel Brasilien – Deutschland</h1>
  <p class="sub">Route, Kosten und technische Machbarkeit</p>
  <p class="meta">Rolle 1 · Kabel-Techno-Ökonomie · Stand 27.11.2026<br>
  Basis: 2 GW Bipol, 525 kV · Preisbasis 2025 · Anlandepunkt in Brasilien noch offen</p>
</section>""")

ABC = (A, B, C)
yrs = lambda r: de(r["lay_days"] / 365, 1)

# 1 key messages, conclusions and levers
slides.append(f"""
<section>
  <h2>Kernaussagen, Folgerungen und Hebel</h2>
  <div class="cols">
  <div>
  <h3>Kernaussagen</h3>
  <ol>
    <li><b>Technisch nicht erprobt:</b> Jede Route ist tiefer als 3.000 m, selbst die flachste bis
        ≈ {de(B['max_depth_m'])} m. Verlegt wurde bisher bis 2.150 m. [D]</li>
    <li><b>Zu teuer:</b> {de(min(tots),1)}–{de(max(tots),1)} Mrd. €, das
        <b>{de(min(tots)/budget,1)}–{de(max(tots)/budget,1)}-Fache</b> des Budgets von {de(budget,1)} Mrd. €. [D]</li>
    <li><b>Hohe Verluste:</b> Bei Volllast kommt nur ≈ ⅔ der Leistung an. [D]</li>
    <li><b>Lange Bauzeit:</b> mit einem Verlegeschiff gut 6 Jahre. [D]</li>
  </ol>
  </div>
  <div>
  <h3>Folgerungen und Hebel</h3>
  <ul>
    <li>Die <b>Route ist kaum ein Hebel</b>: Die Varianten unterscheiden sich um ≈ 2 % in den Kosten. [D]</li>
    <li><b>Voraussetzung</b> für jede Variante: ein Kabel, das für ≈ 4.500 m qualifiziert ist. [D]</li>
    <li><b>Verluste senken</b>: höhere Spannung oder größerer Querschnitt [A], Teillastbetrieb [D].</li>
    <li><b>Budget</b> nur erreichbar, wenn die Kosten pro km um mehr als die Hälfte sinken. [D]</li>
    <li><b>Bauzeit</b>: mehrere Schiffe parallel, Bau in Abschnitten. [A]</li>
  </ul>
  </div>
  </div>
</section>""")

# 2 biggest risks
RISKS = [
    ["Tiefe über 3.000 m", "Für 3.000–6.000 m gibt es nur eine Designstudie; jede Route reicht tiefer. [D]",
     "Qualifizierung für ≈ 4.500 m (Zuschuss in Aussicht); flachste Route B. [D]"],
    ["Kosten und Finanzierung", f"{de(min(tots),1)}–{de(max(tots),1)} Mrd. € gegenüber {de(budget,1)} Mrd. € Budget. [D]",
     "Staatliche Kreditgarantie und Zuschüsse [D]; geringere Leistung oder Bau in Stufen. [A]"],
    ["Verluste", "≈ 35 % bei Volllast, ≈ 18 % bei halber Last. [D]",
     "Höhere Spannung oder größerer Querschnitt [A]; Teillastbetrieb. [D]"],
    ["Bauzeit und Verzug", "Gut 6 Jahre mit einem Schiff; bei mehr als 30 Monaten Verzug kann der Abnehmer aussteigen. [D] "
     "Schiffe und Fertigung sind knapp. [A]",
     "Mehrere Schiffe, Bau in Abschnitten, Kapazitäten früh sichern. [A]"],
    ["Schäden und Reparaturen", "≈ 55 Tage/Jahr mit halber Leistung. [D] Anker und Fischerei im Flachwasser, "
     "Hangrutschungen, Sabotage; im Bündel fallen beide Pole zugleich aus. [A]",
     "Reparaturvertrag mit reserviertem Schiff, Ersatzteile auf Lager; Pole im Flachen getrennt verlegen; Überwachung. [A]"],
    ["Genehmigung in ≈ 10 Staaten", "Eigenes Recht und Umweltprüfung je Staat; Transitstaaten haben keinen Nutzen; "
     "umstrittene Gewässer. [A]",
     "Staatsvertrag DE–BR mit Transitstaaten; Netzabzweig als Nutzen; EU-Förderstatus (PCI/PMI). [A]"],
]
trs = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td></tr>" for a, b, c in RISKS)
slides.append(f"""
<section class="dense">
  <h2>Die größten Risiken</h2>
  <table class="mid"><tr><th style="width:20%">Risiko</th><th style="width:42%">Was droht</th><th>Gegenmaßnahme</th></tr>{trs}</table>
  <p class="note">Ausführlich: Folien „Wichtigste Faktoren“ im hinteren Teil.</p>
</section>""")

# 3 proposed routes with assessment
cell = lambda f: "".join(f"<td>{f(r)}</td>" for r in ABC)
slides.append(f"""
<section class="fig">
  <h2>Vorgeschlagene Routen und Bewertung</h2>
  <div class="cols wide">
    {img("map_routes.png")}
    <div>
    <table class="rt">
      <tr><th>[D]</th><th>A · Touros<br>kostenminimal</th><th>B · Touros<br>geringste Tiefe</th><th>C · Pecém<br>kürzeste</th></tr>
      <tr><td>Leistung</td>{cell(lambda r: '2 GW Bipol')}</tr>
      <tr><td>Länge</td>{cell(lambda r: de(r['length_km']) + ' km')}</tr>
      <tr><td>Investition</td>{cell(lambda r: de(r['total_bn'],1) + ' Mrd. €')}</tr>
      <tr><td>Max. Tiefe</td>{cell(lambda r: de(r['max_depth_m']) + ' m')}</tr>
      <tr><td>&gt; 3.000 m</td>{cell(lambda r: de(r['km']['abyssal']) + ' km')}</tr>
      <tr><td>Verlust Volllast</td>{cell(lambda r: de(r['loss_full_load_pct']) + ' %')}</tr>
      <tr><td>Bauzeit, 1 Schiff</td>{cell(lambda r: yrs(r) + ' Jahre')}</tr>
      <tr class="pro"><td>+</td><td>am günstigsten</td><td>am flachsten, kürzeste Strecke &gt; 3.000 m</td><td>am kürzesten, geringste Verluste</td></tr>
      <tr class="con"><td>−</td><td>quert die Biskaya mit fast 4.900 m</td><td>am längsten, mehr Flachwasser mit Schiffsverkehr [A]</td><td>am tiefsten, fast 3.000 km &gt; 3.000 m</td></tr>
      <tr class="hl"><td><b>Bewertung</b></td><td>Rückfalloption, wenn die Biskaya qualifiziert wird</td>
        <td><b>Vorschlag:</b> technisch am wenigsten extrem, ≈ 2 % teurer</td><td>nur bei Anlandung in Pecém; höchstes Tiefenrisiko</td></tr>
    </table>
    <p class="note">Alle Werte für <b>2 GW</b> (Bipol, 525 kV, zwei Kabel mit je ≈ 1 GW). Kostengünstigste Wege auf einem 0,05°-Raster. Alle Varianten liegen über dem Doppelten des Budgets.
       Die Anlandepunkte in Brasilien sind Beispiele, die Auswahl ist noch offen. [D]</p>
    </div>
  </div>
</section>""")

for ps in P["slides"]:
    trs = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td></tr>" for a, b, c in ps["rows"])
    slides.append(f"""
<section class="dense">
  <h2>{ps['title']}</h2>
  <table><tr><th style="width:19%">Problem</th><th style="width:43%">Warum ist das ein Problem?</th><th>Mögliche Lösung</th></tr>{trs}</table>
</section>""")

slides.append(f"""
<section class="fig">
  <h2>Datengrundlage: Tiefe des Atlantiks</h2>
  {img("map_gebco_2025_atlantic_30s.png")}
  <p class="note">GEBCO 2025, 30″. Die Linien bei 500 / 1.500 / 3.000 m sind die Grenzen der Kostenklassen.
  Der Mittelatlantische Rücken und die Inseln sind flacher, die Becken dazwischen 4.000–6.000 m tief. [D]</p>
</section>""")

slides.append("""
<section>
  <h2>Was die technische Machbarkeit bestimmt</h2>
  <table>
    <tr><th>Faktor</th><th>Zusammenhang</th></tr>
    <tr><td><b>Wassertiefe</b></td><td>Wichtigster Faktor. Verlegt wurde bis 2.150 m, typgeprüft bis 3.000 m;
      für 3.000–6.000 m gibt es <b>nur eine Designstudie</b>. [D] Die Zugkraft beim Verlegen ≈ Gewicht im Wasser × Tiefe [A]:
      ~80 t heute, ~150 t pro Kabel bei 6.000 m. Dafür braucht es eine leichtere Armierung, die nicht erprobt ist. [D]</td></tr>
    <tr><td><b>Reparatur &amp; Verfügbarkeit</b></td><td>Ein Fehler legt einen Pol still, es bleibt halbe Leistung.
      Die Reparatur dauert je nach Tiefe Wochen (Schelf) bis mehrere Monate (Tiefsee).
      Ergebnis: ≈ 0,8–0,9 Fehler/Jahr und <b>≈ 55 Tage/Jahr mit halber Leistung</b>. [D]</td></tr>
    <tr><td><b>Bauzeit</b></td><td>Je tiefer, desto langsamer wird verlegt; dazu kommen Wetterausfall und Muffen auf See.
      Das sind <b>≈ 2.250–2.350 Verlegetage</b> je nach Route, mit einem Schiff also <b>gut 6 Jahre</b>. [D]</td></tr>
    <tr><td><b>Nicht in den Daten</b></td><td>Schiffsverkehr, bestehende Kabel und Schutzgebiete außerhalb Brasiliens. [D]
      Die Route quert die Meereszonen von ≈ 10 Staaten, das ist auch eine politische Frage. [A]</td></tr>
  </table>
</section>""")

slides.append("""
<section>
  <h2>Was die Kosten bestimmt</h2>
  <div class="cols">
  <div>
  <table>
    <tr><th>Tiefenklasse [D]</th><th class="r">Kosten je km Route, relativ</th></tr>
    <tr><td>Schelf 0–500 m</td><td class="r">×1,2</td></tr>
    <tr class="hl"><td>Hang 500–1.500 m</td><td class="r">×1,0</td></tr>
    <tr><td>Tiefsee 1.500–3.000 m</td><td class="r">×1,25</td></tr>
    <tr><td>Abyssal &gt; 3.000 m</td><td class="r"><b>×1,9</b></td></tr>
  </table>
  <p class="note">Zwei Kabel inklusive Lieferung, Verlegung, Eingraben und Reserve. [D]</p>
  </div>
  <div>
  <ul>
    <li>Der <b>Schelf</b> ist teurer als der Hang, weil das Kabel eingegraben werden muss. [D]</li>
    <li>Für <b>Abschnitte über 3.000 m</b> kommen einmalige Kosten für die Qualifizierung hinzu. [D]</li>
    <li>Fixkosten: 2 Konverter, die Muffen auf See und 2 Anlandungen. [D]</li>
    <li class="key">Faustregel: Die Kosten hängen fast nur von der <b>Länge</b> und dem
        <b>Anteil der Abschnitte über 3.000 m</b> ab. Das Kabel macht ≈ 95 % aus. [D]</li>
  </ul>
  </div>
  </div>
</section>""")

slides.append("""
<section>
  <h2>Was die Netzverluste bestimmt</h2>
  <p class="formula">Verlust ∝ Länge × Leiterwiderstand × Strom² &nbsp;→&nbsp; relativer Verlust ∝ Länge × Leistung / Spannung² [A]</p>
  <ul class="big">
    <li>Bei 2 GW und 525 kV: <b>≈ 4 % pro 1.000 km</b> (Kupfer auf dem Schelf: 3,1 %), dazu 1,7 % in den Konvertern. [D]</li>
    <li>Bei ≈ 8.500–9.100 km sind das <b>≈ 34–36 % bei Volllast</b> und ≈ 18–19 % bei halber Last. [D]</li>
    <li>Halbe Leistung ergibt halben relativen Verlust. [D] Ein größerer Leiterquerschnitt senkt den Widerstand. [A]</li>
    <li>Höhere Spannung, z. B. 800 statt 525 kV, ergäbe ≈ 43 % der Verluste. [A]
        <span class="warn">Dafür gibt es keine Kabeldaten, das ist eine Annahme.</span></li>
  </ul>
</section>""")


slides.append("""
<section>
  <h2>Mehr oder weniger als 2 GW: Was ändert sich?</h2>
  <div class="cols">
  <div>
  <ul>
    <li><b>2 GW gilt für das ganze System</b>: ein Bipol aus zwei Kabeln mit je ≈ 1 GW.
        Fällt ein Kabel aus, bleibt halbe Leistung. [D]</li>
    <li>Kostendaten gibt es <b>nur für dieses eine Design</b>. Wie sich die Kosten mit der Leistung ändern,
        ist aus den Daten <b>nicht ablesbar</b>. [D]</li>
    <li>Das Kabel macht ≈ 95 % der Kosten aus [D]. Sein Preis hängt vor allem vom Leiterquerschnitt ab,
        also vom Strom. [A]</li>
    <li class="key">PyPSA-Eur rechnet <b>linear in MW</b> (HVDC submarine: 3.220 €/MW/km, DEA 2025). Bei 2 GW liegt das
        in derselben Größenordnung wie unsere Daten. [D] Wählt das Modell die Leistung selbst, unterstellt es eine
        Skalierung, die für dieses Kabel nicht belegt ist. [A]</li>
  </ul>
  </div>
  <div>
  <table>
    <tr><th style="width:26%">Leistung</th><th>Kosten und Verluste</th></tr>
    <tr><td><b>Weniger</b>, z. B. 1 GW</td><td>Dünnere Kabel, also billiger, aber kaum halb so teuer: Isolierung, Armierung,
        Verlegung und Muffen bleiben. Verluste in % bei passendem Querschnitt etwa gleich. [A]</td></tr>
    <tr><td><b>2 GW-Kabel, halb ausgelastet</b></td><td>Investition gleich, Verluste ≈ 18 statt ≈ 35 %. [D]</td></tr>
    <tr><td><b>Mehr</b>, z. B. 3–4 GW</td><td>Bei 525 kV sind die Querschnitte schon nahe am Maximum; schwerere Kabel sind
        in der Tiefsee kritisch. [A] Wege: höhere Spannung (keine Kabeldaten) oder ein zweiter Bipol,
        ≈ doppelte Kabelkosten, also annähernd linear. [A]</td></tr>
  </table>
  <p class="note"><span class="warn">Nächster Schritt:</span> Angebote für andere Leistungen anfragen, z. B. 1 GW
     und 640 kV, bevor das Modell die Leistung frei wählt. [A]</p>
  </div>
  </div>
</section>""")


slides.append(f"""
<section class="fig">
  <h2>Tiefenprofile</h2>
  {img("depth_profiles.png")}
  <p class="note">Die tiefsten Abschnitte: das Becken zwischen Brasilien und Afrika (4.000–6.000 m) und die Biskaya (≈ 4.900 m).
  Route B umgeht die Biskaya über die spanische Küste. [D]</p>
</section>""")


rows = "".join(
    f"<tr><td>{n}</td><td class='r'>{de(R[k]['length_km'])} km</td><td class='r'>{de(R[k]['total_bn'],1)} Mrd. €</td>"
    f"<td class='r'>{de(R[k]['max_depth_m'])} m</td><td class='r'>{de(R[k]['km']['abyssal'])} km</td></tr>"
    for k, n in land.items())
slides.append(f"""
<section>
  <h2>Anlandepunkt in Brasilien: noch offen</h2>
  <div class="cols">
  <div>
  <p>Kostenminimaler Weg je Anlandepunkt bis in die Deutsche Bucht [D]:</p>
  <table>
    <tr><th>Anlandung</th><th class="r">Länge</th><th class="r">Investition</th><th class="r">max. Tiefe</th><th class="r">&gt; 3.000 m</th></tr>
    {rows}
  </table>
  <p class="note">Die Bandbreite beträgt ≈ {de(max(tots)-min(tots),0)} Mrd. € ({de(100*(max(tots)/min(tots)-1),0)} %).
     Der Anlandepunkt verändert die Machbarkeit stärker als die Kosten. [D]</p>
  </div>
  <div>
  <p><b>Kriterien für die Auswahl (gemeinsam mit Rolle 2):</b></p>
  <ul>
    <li><b>Nähe zu Afrika</b>: Die Ostspitze bei Natal/Touros hat die kürzeste und flachste Tiefseequerung. [D]</li>
    <li><b>Nähe zur Erzeugung</b>: Wind- und Solarstandorte in CE und RN (Shortlist). [D]</li>
    <li><b>Hafen &amp; Logistik</b>: Pecém, Natal (Shortlist). [D]</li>
    <li><b>Netz</b>: Anschluss an das Netz im Nordosten für den Konverter. [A]</li>
    <li><b>Küste</b>: Schutzgebiete und Schiffsverkehr (Daten liegen vor). [D]</li>
  </ul>
  </div>
  </div>
</section>""")


slides.append("""
<section>
  <h2>Methode, Quellen und Grenzen</h2>
  <ul>
    <li><b>Kabeldaten</b>: workshop/inputs/cable_system_design.yaml (Preisbasis 2025, EUR).</li>
    <li><b>Budget</b>: workshop/inputs/financing_term_sheet.md (Obergrenze 31,4 Mrd. €).</li>
    <li><b>Bathymetrie</b>: GEBCO 2025, Atlantik-Korridor 30″; für die Routensuche auf 0,05° gemittelt.</li>
    <li><b>Routenwahl</b>: kürzester Weg (Dijkstra), Kosten je km nach Tiefenklasse; Variante B mit Tiefengrenze ≈ 4.580 m.</li>
    <li><b>Verluste</b>: Gleichstromwiderstand bei maximaler Temperatur, Nennstrom 1.905 A, Konverter je 0,86 %.</li>
    <li><b>Grenzen</b>: grobes Raster, in Küstennähe ungenau; keine Daten zu Schiffsverkehr, Kabeln und Schutzgebieten
        außerhalb Brasiliens; Anlandung in Deutschland pauschal in der Deutschen Bucht; Kapitalkosten noch nicht annualisiert.</li>
    <li><b>Kennzeichnung</b>: [D] steht für Zahlen und Aussagen aus den Dateien oben oder daraus berechnet; [A] für allgemeines Fachwissen ohne Beleg im Repo, vor Verwendung prüfen.</li>
    <li>Skripte: workshop/cable-route/ (grid.py, routes.py, plot_maps.py, make_slides.py, make_slides_pdf.py, problems.json).</li>
  </ul>
</section>""")

slides.append(f"""
<section class="fig">
  <h2>Anhang: Küste Nordost-Brasilien</h2>
  {img("map_brazil_northeast.png")}
</section>""")
slides.append(f"""
<section class="fig">
  <h2>Anhang: Nordsee</h2>
  {img("map_europe_northsea.png")}
</section>""")

css = """
:root{--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8880;--surf:#fcfcfb;--line:#e6e5e0;--acc:#2a78d6;--warn:#b5560f}
*{box-sizing:border-box}html,body{margin:0;background:#2b2b2a;font-family:"Segoe UI",Helvetica,Arial,sans-serif;color:var(--ink)}
section{display:none;width:1280px;height:720px;margin:20px auto;background:var(--surf);padding:48px 64px;position:relative;overflow:hidden}
section.active{display:block}
h1{font-size:44px;margin:180px 0 12px}h2{font-size:30px;margin:0 0 24px;font-weight:600}
.title{border-left:12px solid var(--acc)}.sub{font-size:24px;color:var(--ink2);margin:0 0 48px}.meta{color:var(--ink2);font-size:16px;line-height:1.6}
ul,ol{font-size:18px;line-height:1.5;padding-left:24px}li{margin:6px 0}.big{font-size:21px}.big li{margin:12px 0}
table{border-collapse:collapse;font-size:15px;width:100%}th{text-align:left;color:var(--ink2);font-weight:600;border-bottom:2px solid var(--ink2);padding:6px 10px}
td{border-bottom:1px solid var(--line);padding:7px 10px;vertical-align:top}.r{text-align:right}tr.hl td{background:#eef4fc}
tr.pro td,tr.con td{font-size:14px;color:var(--ink2)}tr.pro td:first-child,tr.con td:first-child{font-weight:700;font-size:18px}
.note{color:var(--ink2);font-size:14px;margin-top:14px}.warn{color:var(--warn)}.key{font-weight:500}
.formula{font-size:20px;background:#f1f1ef;padding:14px 18px;border-radius:4px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:40px}.cols.wide{grid-template-columns:auto 1fr;gap:28px}
.fig img{max-height:490px;max-width:100%;display:block;margin:0 auto}.cols.wide img{max-height:560px;margin:0}
.side{font-size:16px;line-height:1.5;color:var(--ink2)}
h3{font-size:20px;margin:0 0 4px;color:var(--acc)}
.dense table.mid{font-size:15px}.dense table.mid td{padding:9px 10px}
table.rt{font-size:13px}table.rt td,table.rt th{padding:5px 7px}table.rt tr.pro td,table.rt tr.con td{font-size:12.5px}
.dense h2{font-size:24px;margin-bottom:12px}.dense table{font-size:12px}.dense td{padding:4px 8px}.dense .note{font-size:11px;margin-top:8px}
.tag{display:inline-block;font-size:.72em;font-weight:700;line-height:1;padding:2px 4px;border-radius:3px;vertical-align:1px;margin:0 1px}
.tag.d{background:#e3eefb;color:#1d5aa6}.tag.a{background:#fbe9dc;color:#9a4a0e}
.lg{position:absolute;left:64px;bottom:18px;color:var(--muted);font-size:12px}
.pg{position:absolute;right:28px;bottom:18px;color:var(--muted);font-size:13px}
@media print{@page{size:1280px 720px;margin:0}html,body{background:none}section{display:block!important;margin:0;page-break-after:always}}
"""
js = """
const s=[...document.querySelectorAll('section')];let i=0;
s.forEach((x,k)=>{const p=document.createElement('div');p.className='pg';p.textContent=(k+1)+' / '+s.length;x.appendChild(p);
  if(!x.classList.contains('title')){const l=document.createElement('div');l.className='lg';l.innerHTML='<span class="tag d">D</span> aus den Workshop-Daten oder daraus berechnet &nbsp;·&nbsp; <span class="tag a">A</span> allgemeines Fachwissen, nicht durch die Daten im Repo belegt';x.appendChild(l)}});
function show(n){i=Math.max(0,Math.min(s.length-1,n));s.forEach((x,k)=>x.classList.toggle('active',k===i))}
document.addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key))show(i+1);if(['ArrowLeft','PageUp'].includes(e.key))show(i-1)});
document.addEventListener('click',e=>show(e.clientX>innerWidth/2?i+1:i-1));show(0);
"""
html = f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><title>HVDC-Kabel Brasilien–Deutschland</title>
<style>{css}</style></head><body>{''.join(slides)}<script>{js}</script></body></html>"""
html = html.replace("[D]", '<span class="tag d">D</span>').replace("[A]", '<span class="tag a">A</span>')
(d / "slides.html").write_text(html, encoding="utf-8")
print(f"{len(slides)} slides -> {d/'slides.html'}")
