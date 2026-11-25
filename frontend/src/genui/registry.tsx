/**
 * React implementations for every catalog component. The agent can only ever
 * reference these by name; it never ships code or HTML to the browser.
 */
import { defineRegistry, useBoundProp } from "@json-render/react";
import { catalog } from "./catalog";

const CATEGORY_ICON: Record<string, string> = {
  food: "🍽", sight: "🏛", activity: "🎟", transport: "🚆", stay: "🛏",
};

const eur = (n: number) => `€${Math.round(n).toLocaleString("en")}`;

export const { registry } = defineRegistry(catalog, {
  components: {
    Stack: ({ props, children }) => (
      <div className={`stack ${props.direction ?? "vertical"} gap-${props.gap ?? "md"}`}>{children}</div>
    ),
    Heading: ({ props }) => {
      const Tag = (`h${props.level ?? 2}`) as "h1" | "h2" | "h3";
      return <Tag className="heading">{props.text}</Tag>;
    },
    Text: ({ props }) => <p className={`text ${props.tone ?? "default"}`}>{props.text}</p>,
    Card: ({ props, children }) => (
      <section className="card" aria-label={props.title}>
        <header>
          <h3>{props.title}</h3>
          {props.subtitle && <span className="muted">{props.subtitle}</span>}
        </header>
        <div className="card-body">{children}</div>
      </section>
    ),
    Stat: ({ props }) => (
      <div className="stat" data-testid="stat">
        <span className="stat-label">{props.label}</span>
        <strong className="stat-value">{props.value}</strong>
      </div>
    ),
    DayCard: ({ props }) => (
      <article className="day-card" data-testid="day-card">
        <h3><span className="day-badge">Day {props.day}</span> {props.title}</h3>
        <ol>
          {props.activities.map((a, i) => (
            <li key={i}>
              <time>{a.time}</time>
              <span aria-hidden>{CATEGORY_ICON[a.category]}</span>
              <span className="grow">{a.name}</span>
              <span className="muted">{a.cost ? eur(a.cost) : "free"}</span>
            </li>
          ))}
        </ol>
      </article>
    ),
    Table: ({ props }) => (
      <table className="table">
        <thead><tr>{props.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {props.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}
        </tbody>
      </table>
    ),
    BarChart: ({ props }) => {
      const max = Math.max(1, ...props.data.map((d) => d.value));
      return (
        <figure className="bar-chart" aria-label={props.title}>
          <figcaption>{props.title}</figcaption>
          {props.data.map((d) => (
            <div className="bar-row" key={d.label}>
              <span className="bar-label">{d.label}</span>
              <span className="bar-track">
                <span className="bar" style={{ width: `${(d.value / max) * 100}%` }} />
              </span>
              <span className="bar-value">{props.unit === "€" ? eur(d.value) : `${d.value}${props.unit ?? ""}`}</span>
            </div>
          ))}
        </figure>
      );
    },
    BulletList: ({ props }) => (
      <div className="bullets">
        {props.title && <h4>{props.title}</h4>}
        <ul>{props.items.map((t, i) => <li key={i}>{t}</li>)}</ul>
      </div>
    ),
    TextInput: ({ props, bindings }) => {
      const [value, setValue] = useBoundProp<string>(props.value as string, bindings?.value);
      return (
        <label className="field">
          <span>{props.label}</span>
          <input value={value ?? ""} placeholder={props.placeholder ?? ""} onChange={(e) => setValue(e.target.value)} />
        </label>
      );
    },
    NumberInput: ({ props, bindings }) => {
      const [value, setValue] = useBoundProp<number>(props.value as number, bindings?.value);
      return (
        <label className="field">
          <span>{props.label}</span>
          <input
            type="number"
            value={value ?? ""}
            min={props.min ?? undefined}
            max={props.max ?? undefined}
            onChange={(e) => setValue(e.target.value === "" ? (undefined as unknown as number) : Number(e.target.value))}
          />
        </label>
      );
    },
    Select: ({ props, bindings }) => {
      const [value, setValue] = useBoundProp<string>(props.value as string, bindings?.value);
      return (
        <label className="field">
          <span>{props.label}</span>
          <select value={value ?? ""} onChange={(e) => setValue(e.target.value)}>
            {props.options.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </label>
      );
    },
    Button: ({ props, emit, loading }) => (
      <button className={`btn ${props.variant ?? "primary"}`} disabled={loading} onClick={() => emit("press")}>
        {props.label}
      </button>
    ),
  },
  // Type-level stubs only: the real handlers need React callbacks (talk to the
  // agent), so GenerativeView passes them to <JSONUIProvider handlers={...}>.
  actions: {
    submitPreferences: async () => {},
    replan: async () => {},
  },
});
