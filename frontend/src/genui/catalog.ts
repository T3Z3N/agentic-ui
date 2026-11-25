/**
 * The component catalog: the ONLY UI vocabulary the agent may use.
 *
 * This file is the single source of truth. `npm run export-catalog` writes it to
 * ../shared/catalog.schema.json so the Python backend validates every spec it
 * emits against exactly the same contract the React renderer enforces.
 */
import { defineCatalog } from "@json-render/core";
import { schema } from "@json-render/react/schema";
import { z } from "zod";

const gap = z.enum(["sm", "md", "lg"]).nullable();

export const catalog = defineCatalog(schema, {
  components: {
    Stack: {
      props: z.object({
        direction: z.enum(["vertical", "horizontal"]).nullable(),
        gap,
      }),
      description: "Layout container that stacks children vertically or horizontally.",
    },
    Heading: {
      props: z.object({ text: z.string(), level: z.number().int().min(1).max(3).nullable() }),
      description: "A section heading.",
    },
    Text: {
      props: z.object({ text: z.string(), tone: z.enum(["default", "muted"]).nullable() }),
      description: "A paragraph of text.",
    },
    Card: {
      props: z.object({ title: z.string(), subtitle: z.string().nullable() }),
      description: "A bordered card that groups children under a title.",
    },
    Stat: {
      props: z.object({ label: z.string(), value: z.string() }),
      description: "A KPI tile: a short label over a big value.",
    },
    DayCard: {
      props: z.object({
        day: z.number().int().min(1),
        title: z.string(),
        activities: z.array(
          z.object({
            time: z.string(),
            name: z.string(),
            category: z.enum(["food", "sight", "activity", "transport", "stay"]),
            cost: z.number().min(0),
          }),
        ),
      }),
      description: "One day of an itinerary with timed activities and costs.",
    },
    Table: {
      props: z.object({ columns: z.array(z.string()), rows: z.array(z.array(z.string())) }),
      description: "A simple data table.",
    },
    BarChart: {
      props: z.object({
        title: z.string(),
        unit: z.string().nullable(),
        data: z.array(z.object({ label: z.string(), value: z.number().min(0) })),
      }),
      description: "Horizontal bar chart for comparing a few values.",
    },
    BulletList: {
      props: z.object({ title: z.string().nullable(), items: z.array(z.string()) }),
      description: "A titled bullet list (tips, packing list...).",
    },
    TextInput: {
      props: z.object({ label: z.string(), value: z.unknown(), placeholder: z.string().nullable() }),
      description: "Text field. Bind value with { $bindState: '/path' }.",
    },
    NumberInput: {
      props: z.object({ label: z.string(), value: z.unknown(), min: z.number().nullable(), max: z.number().nullable() }),
      description: "Number field. Bind value with { $bindState: '/path' }.",
    },
    Select: {
      props: z.object({ label: z.string(), value: z.unknown(), options: z.array(z.string()) }),
      description: "Dropdown. Bind value with { $bindState: '/path' }.",
    },
    Button: {
      props: z.object({ label: z.string(), variant: z.enum(["primary", "secondary"]).nullable() }),
      description: "Button. Emits 'press'; wire it with on.press -> action.",
    },
  },
  actions: {
    submitPreferences: { description: "Send the filled-in trip preferences form back to the agent." },
    replan: { description: "Ask the agent to start over with new preferences." },
  },
});

export type Catalog = typeof catalog;
