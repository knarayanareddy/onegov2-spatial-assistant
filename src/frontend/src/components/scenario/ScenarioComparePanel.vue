<!-- ScenarioComparePanel.vue — detailed A/B scenario comparison (design doc §16 ext).
     Compares two assumption sets over a shared H3 universe via POST
     /api/scenario/compare, then shows the verdict change, per-factor attribution
     (verzilting/overstroming/bescherming/vraag) and a per-cell diff with verdict
     transitions. Plain JSON endpoint (no SSE). -->
<script setup lang="ts">
import { reactive, ref } from "vue";

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
    }
  } catch {
    error.value = "Kan de server niet bereiken.";
  } finally {
    loading.value = false;
  }
}

function pct(x: number): string {
  return `${(x * 100).toFixed(0)}%`;
}
function signed(x: number, digits = 1): string {
  return `${x > 0 ? "+" : ""}${x.toFixed(digits)}`;
}
function barWidth(share: number): string {
  return `${Math.min(100, Math.abs(share))}%`;
}
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
