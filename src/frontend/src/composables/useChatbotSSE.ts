// useChatbotSSE.ts — consume the Phase-1 knowledge chatbot's SSE stream.
// POSTs to /api/chatbot/ask and parses the event/data lines emitted by
// app/routers/chatbot.py: meta, intent, sources_considered, followup_question,
// text, citations, done. Chunk-safe line buffering (mirrors useScenarioSSE.ts).
//
// Read-only: this never runs a scenario. Pass `scenario_card` (or `scenario_id`)
// to let the bot EXPLAIN an already-produced ScenarioCard.

export interface Citation {
  source_id: string
  title_nl: string
  url: string
  locator: string
  kind: string
}

export interface FAQEntry {
  id: string
  question_nl: string
  answer_nl: string
  citations: Citation[]
  tags: string[]
}

export interface ChatbotAskRequest {
  question: string
  scenario_id?: string
  scenario_card?: Record<string, unknown> | null
  model?: string
}

export interface ChatbotSSEHandlers {
  onMeta?: (m: any) => void
  onIntent?: (i: { intent: string; confidence: number; used_llm?: boolean; runnable?: boolean; scenario_id?: string }) => void
  onSources?: (sources: Citation[]) => void
  onFollowup?: (question_nl: string) => void
  onText?: (chunk: string) => void
  onCitations?: (citations: Citation[]) => void
  onError?: (msg: string) => void
  onDone?: () => void
  // Phase 2 — scenario-from-chat events (same names as the scenario engine SSE)
  onParamsConfirmed?: (recipe: any) => void
  onReasoning?: (step: any) => void
  onFeasibility?: (f: { feasibility_class: string; score_avg: number; stop_share: number }) => void
  onOfficial?: (o: any) => void
  onScenarioCard?: (card: any) => void
  onMapData?: (overlays: any[]) => void
  onDelta?: (delta: any) => void
}

export interface RecipeRequest {
  weights: Record<string, number>
  knmi_preset?: string
  growth_preset?: string
  base?: string
  time_horizon?: number
  added_homes?: number
  location_name?: string | null
  intake_id?: string | null
}

export function useChatbotSSE() {
  // Shared SSE POST + chunk-safe line buffering used by both ask and runRecipe.
  async function _stream(url: string, body: unknown, h: ChatbotSSEHandlers): Promise<void> {
    let res: Response
    try {
      res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
    } catch {
      h.onError?.('Kan de server niet bereiken.')
      return
    }
    if (!res.ok || !res.body) {
      h.onError?.(`Serverfout (${res.status})`)
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let event = ''
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (line.startsWith('event:')) { event = line.slice(6).trim(); continue }
        if (!line.startsWith('data:')) continue
        let data: any = null
        try { data = JSON.parse(line.slice(5).trim()) } catch { /* keep-alive */ continue }
        dispatch(event, data, h)
      }
    }
  }

  async function ask(req: ChatbotAskRequest, h: ChatbotSSEHandlers): Promise<void> {
    await _stream('/api/chatbot/ask', req, h)
  }

  // Phase 4: run a validated declarative recipe (reuses the scenario SSE handlers).
  async function runRecipe(recipe: RecipeRequest, h: ChatbotSSEHandlers): Promise<void> {
    await _stream('/api/chatbot/recipe/run', recipe, h)
  }

  async function fetchRecipeSchema(): Promise<any | null> {
    try {
      const res = await fetch('/api/chatbot/recipe/schema')
      return res.ok ? await res.json() : null
    } catch {
      return null
    }
  }

  function dispatch(event: string, data: any, h: ChatbotSSEHandlers) {
    switch (event) {
      case 'meta':               h.onMeta?.(data); break
      case 'intent':             h.onIntent?.(data); break
      case 'sources_considered': h.onSources?.((data as Citation[]) || []); break
      case 'followup_question':  h.onFollowup?.(data.question_nl); break
      case 'text':               h.onText?.(data.content ?? ''); break
      case 'citations':          h.onCitations?.((data as Citation[]) || []); break
      case 'error':              h.onError?.(data.message || 'Onbekende fout'); break
      case 'done':               h.onDone?.(); break
      // Phase 2 — scenario-from-chat
      case 'scenario_params_confirmed': h.onParamsConfirmed?.(data); break
      case 'reasoning_step':            h.onReasoning?.(data); break
      case 'feasibility_class':         h.onFeasibility?.(data); break
      case 'official_position':         h.onOfficial?.(data); break
      case 'scenario_card':             h.onScenarioCard?.(data); break
      case 'map_data':                  h.onMapData?.(data.overlays || []); break
      case 'scenario_delta':            h.onDelta?.(data); break
    }
  }

  async function fetchFaqs(): Promise<FAQEntry[]> {
    try {
      const res = await fetch('/api/chatbot/faqs')
      if (!res.ok) return []
      const json = await res.json()
      return (json.faqs as FAQEntry[]) || []
    } catch {
      return []
    }
  }

  return { ask, runRecipe, fetchRecipeSchema, fetchFaqs }
}
