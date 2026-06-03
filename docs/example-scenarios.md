# Example scenarios

These are the **exploratory, what-if** questions the challenge owners (Sebastiaan Schmidt, Tim Padmos, Thijs Raterink) supplied as the authoritative list to engage with on the working assistant. Use them as a starting point and as a sanity check that your prototype combines at least two data themes for the Must criterion in [CHALLENGE.md](../CHALLENGE.md). Several of them sharpen one of the brief's three guiding questions on a more concrete axis; one is genuinely new.

## 1. Dry KNMI climate scenario combined with verzilting on the Hollandse IJssel

> *How does drinking-water production behave under a dry KNMI climate scenario when verzilting on the Hollandse IJssel intake increases at the same time?*

Sharpens the brief's *Hollandse IJssel verzilting* question by anchoring the climate axis on a published KNMI climate scenario instead of an unspecified shock. Touches: `drinkwaterzekerheid` (intake points, production chain, drinkwaterbedrijven, six-hour zones), `gebiedsviewer/verzilting`. Optional external source: KNMI klimaatscenario's 2050 ([klimaatscenarios.knmi.nl](https://www.klimaatscenarios.knmi.nl)).

## 2. KRW enforcement restricts agricultural land use around grondwaterbeschermingszones

> *If KRW enforcement leads to restrictions on agricultural land use around grondwaterbeschermingszones, which areas are affected and how does this change the protection of drinking-water sources?*

New angle that the brief mentions only as regulatory context. Touches: `drinkwaterzekerheid` (drinkwater_infrastructuur, zes-uur-zones, intrekgebieden), `gebiedsviewer` (nutriënten verontreinigde gebieden, natuurnetwerk, stabiliteit), and optionally `extra_data/lgn` for current agricultural land use.

## 3. 80,000 new homes in the Zuidelijke Randstad raise water demand and pressure on soil and subsurface

> *What does an extra 80,000 homes in the Zuidelijke Randstad mean for drinking-water demand and for the pressure on soil and subsurface in the same area?*

Concretises the population-growth axis from the brief with a specific volume. Touches: `drinkwaterzekerheid` (productieketen, drinkwaterbedrijven), `gebiedsviewer` (bodemdaling, daling bij ontwateringsdiepte, veenoxidatie, stabiliteit, overstromingskwetsbaarheid), `extra_data/CBS` vierkantstatistieken (population baseline), `extra_data/woondeals` (capaciteitskaart_afname_regionaal, PMIEK projects).

## 4. Combined shock: drought + loss of one intake + population peak load

> *What happens to drinking-water security if drought, the loss of one intake point, and a population peak load all hit at the same time?*

This is the explicit Should-criterion combination from the brief: *droog klimaatscenario met/zonder wegvallen innamepunt, met/zonder bevolkingsgroei*. Strong fit for a comparison demo. Touches: `drinkwaterzekerheid` (intake points, production chain, six-hour zones, drinkwaterbedrijven), `gebiedsviewer/verzilting`, `extra_data/CBS`.

## 5. Optional datacenter realisation: water consumption and effect on drinking-water availability

> *If an additional datacenter is realised in Zuid-Holland, what is its water consumption and how does that affect drinking-water availability in the surrounding area?*

Genuinely new angle, not in the brief. Treat the datacenter water profile as an explicit assumption (litres per day, location) and surface that assumption in the Insight panel. Touches: `drinkwaterzekerheid` (productieketen, drinkwaterbedrijven, six-hour zones), `gebiedsviewer` (groenblauwe ruimte, stabiliteit), `extra_data/woondeals` (capaciteitskaart_afname_regionaal) for grid co-location.

## 6. Opportunity: nature restoration in intrekgebieden improves soil filter capacity

> *Where in Zuid-Holland would nature restoration in intrekgebieden deliver the largest improvement in soil filter capacity, and therefore in drinking-water robustness?*

Sharpens the brief's *kansen in intrekgebieden* question by naming the mechanism: nature restoration improving filter capacity. Touches: `drinkwaterzekerheid` (intrekgebieden, six-hour zones, toestandsbeoordeling), `gebiedsviewer` (natuurnetwerk, natuurlijke_spons_kansrijk, groenblauwe_ruimte_huidig_new, nutriënten verontreinigde gebieden), and optionally `extra_data/lgn` for land-use shifts.

## How to use these scenarios

- Pick **one** scenario as the spine of your prototype.
- Show the **reasoning chain** in the Insight panel and in MLflow at [http://localhost:5001](http://localhost:5001).
- For the Should criterion, demo a **second** scenario (or a comparison such as "with vs without verzilting shock") on the same prototype.
- Be explicit about **assumptions, data gaps, and the time horizon** (2025 baseline vs 2040 projection). The brief rewards a prototype that surfaces uncertainty rather than hiding it.
