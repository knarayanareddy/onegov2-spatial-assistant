<script setup lang="ts">
// KennisbasisPanel.vue (Phase 5) — "Wat weet dit systeem?" Always-accessible
// inventory of every loaded dataset, its publisher/source link, column count and
// freshness date. Closes the glanceable half of the intuition pointer.
import { onMounted, ref } from "vue";

interface Tbl { name: string; columns: number; last_updated: string | null; empty: boolean }
interface Theme { theme: string; label: string; publisher: string; url: string; voorbeeldvragen: string[]; tables: Tbl[] }

const themes = ref<Theme[]>([]);
const note = ref("");
const loading = ref(true);

onMounted(async () => {
  try {
    const r = await fetch("/api/kennisbasis");
    if (r.ok) {
      const j = await r.json();
      themes.value = j.themes ?? [];
      note.value = j.note_nl ?? "";
    }
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="kb">
    <header class="kb__head">
      <h2>📚 Kennisbasis — wat weet dit systeem?</h2>
      <p class="sub">{{ note || "Elke geladen dataset, met bron en actualiteit." }}</p>
    </header>
    <p v-if="loading" class="muted">Laden…</p>
    <div class="kb__grid">
      <article v-for="t in themes" :key="t.theme" class="theme">
        <div class="theme__head">
          <h3>{{ t.label }}</h3>
          <a :href="t.url" target="_blank" rel="noopener noreferrer">{{ t.publisher }} ↗</a>
        </div>
        <ul class="tables">
          <li v-for="tb in t.tables" :key="tb.name" :class="{ empty: tb.empty }">
            <span class="tname">{{ tb.name }}</span>
            <span class="tmeta">
              {{ tb.columns }} kolommen
              <template v-if="tb.last_updated"> · bijgewerkt {{ tb.last_updated }}</template>
              <template v-if="tb.empty"> · ⚠️ leeg</template>
            </span>
          </li>
        </ul>
        <p v-if="t.voorbeeldvragen.length" class="vbv">
          Voorbeeld: <em>{{ t.voorbeeldvragen[0] }}</em>
        </p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.kb { height: 100%; overflow: auto; padding: 18px 22px; background: #f6f8fa; }
.kb__head h2 { margin: 0; color: #0a4d68; font-size: 20px; }
.sub { margin: 2px 0 16px; color: #5b6b76; font-size: 13px; }
.muted { color: #5b6b76; }
.kb__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
.theme { background: #fff; border: 1px solid #e1e8ec; border-radius: 12px; padding: 14px 16px; }
.theme__head { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.theme__head h3 { margin: 0; font-size: 15px; color: #15242e; }
.theme__head a { font-size: 12px; color: #0a4d68; white-space: nowrap; }
.tables { list-style: none; margin: 10px 0 0; padding: 0; }
.tables li { display: flex; flex-direction: column; padding: 5px 0; border-top: 1px solid #eef2f4; font-size: 12.5px; }
.tables li.empty { opacity: .6; }
.tname { font-family: ui-monospace, Menlo, monospace; font-size: 12px; color: #15242e; }
.tmeta { color: #5b6b76; font-size: 11.5px; }
.vbv { margin: 10px 0 0; font-size: 12px; color: #5b6b76; }
</style>
