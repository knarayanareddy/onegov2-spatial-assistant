<script setup lang="ts">
import { onBeforeMount, ref } from "vue";
import ChatPanel from "./components/chat/ChatPanel.vue";
import MeerInfoPage from "./components/info/MeerInfoPage.vue";
import AppHeader from "./components/layout/AppHeader.vue";
import SplitPane from "./components/layout/SplitPane.vue";
import MapPanel from "./components/map/MapPanel.vue";
import ScenarioPanel from "./components/scenario/ScenarioPanel.vue";
import ScenarioLibrary from "./components/scenario/ScenarioLibrary.vue";
import CumulativePanel from "./components/scenario/CumulativePanel.vue";
import ChatbotPanel from "./components/chatbot/ChatbotPanel.vue";
import KennisbasisPanel from "./components/kennisbasis/KennisbasisPanel.vue";
import { useDataDictionary } from "./composables/useDataDictionary";
import { useDuckDB } from "./composables/useDuckDB";
import { useMeerInfo } from "./composables/useMeerInfo";

const { init: initDB } = useDuckDB();
const { fetchDictionary } = useDataDictionary();
const { meerInfoOpen } = useMeerInfo();

type View = "assistent" | "chatbot" | "scenario" | "stapeling" | "kennisbasis" | "bibliotheek";
const view = ref<View>("assistent");
const tabs: { id: View; label: string }[] = [
  { id: "assistent", label: "🗺️ Assistent" },
  { id: "chatbot", label: "💧 Kennis-chat" },
  { id: "scenario", label: "🔮 Scenario-engine" },
  { id: "stapeling", label: "➕ Stapeling" },
  { id: "kennisbasis", label: "📚 Kennisbasis" },
  { id: "bibliotheek", label: "🗂️ Scenario's" },
];

onBeforeMount(() => {
  initDB();
  fetchDictionary();
});
</script>

<template>
  <div class="app">
    <AppHeader />
    <nav class="viewtabs">
      <button
        v-for="t in tabs"
        :key="t.id"
        :class="{ active: view === t.id }"
        @click="view = t.id"
      >{{ t.label }}</button>
    </nav>

    <ChatbotPanel v-if="view === 'chatbot'" />
    <ScenarioPanel v-else-if="view === 'scenario'" />
    <CumulativePanel v-else-if="view === 'stapeling'" />
    <KennisbasisPanel v-else-if="view === 'kennisbasis'" />
    <ScenarioLibrary v-else-if="view === 'bibliotheek'" />
    <MeerInfoPage v-else-if="meerInfoOpen" />
    <SplitPane v-else>
      <template #left>
        <ChatPanel />
      </template>
      <template #right>
        <MapPanel />
      </template>
    </SplitPane>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.app :deep(.pzh-header) {
  position: relative;
  z-index: 1000;
}

.viewtabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding: 8px 12px;
  background: #f0f4f7;
  border-bottom: 1px solid #dce3e8;
}
.viewtabs button {
  padding: 6px 12px;
  border: 1px solid #cfdde4;
  border-radius: 8px;
  background: #fff;
  color: #0a4d68;
  font-size: 13px;
  cursor: pointer;
}
.viewtabs button.active {
  background: #0a4d68;
  color: #fff;
  border-color: #0a4d68;
}
</style>
