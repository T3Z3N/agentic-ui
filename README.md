# Wayfinder — an agentic (generative) UI demo

A travel-planning agent that answers with **interface, not just text**.
Ask for a trip. The agent replies with a form it generated. Fill it in, and it renders an
itinerary with day cards, KPI tiles, a budget chart and a table. All of that UI is plain
**JSON** that a Python LangGraph agent sends and React renders.

| Layer | Tech |
|---|---|
| Agent | Python · [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) · LangChain structured output · Ollama (local LLM) |
| Agent ↔ UI transport | [AG-UI protocol](https://docs.ag-ui.com) over HTTP + SSE (`ag-ui-langgraph` on the server, `@ag-ui/client` in the browser) |
| Generative UI | [json-render](https://github.com/vercel-labs/json-render): a typed component catalog (Zod) plus a JSON spec renderer |
| Frontend | React 19 · Vite · TypeScript |
| Tests | pytest · Vitest + Testing Library · Playwright |

## How it works

```
┌──────────────── React (Vite) ─────────────────┐        ┌──────────── FastAPI + LangGraph ────────────┐
│ chat ── HttpAgent.runAgent() ─── AG-UI POST ──┼──────► │ route ─┬─ no prefs ─► ask_preferences ─┐      │
│                                               │        │        └─ prefs ────► plan_trip ───────┤      │
│ canvas ◄─ json-render <Renderer spec=…/> ◄────┼─ SSE ──┤  STATE_SNAPSHOT { ui_spec, … }  ◄──────┘      │
│   form submit → state.preferences ────────────┼──────► │  (graph state is shared with the browser)    │
└───────────────────────────────────────────────┘        └──────────────────────────────────────────────┘
                      ▲                                                       ▲
                      └──── shared/catalog.schema.json (exported from Zod) ───┘
```

1. **The agent decides content; the catalog bounds the UI.** The LLM fills typed Pydantic models
   (`TripRequest`, `TripPlan`) through structured output. It also decides optional sections such as tips
   and a packing list. A composer (`backend/src/travel_agent/ui.py`) turns that data into a json-render
   spec, a flat map of `{type, props, children}` elements.
2. **There is one contract, enforced on both sides.** `frontend/src/genui/catalog.ts` is the single source of truth.
   `npm run export-catalog` writes it to `shared/catalog.schema.json`. The backend validates every spec
   against it before sending (`catalog.py`), and the browser validates again before rendering
   (`validate.ts`). Unknown components, bad props and unknown actions are all rejected, so the agent can
   never ship arbitrary HTML or code.
3. **The agent and the UI share state over AG-UI.** The graph's `ui_spec` reaches the browser through `STATE_SNAPSHOT`
   events. When the user submits the generated form, the browser writes `preferences` back into agent
   state. This is the human-in-the-loop step.
4. **Inputs bind to state with no custom glue.** Inputs use json-render `{"$bindState": "/prefs/budget"}` bindings,
   and buttons fire catalog actions (`submitPreferences`, `replan`).

### Design decisions worth talking about

- **Why the composer, rather than having the LLM write UI JSON directly?** Small local models are unreliable
  at producing large nested layouts, but they are good at filling a schema. Splitting *what* (LLM) from *how*
  (composer) makes the demo reliable on an 8B model, and it keeps the layout consistent. A larger model
  could write specs directly using `shared/catalog.prompt.md`. The validators already guard that path.
- **Why `@ag-ui/client` rather than CopilotKit?** CopilotKit's React client needs an extra Node runtime in front of a
  Python AG-UI endpoint. Speaking AG-UI directly keeps the stack at two processes.
- **Bugs found against a real model, each with a regression test:**
  - Structured-output tokens leaked into the chat. The fix tags internal LLM calls with
    `emit-messages: False`, so the AG-UI bridge doesn't stream them.
  - Duplicate `STATE_SNAPSHOT`s desynced json-render's mount-time action handlers from the form
    store. The fix keys the store on spec content and remounts the provider.
  - Small-model quirks such as "9:00 AM", ": 12:00 PM" and miscounted days. The fix is
    deterministic clean-up in `tidy_plan`.
- **Failures degrade instead of crashing.** If the LLM is down or returns bad output, or the user submits bad
  preferences, the agent renders an error card through the same pipeline. It doesn't crash the run.

## Run it

Prerequisites: Python 3.12+ with [uv](https://docs.astral.sh/uv/), Node 20+, and optionally [Ollama](https://ollama.com).

```bash
make install
```

**With a real local LLM (Ollama):**

```bash
brew install ollama && ollama serve   # or: brew services start ollama
ollama pull llama3.1:8b               # ~4.9 GB
make backend            # LLM_PROVIDER=ollama by default; OLLAMA_MODEL to override
make frontend           # http://localhost:5173
```

On a laptop with `llama3.1:8b`, the first reply (the form) takes a few seconds, and a full itinerary
takes roughly 40–70 s. The model's prices are rough estimates, so don't treat them as real quotes.

**Without an LLM (deterministic fake planner):**

```bash
LLM_PROVIDER=fake make backend
make frontend
```

## Test

```bash
make test       # pytest (catalog, composer, LLM layer, graph, AG-UI endpoint) + Vitest (renderer, contract)
make test-e2e   # Playwright: chat → generated form → generated itinerary → replan
```

After changing `catalog.ts`, run `make catalog`. It re-exports the schema and the backend fixtures, and
the contract tests fail if you forget.

## Project layout

```
backend/src/travel_agent/
  models.py   domain models the LLM fills (structured output)
  llm.py      Planner interface: OllamaPlanner | FakePlanner
  ui.py       composer: domain data → json-render spec
  catalog.py  validates specs against shared/catalog.schema.json
  graph.py    LangGraph state machine (shared state: preferences, ui_spec)
  server.py   FastAPI + AG-UI endpoint at /agent
frontend/src/
  genui/catalog.ts         Zod component catalog (source of truth)
  genui/registry.tsx       React implementations of each component
  genui/GenerativeView.tsx validates + renders a spec, wires actions
  agent/useTravelAgent.ts  AG-UI HttpAgent hook
shared/                    exported catalog + backend-generated fixtures
```
