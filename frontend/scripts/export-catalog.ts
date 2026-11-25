/**
 * Exports the React catalog so the Python agent shares the exact contract.
 *   ../shared/catalog.schema.json  -> JSON Schema used by the backend validator
 *   ../shared/catalog.prompt.md    -> LLM-readable description of the catalog
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import { catalog } from "../src/genui/catalog";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../shared");
mkdirSync(out, { recursive: true });

const doc = {
  componentNames: catalog.componentNames,
  actionNames: catalog.actionNames,
  spec: catalog.jsonSchema(),
  // catalog.jsonSchema() only constrains element *types*; export each
  // component's Zod props schema too so the backend can validate props.
  components: Object.fromEntries(
    Object.entries(catalog.data.components).map(([name, def]) => [
      name,
      { description: def.description, props: z.toJSONSchema(def.props, { io: "input" }) },
    ]),
  ),
};
writeFileSync(resolve(out, "catalog.schema.json"), JSON.stringify(doc, null, 2) + "\n");
writeFileSync(resolve(out, "catalog.prompt.md"), catalog.prompt() + "\n");
console.log(`catalog exported to ${out} (${catalog.componentNames.length} components)`);
