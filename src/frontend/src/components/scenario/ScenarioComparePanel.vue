<!-- ScenarioComparePanel.vue — A/B comparison with persistent full-height map (right column). -->
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
  { key: "weight_salinity",          label: "Gewicht verzilting" },
  { key: "weight_demand",            label: "Gewicht vraag" },
  { key: "weight_flood",             label: "Gewicht overstroming" },
  { key: "weight_protection",        label: "Gewicht bescherming" },
];

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
    if (!r.ok) { error.value = `Serverfout (${r.status})`; }
    else {
      result.value = await r.json();
      renderOverlay(result.value?.overlay?.cells ?? []);
    }
  } catch {
    error.value = "Kan de server niet bereiken.";
  } finally { loading.value = false; }
}

function signed(x: number, digits = 1) { return `${x > 0 ? "+" : ""}${x.toFixed(digits)}`; }
function barWidth(share: number)       { return `${Math.min(100, Math.abs(share))}%`; }

// ---- map ----
const mapEl = ref<HTMLDivElement | null>(null);
let overlay: MapboxOverlay | null = null;
let map: maplibregl.Map | null = null;

function deltaColor(d: number): [number, number, number, number] {
  const x = Math.max(-50, Math.min(50, d)) / 50;
  if (x >  0.02) return [220, 53,  69, Math.round(80 + 170 * x)];
  if (x < -0.02) return [40,  167, 69, Math.round(80 + 170 * -x)];
  return [150, 160, 170, 80];
}

// Colour per verdict
const VERDICT_COLOR: Record<string, string> = { STOP:"#dc3545", CAUTION:"#e6a817", GO:"#28a745" };

function tooltipHtml(o: any, labelA: string, labelB: string): string {
  const sign  = o.delta > 0 ? "+" : "";
  const trend = o.delta >  1 ? "<span style='color:#dc3545;font-weight:700'>⬆ verslechterd</span>"
              : o.delta < -1 ? "<span style='color:#28a745;font-weight:700'>⬇ verbeterd</span>"
              : "<span style='color:#888'>≈ gelijk</span>";
  const va = o.verdict_a_nl ?? o.verdict_a ?? "—";
  const vb = o.verdict_b_nl ?? o.verdict_b ?? "—";
  const ca = VERDICT_COLOR[o.verdict_a ?? ""] ?? "#888";
  const cb = VERDICT_COLOR[o.verdict_b ?? ""] ?? "#888";
  const bedrijf  = o.drinkwaterbedrijf ?? "—";
  const verzilt  = o.verzilting ? "Ja (>200mg/l)" : "Nee";
  const zes      = o.in_zes_uur_zone ? "Binnen zone" : "Buiten zone";
  const overs    = o.overstromingsrisico ?? "—";
  const locTitle = o.gemeentenaam && o.gemeentenaam !== "—"
    ? `${o.gemeentenaam}${o.buurtnaam && o.buurtnaam !== "—" ? " · " + o.buurtnaam : ""}`
    : o.h3_id;
  const locSub = o.regio && o.regio !== "—" ? `${o.provincie ?? "Zuid-Holland"} · ${o.regio}` : (o.provincie ?? "Zuid-Holland");
  return `<div style="font:12.5px/1.5 system-ui,sans-serif;min-width:280px">
    <div style="background:#0a4d68;color:#fff;padding:8px 12px;border-radius:6px 6px 0 0">
      <div style="font-weight:700;font-size:13px">${locTitle}</div>
      <div style="font-size:11px;opacity:.8;margin-top:1px">${locSub}</div>
    </div>
    <div style="padding:10px 12px;display:flex;flex-direction:column;gap:5px">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:4px">
        <div style="background:#f4f7f9;border-radius:6px;padding:7px 10px;text-align:center">
          <div style="font-size:10.5px;color:#666;margin-bottom:2px">${labelA}</div>
          <div style="font-size:15px;font-weight:700">${o.score_a.toFixed(1)}<span style="font-size:11px;color:#888">/100</span></div>
          <div style="font-size:11px;font-weight:700;color:${ca}">${va}</div>
        </div>
        <div style="background:#f4f7f9;border-radius:6px;padding:7px 10px;text-align:center">
          <div style="font-size:10.5px;color:#666;margin-bottom:2px">${labelB}</div>
          <div style="font-size:15px;font-weight:700">${o.score_b.toFixed(1)}<span style="font-size:11px;color:#888">/100</span></div>
          <div style="font-size:11px;font-weight:700;color:${cb}">${vb}</div>
        </div>
      </div>
      <div style="text-align:center;font-size:12.5px">Verschil: <b>${sign}${o.delta.toFixed(1)} punt</b> — ${trend}</div>
      <hr style="border:none;border-top:1px solid #e0e7ee;margin:4px 0"/>
      <table style="border-collapse:collapse;font-size:11.5px;width:100%">
        <tr><td style="color:#666;padding:2px 8px 2px 0">Drinkwaterbedrijf</td><td><b>${bedrijf}</b></td></tr>
        <tr><td style="color:#666;padding:2px 8px 2px 0">Verzilting (>200mg/l)</td><td>${verzilt}</td></tr>
        <tr><td style="color:#666;padding:2px 8px 2px 0">Overstromingsrisico</td><td>${overs}</td></tr>
        <tr><td style="color:#666;padding:2px 8px 2px 0">6-uur beschermingszone</td><td>${zes}</td></tr>
      </table>
    </div>
  </div>`;
}

