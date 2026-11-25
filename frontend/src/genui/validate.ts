/**
 * Full spec validation in the browser, mirroring backend/src/travel_agent/catalog.py.
 * catalog.validate() checks the spec *structure* (known types, children arrays) but
 * not each component's props, so we also run every element's props through its Zod schema.
 */
import { catalog } from "./catalog";

type Components = typeof catalog.data.components;

export function specIssues(spec: unknown): string[] {
  const structural = catalog.validate(spec);
  if (!structural.success) return [String(structural.error ?? "invalid spec structure")];

  const { root, elements } = spec as { root: string; elements: Record<string, { type: keyof Components; props: unknown; children: string[]; on?: Record<string, unknown> }> };
  const issues: string[] = [];
  if (!(root in elements)) issues.push(`root "${root}" is not in elements`);

  const actions = new Set([...catalog.actionNames, "setState", "pushState", "removeState", "validateForm"]);
  for (const [key, el] of Object.entries(elements)) {
    for (const child of el.children) if (!(child in elements)) issues.push(`${key}: child "${child}" does not exist`);
    const parsed = catalog.data.components[el.type].props.safeParse(el.props);
    if (!parsed.success) {
      for (const i of parsed.error.issues) issues.push(`${key} (${el.type}).${i.path.join(".") || "props"}: ${i.message}`);
    }
    for (const [event, binding] of Object.entries(el.on ?? {})) {
      for (const b of (Array.isArray(binding) ? binding : [binding]) as { action?: string }[]) {
        if (!b.action || !actions.has(b.action)) issues.push(`${key}: on.${event} uses unknown action "${b.action}"`);
      }
    }
  }
  return issues;
}
