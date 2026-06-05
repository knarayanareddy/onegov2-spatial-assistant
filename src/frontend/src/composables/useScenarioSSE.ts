// useScenarioSSE.ts — consume the scenario engine's SSE stream (design doc §6, v3).
// POSTs to /api/scenario/run and parses the event/data lines emitted by
// app/routers/scenario.py: scenario_params_confirmed, reasoning_step,
// feasibility_class, official_position, scenario_card, map_data, scenario_delta,
// followup_question, done. Chunk-safe line buffering.

export type H3Cell = { h3_id: string; score: number; klasse: 'GO' | 'CAUTION' | 'STOP' }
export type Overlay = { layer_id: string; label_nl: string; type: string; cells: H3Cell[]; colorScale: Record<string, string> }

export interface ScenarioRunRequest {
  question: string
  compare?: boolean
  baseline?: Record<string, number>
  shock?: Record<string, number>
  assumptions?: Record<string, number>
}

export interface ScenarioSSEHandlers {
  onParams?: (p: any) => void
  onReasoning?: (step: any) => void
  onFeasibility?: (f: { feasibility_class: string; score_avg: number; stop_share: number }) => void
  onOfficial?: (o: any) => void
  onCard?: (card: any) => void
  onMapData?: (overlays: Overlay[]) => void
  onDelta?: (delta: any) => void
  onFollowup?: (q: string) => void
  onError?: (msg: string) => void
  onDone?: () => void
}

export function useScenarioSSE() {
  async function run(req: ScenarioRunRequest, h: ScenarioSSEHandlers): Promise<void> {
    const res = await fetch('/api/scenario/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
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

  function dispatch(event: string, data: any, h: ScenarioSSEHandlers) {
    switch (event) {
      case 'scenario_params_confirmed': h.onParams?.(data); break
      case 'reasoning_step':            h.onReasoning?.(data); break
      case 'feasibility_class':         h.onFeasibility?.(data); break
      case 'official_position':         h.onOfficial?.(data); break
      case 'scenario_card':             h.onCard?.(data); break
      case 'map_data':                  h.onMapData?.(data.overlays || []); break
      case 'scenario_delta':            h.onDelta?.(data); break
      case 'followup_question':         h.onFollowup?.(data.question_nl); break
      case 'error':                     h.onError?.(data.message_nl || 'Onbekende fout'); break
      case 'done':                      h.onDone?.(); break
    }
  }

  return { run }
}