function fitToCells(cells: any[]) {
  if (!map || !cells.length) return;
  let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;
  for (const c of cells) {
    const [lat, lng] = cellToLatLng(c.h3_id);
    if (lat < minLat) minLat = lat; if (lat > maxLat) maxLat = lat;
    if (lng < minLng) minLng = lng; if (lng > maxLng) maxLng = lng;
  }
  map.fitBounds([[minLng, minLat], [maxLng, maxLat]], { padding: 50, maxZoom: 12, duration: 700 });
}

function renderOverlay(cells: any[]) {
  if (!overlay) return;
  overlay.setProps({
    layers: [new H3HexagonLayer({
      id: "compare_delta_h3",
      data: cells,
      pickable: true,
      extruded: false,
      coverage: 0.92,
      getHexagon:   (d: any) => d.h3_id,
      getFillColor: (d: any) => deltaColor(d.delta),
      getLineColor: [255, 255, 255, 80],
      lineWidthMinPixels: 1,
    })],
  });
  fitToCells(cells);
}

onMounted(() => {
  if (!mapEl.value) return;
  map = new maplibregl.Map({
    container: mapEl.value,
    style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    center: [4.5, 51.92], zoom: 8,
  });
  overlay = new MapboxOverlay({
    interleaved: true, layers: [],
    getTooltip: ({ object }: any) => {
      if (!object) return null;
      const la = result.value?.overlay?.label_a ?? "Scenario A";
      const lb = result.value?.overlay?.label_b ?? "Scenario B";
      return { html: tooltipHtml(object, la, lb), style: { background:"#fff", border:"1px solid #dce3e8", borderRadius:"8px", boxShadow:"0 4px 16px rgba(0,0,0,.18)", padding:"0", overflow:"hidden" } };
    },
  });
  map.addControl(overlay as any);
});
</script>

