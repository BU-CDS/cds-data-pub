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
COLS_SHOWN = 20  # longer column lists show this many, then a filter and "Show all"
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
CONTRAST_UI = (  # >= 3:1 (focus ring)
    ("focus", "bg"),
    ("focus", "surface"),
    ("on-accent", "text"),  # the ring on the header, whose background is the text colour
)


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
header :focus-visible{outline-color:var(--on-accent);}
button{font:inherit;}
.wrap{max-width:min(var(--content-max),98vw);width:100%;margin:0 auto;\
padding:14px var(--content-pad) 60px;flex:1 0 auto;display:grid;\
grid-template-columns:minmax(0,1fr);\
gap:20px;}
@media(min-width:1100px){.wrap{grid-template-columns:270px minmax(0,1fr);}\
.side-in{max-height:100%;overflow:auto;position:relative;}\
.filters{border:1px solid var(--border);border-radius:10px;\
background:var(--surface2);padding:10px 12px;}\
.side .chip{background:var(--surface);}}
main{min-width:0;}
.hdr-tag{display:inline-block;margin-left:.6em;padding:1px 8px;border-radius:999px;\
background:#cc0000;color:#ffffff;font-size:0.7em;font-weight:600;letter-spacing:.04em;vertical-align:.15em;}
.intro p{margin:0 0 8px;}
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
.flist .sz{color:var(--muted);white-space:nowrap;font-variant-numeric:tabular-nums;}
@media(max-width:1099px){.ftoggle{display:inline-block;}\
.chips-wrap:not(.open){display:none;}}
.ds{background:var(--surface);border:1px solid var(--border);border-radius:8px;\
box-shadow:0 1px 2px var(--shadow);padding:14px 16px;margin:0 0 14px;}
.ds-hd{display:flex;align-items:flex-start;gap:12px;}
.ds h2{flex:1;min-width:0;font-family:"Whitney SSm A",var(--t-sans);font-size:1.125rem;\
font-weight:600;\
margin:0;overflow-wrap:anywhere;}
.acts{display:flex;gap:6px;flex-shrink:0;}
.perma{color:inherit;text-decoration:none;}.perma:hover{text-decoration:underline;}\
.ds:target{outline:2px solid var(--accent);outline-offset:2px;}
.meta .who{color:var(--text);}
.dx{margin:2px 0 6px;padding:12px 16px 14px;background:var(--surface2);border-radius:8px;\
font-size:0.875rem;--rule:color-mix(in srgb,var(--muted) 40%,var(--surface2));}
.dx-facts{display:grid;grid-template-columns:max-content minmax(0,1fr);column-gap:16px;margin:0;}\
.files .hash code{display:block;margin-bottom:4px;}
.dx-facts dt{font-weight:600;color:var(--muted);}.dx-facts dd{margin:0;overflow-wrap:anywhere;}
.dx-facts>*{padding:8px 0;border-top:1px solid var(--rule);}\
.dx-facts>:nth-child(-n+2){padding-top:0;border-top:0;}.dx-facts>:nth-last-child(-n+2){padding-bottom:0;}
.dx-h{font-size:0.875rem;font-weight:600;margin:12px 0 6px;padding-top:12px;\
border-top:1px solid var(--rule);}.dx-h span{font-weight:400;color:var(--muted);}\
.dx>.dx-h:first-child{margin-top:0;padding-top:0;border-top:0;}
.dx-cols{list-style:none;margin:0;padding:0;display:grid;\
grid-template-columns:repeat(auto-fill,minmax(10rem,1fr));gap:1px 20px;}\
.dx-cols li{overflow-wrap:anywhere;}\
.dx-cols code{font-family:var(--t-mono);font-size:0.8rem;}
.dx-cols.clip:not(.filtering) li.x{display:none;}
.colq{width:min(100%,18rem);padding:5px 8px;margin:0 0 8px;border:1px solid var(--muted);\
border-radius:6px;background:var(--surface);color:var(--text);font:inherit;}
.colcount{color:var(--muted);margin:0 0 6px;}
.colmore{background:none;border:0;padding:4px 0;margin-top:4px;color:var(--accent);\
cursor:pointer;font:inherit;text-decoration:underline;}
header .orglink{color:#ffffff;}\
header .orglink{text-decoration:none;}header .orglink:hover{text-decoration:underline;}
.band{background:var(--surface2);border:1px solid var(--border);border-radius:10px;\
padding:16px 18px;margin:0 0 14px;}
.band .lede{font-family:"Whitney SSm A",var(--t-sans);font-size:1.3rem;font-weight:600;\
line-height:1.25;margin:0 0 8px;}
.band .facts{display:flex;flex-wrap:wrap;gap:6px 18px;margin:0 0 12px;color:var(--muted);\
font-size:0.875rem;font-variant-numeric:tabular-nums;}.band .facts b{color:var(--text);}
.band .ctas{display:flex;flex-wrap:wrap;gap:8px;margin:0;}
.cta{display:inline-block;padding:6px 12px;border-radius:6px;border:1px solid var(--accent);\
color:var(--accent);text-decoration:none;font-size:0.9rem;}.cta.primary{background:var(--accent);\
color:var(--on-accent);}
.wrap.doc{display:block;max-width:min(48rem,98vw);}
.back{display:inline-block;margin:0 0 10px;font-size:0.875rem;}.back::before{content:"\\2190\\00a0";}
.prose h2{font-family:"Whitney SSm A",var(--t-sans);font-size:1.5rem;margin:4px 0 12px;}
.prose h3{font-size:1.05rem;margin:22px 0 6px;}.prose p{margin:0 0 10px;}
.prose ul{margin:0 0 10px;padding-left:1.3em;}.prose li{margin-bottom:4px;}
.gloss{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:6px 18px;margin:0;}\
.gloss dt{font-weight:600;}.gloss dd{margin:0;}
@media(max-width:600px){.gloss{grid-template-columns:1fr;gap:0;}.gloss dd{margin-bottom:8px;}}
.meta{color:var(--muted);font-size:0.875rem;margin:4px 0 6px;font-variant-numeric:tabular-nums;\
overflow-wrap:anywhere;}
.badges{display:flex;flex-wrap:wrap;gap:4px;margin:0 0 8px;}
.lic,.tag{border:1px solid var(--border);background:var(--surface2);color:var(--text);\
border-radius:999px;padding:1px 8px;font-size:0.875rem;text-decoration:none;}.lic{font-weight:600;}
.desc{max-width:80ch;}.desc p{margin:0 0 6px;}.desc p:last-child{margin-bottom:0;}
.desc.clamp p:not(:first-child){display:none;}\
.desc.clamp p:first-child{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;\
line-clamp:2;overflow:hidden;}
details.det>summary{cursor:pointer;color:var(--accent);font-size:0.875rem;padding:6px 0;}
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
.files .hash::before{content:"sha256 ";color:var(--muted);}\
.dx{padding:10px 12px 12px;}.dx-facts{grid-template-columns:1fr;}\
.dx-facts dd{padding-top:0;border-top:0;}}
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
.ft-link{color:var(--muted);font-size:0.75rem;text-decoration:none;display:inline-flex;\
align-items:center;}.ft-link:hover{color:var(--accent);text-decoration:underline;}
@media(max-width:480px){.pagefoot{gap:12px 18px;}.pagefoot .ft-l{min-width:0;}\
.ft-emblem{height:auto;max-height:30px;max-width:100%;}}
@media(pointer:coarse){header{padding-top:16px;padding-bottom:16px;}\
.chip,.btn,.copy,.fmt label,.more-tags,.clear,.more,.ft-link,\
details.det>summary,.more-files summary,.files .fn a{min-height:40px;display:inline-flex;\
align-items:center;}}
@media(pointer:coarse) and (max-width:1099px){.ftoggle{min-height:40px;display:inline-flex;\
align-items:center;}}
@media(min-width:1100px) and (min-height:38em){.shell,.shell body{height:100%;overflow:hidden;}\
.shell .wrap{flex:1 1 auto;min-height:0;padding-bottom:10px;grid-template-rows:minmax(0,1fr);}.shell .side{min-height:0;}\
.shell main{display:flex;flex-direction:column;min-height:0;height:100%;}\
.shell .list{flex:1 1 auto;min-height:0;overflow:auto;border:1px solid var(--border);\
border-radius:10px;background:var(--surface2);padding:14px 16px;scroll-padding-top:14px;}\
.shell .list .ds:last-child{margin-bottom:0;}.shell .pagefoot{margin-top:0;padding-top:10px;\
padding-bottom:12px;}}
@media(max-width:1099px){.wrap{display:block;}.side{position:sticky;top:0;z-index:4;\
background:var(--bg);margin:-8px calc(-1*var(--content-pad)) 16px;\
padding:8px var(--content-pad);border-bottom:1px solid var(--border);}\
html{scroll-padding-top:var(--stick,90px);}\
.filters{display:flex;flex-wrap:wrap;align-items:center;column-gap:10px;}\
.side input[type=search]{flex:1 1 12rem;width:auto;}.chips-wrap,.count{flex-basis:100%;}\
.count{margin:4px 0 0;}.chips-wrap.open{max-height:50dvh;overflow:auto;}}
@media(max-width:1099px) and (max-height:500px){.side{position:static;}}
@media(min-width:1300px){.ds{display:grid;grid-template-columns:minmax(0,80ch) \
minmax(240px,1fr);grid-template-rows:auto auto auto 1fr auto;column-gap:28px;}\
.ds-hd{display:contents;}.ds h2{grid-area:1/1;}.acts{grid-area:1/2;}\
.meta{grid-area:2/1;}.badges{grid-area:2/2/5/3;\
align-self:start;margin-top:12px;padding-top:10px;border-top:1px solid var(--border);}\
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


def producer(ds: Dataset) -> str | None:
    """Who made the data, from its citation: an organization by name, people by family name
    ("A", "A & B", "A et al."). Without a [citation] the dataset is cited as CDS's own, so
    CDS is named (review 2026-10-09 #6: the page says every dataset names its producer)."""
    if not ds.citation:
        return "BU Computing & Data Sciences"
    first = ds.citation.authors[0]
    if ", " not in first:
        return first
    fam = [a.split(", ", 1)[0] for a in ds.citation.authors if ", " in a]
    if len(ds.citation.authors) == 1:
        return fam[0]
    if len(ds.citation.authors) == 2 and len(fam) == 2:
        return f"{fam[0]} & {fam[1]}"
    return f"{fam[0]} et al."


def _meta(ds: Dataset) -> str:
    n, fmts = len(ds.files), snippets.formats(ds)
    who = producer(ds)
    parts = [f'from <span class="who">{_e(who)}</span>'] if who else []
    table = next((f for f in ds.files if f.rows is not None or f.columns), None)
    shape = (
        [
            " × ".join(
                ([f"{table.rows:,} rows"] if table.rows is not None else [])
                + ([f"{len(table.columns)} columns"] if table.columns else [])
            )
        ]
        if table
        else []
    )
    parts += [
        f"{n} file{'s' * (n != 1)}" + (f" ({', '.join(fmts)})" if fmts else ""),
        *shape,
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
    # Search covers what the card shows: names, description, tags, producer, coverage, formats,
    # file names and column names ("csv" finds every CSV dataset, "dbh" the trees table).
    found = (
        ds.title,
        ds.description,
        *ds.tags,
        producer(ds) or "",
        ds.coverage or "",
        *snippets.formats(ds),
        *(f.name for f in ds.files),
        *(c for f in ds.files for c in f.columns),
    )
    text = " ".join(" ".join(found).lower().split())
    return (
        f'<article class="ds" id="{ds.slug}" data-tags="{" ".join(ds.tags)}" '
        f'data-text="{_e(text)}"><div class="ds-hd"><h2 id="t-{ds.slug}">'
        f'<a class="perma" href="#{ds.slug}">{_e(ds.title)}</a></h2>'
        f'<div class="acts"><button type="button" class="btn link" data-link="#{ds.slug}" '
        f'aria-describedby="t-{ds.slug}" hidden>Copy link</button>'
        f"{_cite(ds)}{_get_data(ds)}</div></div>"
        f'<p class="meta">{_meta(ds)}</p><p class="badges">{_badges(ds)}</p>'
        f'<div class="desc">{_paragraphs(ds.description)}</div>'
        '<button type="button" class="more" aria-expanded="false" hidden>more</button>'
        f'<details class="det"><summary aria-describedby="t-{ds.slug}">Details</summary>'
        f'<div class="dx">{_details(ds)}</div></details></article>'
    )


def _columns(f: DataFile) -> str:
    """One table file's column names, in file order. Past COLS_SHOWN the page script hides the
    rest behind "Show all" and offers a filter; without the script every name shows."""
    n = len(f.columns)
    long = n > COLS_SHOWN
    names = "".join(
        f"<li{' class="x"' if i >= COLS_SHOWN else ''}><code>{_e(c)}</code></li>"
        for i, c in enumerate(f.columns)
    )
    head = f'<h3 class="dx-h">Column names <span>· {n} in {_e(f.name)}</span></h3>'
    if not long:
        return f'{head}<ul class="dx-cols">{names}</ul>'
    return (
        f'{head}<input type="search" class="colq" placeholder="Filter column names" '
        f'aria-label="Filter column names in {_e(f.name)}" hidden>'
        '<p class="colcount" aria-live="polite" hidden></p>'
        f'<ul class="dx-cols">{names}</ul>'
        '<button type="button" class="colmore" aria-expanded="false" hidden>'
        f"Show all {n} column names</button>"
    )


def _details(ds: Dataset) -> str:
    """The Details panel: facts, column names per table file, files. One panel with labelled
    sections, chosen 2026-10-09 (docs/design-decisions.md)."""
    facts = []
    if ds.coverage:
        facts.append(f"<dt>Coverage</dt><dd>{_e(ds.coverage)}</dd>")
    if ds.source:
        shown = ds.source.removeprefix("https://").rstrip("/")
        facts.append(f'<dt>Source</dt><dd><a href="{_e(ds.source)}">{_e(shown)}</a></dd>')
    if ds.contact:
        mail = _e(ds.contact)
        facts.append(f'<dt>Contact</dt><dd><a href="mailto:{mail}">{mail}</a></dd>')
    n = len(ds.files)
    return (
        (f'<dl class="dx-facts">{"".join(facts)}</dl>' if facts else "")
        + "".join(_columns(f) for f in ds.files if f.columns)
        + f'<h3 class="dx-h">Files <span>· {n}, with sha256 checksums</span></h3>'
        + _files_table(ds)
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
    return (
        '<aside class="side" aria-label="Find datasets"><div class="side-in">'
        '<div class="filters" hidden>'
        '<input type="search" id="q" placeholder="Search datasets" '
        'aria-label="Search names, descriptions, tags, formats and columns">'
        '<button type="button" class="ftoggle" aria-expanded="false" aria-controls="chips">'
        'Filters<span class="fcount"></span></button>'
        '<div class="chips-wrap" id="chips"><p class="chips-hd" id="chips-hd">Match all selected '
        f'tags</p><div class="chips" role="group" aria-labelledby="chips-hd">{chips}</div>{more}'
        f'</div><p class="count" aria-live="polite">{n} of {n} datasets</p>'
        '<button type="button" class="clear" hidden>Clear filters</button></div></div></aside>'
    )


CDS_URL = "https://www.bu.edu/cds-faculty/"
INTRO = (
    "<p>Open datasets curated and hosted by the Boston University "
    f'<a href="{CDS_URL}">Faculty of Computing &amp; Data Sciences</a> for research and teaching, '
    'on the NSF-funded <a href="https://www.openstoragenetwork.org/">Open Storage Network</a>. '
    "Each dataset names who produced it. Every file downloads directly, with no account.</p>"
)
INTRO_SHORT = (  # under the band, which already says who curates it and the no-account facts
    '<p>Hosted on the NSF-funded <a href="https://www.openstoragenetwork.org/">Open Storage '
    "Network</a>. Each dataset names who produced it.</p>"
)


def _about_body(catalog: Catalog) -> str:
    """How the catalog works. Answers the simulated readers' questions of 2026-10-09:
    provenance, permanence, demo status and the terms the cards use (docs/design-decisions.md)."""
    demo = (
        "<p>The datasets listed now are a demo: real public data from other producers, "
        "re-hosted to show how the service works until CDS datasets are added. They are "
        "complete and usable.</p>"
        if catalog.notice
        else ""
    )
    return (
        "<h2>How this catalog works</h2>"
        "<p>Open datasets, curated and hosted by BU Computing &amp; Data Sciences (CDS), free to "
        "download and reuse with no account. Each dataset names who produced it.</p>"
        "<h3>Where the data comes from</h3>"
        "<p>CDS selects datasets approved for public release and hosts copies on the NSF-funded "
        '<a href="https://www.openstoragenetwork.org/">Open Storage Network</a> (OSN). '
        "Re-hosted datasets are unmodified copies of the producer's files, taken on the "
        "snapshot date given in each dataset's README, which also names the source and its "
        f"version.</p>{demo}"
        "<h3>How long files stay</h3>"
        "<p>This catalog is not an archive: OSN keeps no backups, and a dataset can be taken "
        "down. Producers keep the master copy; for a permanent, citable record (a DOI) a dataset "
        "is also deposited in a repository such as Zenodo. When the original has a DOI, the "
        "citation under Cite points to it.</p>"
        "<h3>Dates</h3>"
        "<p>“Added” is when a dataset was listed here; “updated” is when this catalog was last "
        "rebuilt. A dataset's README gives its snapshot date and source version.</p>"
        '<h3>Terms used in the catalog</h3><dl class="gloss">'
        "<dt>Checksum (sha256)</dt><dd>A fingerprint of a file. If the sha256 of your download "
        "matches the one listed, you have exactly the file published here.</dd>"
        "<dt>License</dt><dd>The terms for reuse, as an SPDX identifier such as CC0-1.0 or "
        "CC-BY-4.0, each linked to its full text. “Public domain” means no restrictions.</dd>"
        "<dt>DOI</dt><dd>A permanent identifier for a published dataset or paper "
        "(https://doi.org/…).</dd>"
        "<dt>MiB, GiB</dt><dd>File sizes in binary units: 1 MiB is 1,048,576 bytes, "
        "1 GiB is 1,024 MiB.</dd>"
        '<dt>catalog.json</dt><dd>The whole catalog as one machine-readable <a href="catalog.json">'
        "file</a>: every dataset, file, checksum and citation, for scripts.</dd></dl>"
    )


def _publish_body(steward: str | None) -> str:
    """Who may publish (owner, 2026-10-09: CDS researchers only), what qualifies, what it gives.
    Without a public steward contact it says one is coming instead of inventing an address."""
    reach = (
        f'<p><a class="cta primary" href="mailto:{_e(steward)}">Email the CDS data steward</a></p>'
        if steward
        else "<p>The data steward's contact will be listed here when the catalog goes live.</p>"
    )
    return (
        "<h2>Publish your data with CDS</h2>"
        "<p>Only CDS researchers can publish here, and only data approved for public "
        "release.</p>"
        "<h3>What qualifies</h3><ul>"
        "<li>Public data only: no HIPAA, FERPA or export-controlled data.</li>"
        "<li>A license for reuse, as an SPDX identifier such as CC0-1.0 or CC-BY-4.0.</li>"
        "<li>Up to 50 files per dataset; archive more into fewer files.</li></ul>"
        "<h3>What you get</h3><ul>"
        "<li>Hosting on the Open Storage Network at no cost to you.</li>"
        "<li>A listing here with direct download links, sizes and checksums, ready-made "
        "commands for the shell, AWS CLI, rclone, Python and R, and citations in APA, BibTeX "
        "and RIS.</li><li>An entry in catalog.json, for scripts.</li></ul>"
        "<h3>Before you start</h3><ul>"
        "<li>Keep your master copy: this catalog is not an archive and OSN keeps no backups.</li>"
        "<li>For a DOI, also deposit the dataset in a repository such as Zenodo; the listing "
        "here can cite it.</li></ul>"
        "<h3>What the steward will ask for</h3>"
        "<p>The files; a README (what it is, source, license, contact, date); a title and a "
        "short description; subject tags; and how it should be cited.</p>"
        f"<h3>Contact</h3>{reach}"
    )


def _band(n: int, total: int, updated: date, steward: str | None) -> str:
    """The identity band above the list: what the catalog is, its facts (computed, never
    typed) and the calls to action. Chosen over header links on 2026-10-08
    (docs/design-decisions.md)."""
    return (
        '<section class="band" aria-label="Catalog summary">'
        # "curated and hosted by", not "from": the datasets are produced by others (review #1)
        '<p class="lede">Open datasets, curated and hosted by BU Computing &amp; Data Sciences. '
        "Free to download and reuse.</p>"
        f'<p class="facts"><span><b>{n}</b> dataset{"s" * (n != 1)}</span>'
        f"<span><b>{human_size(total)}</b> to download</span>"
        "<span><b>No account</b> needed</span><span><b>Checksums</b> on every file</span>"
        f'<span>updated <span class="nw">{updated.isoformat()}</span></span></p>'
        # the filled button goes to Publish only once it reaches a real contact (no dead end)
        f'<p class="ctas"><a class="cta{" primary" if steward else ""}" href="publish.html">'
        "Publish your data with CDS</a>"
        '<a class="cta" href="about.html">How it works</a>'
        '<a class="cta" href="catalog.json">Use from code: catalog.json</a></p></section>'
    )


def _document(
    catalog: Catalog,
    assets: Assets,
    updated: date,
    ga_id: str | None,
    *,
    title: str,
    description: str,
    main: str,
    shell: bool = False,
    preview: bool = False,
    manifest_sha: str = "",
) -> str:
    """One page in the site frame: head, header, main, footer. Only the catalog page is the app
    shell and carries the page script; About and Publish are plain documents."""
    css = (
        ":root{color-scheme:light;"
        + _vars()
        + "}"
        + CSS.replace("@@FONT_SEMIBOLD@@", assets.font_semibold).replace(
            "@@FONT_BOOK@@", assets.font_book
        )
        + PANEL_CSS
    )
    notice = f' <span class="hdr-tag">{_e(catalog.notice)}</span>' if catalog.notice else ""
    return (
        f'<!doctype html><html lang="en"{' class="shell"' if shell else ""}><head>'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        + (PREVIEW_MARK if preview else "")
        + (f'<meta name="cds-manifest" content="{manifest_sha}">' if manifest_sha else "")
        + f"<title>{title}</title>"
        f'<meta name="description" content="{description}">'
        f'<link rel="icon" href="{assets.favicon}">'
        + (ga_tag(ga_id) if ga_id else "")
        + f"<style>{css}</style></head><body>"
        f'<header><div class="hwrap"><h1><img class="buplate" src="{assets.plate}" '
        f'alt="Boston University"> <a class="orglink" href="{CDS_URL}"><span class="orgname">'
        "Faculty of Computing &amp; Data Sciences</span></a> "
        '<span class="hsep" aria-hidden="true">|</span> Public Research Data'
        f"{notice}</h1>"
        "</div></header>"
        f"{main}"
        f'<footer class="pagefoot"><div class="ft-l"><img class="ft-emblem" '
        f'src="{assets.signature}" alt="Boston University Faculty of Computing &amp; Data '
        f'Sciences"></div>'
        f'<div class="ft-c"><span class="stamp">Updated {updated.isoformat()}</span></div>'
        '<div class="ft-r"><a class="ft-link" href="catalog.json">catalog.json</a>'
        '<a class="ft-link" href="https://www.bu.edu/policies/digital-privacy-statement/" '
        'target="_blank" rel="noopener">Privacy Statement</a></div></footer>'
        + (
            f'<p class="sr" id="live" aria-live="polite"></p><script>{PAGE_JS}</script>'
            if shell
            else ""
        )
        + "</body></html>\n"
    )


def render_page(
    catalog: Catalog,
    assets: Assets,
    updated: date,
    ga_id: str | None,
    preview: bool = False,
    manifest_sha: str = "",
) -> str:
    """The catalog page.

    Args:
        catalog: Notice, tags and datasets (datasets already in display order).
        assets: Branding data URIs.
        updated: Date for the footer stamp and the band.
        ga_id: GA4 measurement id, or None for no analytics tag.
        preview: Mark the page as a local preview (``check_page`` refuses to publish it).
        manifest_sha: catalog digest stamped so ``deploy.sh`` can refuse a page built from any
            other catalog. Empty = no stamp.

    Returns:
        A complete HTML document.
    """
    n = len(catalog.datasets)
    total = sum(ds.total_size for ds in catalog.datasets)
    body = (
        "".join(render_dataset(ds) for ds in catalog.datasets)
        if n
        else '<p class="empty-catalog">No datasets published yet.</p>'
    )
    main = (
        f'<div class="wrap">{_sidebar(catalog)}<main>'
        + (_band(n, total, updated, catalog.steward) if n else "")
        + f'<section class="intro">{INTRO_SHORT if n else INTRO}</section>'
        '<div class="list" role="region" tabindex="0" aria-label="Datasets">'
        '<p class="empty" hidden>No datasets match. '
        '<button type="button" class="clear">Clear filters</button></p>'
        f"{body}</div></main></div>"
    )
    return _document(
        catalog,
        assets,
        updated,
        ga_id,
        title="CDS Public Research Data",
        description="Open datasets curated and hosted by the Boston University Faculty of "
        "Computing &amp; Data Sciences, free to download.",
        main=main,
        shell=True,
        preview=preview,
        manifest_sha=manifest_sha,
    )


def _doc(body: str) -> str:
    return (
        '<div class="wrap doc"><main><a class="back" href="index.html">All datasets</a>'
        f'<article class="prose">{body}</article></main></div>'
    )


def render_about(
    catalog: Catalog,
    assets: Assets,
    updated: date,
    ga_id: str | None,
    preview: bool = False,
    manifest_sha: str = "",
) -> str:
    """about.html: how the catalog works. Same arguments as ``render_page``."""
    return _document(
        catalog,
        assets,
        updated,
        ga_id,
        title="How it works · CDS Public Research Data",
        description="How the BU CDS open-data catalog works: sources, copies, permanence, terms.",
        main=_doc(_about_body(catalog)),
        preview=preview,
        manifest_sha=manifest_sha,
    )


def render_publish(
    catalog: Catalog,
    assets: Assets,
    updated: date,
    ga_id: str | None,
    preview: bool = False,
    manifest_sha: str = "",
) -> str:
    """publish.html: who may publish and how. Same arguments as ``render_page``."""
    return _document(
        catalog,
        assets,
        updated,
        ga_id,
        title="Publish your data · CDS Public Research Data",
        description="How CDS researchers publish public datasets in the BU CDS open-data catalog.",
        main=_doc(_publish_body(catalog.steward)),
        preview=preview,
        manifest_sha=manifest_sha,
    )
