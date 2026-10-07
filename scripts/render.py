"""Render the catalog page as one self-contained HTML document.

Header, footer, palette and phone rules are ported from pub-cds-scc/build_cluster_page.R
(cluster.cds.bu.edu), including its 2026-09-03 phone fixes, so the two pages read as one family.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape

from scripts.manifest import Catalog, DataFile, Dataset

UNITS = ("KiB", "MiB", "GiB", "TiB", "PiB")
FILES_SHOWN = 5  # longer file lists collapse into a native <details> toggle
PREVIEW_MARK = '<meta name="cds-build" content="preview">'

CSS = """\
:root{--t-sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;\
--t-mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;\
--content-max:1100px;--content-pad:12px;--bg:#f2efec;--surface:#ffffff;--surface2:#ebe6e0;\
--ink:#2d2926;--text:#2d2926;--muted:#6b6158;--border:#dcd5cd;--accent:#0b7468;\
--headbg:#2d2926;--headfg:#ffffff;--shadow:rgba(15,30,45,.10);}
@font-face{font-family:"Whitney SSm A";font-weight:600;font-style:normal;font-display:swap;\
src:url("@@FONT_SEMIBOLD@@") format("woff2");}
@font-face{font-family:"Whitney SSm A";font-weight:400;font-style:normal;font-display:swap;\
src:url("@@FONT_BOOK@@") format("woff2");}
*{box-sizing:border-box}html{font-size:110%;}html,body{height:100%;}\
body{display:flex;flex-direction:column;min-height:100vh;min-height:100dvh;\
font-family:var(--t-sans);color:var(--text);margin:0;background:var(--bg);font-size:0.813rem;\
line-height:1.45;-webkit-font-smoothing:antialiased;}
header{background:var(--headbg);color:var(--headfg);padding:12px var(--content-pad);\
position:relative;border-top:3px solid #cc0000;border-bottom:1px solid rgba(255,255,255,.08);}\
header h1{font-size:1rem;margin:0;font-weight:600;letter-spacing:-.01em;\
font-family:"Whitney SSm A",var(--t-sans);}\
.buplate{height:1.615em;vertical-align:-.449em;margin-right:.34em;}\
.orgname{font-weight:400;letter-spacing:0;}\
.hsep{color:rgba(255,255,255,.4);font-weight:400;padding:0 .6em;}
.hwrap{max-width:min(var(--content-max),98vw);margin:0 auto;display:flex;align-items:baseline;\
gap:14px;flex-wrap:wrap;}
@media(max-width:700px){.hsep{display:block;height:0;padding:0;overflow:hidden;}}\
@media(max-width:480px){header h1{font-size:0.9rem;}}
main{max-width:min(var(--content-max),98vw);width:100%;margin:0 auto;\
padding:14px var(--content-pad) 60px;flex:1 0 auto;}
a{color:var(--accent);}
.intro p{margin:0 0 8px;max-width:75ch;}.intro .terms{color:var(--muted);font-size:0.75rem;}
.notice{background:#fff4d6;border:1px solid #e6c97a;border-radius:6px;padding:8px 12px;\
margin:0 0 12px;max-width:75ch;}
.ds .source{font-size:0.75rem;margin:0 0 6px;overflow-wrap:anywhere;}
.ds{background:var(--surface);border:1px solid var(--border);border-radius:8px;\
box-shadow:0 1px 2px var(--shadow);padding:14px 16px;margin:16px 0;}
.ds h2{font-family:"Whitney SSm A",var(--t-sans);font-size:1rem;font-weight:600;margin:0 0 4px;\
color:var(--ink);overflow-wrap:anywhere;}
.ds .meta{color:var(--muted);font-size:0.75rem;margin:0 0 10px;}
.ds .desc p{margin:0 0 8px;max-width:75ch;}
.ds .contact{font-size:0.75rem;margin:0 0 10px;overflow-wrap:anywhere;}
.files{width:100%;border-collapse:collapse;font-size:0.75rem;}
.files th{text-align:left;font-weight:600;color:var(--muted);border-bottom:1px solid var(--border);\
padding:4px 8px 4px 0;}
.files td{border-bottom:1px solid var(--border);padding:5px 8px 5px 0;vertical-align:top;}
.files .fn{overflow-wrap:anywhere;}.files .sz{white-space:nowrap;}
.files code,.curl code{font-family:var(--t-mono);font-size:0.7rem;overflow-wrap:anywhere;\
word-break:break-all;}
.curlhd{font-size:0.75rem;color:var(--muted);margin:10px 0 4px;}
.curl{background:var(--surface2);border-radius:5px;padding:6px 8px;margin:0;white-space:pre-wrap;\
overflow-wrap:anywhere;}
.empty{color:var(--muted);padding:24px 0;}
@media(min-width:900px){.files{table-layout:fixed;}.files .sz{width:6em;}\
.files .hash{width:28rem;}}
.more summary{cursor:pointer;color:var(--accent);font-size:0.75rem;padding:6px 0;}
@media(max-width:600px){.files thead{display:none;}\
.files,.files tbody,.files tr,.files td{display:block;width:100%;}\
.files tr{border-bottom:1px solid var(--border);padding:6px 0;}.files td{border:0;padding:1px 0;}\
.files .hash::before{content:"sha256 ";color:var(--muted);}}
.pagefoot{max-width:min(var(--content-max),98vw);width:100%;margin:0 auto;margin-top:auto;\
padding:18px var(--content-pad) 30px;border-top:1px solid var(--border);display:flex;\
align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;}
.pagefoot .ft-l{flex:1 1 200px;display:flex;align-items:center;}
.pagefoot .ft-c{flex:0 0 auto;text-align:center;}
.pagefoot .ft-r{flex:1 1 200px;text-align:right;}
.ft-emblem{height:30px;width:auto;display:block;}
.stamp{color:var(--muted);font-size:0.75rem;}
.ft-link{color:var(--muted);font-size:0.75rem;text-decoration:none;display:inline-flex;\
align-items:center;}.ft-link:hover{color:var(--accent);text-decoration:underline;}
@media(max-width:480px){.pagefoot{gap:12px 18px;}.pagefoot .ft-l{min-width:0;}\
.ft-emblem{height:auto;max-height:30px;max-width:100%;}}
@media(pointer:coarse){header{padding-top:16px;padding-bottom:16px;}.ft-link{min-height:40px;}\
.files .fn a{display:inline-block;min-height:40px;padding-top:10px;}\
.more summary{min-height:40px;padding-top:10px;}}
"""


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


def _rows(files: tuple[DataFile, ...]) -> str:
    return "".join(
        f'<tr><td class="fn"><a href="{_e(f.url)}">{_e(f.name)}</a></td>'
        f'<td class="sz" title="{f.size:,} bytes">{human_size(f.size)}</td>'
        f'<td class="hash"><code>{f.sha256}</code></td></tr>'
        for f in files
    )


def _meta(ds: Dataset) -> list[str]:
    count = len(ds.files)
    meta = [
        f'<span title="{ds.total_size:,} bytes">{human_size(ds.total_size)}</span>',
        f"{count} file{'' if count == 1 else 's'}",
        _e(ds.license),
        f"added {ds.added.isoformat()}",
    ]
    if ds.doi:
        meta.append(f'DOI <a href="https://doi.org/{_e(ds.doi)}">{_e(ds.doi)}</a>')
    return meta


def _files_block(ds: Dataset) -> str:
    shown, rest = ds.files[:FILES_SHOWN], ds.files[FILES_SHOWN:]
    table = (
        '<table class="files"><thead><tr><th>File</th><th class="sz">Size</th>'
        f'<th class="hash">sha256</th></tr></thead><tbody>{_rows(shown)}</tbody></table>'
    )
    if rest:
        more = f"Show {len(rest)} more file{'' if len(rest) == 1 else 's'}"
        table += (
            f'<details class="more"><summary>{more}</summary>'
            f'<table class="files"><tbody>{_rows(rest)}</tbody></table></details>'
        )
    return (
        f"{table}"
        '<p class="curlhd">Download from a script:</p>'
        f"<pre class=\"curl\"><code>curl -O '{_e(ds.files[0].url)}'</code></pre>"  # URL_RE bars '
    )


def render_dataset(ds: Dataset) -> str:
    """One card for a dataset."""
    contact = (
        f'<p class="contact">Contact: <a href="mailto:{_e(ds.contact)}">{_e(ds.contact)}</a></p>'
        if ds.contact
        else ""
    )
    source = (
        f'<p class="source">Source: <a href="{_e(ds.source)}">{_e(ds.source)}</a></p>'
        if ds.source
        else ""
    )
    return (
        f'<article class="ds" id="{ds.slug}"><h2>{_e(ds.title)}</h2>'
        f'<p class="meta">{" · ".join(_meta(ds))}</p>'
        f'<div class="desc">{_paragraphs(ds.description)}</div>{source}{contact}'
        f"{_files_block(ds)}</article>"
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
        catalog: Notice and datasets, datasets already in display order.
        assets: Branding data URIs.
        updated: Date for the footer stamp.
        ga_id: GA4 measurement id, or None for no analytics tag.
        preview: Mark the page as a local preview (``check_page`` refuses to publish it).
        manifest_sha: sha256 of the manifest bytes, stamped so ``deploy.sh`` can refuse a page
            built from any other manifest. Empty = no stamp.

    Returns:
        A complete HTML document.
    """
    css = CSS.replace("@@FONT_SEMIBOLD@@", assets.font_semibold).replace(
        "@@FONT_BOOK@@", assets.font_book
    )
    body = (
        "".join(render_dataset(d) for d in catalog.datasets)
        if catalog.datasets
        else '<p class="empty">No datasets published yet.</p>'
    )
    notice = f'<p class="notice">{_e(catalog.notice)}</p>' if catalog.notice else ""
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
        'Sciences</span><span class="hsep">|</span>Public Research Data</h1></div></header>'
        f'<main>{notice}<section class="intro"><p>Public datasets from research at the Boston '
        "University Faculty of Computing &amp; Data Sciences, hosted on the NSF-funded "
        '<a href="https://www.openstoragenetwork.org/">Open Storage Network</a>. Every file '
        "downloads directly, with no account.</p>"
        '<p class="terms">Data is provided as is, and availability is not guaranteed: keep your '
        "own copy of anything you rely on. Cite a dataset by its DOI where one is listed. "
        "Questions go to the contact or source listed on each dataset.</p></section>"
        f"{body}</main>"
        f'<footer class="pagefoot"><div class="ft-l"><img class="ft-emblem" '
        f'src="{assets.signature}" alt="Boston University Faculty of Computing &amp; Data '
        'Sciences"></div>'
        f'<div class="ft-c"><span class="stamp">Updated {updated.isoformat()}</span></div>'
        '<div class="ft-r"><a class="ft-link" '
        'href="https://www.bu.edu/policies/digital-privacy-statement/" target="_blank" '
        'rel="noopener">Privacy Statement</a></div></footer>'
        "</body></html>\n"
    )
