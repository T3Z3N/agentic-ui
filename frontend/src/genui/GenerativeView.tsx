/**
 * Renders an agent-produced json-render spec.
 * Defence in depth: the spec is validated against the catalog in the browser too,
 * so a bad/malicious payload shows an error instead of a broken UI.
 */
import { JSONUIProvider, Renderer, createStateStore, type Spec } from "@json-render/react";
import { useMemo } from "react";
import { registry } from "./registry";
import { specIssues } from "./validate";

export interface GenerativeViewProps {
  spec: Spec;
  busy?: boolean;
  onSubmitPreferences: (prefs: Record<string, unknown>) => void;
  onReplan: () => void;
}

export function GenerativeView({ spec, ...rest }: GenerativeViewProps) {
  // AG-UI may re-send the same ui_spec as a new object (one STATE_SNAPSHOT per graph
  // step). Identify a spec by its *content*, so duplicates neither wipe the user's
  // edits nor desync the action handlers from the state store.
  const specKey = useMemo(() => JSON.stringify(spec), [spec]);
  // `key` remounts the provider for each genuinely new spec: json-render's
  // ActionProvider captures `handlers` once on mount, so they must be rebuilt
  // together with the store they read from.
  return <SpecView key={specKey} spec={spec} {...rest} />;
}

function SpecView({ spec, busy, onSubmitPreferences, onReplan }: GenerativeViewProps) {
  // Mount-scoped (this component remounts per spec), so the store lives exactly
  // as long as the handlers that close over it.
  const [issues, store] = useMemo(
    () => [specIssues(spec), createStateStore(structuredClone(spec.state ?? {}))] as const,
    // eslint-disable-next-line react-hooks/exhaustive-deps -- remount handles spec changes
    [],
  );

  if (issues.length) {
    return (
      <div role="alert" className="card error">
        <h3>The agent sent a UI this app can't render</h3>
        <ul>{issues.slice(0, 8).map((i) => <li key={i}><code>{i}</code></li>)}</ul>
      </div>
    );
  }

  return (
    <JSONUIProvider
      registry={registry}
      store={store}
      handlers={{
        submitPreferences: () => onSubmitPreferences({ ...(store.get("/prefs") as Record<string, unknown>) }),
        replan: () => onReplan(),
      }}
    >
      <Renderer spec={spec} registry={registry} loading={busy} />
    </JSONUIProvider>
  );
}
