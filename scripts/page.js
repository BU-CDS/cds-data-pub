// Catalog page behaviour: tag and text filter kept in the URL, copy buttons, popovers,
// clamped descriptions. No network, storage or cookies (check_page enforces this).
(() => {
  "use strict";
  const d = document;
  const q = d.getElementById("q");
  if (!q) return;
  const $$ = (sel, root = d) => Array.from(root.querySelectorAll(sel));
  const cards = $$(".ds");
  const chips = $$(".chip");
  const live = d.getElementById("live");
  const toc = new Map($$(".toc a").map((a) => [a.hash.slice(1), a.parentElement]));
  const tags = new Map(cards.map((c) => [c, c.dataset.tags.split(" ")]));
  const selected = new Set();
  // Below 1100px the sidebar block is sticky and its height varies (Clear filters, open chips):
  // anchor jumps leave room for it via --stick (scroll-padding-top).
  const side = d.querySelector(".side");
  const stick = () => d.documentElement.style.setProperty("--stick", `${side.offsetHeight + 8}px`);
  new ResizeObserver(stick).observe(side);
  const say = (msg) => {
    live.textContent = "";
    setTimeout(() => { live.textContent = msg; }, 50);
  };
  const hit = (card, extra) => {
    const want = extra ? [...selected, extra] : [...selected];
    const text = q.value.trim().toLowerCase();
    return want.every((t) => tags.get(card).includes(t)) &&
      (!text || card.dataset.text.includes(text));
  };

  function apply() {
    let shown = 0;
    for (const card of cards) {
      const on = hit(card);
      card.hidden = !on;
      if (toc.has(card.id)) toc.get(card.id).hidden = !on;
      shown += on ? 1 : 0;
    }
    for (const chip of chips) {
      const on = selected.has(chip.dataset.tag);
      const n = on ? shown : cards.filter((c) => hit(c, chip.dataset.tag)).length;
      chip.setAttribute("aria-pressed", String(on));
      chip.disabled = !on && n === 0;
      chip.querySelector(".n").textContent = n;
      chip.querySelector(".sr").textContent = n === 1 ? " dataset" : " datasets";
    }
    const active = selected.size > 0 || q.value.trim() !== "";
    d.querySelector(".count").textContent = `${shown} of ${cards.length} datasets`;
    d.querySelector(".filters .clear").hidden = !active;
    d.querySelector(".empty").hidden = shown > 0 || cards.length === 0;
    d.querySelector(".fcount").textContent = selected.size ? ` (${selected.size})` : "";
    const p = new URLSearchParams(location.search); // keep utm_*, gclid and the like
    p.delete("q");
    p.delete("tag");
    if (q.value.trim()) p.set("q", q.value.trim());
    selected.forEach((t) => p.append("tag", t));
    const s = p.toString();
    history.replaceState(history.state, "", location.pathname + (s ? `?${s}` : "") + location.hash);
    stick();
  }

  // Sidebar list: fade its bottom edge while more entries are below. Its size changes with the
  // window, filtering and "More tags", so watch it rather than each cause.
  const tocNav = d.querySelector(".toc");
  if (tocNav) {
    const edge = () => {
      const below = tocNav.scrollTop + tocNav.clientHeight < tocNav.scrollHeight - 2;
      tocNav.classList.toggle("more-below", below);
    };
    tocNav.addEventListener("scroll", edge);
    const watch = new ResizeObserver(edge);
    watch.observe(tocNav);
    watch.observe(tocNav.firstElementChild);
  }

  function clearAll() {
    selected.clear();
    q.value = "";
    apply();
  }

  // Descriptions: clamp to two lines only when they overflow.
  // Measured before filtering, while every card is still visible.
  for (const desc of $$(".desc")) {
    const more = desc.nextElementSibling;
    more.setAttribute("aria-describedby", `t-${desc.closest(".ds").id}`);
    const first = desc.firstElementChild;
    desc.classList.add("clamp");
    const overflow = desc.children.length > 1 || first.scrollHeight > first.clientHeight + 1;
    if (!overflow) {
      desc.classList.remove("clamp");
      continue;
    }
    more.hidden = false;
    more.addEventListener("click", () => {
      const open = !desc.classList.toggle("clamp");
      more.textContent = open ? "less" : "more";
      more.setAttribute("aria-expanded", String(open));
    });
  }

  const params = new URLSearchParams(location.search);
  q.value = params.get("q") || "";
  for (const t of params.getAll("tag")) {
    if (chips.some((c) => c.dataset.tag === t)) selected.add(t);
  }
  $$(cards.length ? ".filters, .copy" : ".copy").forEach((el) => { el.hidden = false; });
  apply();
  const target = location.hash && d.getElementById(location.hash.slice(1));
  // Wide screens scroll the list, not the page: keep its position across reload and Back in
  // the history entry (no storage).
  const list = d.querySelector(".list");
  let saving = 0;
  list.addEventListener("scroll", () => {
    clearTimeout(saving);
    saving = setTimeout(() => {
      history.replaceState({ ...history.state, listTop: list.scrollTop }, "");
    }, 150);
  });
  if (target) {
    if (target.hidden) clearAll();
    target.scrollIntoView(); // again, now that the sticky bar has its final height
  } else if (history.state && history.state.listTop) {
    list.scrollTop = history.state.listTop;
  }

  q.addEventListener("input", apply);
  for (const chip of chips) {
    chip.addEventListener("click", () => {
      const t = chip.dataset.tag;
      if (!selected.delete(t)) selected.add(t);
      apply();
    });
  }
  $$(".clear").forEach((b) => b.addEventListener("click", clearAll));
  for (const a of $$("a.tag")) {
    a.addEventListener("click", (ev) => {
      ev.preventDefault();
      selected.add(new URL(a.href).searchParams.get("tag"));
      apply();
      list.scrollTop = 0; // the top of the filtered results (wide screens)
      d.querySelector("main").scrollIntoView(); // (phones)
    });
  }
  const moreTags = d.querySelector(".more-tags");
  if (moreTags) {
    moreTags.addEventListener("click", () => {
      d.querySelector(".chips").classList.add("all");
      moreTags.hidden = true;
      d.querySelector(".chip.extra").focus(); // focus would otherwise drop to <body>
    });
  }
  const toggle = d.querySelector(".ftoggle");
  toggle.addEventListener("click", () => {
    const open = d.getElementById("chips").classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });

  for (const button of $$(".copy")) {
    button.setAttribute("aria-describedby", `t-${button.closest(".ds").id}`);
    button.addEventListener("click", () => {
      const text = button.parentElement.querySelector("code").textContent;
      const done = (ok) => {
        const msg = ok ? "Copied" : "Copy failed — select the text";
        button.textContent = msg;
        say(msg);
        setTimeout(() => { button.textContent = "Copy"; }, 1500);
      };
      if (!navigator.clipboard) return done(false);
      navigator.clipboard.writeText(text).then(() => done(true), () => done(false));
    });
  }

  const pops = $$("details.pop");
  for (const pop of pops) {
    pop.addEventListener("toggle", () => {
      if (!pop.open) return;
      pops.forEach((o) => { if (o !== pop) o.open = false; });
      pop.querySelector(".pop-body").scrollIntoView({ block: "nearest" }); // not cut off by the list
    });
    pop.addEventListener("focusout", (ev) => {
      // Tab out closes it (WCAG 2.4.11). A click on plain text inside does not: focus then goes
      // nowhere (relatedTarget null) or to a focusable ancestor such as the scrolling list.
      const to = ev.relatedTarget;
      if (to && !pop.contains(to) && !to.contains(pop)) pop.open = false;
    });
  }
  // An outside click closes popovers, unless the press began inside one (a drag-select
  // that ends outside must not close the popover it selects in).
  let pressedIn = null;
  d.addEventListener("pointerdown", (ev) => {
    pressedIn = pops.find((p) => p.contains(ev.target));
  });
  d.addEventListener("click", (ev) => {
    pops.forEach((p) => {
      if (p.open && !p.contains(ev.target) && p !== pressedIn) p.open = false;
    });
    pressedIn = null;
  });
  d.addEventListener("keydown", (ev) => {
    if (ev.key !== "Escape") return;
    const open = pops.find((p) => p.open);
    if (!open) return;
    const inside = open.contains(d.activeElement);
    open.open = false;
    if (inside) open.querySelector("summary").focus();
  });
})();
