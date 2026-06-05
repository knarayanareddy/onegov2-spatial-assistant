<!-- ScenarioComparePanel.vue — detailed A/B scenario comparison (design doc §16 ext).
     Compares two assumption sets over a shared H3 universe via POST
     /api/scenario/compare, then shows the verdict change, per-factor attribution
     (verzilting/overstroming/bescherming/vraag) and a per-cell diff with verdict
     transitions. Plain JSON endpoint (no SSE). -->
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { cellToLatLng } from "h3-js";

const VLABEL: Record<string, string> = { GO: "HAALBAAR", CAUTION: "RISICO", STOP: "NIET HAALBAAR" };
const KNOBS: { key: string; label: string }[] = [
  { key: "knmi_dryness_multiplier", label: "KNMI droogte (1.0–1.8)" },
  { key: "weight_salinity", label: "Gewicht verzilting" },
  { key: "weight_demand", label: "Gewicht vraag" },
  { key: "weight_flood", label: "Gewicht overstroming" },
  { key: "weight_protection", label: "Gewicht bescherming" },
];

// Defaults make the out-of-the-box comparison meaningful: KNMI B vs KNMI Hd.
const a = reactive<Record<string, number>>({
  knmi_dryness_multiplier: 1.0, weight_salinity: 0.4, weight_demand: 0.3,
  weight_flood: 0.2, weight_protection: 0.1,
});
const b = reactive<Record<string, number>>({
  knmi_dryness_multiplier: 1.8, weight_salinity: 0.4, weight_demand: 0.3,
  weight_flood: 0.2, weight_protection: 0.1,
});
const labelA = ref("Scenario A (KNMI B)");
const labelB = ref("Scenario B (KNMI Hd)");
const base = ref<"salinity" | "populated">("salinity");

const loading = ref(false);
const error = ref("");
const result = ref<any>(null);

async function compare() {
  loading.value = true; error.value = ""; result.value = null;
  try {
    const r = await fetch("/api/scenario/compare", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        a: { label: labelA.value, assumptions: { ...a } },
        b: { label: labelB.value, assumptions: { ...b } },
        base: base.value, top_n: 12,
      }),
    });
    if (!r.ok) {
      error.value = `Serverfout (${r.status})`;
    } else {
      result.value = await r.json();
      renderOverlay(result.value?.overlay?.cells ?? []);
    }
  } catch {
    error.value = "Kan de server niet bereiken.";
  } finally {
    loading.value = false;
  }
}

function signed(x: number, digits = 1): string {
  return `${x > 0 ? "+" : ""}${x.toFixed(digits)}`;
}
function barWidth(share: number): string {
  return `${Math.min(100, Math.abs(share))}%`;
}

// ---- delta-map overlay (deck.gl H3HexagonLayer over MapLibre) ----
const mapEl = ref<HTMLDivElement | null>(null);
let overlay: MapboxOverlay | null = null;
let map: maplibregl.Map | null = null;

// Diverging colour: red where B is worse (delta > 0), green where B is better
// (delta < 0), neutral near zero. Alpha scales with magnitude (capped at ±50).
function deltaColor(d: number): [number, number, number, number] {
  const x = Math.max(-50, Math.min(50, d)) / 50;
  if (x > 0.02) return [220, 53, 69, Math.round(70 + 150 * x)];
  if (x < -0.02) return [40, 167, 69, Math.round(70 + 150 * -x)];
  return [150, 160, 170, 60];
}

function tooltipHtml(o: any): string {
  const d = o.delta > 0 ? `+${o.delta}` : `${o.delta}`;
  return `<div style="font:12px system-ui,sans-serif;line-height:1.4">`
    + `<b>${o.h3_id}</b><br/>A ${o.score_a} · B ${o.score_b} · Δ <b>${d}</b></div>`;
}

// Auto-fit the camera to the scored cells (h3-js centroids).
function fitToCells(cells: any[]) {
  if (!map || !cells.length) return;
  let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;
  for (const c of cells) {
    const [lat, lng] = cellToLatLng(c.h3_id);
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
    if (lng < minLng) minLng = lng;
    if (lng > maxLng) maxLng = lng;
  }
  map.fitBounds([[minLng, minLat], [maxLng, maxLat]], { padding: 40, maxZoom: 11, duration: 600 });
}

function renderOverlay(cells: any[]) {
  if (!overlay) return;
  overlay.setProps({
    layers: [new H3HexagonLayer({
      id: "compare_delta_h3",
      data: cells,
      pickable: true,
      extruded: false,
      getHexagon: (d: any) => d.h3_id,
      getFillColor: (d: any) => deltaColor(d.delta),
      getLineColor: [255, 255, 255, 30],
      lineWidthMinPixels: 0.5,
    })],
  });
  fitToCells(cells);
}

