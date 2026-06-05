<!-- ScenarioPanel.vue — scenario engine UI (design doc v3, §16).
     DrinkwaterDruk H3 overlay (deck.gl H3HexagonLayer via MapboxOverlay over
     MapLibre), GO/CAUTION/STOP verdict, reasoning trail (Insight), assumption
     sliders that re-run, and a with/without-shock comparison. Consumes
     /api/scenario/run via useScenarioSSE. deck.gl v9 + maplibre-gl v5. -->
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useScenarioSSE, type Overlay } from "../../composables/useScenarioSSE";

const COLORS: Record<string, [number, number, number]> = {
  GO: [40, 167, 69], CAUTION: [255, 193, 7], STOP: [220, 53, 69],
};
const VLABEL: Record<string, string> = { GO: "HAALBAAR", CAUTION: "RISICO", STOP: "NIET HAALBAAR" };

const question = ref("Wat als de Hollandse IJssel-inname verzilt onder KNMI Hd in 2040?");
const verdict = ref(""); const score = ref(0); const stopShare = ref(0);
const steps = reactive<any[]>([]); const official = ref<any>(null); const delta = ref<any>(null);
const cardMeta = ref<{ av: string; vs: string } | null>(null);
const loading = ref(false);
const assumptions = reactive<Record<string, number>>({
  knmi_dryness_multiplier: 1.8, weight_salinity: 0.4, weight_demand: 0.3,
  weight_flood: 0.2, weight_protection: 0.1,
});

const { run } = useScenarioSSE();
const mapEl = ref<HTMLDivElement | null>(null);
let overlay: MapboxOverlay | null = null;

function renderOverlay(overlays: Overlay[]) {
  const ov = overlays.find((o) => o.layer_id === "drinkwaterdruk_h3");
  if (!ov || !overlay) return;
  overlay.setProps({
    layers: [new H3HexagonLayer({
      id: "drinkwaterdruk_h3",
      data: ov.cells,
      pickable: true,
      extruded: false,
      getHexagon: (d: any) => d.h3_id,
      getFillColor: (d: any) => [...(COLORS[d.klasse] ?? [120, 120, 120]), 190] as [number, number, number, number],
      getLineColor: [255, 255, 255, 30],
      lineWidthMinPixels: 0.5,
    })],
  });
}

async function runScenario(compare = false) {
  loading.value = true; steps.length = 0; delta.value = null;
  await run(
    { question: question.value, compare, assumptions: { ...assumptions },
      baseline: { knmi_dryness_multiplier: 1.0 }, shock: { knmi_dryness_multiplier: 1.8 } },
    {
      onFeasibility: (f) => { verdict.value = f.feasibility_class; score.value = f.score_avg; stopShare.value = f.stop_share; },
      onReasoning: (s) => steps.push(s),
      onOfficial: (o) => (official.value = o),
      onCard: (card) => (cardMeta.value = { av: card.assumptions_version, vs: card.validation_status }),
      onMapData: renderOverlay,
      onDelta: (d) => (delta.value = d),
      onError: (m) => { verdict.value = "FOUT"; console.error(m); },
      onDone: () => (loading.value = false),
    },
  );
}

const uncertainty = ref<any>(null);
async function runUncertainty() {
  uncertainty.value = { loading: true };
  try {
    const r = await fetch("/api/scenario/uncertainty", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question.value }),
    });
    uncertainty.value = r.ok ? await r.json() : { error: `Serverfout (${r.status})` };
  } catch {
    uncertainty.value = { error: "Kan de server niet bereiken." };
  }
}

onMounted(() => {
  const map = new maplibregl.Map({
    container: mapEl.value!, style: "https://demotiles.maplibre.org/style.json",
    center: [4.5, 51.92], zoom: 8,
  });
  overlay = new MapboxOverlay({ interleaved: true, layers: [] });
  map.addControl(overlay as any);
  map.on("load", () => runScenario(false));
});
</script>

