import { useState, type FormEvent } from "react";
import type { HttpAgent } from "@ag-ui/client";
import { useTravelAgent } from "./agent/useTravelAgent";
import { GenerativeView } from "./genui/GenerativeView";
import "./App.css";

const SUGGESTIONS = ["Plan 3 days in Lisbon", "A 2-day food trip to Tokyo", "5 days in Rome for history lovers"];

export default function App({ agent }: { agent?: HttpAgent }) {
  const { messages, spec, running, error, send } = useTravelAgent(agent);
  const [draft, setDraft] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    void send(draft);
    setDraft("");
  };

  return (
    <div className="layout">
      <aside className="chat">
        <header className="brand">
          <h1>Wayfinder</h1>
          <p className="muted">LangGraph agent · AG-UI protocol · json-render UI</p>
        </header>

        <ol className="messages" aria-live="polite">
          {messages.length === 0 && (
            <li className="hint">
              Ask for a trip. The agent replies with <em>interface</em>, not just text.
              <div className="chips">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="chip" onClick={() => void send(s)} disabled={running}>{s}</button>
                ))}
              </div>
            </li>
          )}
          {messages.map((m) => (
            <li key={m.id} className={`msg ${m.role}`}>{m.text}</li>
          ))}
          {running && (
            <li className="msg assistant typing" aria-label="Agent is thinking">
              Thinking… local models can take up to a minute.
            </li>
          )}
        </ol>
        {error && <p role="alert" className="error-text">Agent error: {error}</p>}

        <form className="composer" onSubmit={submit}>
          <input
            aria-label="Message"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Plan 3 days in Lisbon"
            disabled={running}
          />
          <button className="btn primary" disabled={running || !draft.trim()}>Send</button>
        </form>
      </aside>

      <main className="canvas" aria-label="Generated interface" aria-busy={running}>
        {spec ? (
          <GenerativeView
            spec={spec}
            busy={running}
            onSubmitPreferences={(prefs) => void send("Here are my preferences.", { preferences: prefs })}
            onReplan={() => void send("I'd like to change my preferences.", { edit_preferences: true })}
          />
        ) : (
          <div className="empty">
            <h2>Generative UI canvas</h2>
            <p className="muted">
              The agent streams a JSON spec over AG-UI; it's validated against a typed component
              catalog and rendered here.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
