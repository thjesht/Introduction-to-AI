# Introduction-to-AI – VLSM extension (v1.1.0)

This is an additive VLSM feature package designed to integrate with the existing `ipcalc.py` without modifying or replacing it. The original uploaded calculator is preserved in this bundle as `ipcalc_existing.py` for reference; keep your repository's existing `ipcalc.py` as the source of truth.

## Scope and behavior

- IPv4 VLSM allocation; IPv6 VLSM is intentionally not supported in this first release.
- Largest host requirement is allocated first; equal-sized requests preserve input order.
- Conventional LAN accounting reserves network and broadcast addresses (usable hosts = total addresses - 2).
- Rejects invalid host counts, duplicate subnet names, unsupported IPv6 parents, and insufficient address space.
- Shared calculation engine powers CLI, optional Tkinter desktop UI, and optional FastAPI HTTP API.
- No third-party dependency is required for the calculation engine, CLI, or Tkinter UI.

## Create the feature branch in VS Code terminal

```powershell
git switch develop
git pull origin develop
git switch -c feature/vlsm-calculator
```

Copy the `network_toolkit` folder, `tests` folder, and `pyproject.toml` into the root of your existing project. Do not overwrite `ipcalc.py`.

## Run the test suite

From the project root:

```powershell
python -m unittest discover -s tests -v
```

Or, if using pytest:

```powershell
python -m pip install -e ".[dev]"
pytest -q
```

## CLI

```powershell
python -m network_toolkit.cli 192.168.10.0/24 --subnet Users 100 --subnet Servers 50 --subnet Voice 20 --subnet Management 10
```

JSON output:

```powershell
python -m network_toolkit.cli 192.168.10.0/24 --subnet Users 100 --subnet Servers 50 --json
```

## Desktop GUI (Tkinter)

```powershell
python -m network_toolkit.gui
```

Tkinter is included with most standard Windows Python installations. If your Python distribution does not include it, install/repair Python with the Tcl/Tk option enabled.

## REST API (optional)

```powershell
python -m pip install -e ".[api]"
uvicorn network_toolkit.api:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation. Example request:

```json
{
  "parent": "192.168.10.0/24",
  "subnets": [
    {"name": "Users", "hosts": 100},
    {"name": "Servers", "hosts": 50},
    {"name": "Voice", "hosts": 20}
  ]
}
```

## Integration and Git workflow

The extension is deliberately isolated so the existing calculator keeps working. After tests pass:

```powershell
git add network_toolkit tests pyproject.toml README.md
git commit -m "Add VLSM calculator module with CLI GUI and API"
git push -u origin feature/vlsm-calculator
```

Open a Pull Request on GitHub: `feature/vlsm-calculator` → `develop`. Merge only after reviewing the diff and confirming the existing `ipcalc.py` behavior remains unchanged.

## Known next steps

- Add integration tests for the existing `ipcalc.py` command-line behavior.
- Add optional VLSM reservation modes for point-to-point `/31` links.
- Add CSV/XLSX export and persistent project plans.
- Add web frontend separately; this package currently exposes the backend REST API, not a browser UI.
