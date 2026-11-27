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

slides.append(f"""
<section>
  <h2>Kernaussagen</h2>
  <ol class="big">
    <li><b>Technisch nicht erprobt:</b> Kein Seeweg bleibt unter 3.000 m.
        Das bestmögliche Maximum liegt bei <b>≈ 4.430 m</b>, verlegt wurde bisher bis 2.150 m. [D]</li>
    <li><b>Zu teuer:</b> <b>{de(min(tots),1)}–{de(max(tots),1)} Mrd. €</b> je nach Anlandepunkt,
        das ist das <b>{de(min(tots)/budget,1)}–{de(max(tots)/budget,1)}-Fache</b> der Budgetgrenze von {de(budget,1)} Mrd. €. [D]</li>
    <li><b>Hohe Verluste:</b> Bei Volllast kommt nur etwa <b>⅔</b> der Leistung an (≈ 35 % Verlust). [D]</li>
    <li><b>Die Route ist nicht der Hebel:</b> Die Varianten unterscheiden sich um wenige Prozent. [D]
        Entscheidend sind Spannung, Leistung und Tiefenqualifikation. [A]</li>
  </ol>
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

slides.append(f"""
<section class="fig">
  <h2>Drei Beispielrouten</h2>
  <div class="cols wide">
    {img("map_routes.png")}
    <div class="side">
      <p>Berechnet als kostengünstigster Weg über ein Raster mit 0,05° Auflösung, gewichtet mit den Kosten pro km der Tiefenklasse. [D]</p>
      <p>Alle Routen führen an Westafrika und Portugal entlang und durch den Ärmelkanal. Der afrikanische
         Kontinentalhang ist der günstigste Abschnitt. [D]</p>
      <p class="warn">Die brasilianischen Anlandepunkte sind <b>Beispiele</b>, die Auswahl ist noch offen.</p>
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

slides.append(f"""
<section>
  <h2>Routenvergleich</h2>
  <table>
    <tr><th>[D] berechnet</th><th>A · Touros, kostenminimal</th><th>B · Touros, geringste Tiefe</th><th>C · Pecém, kürzeste</th></tr>
    <tr><td>Länge</td><td>{de(A['length_km'])} km</td><td>{de(B['length_km'])} km</td><td>{de(C['length_km'])} km</td></tr>
    <tr><td>Investition</td><td><b>{de(A['total_bn'],1)} Mrd. €</b></td><td>{de(B['total_bn'],1)} Mrd. €</td><td>{de(C['total_bn'],1)} Mrd. €</td></tr>
    <tr><td>Maximale Tiefe</td><td>{de(A['max_depth_m'])} m</td><td><b>{de(B['max_depth_m'])} m</b></td><td>{de(C['max_depth_m'])} m</td></tr>
    <tr><td>Strecke tiefer als 3.000 m</td><td>{de(A['km']['abyssal'])} km</td><td><b>{de(B['km']['abyssal'])} km</b></td><td>{de(C['km']['abyssal'])} km</td></tr>
    <tr><td>Verlust Voll- / Halblast</td><td>{de(A['loss_full_load_pct'])} / {de(A['loss_half_load_pct'])} %</td>
        <td>{de(B['loss_full_load_pct'])} / {de(B['loss_half_load_pct'])} %</td><td><b>{de(C['loss_full_load_pct'])} / {de(C['loss_half_load_pct'])} %</b></td></tr>
    <tr class="pro"><td>+</td><td>am günstigsten, kürzeste Tiefseequerung nach Afrika</td>
        <td>umgeht die Biskaya, technisch am wenigsten extrem</td><td>am kürzesten, geringste Verluste</td></tr>
    <tr class="con"><td>−</td><td>quert die Biskaya mit fast 4.900 m</td>
        <td>am längsten [D], mehr Schelfstrecke mit Schiffsverkehr und Fischerei [A]</td><td>am tiefsten (5.900 m), fast 3.000 km auf freier Tiefsee</td></tr>
  </table>
  <p class="note">Die Unterschiede in den Kosten liegen bei ≈ 2 %. Alle Varianten liegen über dem Doppelten der Budgetgrenze von {de(budget,1)} Mrd. €. [D]</p>
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

slides.append(f"""
<section>
  <h2>Folgerungen und Hebel</h2>
  <ul class="big">
    <li>Die <b>Route</b> ist weitgehend festgelegt (Westafrika → Iberien → Ärmelkanal); dort ist kaum etwas zu holen. [D]</li>
    <li><b>Machbarkeit</b> erfordert ein Kabel, das für ≈ 4.500 m qualifiziert ist. Das ist die Voraussetzung für jede Variante. [D]</li>
    <li><b>Wirtschaftlichkeit</b>: Die Verluste von ≈ ⅓ wiegen schwerer als die Wahl der Route. [D] Mögliche Hebel:
      <ul>
        <li>höhere Spannung oder größerer Querschnitt (Annahme, keine Daten) [A]</li>
        <li>geringere Leistung bzw. Teillastbetrieb [D]</li>
        <li>Teilstrecke über Land durch Afrika und Europa (nicht untersucht) [A]</li>
      </ul></li>
    <li>Um die Budgetgrenze zu erreichen, müssten die Kosten pro km <b>um mehr als die Hälfte sinken</b>. [D]</li>
  </ul>
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
