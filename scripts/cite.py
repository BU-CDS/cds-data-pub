"""Citations for a dataset in APA, BibTeX and RIS.

A dataset's [citation] table describes its original publication; without one, the dataset cites
its catalog entry (BU CDS, the year it was added, its anchor on the page).
"""

from __future__ import annotations

from scripts.manifest import Citation, Dataset

PAGE_URL = "https://data.cds.bu.edu/"
ORG = "Boston University Faculty of Computing & Data Sciences"
PUBLISHER = "BU CDS Public Research Data"
_TEX = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def effective(ds: Dataset) -> Citation:
    """The dataset's own citation, or one for its catalog entry."""
    return ds.citation or Citation(
        authors=(ORG,), year=ds.added.year, title=ds.title, publisher=PUBLISHER, url=None
    )


def link(ds: Dataset) -> str:
    """Citation URL: the DOI (APA 7 prefers it), else [citation].url, else the source, else the
    catalog anchor."""
    if ds.doi:
        return f"https://doi.org/{ds.doi}"
    if ds.citation and ds.citation.url:
        return ds.citation.url
    return ds.source or f"{PAGE_URL}#{ds.slug}"


def _person(author: str) -> bool:
    return ", " in author


def _apa_name(author: str) -> str:
    if not _person(author):
        return author
    family, given = author.split(", ", 1)
    return f"{family}, " + " ".join(f"{part[0]}." for part in given.replace(".", " ").split())


def apa(ds: Dataset) -> str:
    """APA 7 reference for a data set."""
    c = effective(ds)
    names = [_apa_name(a) for a in c.authors]
    who = names[0] if len(names) == 1 else ", ".join(names[:-1]) + ", & " + names[-1]
    who += "" if who.endswith(".") else "."  # APA ends the author element with a period
    publisher = "" if c.authors == (c.publisher,) else f" {c.publisher}."  # APA omits a repeat
    return f"{who} ({c.year}). {c.title} [Data set].{publisher} {link(ds)}"


def _tex(text: str) -> str:
    return "".join(_TEX.get(ch, ch) for ch in text)


def bibtex(ds: Dataset) -> str:
    """A @misc BibTeX entry; organizations are braced so BibTeX keeps them one author."""
    c = effective(ds)
    authors = " and ".join(_tex(a) if _person(a) else "{" + _tex(a) + "}" for a in c.authors)
    rows = [
        ("author", authors),
        ("title", "{" + _tex(c.title) + "}"),
        ("year", str(c.year)),
        ("publisher", _tex(c.publisher)),
    ]
    if ds.doi:
        rows.append(("doi", ds.doi))
    rows.append(("url", link(ds)))
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in rows)
    return f"@misc{{{ds.slug},\n{body}\n}}"  # slugs are unique keys


def ris(ds: Dataset) -> str:
    """An RIS record of type DATA."""
    c = effective(ds)
    lines = ["TY  - DATA", *(f"AU  - {a}" for a in c.authors), f"TI  - {c.title}"]
    lines += [f"PY  - {c.year}", f"PB  - {c.publisher}"]
    if ds.doi:
        lines.append(f"DO  - {ds.doi}")
    lines += [f"UR  - {link(ds)}", "ER  - "]
    return "\n".join(lines)