<template>
  <div class="cmp">
    <!-- Two-column: left = controls + results, right = persistent map -->
    <div class="layout">

      <!-- LEFT: controls + results -->
      <div class="left">
        <header class="head">
          <h3>⚖️ Scenario's vergelijken</h3>
          <p class="sub">Twee aannamesets over hetzelfde H3-gebied — gevolgen per factor en per cel.</p>
        </header>

        <!-- Scenario A/B sliders -->
        <div class="controls">
          <div class="side">
            <input v-model="labelA" class="lbl" placeholder="Label scenario A" />
            <label v-for="kn in KNOBS" :key="'a-'+kn.key">
              <span class="k">{{ kn.label }}</span>
              <input type="range" min="0" max="2" step="0.05" v-model.number="a[kn.key]" />
              <span class="v">{{ (a[kn.key] ?? 0).toFixed(2) }}</span>
            </label>
          </div>
          <div class="side">
            <input v-model="labelB" class="lbl" placeholder="Label scenario B" />
            <label v-for="kn in KNOBS" :key="'b-'+kn.key">
              <span class="k">{{ kn.label }}</span>
              <input type="range" min="0" max="2" step="0.05" v-model.number="b[kn.key]" />
              <span class="v">{{ (b[kn.key] ?? 0).toFixed(2) }}</span>
            </label>
          </div>
        </div>

        <div class="actions">
          <label class="base-lbl">Universum:
            <select v-model="base">
              <option value="salinity">Verzilting (intake)</option>
              <option value="populated">Bebouwd (vraag)</option>
            </select>
          </label>
          <button :disabled="loading" @click="compare">
            {{ loading ? "Bezig…" : "▶ Vergelijk" }}
          </button>
        </div>

        <p v-if="error" class="err">⚠️ {{ error }}</p>

        <!-- Results -->
        <div v-if="result" class="results">
          <div class="verdict-row">
            <span class="badge">{{ result.delta.feasibility_change }}</span>
            <span>Δ score <strong>{{ signed(result.delta.score_avg_delta) }}</strong> ·
              Δ STOP <strong>{{ signed(result.delta.stop_share_delta * 100, 0) }} pp</strong> ·
              {{ result.universe.n_cells.toLocaleString() }} cellen</span>
          </div>
          <p class="narrative">{{ result.delta.narrative_nl }}</p>

          <section class="attr">
            <h4>Bijdrage per factor</h4>
            <div v-for="f in result.factor_attribution" :key="f.factor" class="frow">
              <span class="fname">{{ f.factor_nl }}</span>
              <span class="fnums">{{ f.mean_a.toFixed(1) }} → {{ f.mean_b.toFixed(1) }} (<strong>{{ signed(f.delta) }}</strong>)</span>
              <span class="fbar"><i :class="{ up: f.delta > 0, down: f.delta < 0 }" :style="{ width: barWidth(f.share_of_change_pct) }" /></span>
              <span class="fshare">{{ signed(f.share_of_change_pct, 0) }}%</span>
            </div>
          </section>

          <section class="cells">
            <h4>Gevolgen per cel</h4>
            <p class="counts">
              <span class="worse">{{ result.cell_diff.n_worsened.toLocaleString() }} verslechterd</span> ·
              <span class="better">{{ result.cell_diff.n_improved.toLocaleString() }} verbeterd</span> ·
              {{ result.cell_diff.n_unchanged.toLocaleString() }} gelijk
            </p>
            <div v-if="result.cell_diff.transitions.length" class="trans">
              <span v-for="t in result.cell_diff.transitions" :key="t.from+t.to" class="chip">
                {{ VLABEL[t.from]||t.from }} → {{ VLABEL[t.to]||t.to }}: {{ t.n }}
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
                  <td>{{ VLABEL[c.klasse_a]||c.klasse_a }} → {{ VLABEL[c.klasse_b]||c.klasse_b }}</td>
                </tr>
              </tbody>
            </table>
          </section>
        </div>
      </div>

      <!-- RIGHT: persistent full-height map -->
      <div class="map-col">
        <div class="map-title">
          Kaart: Δ DrinkwaterDruk per H3-cel (A → B)
          <span v-if="result"> · {{ result.universe.n_cells.toLocaleString() }} cellen</span>
        </div>
        <div ref="mapEl" class="map" />
        <ul class="legend">
          <li><i class="red" />hoger (slechter) in B</li>
          <li><i class="green" />lager (beter) in B</li>
          <li><i class="grey" />ongeveer gelijk</li>
        </ul>
        <p v-if="!result" class="maphint">Klik "▶ Vergelijk" om de kaart te vullen</p>
      </div>

    </div>
  </div>
</template>

