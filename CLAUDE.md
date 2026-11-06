## Approach
- Reason only as much as the task needs; keep output concise.
- No sycophantic openers or closing fluff.
- No emojis or em-dashes.
- Do not guess APIs, versions, flags, commit SHAs, or package names. Verify by reading code or docs before asserting.

## Token efficiency
- Read only files directly needed, and only the relevant functions/sections. Skip files over 100KB unless required. Ask before broad scans.
- Do not re-read files or restate context already established, unless the files changed.
- Keep plans to 3-5 steps unless complexity requires more.
- For edits, show only the changed section, not full file.
- Default to brief answers. Expand only if asked.

## Project layout
Python CLI and systemd service that updates packages on Debian (apt) and RHEL (dnf) based systems.
- `linupdate.py` CLI entry point. `service.py` service entry point (main loop, or a module agent when given an argument).
- `src/controllers/` all code, imported as `src.controllers...` from the repository root (no `__init__.py`):
  - `app/` app config, service, triggers. `package/` package manager abstraction (`package.py`) and backends (`apt.py`, `dnf.py`).
  - `module/` module loader, `module/reposerver/` Repomanager server module (config, args, agent, status).
  - top-level helpers: args, lock, logging, mail, http requests, system detection, yaml, exit/exceptions.
- `templates/` default config files (`linupdate.template.yml`, `update.template.yml`, `modules/`), systemd unit, mail template.
- `version` holds the current version. `CHANGELOG.md` is used to build package changelogs.
- `.github/workflows/packaging/` deb (control, maintainer scripts) and rpm (spec) packaging. `.github/scripts/` CI helpers. `.github/tests/` pytest suite.

## Constraints
- Must stay compatible with Python 3.6 (CentOS 8): no walrus, no `match`, no PEP 604/585 type syntax, etc.
- Some modules are named like stdlib/third-party ones (`logging.py`, `yaml.py`, `apt.py`): always import them with their full `src.controllers...` path.
- `apt` (python3-apt) and `pyinotify` are distribution-only; tests stub them in `.github/tests/conftest.py`.

## Checks
Run from the repository root:
- Unit tests: `python3 -m pytest .github/tests -v`.
- Pylint: `pylint --recursive=y . --fail-under=9.9` (config in `.pylintrc`).
- Python 3.6 compatibility: `vermin --target=3.6- --violations --no-tips --no-parse-comments src linupdate.py service.py .github/tests`.
- Shell scripts: `shellcheck -x .github/scripts/*.sh .github/workflows/packaging/deb/{preinst,postinst,prerm,postrm}`.
- Package build and install tests only run in CI (`build-and-test-deb.yml`, `build-and-test-rpm.yml`).

## Commits
- Never commit or push anything
