<script setup lang="ts">
// ChatbotPanel.vue — Phase-1 grounded Dutch knowledge chatbot.
// Answers questions about the build, the data and the methodology, surfaces the
// honest data caveats, and (read-only) explains an already-produced ScenarioCard
// when one is passed via the `scenarioCard` prop. Every answer carries sources.
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import {
  type Citation,
  type FAQEntry,
  useChatbotSSE,
} from "../../composables/useChatbotSSE";

const props = defineProps<{ scenarioCard?: Record<string, unknown> | null }>();

interface ScenarioResult {
  recipe?: Record<string, any>;
  cards: any[];
  delta?: any;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  followup?: string;
  intent?: string;
  usedLlm?: boolean;
  scenario?: ScenarioResult;
}

const { ask, runRecipe, fetchRecipeSchema, fetchFaqs } = useChatbotSSE();

const messages = ref<Message[]>([]);
const input = ref("");
const loading = ref(false);
const faqs = ref<FAQEntry[]>([]);
const showFaqs = ref(true);
const scroller = ref<HTMLElement | null>(null);

// Phase 4 — recipe-builder state
const showRecipe = ref(false);
const weights = reactive({ salinity: 0.4, demand: 0.3, flood: 0.2, protection: 0.1 });
const knmi = ref("Hd");
const growth = ref("middel");
const base = ref("salinity");
const recipeLocation = ref("");
const schema = ref<any | null>(null);
const weightSum = computed(() =>
  Number((weights.salinity + weights.demand + weights.flood + weights.protection).toFixed(2)),
);
const recipeReady = computed(() => Math.abs(weightSum.value - 1) <= 0.01 && !loading.value);

onMounted(async () => {
  faqs.value = await fetchFaqs();
  schema.value = await fetchRecipeSchema();
});

async function runRecipeNow() {
  if (!recipeReady.value) return;
  showRecipe.value = false;
  showFaqs.value = false;
  const label =
    `Recept — verzilting ${weights.salinity}, vraag ${weights.demand}, ` +
    `overstroming ${weights.flood}, bescherming ${weights.protection} · ` +
    `KNMI ${knmi.value} · ${base.value}`;
  messages.value.push({ role: "user", content: label });
  const assistant: Message = { role: "assistant", content: "", scenario: { cards: [] } };
  messages.value.push(assistant);
  loading.value = true;
  await scrollToBottom();
  await runRecipe(
    {
      weights: { ...weights },
      knmi_preset: knmi.value,
      growth_preset: growth.value,
      base: base.value,
      location_name: recipeLocation.value || null,
    },
    {
      onIntent: (i) => { assistant.intent = i.intent; },
      onParamsConfirmed: (r) => { assistant.scenario!.recipe = r; },
      onScenarioCard: (card) => { assistant.scenario!.cards.push(card); void scrollToBottom(); },
      onDelta: (d) => { assistant.scenario!.delta = d; },
      onFollowup: (f) => { assistant.followup = f; },
      onError: (msg) => { assistant.content = assistant.content || `⚠️ ${msg}`; },
      onDone: () => { loading.value = false; void scrollToBottom(); },
    },
  );
}

async function scrollToBottom() {
  await nextTick();
  scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: "smooth" });
}

async function send(question: string) {
  const q = question.trim();
  if (!q || loading.value) return;
  input.value = "";
  showFaqs.value = false;
  messages.value.push({ role: "user", content: q });
  const assistant: Message = { role: "assistant", content: "", citations: [] };
  messages.value.push(assistant);
  loading.value = true;
  await scrollToBottom();

  await ask(
    { question: q, scenario_card: props.scenarioCard ?? undefined },
    {
      onIntent: (i) => {
        assistant.intent = i.intent;
        assistant.usedLlm = i.used_llm;
      },
      onText: (chunk) => {
        assistant.content += chunk;
        void scrollToBottom();
      },
      onCitations: (c) => {
        assistant.citations = c;
      },
      onFollowup: (f) => {
        assistant.followup = f;
      },
      onError: (msg) => {
        assistant.content = assistant.content || `⚠️ ${msg}`;
      },
      // Phase 2 — scenario-from-chat
      onParamsConfirmed: (recipe) => {
        assistant.scenario = assistant.scenario ?? { cards: [] };
        assistant.scenario.recipe = recipe;
      },
      onScenarioCard: (card) => {
        assistant.scenario = assistant.scenario ?? { cards: [] };
        assistant.scenario.cards.push(card);
        void scrollToBottom();
      },
      onDelta: (delta) => {
        assistant.scenario = assistant.scenario ?? { cards: [] };
        assistant.scenario.delta = delta;
      },
      onDone: () => {
        loading.value = false;
        void scrollToBottom();
      },
    },
  );
}
</script>

