// Frontend Engineering Journal dashboard.
// Pure view: it renders data.json, which `journal export` / `journal serve` generate from Markdown.
// No framework, no innerHTML: every value from the data is inserted as text.

const SVG_NS = "http://www.w3.org/2000/svg";
const LEVELS = { excellent: "Excellent", good: "Good", minimum: "Minimum", partial: "Partial" };
const ACTIVITY_LABELS = { coding: "Coding", study: "Study", english: "English", typing: "Typing" };

/* ---------- DOM helpers ---------------------------------------------------------------- */

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value == null || value === false) continue;
    if (key === "class") el.className = value;
    else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
    else el.setAttribute(key, value === true ? "" : value);
  }
  el.append(...children.flat().filter((child) => child != null && child !== false));
  return el;
}

function s(tag, attrs = {}, ...children) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  el.append(...children.flat().filter(Boolean));
  return el;
}

/* ---------- formatting ----------------------------------------------------------------- */

const utcDate = (iso) => new Date(`${iso}T00:00:00Z`);
const dateFormat = (options) => new Intl.DateTimeFormat("en-US", { timeZone: "UTC", ...options });
const longDate = (iso) => dateFormat({ weekday: "long", month: "long", day: "numeric" }).format(utcDate(iso));
const fullDate = (iso) => dateFormat({ year: "numeric", month: "long", day: "numeric" }).format(utcDate(iso));
const shortDate = (iso) => dateFormat({ month: "short", day: "numeric" }).format(utcDate(iso));

function minutes(value) {
  const hours = Math.floor(value / 60);
  const rest = value % 60;
  if (hours && rest) return `${hours}h ${String(rest).padStart(2, "0")}m`;
  return hours ? `${hours}h` : `${rest}m`;
}

const percent = (value) => (value == null ? "–" : `${Math.round(value * 100)}%`);

/* ---------- components ----------------------------------------------------------------- */

function section(id, title, ...children) {
  return h("section", { class: "page-section", id, "aria-labelledby": `${id}-title` }, h("h2", { id: `${id}-title` }, title), ...children);
}

function block(title, ...children) {
  return h("div", { class: "block" }, title && h("h3", {}, title), ...children);
}

function rows(items) {
  return h(
    "dl",
    { class: "rows" },
    items.map(([label, value]) => h("div", { class: "row" }, h("dt", {}, label), h("dd", {}, value))),
  );
}

function progressBar(value, max, label) {
  const ratio = max > 0 ? Math.min(1, value / max) : 0;
  return h(
    "div",
    { class: "bar", role: "img", "aria-label": label },
    h("span", { style: `width:${(ratio * 100).toFixed(1)}%` }),
  );
}

function barRow(label, value, max, text) {
  return h("div", { class: "bar-row" }, h("span", {}, label), progressBar(value, max, `${label}: ${text}`), h("span", {}, text));
}

function emptyState(title, hint) {
  return h("div", { class: "empty" }, h("strong", {}, title), hint);
}

