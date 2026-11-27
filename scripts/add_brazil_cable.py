# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
#
# SPDX-License-Identifier: MIT
"""Add the Brazil export site and the HVDC cable to Germany (role 4 wiring).

Brazil is a dedicated export site (no demand, no grid): role 2's firm-supply
plants at the landing point feed the cable, which imports into German node 08
(North). Cable and Brazilian plants are fixed capacity - this is the
cost-benefit study of a given cable, not a capacity expansion.

Costs are consolidated in real 2025 EUR, all annualised at 7%:
  - cable: role 1's aggregate CAPEX, FOM and repairs (workshop/cable-route),
    annualised at the model's own discount rate so the cable is treated like
    every other asset in the network;
  - Brazilian plants and battery: role 2's annualised figures (workshop/brazil/
    costs_firm_supply.txt), passed in the config;
  - the connection from the plants to the landing (role 2, variant A) is folded
    into the cable's annual cost.

The intertemporal study discount rate (role 4's 2% real, 1-3% band) is applied
later, in post-processing on the solved runs - not here.
"""

import importlib.util
import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
ROUTES_JSON = ROOT / "workshop/cable-route/skripte/routes.json"
CAPEX_OPEX_PY = ROOT / "workshop/cable-route/skripte/capex_opex.py"

DE_LANDING_BUS = "DE0 8AC"  # node 08, North
CABLE_CARRIER = "Brazil cable"
CABLE_COLOR = "#D55E00"  # workshop plot style, one colour per technology group
# timeseries column per technology
PROFILE_COL = {
    "solar": "solar_GW", "onwind": "onwind_GW",
    "offwind_fixed": "offwind_fixed_GW", "offwind_floating": "offwind_floating_GW",
    "offwind": "offwind_GW",
}
CARRIER = {"offwind_fixed": "offwind-ac", "offwind_floating": "offwind-float", "offwind": "offwind-ac"}


def annuity(rate, years):
    """Capital recovery factor: annual cost per unit of overnight investment."""
    if rate == 0:
        return 1.0 / years
    return rate / (1.0 - (1.0 + rate) ** -years)


def _capex_opex():
    spec = importlib.util.spec_from_file_location("cable_capex_opex", CAPEX_OPEX_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cable_costs(route, p_nom_mw, discount_rate, connection_eur=0.0):
    """Annualised cable cost, real 2025 EUR, from role 1's rounded aggregates."""
    routes = json.loads(ROUTES_JSON.read_text())
    r = routes[route]
    life = _capex_opex().LIFE
    capex = r["total_bn"] * 1e9
    fom = r["fom_mio"] * 1e6
    repair = r["repair_mio"] * 1e6
    annual = annuity(discount_rate, life) * capex + fom + repair + connection_eur
    return {
        "capital_cost": annual / p_nom_mw,  # EUR/MW/yr
        "efficiency": 1.0 - r["loss_full_load_pct"] / 100.0,
        "lifetime": life,
        # one pole out leaves half power; spread the fault days as an average
        "availability": 1.0 - 0.5 * r["half_power_days_per_year"] / 365.0,
        "capex_eur": capex,
        "annual_eur": annual,
    }


def _profiles(path, snapshots):
    """Role 2's hourly timeseries, averaged to the model's snapshots (GW per tech)."""
    ts = pd.read_csv(ROOT / path, index_col=0, parse_dates=True)
    freq = pd.infer_freq(snapshots[:3]) or "2h"
    return ts.resample(freq).mean().reindex(snapshots).interpolate(limit_direction="both").fillna(0.0)


def add_brazil_cable(n, config, costs):
    """Add Brazil and the cable to network `n`. No-op unless enabled in config."""
    cfg = config.get("brazil_cable")
    if not cfg or not cfg.get("enabled", False):
        return

    route = cfg["route"]
    landing = cfg.get("landing_bus", DE_LANDING_BUS)
    if landing not in n.buses.index:
        raise ValueError(f"German landing bus {landing!r} not in the network")

    br = cfg["brazil"]
    br_bus, bat_bus = br["bus"], f"{br['bus']} battery"

    n.add("Bus", br_bus, carrier="AC", country="BR", x=br["x"], y=br["y"])
    n.add("Bus", bat_bus, carrier="battery", country="BR", x=br["x"], y=br["y"])

    ts = _profiles(br["timeseries"], n.snapshots)
    for tech, spec in br["generators"].items():
        cap = spec["p_nom"]
        if cap <= 0:
            continue
        profile = (ts[PROFILE_COL[tech]] / (cap / 1e3)).clip(0.0, 1.0)  # GW / GW
        n.add(
            "Generator", f"{br_bus} {tech}", bus=br_bus, carrier=CARRIER.get(tech, tech),
            p_nom=cap, p_nom_extendable=False,
            capital_cost=spec["capital_cost"], marginal_cost=0.0,
            p_max_pu=pd.Series(profile.values, index=n.snapshots),
        )

    bat = br["battery"]
    if bat["power_mw"] > 0:
        n.add(
            "Store", f"{bat_bus} Store", bus=bat_bus,
            e_nom=bat["energy_mwh"], e_nom_extendable=False,
            capital_cost=bat["storage_cost"],
        )
        for side, (b0, b1) in {"charger": (br_bus, bat_bus), "discharger": (bat_bus, br_bus)}.items():
            n.add(
                "Link", f"{bat_bus} {side}", bus0=b0, bus1=b1,
                p_nom=bat["power_mw"], p_nom_extendable=False,
                efficiency=bat.get("inverter_efficiency", 0.96),
                capital_cost=bat["inverter_cost"],
            )

    rate = cfg["cable"].get("discount_rate", costs.at["HVDC submarine", "discount rate"])
    c = cable_costs(route, cfg["cable"]["p_nom"], rate, br.get("connection_cost", 0.0))
    if CABLE_CARRIER not in n.carriers.index:
        n.add("Carrier", CABLE_CARRIER, nice_name="Brazil cable", color=CABLE_COLOR, co2_emissions=0.0)
    n.add(
        "Link", f"{br_bus} -> {landing}", bus0=br_bus, bus1=landing, carrier=CABLE_CARRIER,
        p_nom=cfg["cable"]["p_nom"], p_nom_extendable=False,
        capital_cost=c["capital_cost"], efficiency=c["efficiency"],
        lifetime=c["lifetime"], p_max_pu=c["availability"],
    )
    logger.info(
        "Added Brazil export site (%s) and cable %s -> %s: %s MW, %.1f%% losses, "
        "%.0f EUR/MW/yr, efficiency %.3f, availability %.3f",
        br_bus, br_bus, landing, cfg["cable"]["p_nom"],
        100 * (1 - c["efficiency"]), c["capital_cost"], c["efficiency"], c["availability"],
    )
