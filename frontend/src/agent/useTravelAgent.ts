/**
 * Talks to the Python LangGraph agent over the AG-UI protocol (HTTP + SSE).
 * No CopilotKit runtime is needed: @ag-ui/client's HttpAgent speaks AG-UI directly.
 *
 * Shared state contract with the graph (see backend/src/travel_agent/graph.py):
 *   preferences  <- written here when the generated form is submitted
 *   ui_spec      -> written by the agent, rendered with json-render
 */
import { HttpAgent, type Message } from "@ag-ui/client";
import type { Spec } from "@json-render/react";
import { useCallback, useEffect, useMemo, useState } from "react";

export interface AgentState {
  preferences?: Record<string, unknown> | null;
  edit_preferences?: boolean;
  ui_spec?: Spec | null;
}

export interface ChatLine {
  id: string;
  role: "user" | "assistant";
  text: string;
}

export const AGENT_URL = import.meta.env.VITE_AGENT_URL ?? "http://localhost:8000/agent";

export function toChatLines(messages: readonly Message[]): ChatLine[] {
  return messages.flatMap((m) =>
    (m.role === "user" || m.role === "assistant") && typeof m.content === "string" && m.content
      ? [{ id: m.id, role: m.role, text: m.content }]
      : [],
  );
}

export function useTravelAgent(agent?: HttpAgent) {
  const a = useMemo(() => agent ?? new HttpAgent({ url: AGENT_URL, threadId: crypto.randomUUID() }), [agent]);
  const [messages, setMessages] = useState<ChatLine[]>([]);
  const [state, setState] = useState<AgentState>({});
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const sub = a.subscribe({
      onMessagesChanged: ({ messages }) => setMessages(toChatLines(messages)),
      onStateChanged: ({ state }) => setState({ ...(state as AgentState) }),
      onRunErrorEvent: ({ event }) => setError(event.message),
    });
    return () => sub.unsubscribe();
  }, [a]);

  const send = useCallback(
    async (text: string, statePatch?: Partial<AgentState>) => {
      if (!text.trim() || a.isRunning) return;
      setError(null);
      if (statePatch) a.setState({ ...(a.state as AgentState), ...statePatch });
      a.addMessage({ id: crypto.randomUUID(), role: "user", content: text });
      setMessages(toChatLines(a.messages));
      setRunning(true);
      try {
        await a.runAgent();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setRunning(false);
      }
    },
    [a],
  );

  return { messages, spec: state.ui_spec ?? null, running, error, send };
}
