"""Render the catalog page: sidebar filter, compact cards, Cite / Get data popovers.

Header, footer, palette and phone rules descend from pub-cds-scc (cluster.cds.bu.edu), which is
light-only by design; so is this page. Every manifest string is escaped here. Behaviour lives in
scripts/page.js, embedded once; check_page admits it by sha256.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import quote

from scripts import cite, snippets
from scripts.manifest import Catalog, DataFile, Dataset, license_url

UNITS = ("KiB", "MiB", "GiB", "TiB", "PiB")
FILES_SHOWN = 5  # longer file lists collapse into a native <details> toggle
TAGS_SHOWN = 12  # more tags sit behind "More tags"
PREVIEW_MARK = '<meta name="cds-build" content="preview">'
PAGE_JS = Path(__file__).with_name("page.js").read_text(encoding="utf-8")

# Colour tokens (light only, like cluster.cds.bu.edu).
TOKENS = {
    "bg": "#f2efec",
    "surface": "#ffffff",
    "surface2": "#ebe6e0",
    "text": "#2d2926",
    "muted": "#6b6158",
    "border": "#dcd5cd",
    "accent": "#0b7468",
    "on-accent": "#ffffff",
    "focus": "#0b7468",
    "shadow": "rgba(15,30,45,.10)",
    "code-bg": "#2d2926",
    "code-fg": "#f2efec",
    "chip-on-bg": "#2d2926",
    "chip-on-fg": "#ffffff",
}
CONTRAST_TEXT = (  # >= 4.5:1
    ("text", "bg"),
    ("text", "surface"),
    ("text", "surface2"),
    ("muted", "bg"),
    ("muted", "surface"),
    ("muted", "surface2"),
    ("accent", "bg"),
    ("accent", "surface"),
    ("accent", "surface2"),
    ("on-accent", "accent"),
    ("code-fg", "code-bg"),
    ("chip-on-fg", "chip-on-bg"),
)
CONTRAST_UI = (("focus", "bg"), ("focus", "surface"))  # >= 3:1 (focus ring)


def _vars() -> str:
    return ";".join(f"--{name}:{value}" for name, value in TOKENS.items())


CSS = """\
:root{--t-sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;\
--t-mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;\
--content-max:1920px;--content-pad:12px;}
@font-face{font-family:"Whitney SSm A";font-weight:600;font-style:normal;font-display:swap;\
src:url("@@FONT_SEMIBOLD@@") format("woff2");}
@font-face{font-family:"Whitney SSm A";font-weight:400;font-style:normal;font-display:swap;\
src:url("@@FONT_BOOK@@") format("woff2");}
[hidden]{display:none!important}
*{box-sizing:border-box}html{font-size:110%;}\
body{display:flex;flex-direction:column;min-height:100vh;min-height:100dvh;\
font-family:var(--t-sans);color:var(--text);margin:0;background:var(--bg);font-size:1rem;\
line-height:1.45;-webkit-font-smoothing:antialiased;}
header{background:#2d2926;color:#ffffff;padding:12px var(--content-pad);position:relative;\
border-top:3px solid #cc0000;border-bottom:1px solid rgba(255,255,255,.08);}\
header h1{font-size:1rem;margin:0;font-weight:600;letter-spacing:-.01em;\
font-family:"Whitney SSm A",var(--t-sans);}\
.buplate{height:1.615em;vertical-align:-.449em;margin-right:.34em;}\
.orgname{font-weight:400;letter-spacing:0;}\
.hsep{color:rgba(255,255,255,.4);font-weight:400;padding:0 .6em;}
.hwrap{max-width:min(var(--content-max),98vw);margin:0 auto;display:flex;align-items:baseline;\
gap:14px;flex-wrap:wrap;}
@media(max-width:700px){.hsep{display:block;height:0;padding:0;overflow:hidden;}}\
@media(max-width:480px){header h1{font-size:0.9rem;}}
a{color:var(--accent);}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px;}
button{font:inherit;}
.wrap{max-width:min(var(--content-max),98vw);width:100%;margin:0 auto;\
padding:14px var(--content-pad) 60px;flex:1 0 auto;display:grid;\
grid-template-columns:minmax(0,1fr);\
gap:20px;}
@media(min-width:1100px){.wrap{grid-template-columns:270px minmax(0,1fr);}\
.side-in{max-height:100%;display:flex;flex-direction:column;gap:12px;}\
.filters,.toc-box{border:1px solid var(--border);border-radius:10px;\
background:var(--surface2);padding:10px 12px;}\
.toc-box{display:flex;flex-direction:column;min-height:0;}.toc-box .toc-hd{margin-top:0;}\
.side .chip{background:var(--surface);}}
main{min-width:0;}
.hdr-tag{display:inline-block;margin-left:.6em;padding:1px 8px;border-radius:999px;\
background:#cc0000;color:#ffffff;font-size:0.7em;font-weight:600;letter-spacing:.04em;vertical-align:.15em;}
.intro p{margin:0 0 8px;}
.summary{color:var(--muted);font-size:0.875rem;margin:0 0 12px;font-variant-numeric:tabular-nums;}
.side input[type=search]{width:100%;padding:7px 9px;border:1px solid var(--muted);\
border-radius:6px;background:var(--surface);color:var(--text);font:inherit;}
.chips-hd{font-size:0.875rem;color:var(--muted);margin:10px 0 4px;}
.chips{display:flex;flex-wrap:wrap;gap:4px;}
.chip{border:1px solid var(--border);background:var(--surface2);color:var(--text);\
border-radius:999px;padding:2px 9px;font-size:0.875rem;cursor:pointer;\
font-variant-numeric:tabular-nums;}
.chip .n{color:var(--muted);}
.chip[aria-pressed=true]{background:var(--chip-on-bg);color:var(--chip-on-fg);\
border-color:var(--chip-on-bg);}.chip[aria-pressed=true]::before{content:"\\2713\\00a0";}
.chip[aria-pressed=true] .n{color:inherit;}
.chip:disabled{cursor:default;opacity:.6;}
.chip.extra{display:none;}\
.chips.all .chip.extra,.chip.extra[aria-pressed=true]{display:inline-block;}
.more-tags,.clear,.more,.ftoggle{background:none;border:0;padding:4px 0;\
color:var(--accent);\
cursor:pointer;font-size:0.875rem;text-decoration:underline;}
.ftoggle{display:none;}
.count{font-size:0.875rem;color:var(--muted);margin:8px 0 2px;font-variant-numeric:tabular-nums;}
.toc-hd{font-size:0.8rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);\
margin:14px 0 4px;}
.toc{overflow:auto;min-height:0;padding:4px;scroll-padding-block:3.5rem;}
.toc ol{list-style:none;margin:0;padding:0;}
.toc a{display:flex;justify-content:space-between;gap:8px;padding:3px 4px;border-radius:4px;\
color:var(--text);text-decoration:none;font-size:0.875rem;}.toc a:hover{background:var(--surface);}
.toc .t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.toc .sz,.flist .sz{color:var(--muted);white-space:nowrap;font-variant-numeric:tabular-nums;}
@media(max-width:1099px){.toc-box{display:none;}.ftoggle{display:inline-block;}\
.chips-wrap:not(.open){display:none;}}
.ds{background:var(--surface);border:1px solid var(--border);border-radius:8px;\
box-shadow:0 1px 2px var(--shadow);padding:14px 16px;margin:0 0 14px;}
.ds-hd{display:flex;align-items:flex-start;gap:12px;}
.ds h2{flex:1;min-width:0;font-family:"Whitney SSm A",var(--t-sans);font-size:1.125rem;\
font-weight:600;\
margin:0;overflow-wrap:anywhere;}
.acts{display:flex;gap:6px;flex-shrink:0;}
.meta{color:var(--muted);font-size:0.875rem;margin:4px 0 6px;font-variant-numeric:tabular-nums;\
overflow-wrap:anywhere;}
.badges{display:flex;flex-wrap:wrap;gap:4px;margin:0 0 8px;}
.lic,.tag{border:1px solid var(--border);background:var(--surface2);color:var(--text);\
border-radius:999px;padding:1px 8px;font-size:0.875rem;text-decoration:none;}.lic{font-weight:600;}
.desc{max-width:80ch;}.desc p{margin:0 0 6px;}.desc p:last-child{margin-bottom:0;}
.desc.clamp p:not(:first-child){display:none;}\
.desc.clamp p:first-child{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;\
line-clamp:2;overflow:hidden;}
.toc.more-below{-webkit-mask-image:linear-gradient(to bottom,#000 80%,transparent);\
mask-image:linear-gradient(to bottom,#000 80%,transparent);}
details.det>summary{cursor:pointer;color:var(--accent);font-size:0.875rem;padding:6px 0;}
.src,.contact{font-size:0.875rem;margin:4px 0;overflow-wrap:anywhere;}
.files{width:100%;border-collapse:collapse;font-size:0.875rem;margin-top:6px;}
.files th{text-align:left;font-weight:600;color:var(--muted);border-bottom:1px solid var(--border);\
padding:4px 8px 4px 0;}
.files td{border-bottom:1px solid var(--border);padding:5px 8px 5px 0;vertical-align:top;}
.files .fn{overflow-wrap:anywhere;}.files .sz{white-space:nowrap;font-variant-numeric:tabular-nums;}
.files code{font-family:var(--t-mono);font-size:0.8rem;color:var(--muted);overflow-wrap:anywhere;\
word-break:break-all;}
@media(min-width:900px){.files{table-layout:fixed;}.files .sz{width:6em;}.files .hash{width:30rem;}}
@media(max-width:600px){.files thead{display:none;}\
.files,.files tbody,.files tr,.files td{display:block;width:100%;}\
.files tr{border-bottom:1px solid var(--border);padding:6px 0;}.files td{border:0;padding:1px 0;}\
.files .hash::before{content:"sha256 ";color:var(--muted);}}
.more-files summary{cursor:pointer;color:var(--accent);font-size:0.875rem;padding:6px 0;}
.btn{list-style:none;display:inline-flex;align-items:center;gap:4px;border:1px solid var(--border);\
background:var(--surface);color:var(--text);border-radius:6px;padding:4px 10px;font-size:0.875rem;\
cursor:pointer;white-space:nowrap;}summary.btn::-webkit-details-marker{display:none;}
.pop{position:relative;}
.pop-body{position:absolute;right:0;top:calc(100% + 6px);z-index:5;width:min(560px,90vw);\
background:var(--surface);border:1px solid var(--border);border-radius:8px;\
box-shadow:0 6px 24px var(--shadow);padding:10px 12px;}
@media(max-width:1099px){.ds-hd{flex-wrap:wrap;}.acts{width:100%;flex-wrap:wrap;}\
.pop[open]{flex-basis:100%;order:2;}.pop-body{position:static;width:100%;margin-top:8px;\
box-shadow:none;}}
.fmt{border:0;margin:0;padding:0;min-width:0;}
.fmt legend{font-size:0.875rem;color:var(--muted);margin-bottom:4px;padding:0;}
.fmt input{position:absolute;opacity:0;width:1px;height:1px;}
.fmt label{display:inline-block;padding:3px 8px;border-radius:5px;font-size:0.875rem;\
cursor:pointer;\
color:var(--muted);}
.fmt input:checked+label{background:var(--surface2);color:var(--text);font-weight:600;}
.fmt input:focus-visible+label{outline:2px solid var(--focus);outline-offset:1px;}
.panel{display:none;margin-top:8px;}
.hint{font-size:0.875rem;color:var(--muted);margin:0 0 4px;}
.panel pre{background:var(--code-bg);color:var(--code-fg);border-radius:6px;padding:8px 10px;\
margin:0;white-space:pre-wrap;overflow-wrap:anywhere;font-family:var(--t-mono);font-size:0.8rem;}
.panel pre.prose{font-family:var(--t-sans);font-size:0.875rem;}
.copy{border:1px solid var(--border);background:var(--surface);color:var(--text);border-radius:5px;\
padding:1px 8px;font-size:0.875rem;cursor:pointer;margin-top:4px;}
.hash .copy{margin:0 0 0 6px;}
.bib{font-size:0.875rem;display:inline-block;margin-top:6px;}
.empty{color:var(--muted);padding:24px 0;}.nw{white-space:nowrap;}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;}
.pagefoot{max-width:min(var(--content-max),98vw);width:100%;margin:0 auto;margin-top:auto;\
padding:18px var(--content-pad) 30px;border-top:1px solid var(--border);display:flex;\
align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;}
.pagefoot .ft-l{flex:1 1 200px;display:flex;align-items:center;}
.pagefoot .ft-c{flex:0 0 auto;text-align:center;}
.pagefoot .ft-r{flex:1 1 200px;text-align:right;display:flex;gap:14px;justify-content:flex-end;}
.ft-emblem{height:30px;width:auto;display:block;}
.stamp{color:var(--muted);font-size:0.875rem;}
.ft-link{color:var(--muted);font-size:0.875rem;text-decoration:none;display:inline-flex;\
align-items:center;}.ft-link:hover{color:var(--accent);text-decoration:underline;}
@media(max-width:480px){.pagefoot{gap:12px 18px;}.pagefoot .ft-l{min-width:0;}\
.ft-emblem{height:auto;max-height:30px;max-width:100%;}}
@media(pointer:coarse){header{padding-top:16px;padding-bottom:16px;}\
.chip,.btn,.copy,.fmt label,.more-tags,.clear,.more,.ft-link,\
details.det>summary,.more-files summary,.files .fn a{min-height:40px;display:inline-flex;\
align-items:center;}}
@media(pointer:coarse) and (max-width:1099px){.ftoggle{min-height:40px;display:inline-flex;\
align-items:center;}}
@media(min-width:1100px){html,body{height:100%;overflow:hidden;}\
header{padding-top:8px;padding-bottom:8px;}\
.wrap{flex:1 1 auto;min-height:0;padding-bottom:10px;}.side{min-height:0;}\
main{display:flex;flex-direction:column;min-height:0;height:100%;}\
.list{flex:1 1 auto;min-height:0;overflow:auto;border:1px solid var(--border);\
border-radius:10px;background:var(--surface2);padding:14px 16px;scroll-padding-top:14px;}\
.list .ds:last-child{margin-bottom:0;}.pagefoot{margin-top:0;padding-top:10px;\
padding-bottom:12px;}}
@media(max-width:1099px){.wrap{display:block;}.side{position:sticky;top:0;z-index:4;\
background:var(--bg);margin:-8px calc(-1*var(--content-pad)) 16px;\
padding:8px var(--content-pad);border-bottom:1px solid var(--border);}\
html{scroll-padding-top:var(--stick,90px);}\
.filters{display:flex;flex-wrap:wrap;align-items:center;column-gap:10px;}\
.side input[type=search]{flex:1 1 12rem;width:auto;}.chips-wrap,.count{flex-basis:100%;}\
.count{margin:4px 0 0;}.chips-wrap.open{max-height:50dvh;overflow:auto;}}
@media(min-width:1300px){.ds{display:grid;grid-template-columns:minmax(0,80ch) \
minmax(240px,1fr);grid-template-rows:auto auto auto 1fr auto;column-gap:28px;}\
.ds-hd{display:contents;}.ds h2{grid-area:1/1;}.acts{grid-area:1/2;}\
.meta{grid-area:2/1;}.badges{grid-area:2/2/5/3;align-self:start;margin-top:6px;}\
.desc{grid-area:3/1;margin-top:6px;}.more{grid-area:4/1;justify-self:start;}\
.det{grid-area:5/1/6/3;}}
@media print{html,body{height:auto;overflow:visible;}.side{display:none;}\
.list{overflow:visible;border:0;padding:0;background:none;}}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent);\
font-weight:600;}
.flist{list-style:none;margin:0;padding:0;max-height:18rem;overflow:auto;}\
.flist li{display:flex;justify-content:space-between;gap:12px;padding:4px 0;\
border-bottom:1px solid var(--border);}.flist a{overflow-wrap:anywhere;}
"""
PANEL_CSS = "".join(
    f".fmt input:nth-of-type({i}):checked~.panel:nth-of-type({i}){{display:block;}}"
    for i in range(1, 7)
)


@dataclass(frozen=True)
class Assets:
    """Branding assets, each a ``data:`` URI."""

    plate: str
    signature: str
    font_semibold: str
    font_book: str
    favicon: str


def human_size(n: int) -> str:
    """Format a byte count in binary units with one decimal (``1.5 KiB``); bytes stay whole."""
    if n < 1024:
        return f"{n} B"
    value = float(n)
    for unit in UNITS:
        value /= 1024
        if round(value, 1) < 1024 or unit == UNITS[-1]:
            return f"{value:.1f} {unit}"
    raise AssertionError("unreachable")


def _e(text: str) -> str:
    return escape(text, quote=True)


def _paragraphs(text: str) -> str:
    parts = [" ".join(p.split()) for p in text.split("\n\n") if p.strip()]
    return "".join(f"<p>{_e(p)}</p>" for p in parts)


def ga_tag(ga_id: str) -> str:
    """Google's gtag snippet, using ``window.dataLayer`` (the form pub-cds-scc's validator passes)."""
    return (
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>'
        "<script>window.dataLayer=window.dataLayer||[];"
        "function gtag(){window.dataLayer.push(arguments);}"
        f'gtag("js",new Date());gtag("config","{ga_id}");</script>'
    )


COPY = '<button type="button" class="copy" hidden>Copy</button>'  # page.js names it by its card


def _size(n: int) -> str:
    return f'<span title="{n:,} bytes">{human_size(n)}</span>'


def _rows(files: tuple[DataFile, ...]) -> str:
    return "".join(
        f'<tr><td class="fn"><a href="{_e(f.url)}">{_e(f.name)}</a></td>'
        f'<td class="sz">{_size(f.size)}</td>'
        f'<td class="hash"><code>{f.sha256}</code>{COPY}</td></tr>'
        for f in files
    )


def _files_table(ds: Dataset) -> str:
    shown, rest = ds.files[:FILES_SHOWN], ds.files[FILES_SHOWN:]
    table = (
        '<table class="files"><thead><tr><th>File</th><th class="sz">Size</th>'
        f'<th class="hash">sha256</th></tr></thead><tbody>{_rows(shown)}</tbody></table>'
    )
    if rest:
        more = f"Show {len(rest)} more file{'s' * (len(rest) != 1)}"
        table += (
            f'<details class="more-files"><summary>{more}</summary>'
            f'<table class="files"><tbody>{_rows(rest)}</tbody></table></details>'
        )
    return table


def _choices(group: str, legend: str, panels: list[tuple[str, str]]) -> str:
    radios = "".join(
        f'<input type="radio" name="{group}" id="{group}-{i}"{" checked" if i == 0 else ""}>'
        f'<label for="{group}-{i}">{_e(label)}</label>'
        for i, (label, _) in enumerate(panels)
    )
    bodies = "".join(f'<div class="panel">{body}</div>' for _, body in panels)
    return f'<fieldset class="fmt"><legend>{legend}</legend>{radios}{bodies}</fieldset>'


def _code(hint: str, code: str, prose: bool = False) -> str:
    cls = ' class="prose"' if prose else ""
    return f'<p class="hint">{hint}</p><pre{cls}><code>{_e(code)}</code></pre>{COPY}'


def _pop(label: str, aria: str, body: str, cls: str = "btn") -> str:
    return (
        f'<details class="pop"><summary class="{cls}" aria-label="{_e(aria)}">{label} '
        f'<span aria-hidden="true">▾</span></summary><div class="pop-body">{body}</div></details>'
    )


def _get_data(ds: Dataset) -> str:
    n = len(ds.files)
    items = "".join(
        f'<li><a href="{_e(f.url)}">{_e(f.name)}</a><span class="sz">{_size(f.size)}</span></li>'
        for f in ds.files
    )
    files = (
        f'<p class="hint">{n} file{"s" * (n != 1)} · {_size(ds.total_size)} · '
        f'each link downloads one file</p><ul class="flist">{items}</ul>'
    )
    panels = [("Files", files)] + [
        (s.label, _code(f'{_e(s.hint)} · <a href="{_e(s.docs)}">docs</a>', s.code))
        for s in snippets.get_data(ds)
    ]
    return _pop(
        "Get data",
        f"Get data for {ds.title}",
        _choices(f"gd-{ds.slug}", "Format", panels),
        "btn primary",
    )


def _cite(ds: Dataset) -> str:
    bib = cite.bibtex(ds)
    panels = [
        ("APA", _code("APA 7", cite.apa(ds), prose=True)),
        ("BibTeX", _code("BibTeX", bib)),
        ("RIS", _code("RIS", cite.ris(ds))),
    ]
    download = (
        f'<a class="bib" download="{ds.slug}.bib" '
        f'href="data:application/x-bibtex;charset=utf-8,{quote(bib)}">Download .bib</a>'
    )
    body = _choices(f"ct-{ds.slug}", "Citation style", panels) + download
    return _pop("Cite", f"Cite {ds.title}", body)


def _meta(ds: Dataset) -> str:
    n, fmts = len(ds.files), snippets.formats(ds)
    parts = [
        f"{n} file{'s' * (n != 1)}" + (f" ({', '.join(fmts)})" if fmts else ""),
        f"{_size(ds.total_size)} download",
        f'added <span class="nw">{ds.added.isoformat()}</span>',
    ]
    if ds.doi:
        parts.append(f'DOI <a href="https://doi.org/{_e(ds.doi)}">{_e(ds.doi)}</a>')
    return " · ".join(parts)


def _badges(ds: Dataset) -> str:
    terms = license_url(ds.license)
    lic = (
        f'<a class="lic" href="{_e(terms)}">{_e(ds.license)}</a>'
        if terms
        else f'<span class="lic">{_e(ds.license)}</span>'
    )
    return lic + "".join(f'<a class="tag" href="?tag={t}">{t}</a>' for t in ds.tags)


def render_dataset(ds: Dataset) -> str:
    """One compact card: header with popovers, meta line, badges, description, Details."""
    text = " ".join(" ".join((ds.title, ds.description, *ds.tags)).lower().split())
    source = (
        f'<p class="src">Source: <a href="{_e(ds.source)}">{_e(ds.source)}</a></p>'
        if ds.source
        else ""
    )
    contact = (
        f'<p class="contact">Contact: <a href="mailto:{_e(ds.contact)}">{_e(ds.contact)}</a></p>'
        if ds.contact
        else ""
    )
    return (
        f'<article class="ds" id="{ds.slug}" data-tags="{" ".join(ds.tags)}" '
        f'data-text="{_e(text)}"><div class="ds-hd"><h2 id="t-{ds.slug}">{_e(ds.title)}</h2>'
        f'<div class="acts">{_cite(ds)}{_get_data(ds)}</div></div>'
        f'<p class="meta">{_meta(ds)}</p><p class="badges">{_badges(ds)}</p>'
        f'<div class="desc">{_paragraphs(ds.description)}</div>'
        '<button type="button" class="more" aria-expanded="false" hidden>more</button>'
        f'<details class="det"><summary aria-describedby="t-{ds.slug}">Details</summary>'
        f"{source}{contact}{_files_table(ds)}"
        "</details></article>"
    )


def _sidebar(catalog: Catalog) -> str:
    counts = Counter(t for ds in catalog.datasets for t in ds.tags)
    order = sorted(counts, key=lambda t: (-counts[t], t))
    chips = "".join(
        f'<button type="button" class="chip{" extra" if i >= TAGS_SHOWN else ""}" '
        f'data-tag="{t}" aria-pressed="false">{t} <span class="n">{counts[t]}</span>'
        f'<span class="sr"> dataset{"s" * (counts[t] != 1)}</span></button>'
        for i, t in enumerate(order)
    )
    more = (
        '<button type="button" class="more-tags">More tags</button>'
        if len(order) > TAGS_SHOWN
        else ""
    )
    n = len(catalog.datasets)
    toc = "".join(
        f'<li><a href="#{ds.slug}" title="{_e(ds.title)}"><span class="t">{_e(ds.title)}</span>'
        f'<span class="sz">{human_size(ds.total_size)}</span></a></li>'
        for ds in catalog.datasets
    )
    nav = (
        f'<div class="toc-box"><p class="toc-hd">Datasets</p>'
        f'<nav class="toc" aria-label="Datasets"><ol>{toc}</ol></nav></div>'
    )
    return (
        '<aside class="side" aria-label="Find datasets"><div class="side-in">'
        '<div class="filters" hidden>'
        '<input type="search" id="q" placeholder="Search datasets" '
        'aria-label="Search titles, descriptions and tags">'
        '<button type="button" class="ftoggle" aria-expanded="false" aria-controls="chips">'
        'Filters<span class="fcount"></span></button>'
        '<div class="chips-wrap" id="chips"><p class="chips-hd" id="chips-hd">Match all selected '
        f'tags</p><div class="chips" role="group" aria-labelledby="chips-hd">{chips}</div>{more}'
        f'</div><p class="count" aria-live="polite">{n} of {n} datasets</p>'
        '<button type="button" class="clear" hidden>Clear filters</button></div>'
        + (nav if n else "")
        + "</div></aside>"
    )


def render_page(
    catalog: Catalog,
    assets: Assets,
    updated: date,
    ga_id: str | None,
    preview: bool = False,
    manifest_sha: str = "",
) -> str:
    """The whole page.

    Args:
        catalog: Notice, tags and datasets (datasets already in display order).
        assets: Branding data URIs.
        updated: Date for the footer stamp and the summary line.
        ga_id: GA4 measurement id, or None for no analytics tag.
        preview: Mark the page as a local preview (``check_page`` refuses to publish it).
        manifest_sha: catalog digest stamped so ``deploy.sh`` can refuse a page built from any
            other catalog. Empty = no stamp.

    Returns:
        A complete HTML document.
    """
    css = (
        ":root{color-scheme:light;"
        + _vars()
        + "}"
        + CSS.replace("@@FONT_SEMIBOLD@@", assets.font_semibold).replace(
            "@@FONT_BOOK@@", assets.font_book
        )
        + PANEL_CSS
    )
    n = len(catalog.datasets)
    total = sum(ds.total_size for ds in catalog.datasets)
    notice = f' <span class="hdr-tag">{_e(catalog.notice)}</span>' if catalog.notice else ""
    summary = (
        f'<p class="summary">{n} dataset{"s" * (n != 1)} · {human_size(total)} total download · '
        f'updated <span class="nw">{updated.isoformat()}</span></p>'
        if n
        else ""
    )
    body = (
        "".join(render_dataset(ds) for ds in catalog.datasets)
        if n
        else '<p class="empty-catalog">No datasets published yet.</p>'
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        + (PREVIEW_MARK if preview else "")
        + (f'<meta name="cds-manifest" content="{manifest_sha}">' if manifest_sha else "")
        + "<title>CDS Public Research Data</title>"
        '<meta name="description" content="Public research datasets from the Boston University '
        'Faculty of Computing &amp; Data Sciences, free to download.">'
        f'<link rel="icon" href="{assets.favicon}">'
        + (ga_tag(ga_id) if ga_id else "")
        + f"<style>{css}</style></head><body>"
        f'<header><div class="hwrap"><h1><img class="buplate" src="{assets.plate}" '
        'alt="Boston University"><span class="orgname">Faculty of Computing &amp; Data '
        'Sciences</span> <span class="hsep" aria-hidden="true">|</span> Public Research Data'
        f"{notice}</h1>"
        "</div></header>"
        f'<div class="wrap">{_sidebar(catalog)}<main><section class="intro">'
        "<p>Public datasets from research at the Boston University Faculty of Computing &amp; "
        'Data Sciences, hosted on the NSF-funded <a href="https://www.openstoragenetwork.org/">'
        "Open Storage Network</a>. Every file downloads directly, with no account.</p>"
        "</section>"
        f"{summary}"
        '<div class="list" tabindex="0" aria-label="Datasets">'
        '<p class="empty" hidden>No datasets match. '
        '<button type="button" class="clear">Clear filters</button></p>'
        f"{body}"
        "</div></main></div>"
        f'<footer class="pagefoot"><div class="ft-l"><img class="ft-emblem" '
        f'src="{assets.signature}" alt="Boston University Faculty of Computing &amp; Data '
        f'Sciences"></div>'
        f'<div class="ft-c"><span class="stamp">Updated {updated.isoformat()}</span></div>'
        '<div class="ft-r"><a class="ft-link" href="catalog.json">catalog.json</a>'
        '<a class="ft-link" href="https://www.bu.edu/policies/digital-privacy-statement/" '
        'target="_blank" rel="noopener">Privacy Statement</a></div></footer>'
        '<p class="sr" id="live" aria-live="polite"></p>'
        f"<script>{PAGE_JS}</script></body></html>\n"
    )
