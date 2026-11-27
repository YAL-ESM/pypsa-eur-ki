# Caveat: the 2050 horizon and the Brazil cable

The apparent value of the Brazil interconnector is an artefact of the 2050
horizon. The CO2 cap falls to zero in 2050, so the shadow price of the cap
jumps to 24,354 EUR/t in the island baseline and 35,905 EUR/t in the trade run,
and German marginal prices reach 2,959 and 4,371 EUR/MWh. At those prices any
clean import looks valuable. In 2025-2045, German load-weighted prices are
30-113 EUR/MWh (see `workshop/trade/compare_trade.py` and
`results/de10-trade/comparison_baseline_vs_trade.csv`).

Against that, role 1's 2,000 MW routes cost 68-72 bn EUR, lose 34-35% at full
load, and annualise to 290-360 EUR/MWh delivered at 3-4% WACC over 40 years,
before Brazilian generation (about 26-38 EUR/MWh). The cable therefore does not
pay against 2025-2045 prices and only appears worthwhile against the 2050 cap
artefact.

Decision: do not use 2050 to justify the cable. Drop or fix the zero-CO2 cap
first (role 4), then re-evaluate. Until then, the defensible default is not to
build the interconnector.
