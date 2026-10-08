"""Load and validate the catalog: catalog.toml plus one datasets/<slug>.toml per dataset.

Every rejection raises ManifestError naming the file (and dataset file, when known) and the field.
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BUCKET_BASE = "https://mghp.osn.xsede.org/bu-cds-public-data/"
MAX_FILES = 50
MAX_TAGS = 5
MAX_NOTICE = 24  # the notice is a tag in the page header, e.g. "Demo"
RESERVED_SLUGS = frozenset(("q", "live", "chips", "chips-hd"))  # element ids the page uses
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
LICENSE_RE = re.compile(r"^(?:Public domain|[A-Za-z0-9][A-Za-z0-9.+-]*)$")
# No query, fragment, percent-escape or backslash: browsers decode %2e%2e to .. and read \ as /
URL_RE = re.compile(rf"^{re.escape(BUCKET_BASE)}[^\s\"'<>?#%\\]+$")
HTTPS_RE = re.compile(r"^https://[^\s\"'<>]+$")

CATALOG_KEYS = frozenset(("notice", "tags"))
REQUIRED = ("title", "description", "license", "added", "tags", "file")
DATASET_KEYS = frozenset((*REQUIRED, "contact", "doi", "source", "citation"))
CITATION_REQUIRED = ("authors", "year", "title", "publisher")
CITATION_KEYS = frozenset((*CITATION_REQUIRED, "url", "doi"))
FILE_KEYS = ("name", "url", "size", "sha256")


class ManifestError(ValueError):
    """The catalog is invalid; the message names the file and field."""


@dataclass(frozen=True)
class Citation:
    """How to cite a dataset: its original publication, or (absent) the catalog entry."""

    authors: tuple[str, ...]
    year: int
    title: str
    publisher: str
    url: str | None
    doi: str | None  # the original publication's DOI (re-hosted data)


@dataclass(frozen=True)
class DataFile:
    """One downloadable file."""

    name: str
    url: str
    size: int
    sha256: str


@dataclass(frozen=True)
class Dataset:
    """One catalog entry."""

    slug: str
    title: str
    description: str
    license: str
    contact: str | None
    added: date
    doi: str | None
    source: str | None
    tags: tuple[str, ...]
    citation: Citation | None
    files: tuple[DataFile, ...]

    @property
    def total_size(self) -> int:
        """Sum of file sizes in bytes."""
        return sum(f.size for f in self.files)

    @property
    def prefix(self) -> str:
        """The folder below the bucket that holds every file (validated to be shared)."""
        return self.files[0].url[len(BUCKET_BASE) :].rsplit("/", 1)[0]


@dataclass(frozen=True)
class Catalog:
    """The page-wide notice, the allowed tags, and the datasets in display order."""

    notice: str | None
    tags: tuple[str, ...]
    datasets: list[Dataset]


def license_url(license: str) -> str | None:
    """The license terms page: SPDX for identifiers, none for 'Public domain'."""
    return None if license == "Public domain" else f"https://spdx.org/licenses/{license}.html"


def load_catalog(root: Path) -> Catalog:
    """Read catalog.toml and datasets/*.toml under root; datasets newest ``added`` first."""
    notice, vocab = _parse_catalog_toml(_read(root / "catalog.toml", "catalog.toml"))
    datasets = []
    for path in _dataset_paths(root, strict=True):
        where = f"datasets/{path.name}"
        datasets.append(parse_dataset(path.stem, _read(path, where), vocab, where))
    datasets.sort(key=lambda d: (-d.added.toordinal(), d.slug))
    return Catalog(notice=notice, tags=vocab, datasets=datasets)


def catalog_digest(root: Path) -> str:
    """sha256 over catalog.toml and datasets/*.toml (relative paths and bytes, dotfiles ignored)."""
    h = hashlib.sha256()
    for path in [root / "catalog.toml", *_dataset_paths(root, strict=False)]:
        if path.is_file():
            h.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return h.hexdigest()


def _dataset_paths(root: Path, *, strict: bool) -> list[Path]:
    folder = root / "datasets"
    if not folder.is_dir():
        return []
    paths = []
    for path in sorted(folder.iterdir()):
        if path.name.startswith("."):
            continue
        if path.suffix == ".toml" and path.is_file():
            paths.append(path)
        elif strict:
            raise ManifestError(f"datasets/{path.name}: only <slug>.toml files belong in datasets/")
    return paths


def _read(path: Path, where: str) -> dict:
    if not path.is_file():
        raise ManifestError(f"{where}: missing")
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(f"{where}: not valid TOML: {exc}") from exc


def _text(table: dict, key: str, where: str) -> str:
    value = table[key]
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{where}: field '{key}' must be non-empty text")
    return value.strip()


def _parse_catalog_toml(data: dict) -> tuple[str | None, tuple[str, ...]]:
    extra = set(data) - CATALOG_KEYS
    if extra:
        raise ManifestError(f"catalog.toml: unknown top-level key(s): {', '.join(sorted(extra))}")
    notice = _text(data, "notice", "catalog.toml") if "notice" in data else None
    if notice is not None and len(notice) > MAX_NOTICE:
        raise ManifestError(
            f"catalog.toml: field 'notice' is a short header tag (at most {MAX_NOTICE} characters)"
        )
    tags = data.get("tags", [])
    if (
        not isinstance(tags, list)
        or not all(isinstance(t, str) and SLUG_RE.match(t) for t in tags)
        or len(set(tags)) != len(tags)
    ):
        raise ManifestError(
            "catalog.toml: field 'tags' must be a list of unique lowercase-hyphen tags"
        )
    return notice, tuple(tags)


def parse_dataset(slug: str, entry: dict, vocab: tuple[str, ...], where: str) -> Dataset:
    """Validate one dataset table read from ``where`` (datasets/<slug>.toml)."""
    if not SLUG_RE.match(slug):
        raise ManifestError(
            f"{where}: file name must be the slug: lowercase letters and digits joined by single"
            " hyphens"
        )
    if slug in RESERVED_SLUGS:
        raise ManifestError(
            f"{where}: file name '{slug}' is reserved by the page; pick another slug"
        )
    unknown = set(entry) - DATASET_KEYS
    if unknown:
        raise ManifestError(f"{where}: unknown field(s): {', '.join(sorted(unknown))}")
    for key in REQUIRED:
        if key not in entry:
            raise ManifestError(f"{where}: missing field '{key}'")
    license = _text(entry, "license", where)
    if not LICENSE_RE.match(license):
        raise ManifestError(
            f"{where}: field 'license' must be an SPDX identifier (e.g. CC-BY-4.0)"
            " or 'Public domain'"
        )
    added = entry["added"]
    if type(added) is not date:  # tomllib gives datetime (a date subclass) for date-times
        raise ManifestError(f"{where}: field 'added' must be a date like 2026-10-07")
    contact = _text(entry, "contact", where) if "contact" in entry else None
    if contact is not None and "@" not in contact:
        raise ManifestError(f"{where}: field 'contact' must be an email address")
    doi = _text(entry, "doi", where) if "doi" in entry else None
    if doi is not None and not DOI_RE.match(doi):
        raise ManifestError(f"{where}: field 'doi' must be a bare DOI like 10.1234/example")
    source = _text(entry, "source", where) if "source" in entry else None
    if source is not None and not HTTPS_RE.match(source):
        raise ManifestError(f"{where}: field 'source' must be an https:// URL")
    tags = entry["tags"]
    if not isinstance(tags, list) or not 1 <= len(tags) <= MAX_TAGS:
        raise ManifestError(f"{where}: field 'tags' must list 1 to {MAX_TAGS} tags")
    stray = [t for t in tags if t not in vocab]
    if stray:
        raise ManifestError(
            f"{where}: field 'tags': {', '.join(map(str, stray))} not in catalog.toml tags"
        )
    if len(set(tags)) != len(tags):
        raise ManifestError(f"{where}: field 'tags' has a duplicate tag")
    citation = _parse_citation(entry["citation"], where) if "citation" in entry else None
    files = _parse_files(entry["file"], where)
    return Dataset(
        slug=slug,
        title=_text(entry, "title", where),
        description=_text(entry, "description", where),
        license=license,
        contact=contact,
        added=added,
        doi=doi,
        source=source,
        tags=tuple(tags),
        citation=citation,
        files=files,
    )


def _parse_citation(raw: object, where: str) -> Citation:
    cwhere = f"{where}, [citation]"
    if not isinstance(raw, dict):
        raise ManifestError(f"{cwhere}: must be a table")
    unknown = set(raw) - CITATION_KEYS
    if unknown:
        raise ManifestError(f"{cwhere}: unknown field(s): {', '.join(sorted(unknown))}")
    for key in CITATION_REQUIRED:
        if key not in raw:
            raise ManifestError(f"{cwhere}: missing field '{key}'")
    authors = raw["authors"]
    if (
        not isinstance(authors, list)
        or not authors
        or not all(isinstance(a, str) and a.strip() for a in authors)
    ):
        raise ManifestError(f"{cwhere}: field 'authors' must be a non-empty list of names")
    year = raw["year"]
    if type(year) is not int or not 1900 <= year <= 2100:
        raise ManifestError(f"{cwhere}: field 'year' must be a year like 2020")
    url = _text(raw, "url", cwhere) if "url" in raw else None
    if url is not None and not HTTPS_RE.match(url):
        raise ManifestError(f"{cwhere}: field 'url' must be an https:// URL")
    doi = _text(raw, "doi", cwhere) if "doi" in raw else None
    if doi is not None and not DOI_RE.match(doi):
        raise ManifestError(f"{cwhere}: field 'doi' must be a bare DOI like 10.1234/example")
    return Citation(
        authors=tuple(a.strip() for a in authors),
        year=year,
        title=_text(raw, "title", cwhere),
        publisher=_text(raw, "publisher", cwhere),
        url=url,
        doi=doi,
    )


def _parse_files(raw: object, where: str) -> tuple[DataFile, ...]:
    if not isinstance(raw, list) or not raw:
        raise ManifestError(f"{where}: needs at least one [[file]]")
    if len(raw) > MAX_FILES:
        raise ManifestError(
            f"{where}: {len(raw)} files; the limit is {MAX_FILES}"
            " (package them as .tar.gz or .zip archives)"
        )
    files = tuple(_parse_file(where, i, f) for i, f in enumerate(raw))
    for attr in ("name", "url"):
        values = [getattr(f, attr) for f in files]
        dupes = sorted({v for v in values if values.count(v) > 1})
        if dupes:
            raise ManifestError(f"{where}: duplicate file {attr}: {dupes[0]}")
    folders = {f.url.rsplit("/", 1)[0] for f in files}
    if len(folders) > 1:
        raise ManifestError(f"{where}: all files must sit in one folder of the bucket")
    if not folders.pop().startswith(BUCKET_BASE):
        raise ManifestError(f"{where}: files must sit in a folder below the bucket, not its root")
    return files


def _parse_file(where: str, index: int, entry: object) -> DataFile:
    fwhere = f"{where}, file #{index + 1}"
    if not isinstance(entry, dict):
        raise ManifestError(f"{fwhere}: must be a table")
    if isinstance(entry.get("name"), str) and entry["name"].strip():
        fwhere = f"{where}, file '{entry['name'].strip()}'"
    unknown = set(entry) - set(FILE_KEYS)
    if unknown:
        raise ManifestError(f"{fwhere}: unknown field(s): {', '.join(sorted(unknown))}")
    for key in FILE_KEYS:
        if key not in entry:
            raise ManifestError(f"{fwhere}: missing field '{key}'")
    name = _text(entry, "name", fwhere)
    if "/" in name:
        raise ManifestError(f"{fwhere}: field 'name' must be a file name, not a path")
    url = _text(entry, "url", fwhere)
    if not URL_RE.match(url):
        raise ManifestError(f"{fwhere}: field 'url' must start with {BUCKET_BASE}")
    if any(seg in ("", ".", "..") for seg in url[len(BUCKET_BASE) :].split("/")):
        raise ManifestError(f"{fwhere}: field 'url' has an empty or dot path segment")
    if not url.endswith(f"/{name}"):
        raise ManifestError(f"{fwhere}: field 'url' must end with /{name}")
    size = entry["size"]
    if type(size) is not int or size <= 0:  # type() check also refuses bool
        raise ManifestError(f"{fwhere}: field 'size' must be a positive whole number of bytes")
    sha = _text(entry, "sha256", fwhere).lower()
    if not SHA256_RE.match(sha):
        raise ManifestError(f"{fwhere}: field 'sha256' must be 64 hex characters")
    return DataFile(name=name, url=url, size=size, sha256=sha)
