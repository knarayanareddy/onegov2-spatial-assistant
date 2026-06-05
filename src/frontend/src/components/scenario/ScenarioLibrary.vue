<script setup lang="ts">
// ScenarioLibrary.vue (Phase 5) — "Opgeslagen Scenario's". Browseable list of
// saved scenarios with stable shareable URLs, plus a "Verifieer berekening"
// button that re-runs a scenario on current data and reports match + drift.
import { onMounted, reactive, ref } from "vue";

interface Row {
  scenario_id: string; question_nl: string; scenario_type: string;
  feasibility_class: string; score_avg: number; created_at: string; stable_url: string;
}
const VLABEL: Record<string, string> = { GO: "HAALBAAR", CAUTION: "RISICO", STOP: "NIET HAALBAAR" };

const rows = ref<Row[]>([]);
const loading = ref(true);
const verify = reactive<Record<string, any>>({});

async function load() {
  loading.value = true;
  try {
    const r = await fetch("/api/scenario");
    rows.value = r.ok ? (await r.json()).scenarios ?? [] : [];
  } finally {
    loading.value = false;
  }
}
async function verifyOne(id: string) {
  verify[id] = { loading: true };
  try {
    const r = await fetch(`/api/scenario/${id}/verify`);
    verify[id] = r.ok ? await r.json() : { error: `Fout ${r.status}` };
  } catch {
    verify[id] = { error: "Kan niet verifiëren" };
  }
}
onMounted(load);
</script>

<template>
  <section class="lib">
    <header class="lib__head">
      <h2>🗂️ Opgeslagen scenario's</h2>
      <button class="refresh" @click="load">Vernieuwen</button>
    </header>
    <p v-if="loading" class="muted">Laden…</p>
    <p v-else-if="!rows.length" class="muted">Nog geen scenario's berekend.</p>
    <table v-else class="tbl">
      <thead><tr><th>Vraag</th><th>Oordeel</th><th>Score</th><th>Aangemaakt</th><th></th></tr></thead>
      <tbody>
        <template v-for="r in rows" :key="r.scenario_id">
          <tr>
            <td>
              <a :href="r.stable_url" target="_blank" rel="noopener noreferrer">{{ r.question_nl || r.scenario_id.slice(0, 8) }}</a>
              <div class="sid">{{ r.scenario_type }} · {{ r.scenario_id.slice(0, 8) }}</div>
            </td>
            <td><span class="v" :class="r.feasibility_class.toLowerCase()">{{ VLABEL[r.feasibility_class] || r.feasibility_class }}</span></td>
            <td>{{ Math.round(r.score_avg) }}/100</td>
            <td class="muted">{{ (r.created_at || "").slice(0, 16).replace("T", " ") }}</td>
            <td><button class="vbtn" @click="verifyOne(r.scenario_id)">Verifieer</button></td>
          </tr>
          <tr v-if="verify[r.scenario_id]">
            <td colspan="5" class="vresult">
              <span v-if="verify[r.scenario_id].loading">Herberekenen…</span>
              <span v-else-if="verify[r.scenario_id].error" class="err">{{ verify[r.scenario_id].error }}</span>
              <span v-else>
                <strong :class="verify[r.scenario_id].matches ? 'ok' : 'warn'">
                  {{ verify[r.scenario_id].matches ? "✓ Identiek herberekend" : "⚠️ Afwijking" }}
                </strong>
                — {{ verify[r.scenario_id].note_nl }}
                <template v-if="verify[r.scenario_id].dataset_drift && verify[r.scenario_id].dataset_drift.length">
                  · {{ verify[r.scenario_id].dataset_drift.length }} dataset(s) gewijzigd
                </template>
              </span>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.lib { height: 100%; overflow: auto; padding: 18px 22px; background: #f6f8fa; }
.lib__head { display: flex; justify-content: space-between; align-items: center; }
.lib__head h2 { margin: 0; color: #0a4d68; font-size: 20px; }
.refresh { padding: 6px 12px; border: 1px solid #0a4d68; background: #fff; color: #0a4d68; border-radius: 8px; cursor: pointer; }
.muted { color: #5b6b76; }
.tbl { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e1e8ec; border-radius: 12px; overflow: hidden; margin-top: 12px; font-size: 13px; }
.tbl th, .tbl td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #eef2f4; vertical-align: top; }
.tbl th { background: #f5f8fa; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: #5b6b76; }
.sid { font-size: 11px; color: #5b6b76; margin-top: 2px; }
.v { font-weight: 700; font-size: 11.5px; padding: 2px 8px; border-radius: 6px; }
.v.go { background: #e7f4ec; color: #1a7f37; } .v.caution { background: #fdf6e3; color: #9a6700; } .v.stop { background: #fce9e7; color: #b3261e; }
.vbtn { padding: 5px 10px; border: 1px solid #0a4d68; background: #0a4d68; color: #fff; border-radius: 7px; cursor: pointer; font-size: 12px; }
.vresult { background: #f1f6f9; font-size: 12.5px; }
.vresult .ok { color: #1a7f37; } .vresult .warn { color: #9a6700; } .vresult .err { color: #b3261e; }
</style>
