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
    // Every word must appear, in any order: "boston trees" finds "Boston street and park trees".
    const words = q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return want.every((t) => tags.get(card).includes(t)) &&
      words.every((w) => card.dataset.text.includes(w));
  };

  function apply() {
    let shown = 0;
    for (const card of cards) {
      const on = hit(card);
      card.hidden = !on;
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
    // Tags go in the URL; search text never does, so analytics page views cannot carry it
    const p = new URLSearchParams(location.search); // keep utm_*, gclid and the like
    p.delete("q");
    p.delete("tag");
    selected.forEach((t) => p.append("tag", t));
    const s = p.toString();
    history.replaceState(history.state, "", location.pathname + (s ? `?${s}` : "") + location.hash);
    stick();
  }

  function clearAll() {
    selected.clear();
    q.value = "";
    apply();
  }

  // Descriptions: clamp to two lines only when they overflow. Measured first before filtering,
  // while every card is still visible, then again when the width changes (a page loaded narrow
  // and widened kept "more" buttons that did nothing). A description the reader opened stays open;
  // a hidden card cannot be measured and keeps its last state.
  const descs = $$(".desc");
  const measure = (desc) => {
    const more = desc.nextElementSibling;
    if (more.getAttribute("aria-expanded") === "true" || desc.closest(".ds").hidden) return;
    const first = desc.firstElementChild;
    desc.classList.add("clamp");
    const overflow = desc.children.length > 1 || first.scrollHeight > first.clientHeight + 1;
    desc.classList.toggle("clamp", overflow);
    more.hidden = !overflow;
  };
  for (const desc of descs) {
    const more = desc.nextElementSibling;
    more.setAttribute("aria-describedby", `t-${desc.closest(".ds").id}`);
    more.addEventListener("click", () => {
      const open = !desc.classList.toggle("clamp");
      more.textContent = open ? "less" : "more";
      more.setAttribute("aria-expanded", String(open));
    });
    measure(desc);
  }
  let lastWidth = innerWidth, remeasure = 0;
  addEventListener("resize", () => {
    if (innerWidth === lastWidth) return; // height-only changes (mobile toolbars) wrap nothing
    lastWidth = innerWidth;
    clearTimeout(remeasure);
    remeasure = setTimeout(() => descs.forEach(measure), 150);
  });

  // Long column lists: show the first names, "Show all", and a filter over every name.
  for (const box of $$(".colq")) {
    const list = box.nextElementSibling.nextElementSibling;
    const count = box.nextElementSibling;
    const all = list.nextElementSibling;
    const names = $$("li", list);
    const label = all.textContent;
    list.classList.add("clip");
    box.hidden = all.hidden = false;
    all.addEventListener("click", () => {
      const open = !list.classList.toggle("clip");
      all.textContent = open ? "Show fewer" : label;
      all.setAttribute("aria-expanded", String(open));
    });
    box.addEventListener("input", () => {
      const text = box.value.trim().toLowerCase();
      list.classList.toggle("filtering", text !== "");
      let shown = 0;
      for (const li of names) {
        li.hidden = text !== "" && !li.textContent.toLowerCase().includes(text);
        shown += li.hidden ? 0 : 1;
      }
      count.hidden = text === "";
      count.textContent = shown ? `${shown} of ${names.length} match` : "No column names match";
      all.hidden = text !== "";
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
  // The list scrolls on its own only in the app shell; elsewhere it is no tab stop.
  const shell = matchMedia("(min-width:1100px) and (min-height:38em)");
  const tabStop = () => { list.tabIndex = shell.matches ? 0 : -1; };
  shell.addEventListener("change", tabStop);
  tabStop();
  const refilter = () => {
    apply();
    list.scrollTop = 0; // the top of the filtered results (wide screens)
  };

  q.addEventListener("input", refilter);
  for (const chip of chips) {
    chip.addEventListener("click", () => {
      const t = chip.dataset.tag;
      if (!selected.delete(t)) selected.add(t);
      refilter();
    });
  }
  $$(".clear").forEach((b) => b.addEventListener("click", () => {
    clearAll();
    list.scrollTop = 0;
    q.focus(); // the empty state's Clear filters would leave focus nowhere (it hides itself)
  }));
  for (const a of $$("a.tag")) {
    a.addEventListener("click", (ev) => {
      ev.preventDefault();
      selected.add(new URL(a.href).searchParams.get("tag"));
      refilter();
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

  // Copy link: the dataset's own address (#slug), for sharing one dataset.
  for (const button of $$(".btn.link")) {
    button.hidden = false;
    button.addEventListener("click", () => {
      const url = new URL(button.dataset.link, location.href).href;
      const done = (msg) => {
        button.textContent = msg;
        say(msg);
        setTimeout(() => { button.textContent = "Copy link"; }, 1500);
      };
      if (!navigator.clipboard) {
        history.replaceState(history.state, "", url); // the address bar now holds the link
        return done("Link in address bar");
      }
      navigator.clipboard.writeText(url).then(() => done("Link copied"), () => {
        history.replaceState(history.state, "", url);
        done("Link in address bar");
      });
    });
  }

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
    // A taller tab (Shell, AWS CLI…) can push the body past the list's edge after it opened.
    pop.addEventListener("change", () => {
      pop.querySelector(".pop-body").scrollIntoView({ block: "nearest" });
    });
    pop.addEventListener("focusout", (ev) => {
      // Tab out closes it (WCAG 2.4.11). A click on plain text inside does not: focus then goes
      // nowhere or to a focusable ancestor such as the list, after a press inside (pressedIn).
      const to = ev.relatedTarget;
      if (to && !pop.contains(to) && pressedIn !== pop) pop.open = false;
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
