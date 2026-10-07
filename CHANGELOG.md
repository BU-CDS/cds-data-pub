# Changelog

## 2026-10-07

- New repo, ported and trimmed from cds-osn's catalog page: manifest without versions, withdrawals
  or request files; optional `notice` banner and per-dataset `source`; contributor tooling removed.
- File URLs may not contain percent-escapes or backslashes (a browser would resolve them outside
  the bucket). The runbook's upload command excludes hidden files and hidden folders.
- `contact` is optional; a card shows a Contact line only when one is set. Demo datasets list no
  contact (questions go to the source).