onMounted(() => {
  if (!mapEl.value) return;
  map = new maplibregl.Map({
    container: mapEl.value, style: "https://demotiles.maplibre.org/style.json",
    center: [4.5, 51.92], zoom: 7.5,
  });
  overlay = new MapboxOverlay({
    interleaved: true,
    layers: [],
    getTooltip: ({ object }: any) => (object ? { html: tooltipHtml(object) } : null),
  });
  map.addControl(overlay as any);
});
</script>

<template>
  <div class="cmp">
    <header class="head">
      <h3>Scenario's vergelijken</h3>
      <p class="sub">Twee aannamesets over hetzelfde H3-gebied — met gevolgen per factor en per cel.</p>
    </header>

    <div class="controls">
      <div class="side">
        <input v-model="labelA" class="lbl" />
        <label v-for="kn in KNOBS" :key="'a-' + kn.key">
          <span class="k">{{ kn.label }}</span>
          <input type="range" min="0" max="2" step="0.05" v-model.number="a[kn.key]" />
          <span class="v">{{ (a[kn.key] ?? 0).toFixed(2) }}</span>
        </label>
      </div>
      <div class="side">
        <input v-model="labelB" class="lbl" />
        <label v-for="kn in KNOBS" :key="'b-' + kn.key">
          <span class="k">{{ kn.label }}</span>
          <input type="range" min="0" max="2" step="0.05" v-model.number="b[kn.key]" />
          <span class="v">{{ (b[kn.key] ?? 0).toFixed(2) }}</span>
        </label>
      </div>
    </div>

    <div class="actions">
      <label class="base">Universum:
        <select v-model="base">
          <option value="salinity">Verzilting (intake)</option>
          <option value="populated">Bebouwd (vraag)</option>
        </select>
      </label>
      <button :disabled="loading" @click="compare">{{ loading ? "Bezig…" : "Vergelijk" }}</button>
    </div>

    <section class="mapsec">
      <div class="maptitle">Kaart: verschil in DrinkwaterDruk per H3-cel (A → B) — beweeg over een cel voor details</div>
      <div ref="mapEl" class="map" />
      <ul class="legend">
        <li><i style="background:#dc3545" />hoger (slechter) in B</li>
        <li><i style="background:#28a745" />lager (beter) in B</li>
        <li><i style="background:#96a0aa" />ongeveer gelijk</li>
      </ul>
      <p v-if="!result" class="maphint">Klik op “Vergelijk” om het verschil per cel op de kaart te tonen.</p>
    </section>

    <p v-if="error" class="err">⚠️ {{ error }}</p>

    <div v-if="result" class="results">
      <div class="verdict-row">
        <span class="badge">{{ result.delta.feasibility_change }}</span>
        <span>Δ DrinkwaterDruk <strong>{{ signed(result.delta.score_avg_delta) }}</strong> ·
          Δ STOP-aandeel <strong>{{ signed(result.delta.stop_share_delta * 100, 0) }} pp</strong> ·
          {{ result.universe.n_cells.toLocaleString() }} cellen ({{ result.universe.base }})</span>
      </div>
      <p class="narrative">{{ result.delta.narrative_nl }}</p>

      <section class="attr">
        <h4>Bijdrage per factor (gemiddelde DrinkwaterDruk)</h4>
        <div v-for="f in result.factor_attribution" :key="f.factor" class="frow">
          <span class="fname">{{ f.factor_nl }}</span>
          <span class="fnums">{{ f.mean_a.toFixed(1) }} → {{ f.mean_b.toFixed(1) }}
            (<strong>{{ signed(f.delta) }}</strong>)</span>
          <span class="fbar"><i :class="{ up: f.delta > 0, down: f.delta < 0 }" :style="{ width: barWidth(f.share_of_change_pct) }" /></span>
          <span class="fshare">{{ signed(f.share_of_change_pct, 0) }}%</span>
        </div>
        <p class="note">{{ result.note_nl }}</p>
      </section>

      <section class="cells">
        <h4>Gevolgen per cel</h4>
        <p class="counts">
          <span class="worse">{{ result.cell_diff.n_worsened.toLocaleString() }} verslechterd</span> ·
          <span class="better">{{ result.cell_diff.n_improved.toLocaleString() }} verbeterd</span> ·
          {{ result.cell_diff.n_unchanged.toLocaleString() }} gelijk
        </p>
        <div v-if="result.cell_diff.transitions.length" class="trans">
          <span v-for="t in result.cell_diff.transitions" :key="t.from + t.to" class="chip">
            {{ VLABEL[t.from] || t.from }} → {{ VLABEL[t.to] || t.to }}: {{ t.n }}
          </span>
        </div>
        <table v-if="result.cell_diff.top_increases.length">
          <thead><tr><th>H3-cel</th><th>A</th><th>B</th><th>Δ</th><th>oordeel</th></tr></thead>
          <tbody>
            <tr v-for="c in result.cell_diff.top_increases" :key="c.h3_id">
              <td class="mono">{{ c.h3_id }}</td>
              <td>{{ c.score_a.toFixed(0) }}</td>
              <td>{{ c.score_b.toFixed(0) }}</td>
              <td><strong>{{ signed(c.delta, 0) }}</strong></td>
              <td>{{ VLABEL[c.klasse_a] || c.klasse_a }} → {{ VLABEL[c.klasse_b] || c.klasse_b }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </div>
</template>

<style scoped>
.cmp { height: 100%; overflow: auto; padding: 14px 18px; font-family: system-ui, sans-serif; color: #15242e; }
.head h3 { margin: 0; color: #0a4d68; }
.sub { margin: 2px 0 12px; color: #5a6b78; font-size: 13px; }
.controls { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.side { border: 1px solid #dce3e8; border-radius: 10px; padding: 10px 12px; background: #fafcfd; }
.lbl { width: 100%; font-weight: 600; color: #0a4d68; border: 1px solid #cfdde4; border-radius: 6px; padding: 6px 8px; margin-bottom: 8px; }
.side label { display: grid; grid-template-columns: 1.3fr 1.4fr auto; gap: 8px; align-items: center; font-size: 12px; margin: 5px 0; }
.side .k { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.actions { display: flex; gap: 12px; align-items: center; margin: 12px 0; }
.actions .base { font-size: 13px; color: #33485c; }
.actions select { margin-left: 6px; padding: 5px 8px; border: 1px solid #cfdde4; border-radius: 6px; }
.actions button { padding: 8px 16px; border: 1px solid #0a4d68; background: #0a4d68; color: #fff; border-radius: 8px; cursor: pointer; }
.actions button:disabled { opacity: 0.6; cursor: default; }
.mapsec { position: relative; margin: 6px 0 14px; }
.maptitle { font-size: 12.5px; font-weight: 600; color: #0a4d68; margin-bottom: 6px; }
.map { position: relative; height: 360px; border-radius: 8px; overflow: hidden; border: 1px solid #dce3e8; }
.mapsec .legend { position: absolute; right: 10px; bottom: 10px; background: #fff; padding: 6px 10px; border-radius: 6px; list-style: none; margin: 0; box-shadow: 0 1px 4px rgba(0,0,0,.12); }
.mapsec .legend li { display: flex; align-items: center; gap: 6px; font-size: 11.5px; }
.mapsec .legend i { width: 12px; height: 12px; border-radius: 2px; display: inline-block; }
.maphint { position: absolute; top: 40px; left: 50%; transform: translateX(-50%); background: rgba(255,255,255,.92); padding: 6px 12px; border-radius: 6px; font-size: 12.5px; color: #33485c; }
.err { color: #b3261e; }
.verdict-row { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; font-size: 13px; }
.badge { background: #0a4d68; color: #fff; padding: 4px 10px; border-radius: 8px; font-weight: 700; }
.narrative { font-size: 13.5px; color: #28323a; background: #eef4f7; padding: 10px 12px; border-radius: 8px; }
.attr, .cells { margin-top: 14px; }
h4 { margin: 0 0 8px; color: #0a4d68; }
.frow { display: grid; grid-template-columns: 1.1fr 1.6fr 2fr auto; gap: 10px; align-items: center; font-size: 12.5px; margin: 4px 0; }
.fname { font-weight: 600; }
.fbar { background: #eef2f5; border-radius: 5px; height: 12px; overflow: hidden; }
.fbar i { display: block; height: 100%; }
.fbar i.up { background: #dc3545; }
.fbar i.down { background: #28a745; }
.note { font-size: 11.5px; color: #6a7a86; margin-top: 8px; }
.counts { font-size: 13px; }
.counts .worse { color: #b3261e; font-weight: 600; }
.counts .better { color: #1a7f37; font-weight: 600; }
.trans { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
.chip { background: #fff3cd; border-radius: 6px; padding: 2px 8px; font-size: 11.5px; }
table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid #eef2f5; }
.mono { font-family: ui-monospace, monospace; font-size: 11px; color: #5a6b78; }
</style>
