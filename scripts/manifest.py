"""Load and validate datasets.toml, the catalog manifest.

Every rejection raises ManifestError naming the dataset (slug when known) and the field.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BUCKET_BASE = "https://mghp.osn.xsede.org/bu-cds-public-data/"
MAX_FILES = 50
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
# No query, fragment, percent-escape or backslash: browsers decode %2e%2e to .. and read \ as /
URL_RE = re.compile(rf"^{re.escape(BUCKET_BASE)}[^\s\"'<>?#%\\]+$")
SOURCE_RE = re.compile(r"^https://[^\s\"'<>]+$")

TOP_KEYS = frozenset(("notice", "dataset"))
REQUIRED = ("slug", "title", "description", "license", "added", "file")
DATASET_KEYS = frozenset((*REQUIRED, "contact", "doi", "source"))
FILE_KEYS = ("name", "url", "size", "sha256")


class ManifestError(ValueError):
    """The manifest is invalid; the message names the dataset and field."""


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
    files: tuple[DataFile, ...]

    @property
    def total_size(self) -> int:
        """Sum of file sizes in bytes."""
        return sum(f.size for f in self.files)


@dataclass(frozen=True)
class Catalog:
    """The whole manifest: an optional page-wide notice and the datasets in display order."""

    notice: str | None
    datasets: list[Dataset]


def load_manifest(path: Path) -> Catalog:
    """Read and validate a TOML manifest.

    Raises:
        ManifestError: The file is not valid TOML or an entry is invalid.
    """
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(f"{path}: not valid TOML: {exc}") from exc
    return parse_manifest(data)


def parse_manifest(data: dict) -> Catalog:
    """Validate parsed TOML. Datasets come back newest ``added`` first, then by slug."""
    extra = set(data) - TOP_KEYS
    if extra:
        raise ManifestError(f"unknown top-level key(s): {', '.join(sorted(extra))}")
    notice = _text(data, "notice", "manifest") if "notice" in data else None
    raw = data.get("dataset", [])
    if not isinstance(raw, list):
        raise ManifestError("'dataset' must be an array of tables ([[dataset]])")
    datasets = [_parse_dataset(i, e) for i, e in enumerate(raw)]
    seen: set[str] = set()
    for ds in datasets:
        if ds.slug in seen:
            raise ManifestError(f"dataset '{ds.slug}': duplicate slug")
        seen.add(ds.slug)
    datasets.sort(key=lambda d: (-d.added.toordinal(), d.slug))
    return Catalog(notice=notice, datasets=datasets)


def _text(table: dict, key: str, where: str) -> str:
    value = table[key]
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{where}: field '{key}' must be non-empty text")
    return value.strip()


def _parse_dataset(index: int, entry: object) -> Dataset:
    where = f"dataset #{index + 1}"
    if not isinstance(entry, dict):
        raise ManifestError(f"{where}: must be a table")
    if isinstance(entry.get("slug"), str) and entry["slug"].strip():
        where = f"dataset '{entry['slug'].strip()}'"
    unknown = set(entry) - DATASET_KEYS
    if unknown:
        raise ManifestError(f"{where}: unknown field(s): {', '.join(sorted(unknown))}")
    for key in REQUIRED:
        if key not in entry:
            raise ManifestError(f"{where}: missing field '{key}'")
    slug = _text(entry, "slug", where)
    if not SLUG_RE.match(slug):
        raise ManifestError(
            f"{where}: field 'slug' must be lowercase letters and digits joined by single hyphens"
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
    if source is not None and not SOURCE_RE.match(source):
        raise ManifestError(f"{where}: field 'source' must be an https:// URL")
    raw_files = entry["file"]
    if not isinstance(raw_files, list) or not raw_files:
        raise ManifestError(f"{where}: needs at least one [[dataset.file]]")
    if len(raw_files) > MAX_FILES:
        raise ManifestError(
            f"{where}: {len(raw_files)} files; the limit is {MAX_FILES}"
            " (package them as .tar.gz or .zip archives)"
        )
    files = tuple(_parse_file(where, i, f) for i, f in enumerate(raw_files))
    for attr in ("name", "url"):
        values = [getattr(f, attr) for f in files]
        dupes = sorted({v for v in values if values.count(v) > 1})
        if dupes:
            raise ManifestError(f"{where}: duplicate file {attr}: {dupes[0]}")
    return Dataset(
        slug=slug,
        title=_text(entry, "title", where),
        description=_text(entry, "description", where),
        license=_text(entry, "license", where),
        contact=contact,
        added=added,
        doi=doi,
        source=source,
        files=files,
    )


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
