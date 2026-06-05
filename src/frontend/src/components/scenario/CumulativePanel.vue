<script setup lang="ts">
// CumulativePanel.vue (Phase 5) — cumulative / multi-project overlay + "al vergund"
// layer. Stack several project demands plus operator-entered committed demand and
// see the combined verdict (the stapelingseffect that single-project checks miss).
import { reactive, ref } from "vue";

const VLABEL: Record<string, string> = { GO: "HAALBAAR", CAUTION: "RISICO", STOP: "NIET HAALBAAR" };
const knmi = ref("Hd");
const growth = ref("hoog");
const projects = reactive<any[]>([
  { name: "Woningbouw", kind: "development_units", amount: 20000 },
  { name: "Datacenter", kind: "datacenter_mw", amount: 50 },
]);
const committed = reactive<any[]>([{ label: "Reeds vergund (eigen invoer)", m3_day: 0 }]);
const result = ref<any>(null);
const loading = ref(false);

function addProject() { projects.push({ name: `Project ${projects.length + 1}`, kind: "development_units", amount: 5000 }); }
function addCommitted() { committed.push({ label: "Al vergund", m3_day: 0 }); }

async function run() {
  loading.value = true; result.value = null;
  const payload = {
    knmi_preset: knmi.value, growth_preset: growth.value,
    projects: projects.map((p) => ({ name: p.name, [p.kind]: Number(p.amount) })),
    committed: committed.filter((c) => Number(c.m3_day) > 0).map((c) => ({ label: c.label, m3_day: Number(c.m3_day) })),
  };
  try {
    const r = await fetch("/api/scenario/cumulative", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    result.value = r.ok ? await r.json() : { error: (await r.json()).detail || `Fout ${r.status}` };
  } catch {
    result.value = { error: "Kan de server niet bereiken." };
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="cum">
    <header><h2>➕ Stapeling — meerdere projecten + al vergund</h2>
      <p class="sub">Zie het gecombineerde effect dat losse toetsen missen. De al-vergund-laag is eigen invoer.</p>
    </header>

    <div class="controls">
      <label>KNMI <select v-model="knmi"><option v-for="k in ['B','Hn','Hd','Ln','Ld']" :key="k">{{ k }}</option></select></label>
      <label>Groei <select v-model="growth"><option v-for="g in ['laag','middel','hoog']" :key="g">{{ g }}</option></select></label>
    </div>

    <div class="cols">
      <div class="col">
        <h4>Projecten <button class="add" @click="addProject">+ project</button></h4>
        <div v-for="(p, i) in projects" :key="i" class="row">
          <input v-model="p.name" class="nm" />
          <select v-model="p.kind">
            <option value="development_units">woningen</option>
            <option value="datacenter_mw">datacenter MW</option>
            <option value="m3_day">m³/dag</option>
          </select>
          <input v-model.number="p.amount" type="number" class="amt" />
        </div>
      </div>
      <div class="col">
        <h4>Al vergund / in behandeling <button class="add" @click="addCommitted">+ regel</button></h4>
        <div v-for="(c, i) in committed" :key="i" class="row">
          <input v-model="c.label" class="nm" />
          <input v-model.number="c.m3_day" type="number" class="amt" placeholder="m³/dag" />
        </div>
      </div>
    </div>

    <button class="run" :disabled="loading" @click="run">{{ loading ? "Doorrekenen…" : "Stapeling doorrekenen" }}</button>

    <div v-if="result && result.error" class="err">⚠️ {{ result.error }}</div>
    <div v-else-if="result" class="out">
      <div class="combined" :class="result.combined.feasibility_class.toLowerCase()">
        <strong>{{ VLABEL[result.combined.feasibility_class] }}</strong>
        gecombineerd · score {{ Math.round(result.combined.score_avg) }}/100 ·
        {{ Math.round(result.combined.stop_share * 100) }}% STOP-cellen
      </div>
      <p class="narr">{{ result.narrative_nl }}</p>
      <table class="brk">
        <thead><tr><th>Project</th><th>woning-equiv.</th><th>alleen</th></tr></thead>
        <tbody>
          <tr v-for="(p, i) in result.projects" :key="i">
            <td>{{ p.name }}</td><td>{{ Math.round(p.homes_equiv).toLocaleString("nl-NL") }}</td>
            <td><span class="v" :class="(p.alone_verdict||'').toLowerCase()">{{ VLABEL[p.alone_verdict] || p.alone_verdict }}</span></td>
          </tr>
          <tr class="committedrow">
            <td>Al vergund (eigen invoer)</td>
            <td>{{ Math.round(result.committed_homes_equiv).toLocaleString("nl-NL") }}</td><td>—</td>
          </tr>
        </tbody>
      </table>
      <p class="disc">⚠️ {{ result.disclaimer_nl }}</p>
    </div>
  </section>
</template>

<style scoped>
.cum { height: 100%; overflow: auto; padding: 18px 22px; background: #f6f8fa; }
.cum h2 { margin: 0; color: #0a4d68; font-size: 20px; }
.sub { margin: 2px 0 14px; color: #5b6b76; font-size: 13px; }
.controls { display: flex; gap: 16px; margin-bottom: 12px; }
.controls label, .col label { font-size: 12px; color: #5b6b76; }
select, input { padding: 6px 8px; border: 1px solid #cfdde4; border-radius: 7px; font-size: 13px; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.col { background: #fff; border: 1px solid #e1e8ec; border-radius: 12px; padding: 12px 14px; }
.col h4 { margin: 0 0 8px; font-size: 13px; display: flex; justify-content: space-between; align-items: center; }
.add { font-size: 11px; border: 1px solid #0a4d68; background: #fff; color: #0a4d68; border-radius: 6px; padding: 2px 8px; cursor: pointer; }
.row { display: flex; gap: 6px; margin: 6px 0; }
.nm { flex: 1; } .amt { width: 110px; }
.run { margin: 14px 0; padding: 9px 16px; border: none; border-radius: 9px; background: #0a4d68; color: #fff; font-size: 14px; cursor: pointer; }
.run:disabled { opacity: .5; }
.combined { padding: 10px 14px; border-radius: 8px; font-size: 14px; }
.combined.go { background: #e7f4ec; } .combined.caution { background: #fdf6e3; } .combined.stop { background: #fce9e7; }
.narr { font-size: 13px; color: #15242e; }
.brk { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e1e8ec; border-radius: 10px; overflow: hidden; font-size: 13px; }
.brk th, .brk td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #eef2f4; }
.brk th { background: #f5f8fa; font-size: 11px; text-transform: uppercase; color: #5b6b76; }
.committedrow td { color: #5b6b76; font-style: italic; }
.v { font-weight: 700; font-size: 11px; padding: 2px 7px; border-radius: 5px; }
.v.go { background: #e7f4ec; color: #1a7f37; } .v.caution { background: #fdf6e3; color: #9a6700; } .v.stop { background: #fce9e7; color: #b3261e; }
.disc { font-size: 11.5px; color: #5b6b76; font-style: italic; }
.err { color: #b3261e; margin-top: 10px; }
</style>
