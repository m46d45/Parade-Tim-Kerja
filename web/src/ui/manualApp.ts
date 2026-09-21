/**
 * Manual belajar — render MANUAL.md (Streamlit tab_manual).
 */

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string> = {},
  children: (Node | string)[] = [],
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "className") node.className = v;
    else node.setAttribute(k, v);
  }
  for (const c of children) {
    node.append(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return node;
}

/** Slug for header ids — match GitHub / MANUAL.md TOC anchors. */
export function mdSlug(text: string): string {
  return text
    .toLowerCase()
    .replace(/[''`´]/g, "")
    .replace(/[^\p{L}\p{N}\s-]/gu, "")
    .trim()
    .replace(/\s+/g, "-");
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inline(s: string): string {
  return escapeHtml(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_m, label: string, href: string) => {
      const safeHref = escapeHtml(href);
      if (href.startsWith("http://") || href.startsWith("https://")) {
        return `<a href="${safeHref}" target="_blank" rel="noopener">${label}</a>`;
      }
      return `<a href="${safeHref}">${label}</a>`;
    });
}

/** Lightweight markdown → HTML for MANUAL.md (headers, lists, tables, links, code). */
export function renderManualMarkdown(md: string): string {
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  let i = 0;
  let inUl = false;
  let inOl = false;
  let inTable = false;
  let tableRows: string[][] = [];
  let tocMode = false;

  const closeLists = () => {
    if (inUl) {
      out.push("</ul>");
      inUl = false;
    }
    if (inOl) {
      out.push(tocMode ? '</ol></nav>' : "</ol>");
      inOl = false;
      tocMode = false;
    }
  };

  const flushTable = () => {
    if (!inTable || !tableRows.length) return;
    const [header, ...body] = tableRows;
    out.push("<table><thead><tr>");
    for (const h of header) out.push(`<th>${inline(h)}</th>`);
    out.push("</tr></thead><tbody>");
    for (const row of body) {
      if (row.every((c) => /^[\s|:|-]+$/.test(c))) continue;
      out.push("<tr>");
      for (const c of row) out.push(`<td>${inline(c)}</td>`);
      out.push("</tr>");
    }
    out.push("</tbody></table>");
    inTable = false;
    tableRows = [];
  };

  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith("|") && line.includes("|", 1)) {
      closeLists();
      const cells = line
        .split("|")
        .slice(1, -1)
        .map((c) => c.trim());
      if (!inTable) {
        inTable = true;
        tableRows = [];
      }
      tableRows.push(cells);
      i++;
      continue;
    }
    if (inTable) flushTable();

    if (/^#{1,3}\s/.test(line)) {
      closeLists();
      const level = line.match(/^#+/)![0].length;
      const text = line.replace(/^#+\s*/, "");
      const id = mdSlug(text);
      const cls = text.toLowerCase() === "daftar isi" ? ' class="manual-toc-heading"' : "";
      out.push(`<h${level} id="${id}"${cls}>${inline(text)}</h${level}>`);
      if (text.toLowerCase() === "daftar isi") tocMode = true;
      i++;
      continue;
    }
    if (/^---+$/.test(line.trim())) {
      closeLists();
      out.push("<hr>");
      i++;
      continue;
    }
    if (/^[-*]\s+/.test(line)) {
      if (inOl) {
        out.push(tocMode ? '</ol></nav>' : "</ol>");
        inOl = false;
        tocMode = false;
      }
      if (!inUl) {
        out.push("<ul>");
        inUl = true;
      }
      out.push(`<li>${inline(line.replace(/^[-*]\s+/, ""))}</li>`);
      i++;
      continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      if (inUl) {
        out.push("</ul>");
        inUl = false;
      }
      if (!inOl) {
        out.push(
          tocMode
            ? '<nav class="manual-toc" aria-label="Daftar isi"><ol>'
            : "<ol>",
        );
        inOl = true;
      }
      out.push(`<li>${inline(line.replace(/^\d+\.\s+/, ""))}</li>`);
      i++;
      continue;
    }
    if (line.trim() === "") {
      closeLists();
      i++;
      continue;
    }
    closeLists();
    out.push(`<p>${inline(line)}</p>`);
    i++;
  }
  closeLists();
  flushTable();
  return out.join("\n");
}

export function mountManual(root: HTMLElement): void {
  root.replaceChildren();

  const body = el("div", { className: "manual-body" }, ["Memuat MANUAL.md…"]);
  const dl = el("a", {
    className: "btn-link",
    href: "/MANUAL.md",
    download: "Parade_Tim_Kerja_Manual.md",
  }, ["⬇ Unduh MANUAL.md"]);

  root.append(
    el("div", { className: "panel mode-panel" }, [
      el("h2", {}, ["📖 Manual"]),
      el("div", { className: "btn-row" }, [dl]),
      body,
      el("hr"),
      el("p", { className: "note" }, [
        "Parade Tim Kerja · zone-flow · 5 tim · batch default 4",
      ]),
    ]),
  );

  body.addEventListener("click", (ev) => {
    const a = (ev.target as HTMLElement).closest("a[href^='#']") as HTMLAnchorElement | null;
    if (!a) return;
    const id = decodeURIComponent(a.getAttribute("href")!.slice(1));
    const target = document.getElementById(id);
    if (target && body.contains(target)) {
      ev.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });

  void (async () => {
    try {
      const res = await fetch("/MANUAL.md");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const md = await res.text();
      body.innerHTML = renderManualMarkdown(md);
    } catch (e) {
      body.textContent =
        e instanceof Error
          ? `MANUAL.md tidak ditemukan: ${e.message}`
          : "MANUAL.md tidak ditemukan.";
    }
  })();
}
