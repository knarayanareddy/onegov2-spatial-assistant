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

Touches: `drinkwaterzekerheid` (six-hour zones, productieketen, toestandsbeoordeling), `gebiedsviewer` (groenblauwe ruimte, natuurnetwerk, nutriënten verontreinigde gebieden, natuurlijke spons kansrijk), `lgn` for land-use shifts.

---

## Additional drinkwater-specific scenarios

> _TODO (Sebastiaan Schmidt, Tim Padmos, Thijs Raterink): the brief promises that more drinkwater-specific scenarios and example questions will be supplied by the challenge owners. Add them here, in the same shape as the three above (one Dutch sentence + the data themes it touches), so teams can pick them up directly._

- _TODO_
- _TODO_
- _TODO_

## How to use these scenarios

- Pick **one** scenario as the spine of your prototype.
- Show the **reasoning chain** in the Insight panel and in MLflow at [http://localhost:5001](http://localhost:5001).
- For the Should criterion, demo a **second** scenario (or a comparison such as "with vs without verzilting shock") on the same prototype.
- Be explicit about **assumptions, data gaps, and the time horizon** (2025 baseline vs 2040 projection). The brief rewards a prototype that surfaces uncertainty rather than hiding it.
