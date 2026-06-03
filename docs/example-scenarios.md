# Example scenarios

These are the three guiding **exploratory, what-if** questions the challenge brief expects every team to be able to engage with on the working assistant. Use them as a starting point and as a sanity check that your prototype combines at least two data themes for the Must criterion in [CHALLENGE.md](../CHALLENGE.md).

## 1. Verzilting shock on the Hollandse IJssel intake

> *Wat is de impact op de drinkwaterproductie als de Hollandse IJssel door verzilting zes weken niet bruikbaar is als innamepunt?*

Touches: `drinkwaterzekerheid` (intake points, production chain, drinkwaterbedrijven, six-hour zones), `gebiedsviewer/verzilting`, possibly `gebiedsviewer/overstromingen_kwetsbaarheid_panden_na_dijkdoorbraak` for downstream effects.

## 2. Combined climate and population pressure

> *Welke combinatie van klimaatdruk en bevolkingsgroei brengt de leveringszekerheid het eerst in gevaar?*

Touches: `drinkwaterzekerheid`, `gebiedsviewer` (verzilting, bodemdaling, daling bij ontwateringsdiepte, veenoxidatie, stabiliteit), `extra_data/CBS` vierkantstatistieken 2018 through 2023 for population growth.

## 3. Opportunities in the intrekgebied

> *Waar liggen de kansen: welke ingrepen in intrekgebieden vergroten de robuustheid het meest?*

Touches: `drinkwaterzekerheid` (six-hour zones, productieketen, toestandsbeoordeling), `gebiedsviewer` (groenblauwe ruimte, natuurnetwerk, nutriënten verontreinigde gebieden, natuurlijke spons kansrijk), and optionally `extra_data/lgn` for land-use shifts (LGN now lives under `extra_data/` and is opt-in).

---

## Additional drinkwater-specific scenarios (authoritative)

These six scenarios were supplied by the challenge owners (Sebastiaan Schmidt, Tim Padmos, Thijs Raterink) as the authoritative list of what-if questions to engage with on top of the three brief questions above. Several of them sharpen one of the three brief questions on a more concrete axis; one is genuinely new.

### 4. Dry KNMI climate scenario combined with verzilting on the Hollandse IJssel

> *How does drinking-water production behave under a dry KNMI climate scenario when verzilting on the Hollandse IJssel intake increases at the same time?*

Sharpens scenario 1 by anchoring the climate axis on a published KNMI climate scenario instead of an unspecified shock. Touches: `drinkwaterzekerheid` (intake points, production chain, drinkwaterbedrijven, six-hour zones), `gebiedsviewer/verzilting`. Optional external bron: KNMI klimaatscenario's 2050 ([klimaatscenarios.knmi.nl](https://www.klimaatscenarios.knmi.nl)).

### 5. KRW enforcement restricts agricultural land use around grondwaterbeschermingszones

> *If KRW enforcement leads to restrictions on agricultural land use around grondwaterbeschermingszones, which areas are affected and how does this change the protection of drinking-water sources?*

New angle that the brief mentions only as regulatory context. Touches: `drinkwaterzekerheid` (drinkwater_infrastructuur, zes-uur-zones, intrekgebieden), `gebiedsviewer` (nutri\u00ebnten verontreinigde gebieden, natuurnetwerk, stabiliteit), and optionally `extra_data/lgn` for current agricultural land use.

### 6. 80,000 new homes in the Zuidelijke Randstad raise water demand and pressure on soil and subsurface

> *What does an extra 80,000 homes in the Zuidelijke Randstad mean for drinking-water demand and for the pressure on soil and subsurface in the same area?*

Concretises the population-growth axis from the brief with a specific volume. Touches: `drinkwaterzekerheid` (productieketen, drinkwaterbedrijven), `gebiedsviewer` (bodemdaling, daling bij ontwateringsdiepte, veenoxidatie, stabiliteit, overstromingskwetsbaarheid), `extra_data/CBS` vierkantstatistieken (population baseline), `extra_data/woondeals` (capaciteitskaart_afname_regionaal, PMIEK projects).

### 7. Combined shock: drought + loss of one intake + population peak load

> *What happens to drinking-water security if drought, the loss of one intake point, and a population peak load all hit at the same time?*

This is the explicit Should-criterion combination from the brief: *droog klimaatscenario met/zonder wegvallen innamepunt, met/zonder bevolkingsgroei*. Strong fit for a comparison demo. Touches: `drinkwaterzekerheid` (intake points, production chain, six-hour zones, drinkwaterbedrijven), `gebiedsviewer/verzilting`, `extra_data/CBS`.

### 8. Optional datacenter realisation: water consumption and effect on drinking-water availability

> *If an additional datacenter is realised in Zuid-Holland, what is its water consumption and how does that affect drinking-water availability in the surrounding area?*

Genuinely new angle, not in the brief. Treat the datacenter water profile as an explicit assumption (litres per day, location) and surface that assumption in the Insight panel. Touches: `drinkwaterzekerheid` (productieketen, drinkwaterbedrijven, six-hour zones), `gebiedsviewer` (groenblauwe ruimte, stabiliteit), `extra_data/woondeals` (capaciteitskaart_afname_regionaal) for grid co-location.

### 9. Opportunity: nature restoration in intrekgebieden improves soil filter capacity

> *Where in Zuid-Holland would nature restoration in intrekgebieden deliver the largest improvement in soil filter capacity, and therefore in drinking-water robustness?*

Sharpens scenario 3 (the kansen-side from the brief) by naming the mechanism: nature restoration improving filter capacity. Touches: `drinkwaterzekerheid` (intrekgebieden, six-hour zones, toestandsbeoordeling), `gebiedsviewer` (natuurnetwerk, natuurlijke_spons_kansrijk, groenblauwe_ruimte_huidig_new, nutri\u00ebnten verontreinigde gebieden), and optionally `extra_data/lgn` for land-use shifts.

## How to use these scenarios

- Pick **one** scenario as the spine of your prototype.
- Show the **reasoning chain** in the Insight panel and in MLflow at [http://localhost:5001](http://localhost:5001).
- For the Should criterion, demo a **second** scenario (or a comparison such as "with vs without verzilting shock") on the same prototype.
- Be explicit about **assumptions, data gaps, and the time horizon** (2025 baseline vs 2040 projection). The brief rewards a prototype that surfaces uncertainty rather than hiding it.
