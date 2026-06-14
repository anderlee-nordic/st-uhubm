# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-06-14

Initial release.

### Added
- Pure parsers `parse_query_all` and `parse_hub_info` for the cusbi/cusba `-F`
  output (firmware v04+), decoding the little-endian port-state bitmap and
  reporting port count, firmware, serial, and model.
- `HubManager` and `Hub` Python API wrapping the vendor binary via subprocess,
  with volatile/persistent writes, save/reset/restore, and password change.
- `stuhubm` CLI: `health`, `list`, `status`, `on`, `off`, `toggle`, `all`,
  `save`, `reset`, `restore`, `passwd`; `--json` and `--verbose` output;
  `STUHUBM_*` environment variables; documented exit codes (0/1/2/3/4).
- Optional `stuhubm-gui` NiceGUI web app (`[gui]` extra) with per-port toggles,
  per-tab session isolation, a serialised hardware lock, and a live console.
- Sphinx documentation: user manual plus an auto-generated API reference,
  published on Read the Docs.
- Packaging via hatchling and a PyPI Trusted Publishing release workflow.

### Notes
- Licensed under GPL-2.0-or-later.
- Unofficial: the proprietary StarTech `cusbi` / `cusba` binary is required but
  not redistributed.

[0.1.0]: https://github.com/yourname/st-uhubm/releases/tag/v0.1.0