<template>
  <div class="scenario-panel">
    <header class="bar">
      <input v-model="question" class="q" placeholder="Stel een what-if vraag…" />
      <button :disabled="loading" @click="runScenario(false)">Bereken</button>
      <button :disabled="loading" @click="runScenario(true)">Vergelijk met/zonder schok</button>
      <button :disabled="loading" @click="runUncertainty">Robuustheid (KNMI-band)</button>
    </header>

    <div class="verdict" :class="verdict.toLowerCase()">
      <strong>{{ VLABEL[verdict] || verdict }}</strong>
      <span>DrinkwaterDruk {{ score.toFixed(0) }}/100 · {{ (stopShare * 100).toFixed(0) }}% NIET-HAALBAAR-cellen</span>
    </div>

    <div v-if="uncertainty" class="robust">
      <template v-if="uncertainty.loading">Robuustheid testen over de vijf KNMI-scenario's…</template>
      <template v-else-if="uncertainty.error" class="err">⚠️ {{ uncertainty.error }}</template>
      <template v-else>
        <strong>Robuustheid:</strong> {{ uncertainty.headline_nl }} ·
        score-band {{ uncertainty.score_min }}–{{ uncertainty.score_max }} ·
        <span class="band">
          <span v-for="(v, p) in uncertainty.presets" :key="p" class="chip" :class="v.verdict.toLowerCase()">{{ p }}: {{ VLABEL[v.verdict] || v.verdict }}</span>
        </span>
      </template>
    </div>

    <div class="body">
      <div class="map-wrap">
        <div class="map-title">Kaart toont: DrinkwaterDruk per H3-cel (0–100) — oordeel: {{ VLABEL[verdict] || "—" }}</div>
        <div ref="mapEl" class="map" />
        <ul class="legend">
          <li><i style="background:#28a745" />HAALBAAR</li>
          <li><i style="background:#ffc107" />RISICO</li>
          <li><i style="background:#dc3545" />NIET HAALBAAR</li>
        </ul>
      </div>

      <aside class="side">
        <section class="sliders">
          <h4>Aannames (beleidsmatige schatting)</h4>
          <label v-for="(_, key) in assumptions" :key="key">
            <span class="k">{{ key }}</span>
            <input type="range" min="0" max="2" step="0.05" v-model.number="assumptions[key]" @change="runScenario(false)" />
            <span class="v">{{ assumptions[key].toFixed(2) }}</span>
          </label>
        </section>

        <section v-if="delta" class="delta">
          <h4>Vergelijking</h4>
          <p><strong>{{ delta.feasibility_change }}</strong> · Δscore {{ delta.score_avg_delta }}</p>
          <p class="narrative">{{ delta.narrative_nl }}</p>
        </section>

        <section class="insight">
          <h4>Redeneerproces</h4>
          <ol><li v-for="s in steps" :key="s.step_nr"><strong>{{ s.label_nl }}</strong> — {{ s.description_nl }}</li></ol>
        </section>

        <section v-if="official" class="official">
          <h4>🏛️ Officieel beleid</h4>
          <ul><li v-for="d in official.documents" :key="d.url"><a :href="d.url" target="_blank" rel="noopener noreferrer">{{ d.title }}</a></li></ul>
          <p class="disclaimer">⚠️ {{ official.disclaimer_nl }}</p>
        </section>

        <section v-if="cardMeta" class="provenance">
          <h4>🔖 Herkomst &amp; validatie</h4>
          <p><strong>Aannameversie:</strong> {{ cardMeta.av }}</p>
          <p class="disclaimer">{{ cardMeta.vs }}</p>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.scenario-panel { display: flex; flex-direction: column; height: 100%; font-family: system-ui, sans-serif; }
.bar { display: flex; gap: 8px; padding: 10px; }
.q { flex: 1; padding: 8px; border: 1px solid #cdd8e3; border-radius: 6px; }
.bar button { padding: 8px 12px; border: 1px solid #0a4d68; background: #0a4d68; color: #fff; border-radius: 6px; cursor: pointer; }
.verdict { margin: 0 10px 8px; padding: 10px 14px; border-radius: 8px; display: flex; gap: 12px; align-items: baseline; }
.verdict.go { background: #d4edda } .verdict.caution { background: #fff3cd } .verdict.stop { background: #f8d7da }
.robust { margin: 0 10px 8px; padding: 8px 12px; border-radius: 8px; background: #eef4f7; font-size: 12.5px; color: #15242e; }
.robust .band { display: inline-flex; flex-wrap: wrap; gap: 4px; }
.robust .chip { font-size: 11px; font-weight: 600; border-radius: 5px; padding: 1px 6px; }
.robust .chip.go { background: #e7f4ec; color: #1a7f37 } .robust .chip.caution { background: #fdf6e3; color: #9a6700 } .robust .chip.stop { background: #fce9e7; color: #b3261e }
.body { flex: 1; display: grid; grid-template-columns: 1fr 360px; gap: 10px; padding: 0 10px 10px; min-height: 0; }
.map-wrap { position: relative; border-radius: 8px; overflow: hidden; }
.map { position: absolute; inset: 0; }
.map-title { position: absolute; top: 8px; left: 8px; right: 8px; z-index: 5; background: rgba(255,255,255,.93); padding: 6px 11px; border-radius: 6px; font-size: 12.5px; font-weight: 600; color: #0a4d68; box-shadow: 0 1px 4px rgba(0,0,0,.12); }
.legend { position: absolute; right: 8px; bottom: 8px; background: #fff; padding: 6px 10px; border-radius: 6px; list-style: none; margin: 0; }
.legend li { display: flex; align-items: center; gap: 6px; font-size: 12px; }
.legend i { width: 12px; height: 12px; border-radius: 2px; display: inline-block; }
.side { overflow: auto; display: flex; flex-direction: column; gap: 12px; }
.sliders label { display: grid; grid-template-columns: 1fr 1.4fr auto; gap: 8px; align-items: center; font-size: 12px; margin: 4px 0; }
.sliders .k { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.narrative { font-size: 13px; color: #33485c; }
.disclaimer { color: #666; font-size: 12px; }
h4 { margin: 0 0 6px; }
</style>