function externalLink(url, text) {
  return url ? h("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, text) : h("span", {}, text);
}

function badge(text, kind) {
  return h("span", { class: `badge${kind ? ` badge--${kind}` : ""}` }, text);
}

function dataTable(headers, body, numeric = []) {
  return h(
    "div",
    { class: "table-wrap" },
    h(
      "table",
      { class: "table" },
      h("thead", {}, h("tr", {}, headers.map((text, i) => h("th", { scope: "col", class: numeric.includes(i) ? "num" : null }, text)))),
      h("tbody", {}, body.map((row) => h("tr", {}, row.map((cell, i) => h("td", { class: numeric.includes(i) ? "num" : null }, cell))))),
    ),
  );
}

function figure(title, description, chart, table) {
  return h(
    "figure",
    { class: "block" },
    h("h3", {}, title),
    h("div", { class: "chart" }, chart),
    h("figcaption", { class: "meta" }, description),
    h("details", { class: "meta" }, h("summary", {}, "View data"), table),
  );
}

/* ---------- charts (inline SVG, no library) ---------------------------------------------- */

const CHART = { width: 720, height: 220, top: 12, right: 12, bottom: 28, left: 60 };

function frame(label) {
  return s("svg", { viewBox: `0 0 ${CHART.width} ${CHART.height}`, role: "img", "aria-label": label });
}

function plot() {
  return { w: CHART.width - CHART.left - CHART.right, h: CHART.height - CHART.top - CHART.bottom };
}

function yGrid(svg, max, format, target) {
  const { w, h: ph } = plot();
  const y = (value) => CHART.top + ph - (value / max) * ph;
  for (const value of [0, max / 2, max]) {
    svg.append(
      s("line", { class: "chart__grid", x1: CHART.left, x2: CHART.left + w, y1: y(value), y2: y(value) }),
      s("text", { class: "chart__label", x: CHART.left - 8, y: y(value) + 4, "text-anchor": "end" }, format(value)),
    );
  }
  if (target) {
    svg.append(
      s("line", { class: "chart__target", x1: CHART.left, x2: CHART.left + w, y1: y(target.value), y2: y(target.value) }),
      s("text", { class: "chart__label", x: CHART.left + w, y: y(target.value) - 4, "text-anchor": "end" }, target.label),
    );
  }
  return y;
}

function columnChart(points, { label, target, targetLabel }) {
  const svg = frame(label);
  const { w } = plot();
  const max = Math.ceil(Math.max(target, ...points.map((p) => p.value), 1) / 60) * 60;
  const y = yGrid(svg, max, minutes, { value: target, label: targetLabel });
  const slot = w / points.length;
  points.forEach((point, i) => {
    const top = y(point.value);
    svg.append(s("rect", { class: "chart__bar", x: CHART.left + i * slot + slot * 0.15, y: top, width: slot * 0.7, height: y(0) - top }));
    if (i % 7 === 0 || i === points.length - 1) {
      svg.append(s("text", { class: "chart__label", x: CHART.left + i * slot + slot / 2, y: CHART.height - 8, "text-anchor": "middle" }, shortDate(point.date)));
    }
  });
  return svg;
}

function lineChart(points, { label, target, targetLabel }) {
  const svg = frame(label);
  const { w } = plot();
  const values = points.map((p) => p.value);
  const max = Math.ceil(Math.max(target, ...values) / 10) * 10;
  const y = yGrid(svg, max, (v) => `${Math.round(v)}`, { value: target, label: targetLabel });
  const x = (i) => CHART.left + (points.length === 1 ? w / 2 : (i / (points.length - 1)) * w);
  svg.append(s("polyline", { class: "chart__line", points: points.map((p, i) => `${x(i)},${y(p.value)}`).join(" ") }));
  points.forEach((point, i) => svg.append(s("circle", { class: "chart__dot", cx: x(i), cy: y(point.value), r: 3 })));
  const anchors = [0, points.length - 1].filter((v, i, arr) => arr.indexOf(v) === i);
  anchors.forEach((i) => svg.append(s("text", { class: "chart__label", x: x(i), y: CHART.height - 8, "text-anchor": i === 0 ? "start" : "end" }, shortDate(points[i].date))));
  return svg;
}

/* ---------- sections ------------------------------------------------------------------- */

function overview(data) {
  const { today, weeks, signals, roadmap, meta, insights } = data;
  const targets = meta.targets.dailyMinutes;
  const week = weeks[weeks.length - 1];

  const todayBlock = today
    ? h(
        "div",
        { class: "panel" },
        h("p", { class: "meta" }, longDate(today.date)),
        h("p", {}, today.focus || "No focus set"),
        h(
          "div",
          {},
          data.activities.map((key) =>
            barRow(ACTIVITY_LABELS[key], today.minutes[key], targets[key], `${minutes(today.minutes[key])} / ${minutes(targets[key])}`),
          ),
        ),
      )
    : emptyState("No entry for today", h("span", {}, "Run ", h("code", {}, "journal new"), " to create today's log."));

  const weekBlock = week
    ? h(
        "div",
        {},
        data.activities.map((key) => {
          const goal = targets[key] * Math.max(week.expectedDays, 1);
          return barRow(ACTIVITY_LABELS[key], week.minutes[key], goal, minutes(week.minutes[key]));
        }),
        h("p", { class: "meta" }, `Week ${week.planWeek}: ${week.validDays} of ${week.expectedDays} study days logged. Bars compare against the daily target.`),
      )
    : emptyState("No weeks yet", "The program has not started.");

  const typing = signals.typing;
  const phase = roadmap.find((p) => p.current);
  const activeTopic = phase?.topics.find((t) => t.status === "active");
  const phaseIndex = phase ? roadmap.indexOf(phase) + 1 : null;

  return section(
    "overview",
    "Overview",
    block("Today", todayBlock),
    block("Weekly activity", weekBlock),
    h(
      "div",
      { class: "grid-2 block" },
      h(
        "div",
        { class: "panel" },
        h("h3", {}, "Engineering signals"),
        rows([
          ["Task completion (7 days)", percent(signals.taskCompletion)],
          ["AI independence (7 days)", percent(signals.aiIndependence)],
          ["Typing", typing.latest_wpm ? `${Math.round(typing.latest_wpm)} WPM${typing.latest_accuracy ? ` · ${Math.round(typing.latest_accuracy)}%` : ""}` : "–"],
          ["Mistakes resolved", `${signals.mistakes.resolved} / ${signals.mistakes.found}`],
          ["Streak", `${signals.streak.current} days`],
        ]),
      ),
      h(
        "div",
        { class: "panel" },
        h("h3", {}, "Current focus"),
        rows([
          ["Phase", phase ? `${phase.title} (${phaseIndex} of ${roadmap.length})` : "–"],
          ["Active topic", activeTopic ? activeTopic.title : "None set"],
          ["Program week", `${meta.week} of ${meta.weeks}`],
          ["Topics closed", `${signals.topics.closed} / ${signals.topics.total}`],
        ]),
      ),
    ),
    block("Notes", h("ul", { class: "divided" }, insights.map((text) => h("li", {}, text)))),
  );
}

function dailySection(data) {
  const days = data.daily;
  if (!days.length) {
    return section("daily", "Daily", emptyState("No daily entries yet", h("span", {}, "Run ", h("code", {}, "journal new"), " to start.")));
  }
  let index = days.length - 1;
  const body = h("div", { "aria-live": "polite" });
  const previous = h("button", { class: "button", type: "button", onclick: () => go(-1) }, "← Previous");
  const next = h("button", { class: "button", type: "button", onclick: () => go(1) }, "Next →");
  const title = h("h3", {});

  function text(label, value) {
    return value ? block(label, h("p", { class: "text-block" }, value)) : null;
  }

  function render() {
    const day = days[index];
    title.textContent = fullDate(day.date);
    previous.disabled = index === 0;
    next.disabled = index === days.length - 1;
    const meta = [
      ["Consistency level", day.excused ? "Excused" : (LEVELS[day.level] ?? "Below minimum")],
      ["AI usage", day.ai ?? "–"],
      ["Energy", day.energy ? `${day.energy} / 5` : "–"],
      ["Typing", day.typingWpm ? `${Math.round(day.typingWpm)} WPM${day.typingAccuracy ? ` · ${Math.round(day.typingAccuracy)}%` : ""}` : "–"],
    ];
    const parts = [
      block("Focus", h("p", {}, day.focus || "–")),
      block(
        "Tasks",
        day.tasks.length
          ? h(
              "ul",
              { class: "tasks" },
              day.tasks.map((task) =>
                h(
                  "li",
                  { class: task.done ? "task--done" : null },
                  h("span", { class: "task__mark", "aria-hidden": "true" }, task.done ? "✓" : "○"),
                  h("span", { class: "visually-hidden" }, task.done ? "Done: " : "Open: "),
                  h("span", {}, task.text),
                ),
              ),
            )
          : h("p", { class: "muted" }, "No tasks recorded."),
      ),
      block("Activity", rows(data.activities.map((key) => [ACTIVITY_LABELS[key], minutes(day.minutes[key])]))),
      text("Learned", day.learned),
      text("Built or solved", day.sections.built),
      text("Stuck on", day.sections.stuck),
      text("Notes", day.sections.notes),
      block("Details", rows(meta)),
    ];
    body.replaceChildren(...parts.filter(Boolean));
  }

  function go(step) {
    index = Math.min(days.length - 1, Math.max(0, index + step));
    render();
  }

  render();
  return section("daily", "Daily", h("div", { class: "pager" }, previous, title, next), body);
}

function progressSection(data) {
  const { series, signals, weeks, roadmap, meta } = data;
  const focused = series.focused.map((p) => ({ date: p.date, value: p.minutes }));
  const total = focused.reduce((sum, p) => sum + p.value, 0);
  const dailyTarget = Object.values(meta.targets.dailyMinutes).reduce((a, b) => a + b, 0);

  const focusedFigure = figure(
    "Focused time, last 28 days",
    `${minutes(total)} in total. The dashed line is the daily target (${minutes(dailyTarget)}).`,
    columnChart(focused, { label: `Focused minutes per day over the last 28 days, ${minutes(total)} in total`, target: dailyTarget, targetLabel: "target" }),
    dataTable(["Date", "Focused"], focused.filter((p) => p.value).map((p) => [shortDate(p.date), minutes(p.value)]), [1]),
  );

  const typing = series.typing.map((p) => ({ date: p.date, value: p.wpm, accuracy: p.accuracy }));
  const typingBlock = typing.length
    ? figure(
        "Typing speed",
        `Latest ${Math.round(typing[typing.length - 1].value)} WPM. Target ${meta.targets.typingWpm} WPM at ${meta.targets.typingAccuracy}% accuracy.`,
        lineChart(typing, { label: `Typing speed in words per minute, latest ${Math.round(typing[typing.length - 1].value)}`, target: meta.targets.typingWpm, targetLabel: `${meta.targets.typingWpm} WPM` }),
        dataTable(["Date", "WPM", "Accuracy"], typing.map((p) => [shortDate(p.date), Math.round(p.value), p.accuracy ? `${Math.round(p.accuracy)}%` : "–"]), [1, 2]),
      )
    : block("Typing speed", emptyState("No typing data yet", "Record typing_wpm in a daily file or an assessment."));

  const counts = signals.aiCounts;
  const logged = counts.independent + counts.hint + counts.explained;
  const aiBlock = block(
    "AI usage",
    logged
      ? h("div", {}, ["independent", "hint", "explained"].map((key) => barRow(key[0].toUpperCase() + key.slice(1), counts[key], logged, `${Math.round((counts[key] / logged) * 100)}%`)))
      : emptyState("No AI usage logged", "Set ai: independent, hint or explained in the daily file."),
    h("p", { class: "meta" }, "Self-reported, per day. The trend matters; no level is a failure."),
  );

  const recentWeeks = weeks.slice(-8);
  const weeksBlock = block(
    "Weekly trend",
    dataTable(
      ["Week", "Active days", "Focused", "Tasks done", "AI independence", "Mistakes fixed"],
      recentWeeks.map((w) => [`W${w.planWeek}${w.complete ? "" : " (in progress)"}`, `${w.validDays} / ${w.expectedDays}`, minutes(w.total), percent(w.completion), percent(w.independence), `${w.mistakesResolved} / ${w.mistakesFound}`]),
      [1, 2, 3, 4, 5],
    ),
  );

  const roadmapBlock = block(
    "Roadmap",
    h(
      "ul",
      { class: "divided" },
      roadmap.map((phase) =>
        h(
          "li",
          {},
          h(
            "details",
            { open: phase.current || null },
            h("summary", {}, `${phase.title} `, h("span", { class: "meta" }, `weeks ${phase.firstWeek}–${phase.lastWeek} · ${phase.closed} / ${phase.total} closed`)),
            h("div", { class: "details-body" }, progressBar(phase.closed, phase.total, `${phase.title}: ${phase.closed} of ${phase.total} topics closed`), h("ul", {}, phase.topics.map((t) => h("li", { class: "secondary" }, badge(t.status, t.status), " ", t.title)))),
          ),
        ),
      ),
    ),
  );

  return section("progress", "Progress", focusedFigure, typingBlock, aiBlock, weeksBlock, roadmapBlock);
}

function knowledgeSection(data) {
  const byId = new Map(data.roadmap.map((p) => [p.id, p]));
  const body = data.knowledge.length
    ? h(
        "ul",
        { class: "divided" },
        data.knowledge.map((note) => {
          const phase = byId.get(note.phase);
          return h(
            "li",
            {},
            h("p", {}, externalLink(note.url, note.title), " ", h("span", { class: "meta" }, note.path)),
            phase && h("ul", { class: "secondary" }, phase.topics.map((t) => h("li", { class: t.status === "closed" ? "" : "muted" }, `${t.status === "closed" ? "✓" : "○"} ${t.title}`))),
          );
        }),
      )
    : emptyState("No notes yet", h("span", {}, "Add Markdown files under ", h("code", {}, "knowledge/"), "."));
  return section("knowledge", "Knowledge", body, h("p", { class: "meta" }, "Notes live in Markdown. This page only links to them."));
}

function mistakesSection(data) {
  const list = data.mistakes;
  if (!list.length) {
    return section("mistakes", "Mistakes", emptyState("No mistakes documented", h("span", {}, "Run ", h("code", {}, "journal mistake \"title\" --area react"), " when you learn something the hard way.")));
  }
  const ordered = [...list].sort((a, b) => (a.status === b.status ? 0 : a.status === "open" ? -1 : 1));
  const open = list.filter((m) => m.status === "open").length;
  return section(
    "mistakes",
    "Mistakes",
    h("p", { class: "muted block" }, `${list.length} documented, ${open} open.`),
    h(
      "ol",
      { class: "divided" },
      ordered.map((m) =>
        h(
          "li",
          {},
          h(
            "details",
            {},
            h(
              "summary",
              {},
              m.title,
              " ",
              badge(m.status, m.status),
              " ",
              h("span", { class: "meta" }, `${m.area} · ${shortDate(m.date)}${m.recurred ? " · repeated" : ""}`),
            ),
            h(
              "div",
              { class: "details-body" },
              Object.entries(m.sections).map(([heading, value]) => h("div", {}, h("h4", {}, heading), h("p", { class: "text-block" }, value))),
              m.url && h("p", { class: "meta" }, externalLink(m.url, "Open the file")),
            ),
          ),
        ),
      ),
    ),
  );
}

function reviewsSection(data) {
  const group = (title, items, hint) =>
    block(title, items.length ? h("ul", { class: "divided" }, items.map((r) => h("li", {}, externalLink(r.url, r.title)))) : emptyState(`No ${title.toLowerCase()} reviews yet`, hint));
  return section(
    "reviews",
    "Reviews",
    group("Weekly", data.reviews.weekly, h("span", {}, "Run ", h("code", {}, "journal review week"), " on Friday.")),
    group("Phase", data.reviews.phase, h("span", {}, "Run ", h("code", {}, "journal review phase"), " at the end of a phase.")),
  );
}

/* ---------- boot ------------------------------------------------------------------------ */

function showError(main, errors) {
  main.replaceChildren(
    h("div", { class: "error", role: "alert" }, h("h2", {}, "The dashboard could not be built"), h("p", {}, "Fix these files and refresh the page."), h("ul", {}, errors.map((e) => h("li", {}, e)))),
  );
}

function watchNavigation() {
  const links = [...document.querySelectorAll(".site-nav a")];
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        links.forEach((link) => {
          if (link.hash === `#${entry.target.id}`) link.setAttribute("aria-current", "true");
          else link.removeAttribute("aria-current");
        });
      }
    },
    { rootMargin: "-30% 0px -60% 0px" },
  );
  document.querySelectorAll(".page-section").forEach((el) => observer.observe(el));
}

async function boot() {
  const main = document.getElementById("main");
  let data;
  try {
    const response = await fetch("data.json", { cache: "no-store" });
    const payload = await response.json();
    if (!response.ok) return showError(main, payload.error ?? [`HTTP ${response.status}`]);
    data = payload;
  } catch {
    return showError(main, ["Could not load data.json. Start the dashboard with `journal serve`."]);
  }
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-US", { timeZone: "UTC", year: "numeric", month: "long" })
      .formatToParts(utcDate(data.meta.today))
      .map((part) => [part.type, part.value]),
  );
  document.getElementById("period").textContent = `${parts.year} · ${parts.month}`;
  main.replaceChildren(overview(data), dailySection(data), progressSection(data), knowledgeSection(data), mistakesSection(data), reviewsSection(data));
  watchNavigation();
}

boot();