<style scoped>
.cmp { height: 100%; overflow: hidden; font-family: system-ui, sans-serif; color: #15242e; }
.layout { display: grid; grid-template-columns: 420px 1fr; height: 100%; min-height: 0; }

/* LEFT */
.left { overflow-y: auto; padding: 14px 16px; display: flex; flex-direction: column; gap: 12px; border-right: 1px solid #dce3e8; }
.head h3 { margin: 0; color: #0a4d68; font-size: 15px; }
.sub { margin: 2px 0 0; color: #5a6b78; font-size: 12px; }
.controls { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.side { border: 1px solid #dce3e8; border-radius: 8px; padding: 8px 10px; background: #fafcfd; }
.lbl { width: 100%; font-weight: 600; color: #0a4d68; border: 1px solid #cfdde4; border-radius: 5px; padding: 5px 7px; margin-bottom: 6px; font-size: 12px; }
.side label { display: grid; grid-template-columns: 1.2fr 1.4fr auto; gap: 6px; align-items: center; font-size: 11.5px; margin: 4px 0; }
.side .k { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.side .v { font-size: 11px; color: #0a4d68; font-weight: 600; }
.actions { display: flex; gap: 10px; align-items: center; }
.base-lbl { font-size: 12.5px; color: #33485c; }
.base-lbl select { margin-left: 5px; padding: 4px 7px; border: 1px solid #cfdde4; border-radius: 5px; font-size: 12px; }
.actions button { padding: 8px 18px; border: none; background: #0a4d68; color: #fff; border-radius: 7px; cursor: pointer; font-weight: 700; font-size: 13px; }
.actions button:disabled { opacity: 0.55; cursor: default; }
.err { color: #b3261e; font-size: 12.5px; }
.results { display: flex; flex-direction: column; gap: 12px; }
.verdict-row { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; font-size: 12.5px; }
.badge { background: #0a4d68; color: #fff; padding: 3px 10px; border-radius: 7px; font-weight: 700; font-size: 12px; }
.narrative { font-size: 12.5px; color: #28323a; background: #eef4f7; padding: 8px 11px; border-radius: 7px; line-height: 1.45; }
.attr, .cells { }
h4 { margin: 0 0 6px; color: #0a4d68; font-size: 12.5px; }
.frow { display: grid; grid-template-columns: 1.1fr 1.6fr 2fr auto; gap: 8px; align-items: center; font-size: 11.5px; margin: 3px 0; }
.fname { font-weight: 600; }
.fbar { background: #eef2f5; border-radius: 4px; height: 10px; overflow: hidden; }
.fbar i { display: block; height: 100%; border-radius: 4px; }
.fbar i.up { background: #dc3545; } .fbar i.down { background: #28a745; }
.fshare { font-size: 11px; font-weight: 600; }
.counts { font-size: 12px; margin-bottom: 6px; }
.worse { color: #b3261e; font-weight: 600; } .better { color: #1a7f37; font-weight: 600; }
.trans { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 6px; }
.chip { background: #fff3cd; border-radius: 5px; padding: 2px 7px; font-size: 11px; }
table { width: 100%; border-collapse: collapse; font-size: 11.5px; }
th, td { text-align: left; padding: 4px 7px; border-bottom: 1px solid #eef2f5; }
th { background: #f4f7f9; font-size: 11px; }
.mono { font-family: ui-monospace, monospace; font-size: 10.5px; color: #5a6b78; }

/* RIGHT map column */
.map-col { position: relative; display: flex; flex-direction: column; }
.map-title { position: absolute; top: 10px; left: 10px; right: 10px; z-index: 5; background: rgba(255,255,255,.94); padding: 6px 11px; border-radius: 7px; font-size: 12.5px; font-weight: 600; color: #0a4d68; box-shadow: 0 1px 4px rgba(0,0,0,.12); }
.map { flex: 1; width: 100%; }
.legend { position: absolute; right: 10px; bottom: 10px; background: #fff; padding: 7px 11px; border-radius: 7px; list-style: none; margin: 0; box-shadow: 0 2px 6px rgba(0,0,0,.14); z-index: 5; }
.legend li { display: flex; align-items: center; gap: 7px; font-size: 12px; margin: 3px 0; }
.legend i { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }
.legend i.red   { background: #dc3545; }
.legend i.green { background: #28a745; }
.legend i.grey  { background: #96a0aa; }
.maphint { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); background: rgba(255,255,255,.93); padding: 8px 14px; border-radius: 7px; font-size: 12.5px; color: #33485c; z-index: 5; text-align: center; }
</style>