<template>
  <section class="chatbot">
    <header class="chatbot__head">
      <div>
        <h2>💧 Kennis-chat</h2>
        <p class="sub">
          Vragen over de data, de methode en scenario-resultaten — in begrijpelijk
          Nederlands, met bron.
        </p>
      </div>
      <div class="head-controls">
        <span v-if="props.scenarioCard" class="badge">Uitlegmodus: scenario gekoppeld</span>
        <button class="recipe-toggle" @click="showRecipe = !showRecipe">
          {{ showRecipe ? "× Recept sluiten" : "🧪 Bouw een recept" }}
        </button>
      </div>
    </header>

    <!-- Phase 4 — declarative recipe-builder -->
    <div v-if="showRecipe" class="recipe-builder">
      <p class="rb-title">Recept — weeg de H3-lagen (samen = 1,00)</p>
      <div class="rb-sliders">
        <label v-for="sig in (['salinity','demand','flood','protection'] as const)" :key="sig">
          <span class="rb-label">
            {{ { salinity: 'Verzilting', demand: 'Vraag', flood: 'Overstroming', protection: 'Bescherming' }[sig] }}
            <strong>{{ weights[sig].toFixed(2) }}</strong>
          </span>
          <input type="range" min="0" max="1" step="0.05" v-model.number="weights[sig]" />
        </label>
      </div>
      <p class="rb-sum" :class="{ ok: Math.abs(weightSum - 1) <= 0.01 }">
        Som: {{ weightSum.toFixed(2) }} {{ Math.abs(weightSum - 1) <= 0.01 ? "✓" : "(moet 1,00 zijn)" }}
      </p>
      <div class="rb-row">
        <label>KNMI
          <select v-model="knmi">
            <option v-for="k in (schema?.knmi_presets || ['B','Hn','Hd','Ln','Ld'])" :key="k" :value="k">{{ k }}</option>
          </select>
        </label>
        <label>Groei
          <select v-model="growth">
            <option v-for="g in (schema?.growth_presets || ['laag','middel','hoog'])" :key="g" :value="g">{{ g }}</option>
          </select>
        </label>
        <label>Universum
          <select v-model="base">
            <option v-for="b in (schema?.base_options || ['salinity','populated'])" :key="b" :value="b">{{ b }}</option>
          </select>
        </label>
      </div>
      <div class="rb-row">
        <label class="rb-loc">Locatie (optioneel)
          <input type="text" v-model="recipeLocation" placeholder="bijv. Pijnacker (drop-pin)" />
        </label>
        <button class="rb-run" :disabled="!recipeReady" @click="runRecipeNow">Recept doorrekenen</button>
      </div>
    </div>

    <div ref="scroller" class="chatbot__messages">
      <!-- Veelgestelde vragen -->
      <div v-if="showFaqs && faqs.length" class="faqs">
        <p class="faqs__title">Veelgestelde vragen</p>
        <button
          v-for="f in faqs"
          :key="f.id"
          class="faq-chip"
          @click="send(f.question_nl)"
        >
          {{ f.question_nl }}
        </button>
      </div>

      <div
        v-for="(m, i) in messages"
        :key="i"
        class="msg"
        :class="m.role === 'user' ? 'msg--user' : 'msg--bot'"
      >
        <div class="msg__bubble">
          <p v-if="m.content || m.role === 'user'" class="msg__text">{{ m.content }}<span v-if="loading && i === messages.length - 1 && m.content" class="cursor">▋</span></p>

          <!-- Scenario / recipe run in progress -->
          <p
            v-if="(m.intent === 'scenario_run_request' || m.intent === 'recipe_run') && (!m.scenario || !m.scenario.cards.length) && loading && i === messages.length - 1"
            class="running"
          >{{ m.intent === 'recipe_run' ? 'Recept wordt doorgerekend…' : 'Scenario wordt doorgerekend…' }}</p>

          <!-- Phase 2 — scenario result -->
          <div v-if="m.scenario && (m.scenario.cards.length || m.scenario.recipe)" class="scenario">
            <p v-if="m.scenario.recipe" class="recipe">
              Recept: {{ m.scenario.recipe.scenario_type }} · KNMI {{ m.scenario.recipe.knmi_preset }} ·
              {{ m.scenario.recipe.time_horizon
              }}<span v-if="m.scenario.recipe.intake_id"> · {{ m.scenario.recipe.intake_id }}</span><span
                v-else-if="m.scenario.recipe.location_name"
              > · {{ m.scenario.recipe.location_name }}</span>
            </p>
            <div v-for="(card, ci) in m.scenario.cards" :key="ci" class="scard">
              <div class="scard__head">
                <span class="verdict" :class="'v-' + card.results.feasibility_class">{{ card.results.feasibility_class }}</span>
                <span class="scard__nums">
                  DrinkwaterDruk {{ Math.round(card.results.score_avg) }}/100 ·
                  {{ Math.round(card.results.stop_share * 100) }}% STOP · {{ card.results.n_cells }} cellen
                </span>
              </div>
              <ul class="steps">
                <li v-for="(s, si) in card.reasoning_steps" :key="si">
                  <strong>{{ s.label_nl }}:</strong> {{ s.description_nl }}
                </li>
              </ul>
              <div
                v-if="card.official_position && card.official_position.documents && card.official_position.documents.length"
                class="sources"
              >
                <p class="sources__title">Bronnen</p>
                <ul>
                  <li v-for="(d, di) in card.official_position.documents" :key="di">
                    <a :href="d.url" target="_blank" rel="noopener noreferrer">{{ d.title }}</a>
                  </li>
                </ul>
              </div>
              <a
                v-if="card.stable_url"
                :href="card.stable_url"
                target="_blank"
                rel="noopener noreferrer"
                class="open-engine"
              >Open op kaart in de Scenario-engine →</a>
            </div>
            <div v-if="m.scenario.delta" class="delta">
              <strong>Vergelijking:</strong> {{ m.scenario.delta.narrative_nl }}
            </div>
          </div>

          <!-- Clarifying question (no dead ends) -->
          <button v-if="m.followup" class="followup" @click="send(m.followup)">
            {{ m.followup }}
          </button>

          <!-- Bronnen -->
          <div v-if="m.citations && m.citations.length" class="sources">
            <p class="sources__title">Bronnen</p>
            <ul>
              <li v-for="(c, ci) in m.citations" :key="ci">
                <a
                  v-if="c.url && c.url.startsWith('http')"
                  :href="c.url"
                  target="_blank"
                  rel="noopener noreferrer"
                >{{ c.title_nl }}</a>
                <span v-else>{{ c.title_nl }}<span v-if="c.url"> — {{ c.url }}</span></span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <form class="chatbot__input" @submit.prevent="send(input)">
      <input
        v-model="input"
        type="text"
        placeholder="Stel een vraag over de data, de methode of een scenario…"
        :disabled="loading"
        aria-label="Vraag"
      />
      <button type="submit" :disabled="loading || !input.trim()">
        {{ loading ? "…" : "Vraag" }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.chatbot {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f6f8fa;
}
.chatbot__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid #dce3e8;
  background: #fff;
}
.chatbot__head h2 { margin: 0; font-size: 17px; color: #0a4d68; }
.sub { margin: 2px 0 0; font-size: 12px; color: #5b6b76; }
.badge {
  font-size: 11px;
  background: #e6f0f4;
  color: #0a4d68;
  border: 1px solid #b9d4df;
  border-radius: 999px;
  padding: 4px 10px;
  white-space: nowrap;
}
.head-controls { display: flex; align-items: center; gap: 8px; }
.recipe-toggle {
  font-size: 12px; padding: 6px 10px; border: 1px solid #0a4d68; border-radius: 8px;
  background: #fff; color: #0a4d68; cursor: pointer; white-space: nowrap;
}

.recipe-builder {
  border-bottom: 1px solid #dce3e8; background: #f1f6f9; padding: 14px 18px;
}
.rb-title { margin: 0 0 10px; font-size: 13px; font-weight: 600; color: #0a4d68; }
.rb-sliders { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 18px; }
.rb-sliders label { display: flex; flex-direction: column; font-size: 12px; color: #1c2b33; }
.rb-label { display: flex; justify-content: space-between; }
.rb-sliders input[type="range"] { width: 100%; accent-color: #0a4d68; }
.rb-sum { margin: 8px 0; font-size: 12px; color: #b00020; }
.rb-sum.ok { color: #1a7f37; }
.rb-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; margin-top: 6px; }
.rb-row label { display: flex; flex-direction: column; font-size: 12px; color: #5b6b76; gap: 3px; }
.rb-row select, .rb-row input[type="text"] {
  padding: 6px 8px; border: 1px solid #cfdde4; border-radius: 8px; font-size: 13px;
}
.rb-loc { flex: 1; min-width: 160px; }
.rb-run {
  padding: 8px 14px; border: none; border-radius: 8px; background: #0a4d68; color: #fff;
  font-size: 13px; cursor: pointer;
}
.rb-run:disabled { opacity: .5; cursor: default; }
.chatbot__messages { flex: 1; overflow-y: auto; padding: 16px 18px; }

.faqs { margin-bottom: 14px; }
.faqs__title { font-size: 12px; color: #5b6b76; margin: 0 0 8px; text-transform: uppercase; letter-spacing: .04em; }
.faq-chip {
  display: block;
  width: 100%;
  text-align: left;
  margin: 6px 0;
  padding: 9px 12px;
  border: 1px solid #cfdde4;
  border-radius: 10px;
  background: #fff;
  color: #0a4d68;
  font-size: 13px;
  cursor: pointer;
}
.faq-chip:hover { background: #eef4f7; }

.msg { display: flex; margin: 10px 0; }
.msg--user { justify-content: flex-end; }
.msg--bot { justify-content: flex-start; }
.msg__bubble {
  max-width: 86%;
  padding: 11px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
}
.msg--user .msg__bubble { background: #0a4d68; color: #fff; border-bottom-right-radius: 4px; }
.msg--bot .msg__bubble { background: #fff; color: #1c2b33; border: 1px solid #e1e8ec; border-bottom-left-radius: 4px; }
.msg__text { margin: 0; white-space: pre-wrap; }
.cursor { animation: blink 1s steps(2) infinite; color: #0a4d68; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

.followup {
  margin-top: 10px;
  padding: 8px 12px;
  border: 1px dashed #0a4d68;
  border-radius: 10px;
  background: #eef4f7;
  color: #0a4d68;
  font-size: 13px;
  cursor: pointer;
}

.running { margin: 0; font-size: 13px; color: #5b6b76; font-style: italic; }

.scenario { margin-top: 4px; }
.recipe {
  margin: 0 0 8px; font-size: 12px; color: #5b6b76;
  background: #eef4f7; border-radius: 8px; padding: 6px 10px;
}
.scard {
  border: 1px solid #e1e8ec; border-radius: 10px; padding: 10px 12px; margin: 8px 0; background: #fafcfd;
}
.scard__head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.verdict {
  font-weight: 700; font-size: 12px; color: #fff; border-radius: 6px; padding: 3px 9px; letter-spacing: .03em;
}
.verdict.v-GO { background: #28a745; }
.verdict.v-CAUTION { background: #d39e00; }
.verdict.v-STOP { background: #dc3545; }
.scard__nums { font-size: 12px; color: #1c2b33; }
.steps { margin: 8px 0 0; padding-left: 18px; }
.steps li { font-size: 12px; margin: 3px 0; line-height: 1.45; }
.open-engine {
  display: inline-block; margin-top: 8px; font-size: 12px; font-weight: 600; color: #0a4d68; text-decoration: none;
}
.open-engine:hover { text-decoration: underline; }
.delta {
  margin-top: 8px; font-size: 13px; line-height: 1.5; color: #1c2b33;
  border-left: 3px solid #0a4d68; padding: 6px 10px; background: #f1f6f9; border-radius: 0 8px 8px 0;
}

.sources { margin-top: 10px; border-top: 1px solid #eef2f4; padding-top: 8px; }
.sources__title { margin: 0 0 4px; font-size: 11px; color: #5b6b76; text-transform: uppercase; letter-spacing: .04em; }
.sources ul { margin: 0; padding-left: 18px; }
.sources li { font-size: 12px; margin: 2px 0; }
.sources a { color: #0a4d68; }

.chatbot__input {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #dce3e8;
  background: #fff;
}
.chatbot__input input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #cfdde4;
  border-radius: 10px;
  font-size: 14px;
}
.chatbot__input button {
  padding: 10px 16px;
  border: none;
  border-radius: 10px;
  background: #0a4d68;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}
.chatbot__input button:disabled { opacity: .5; cursor: default; }
</style>
