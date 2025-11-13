# RedEye Project Structure

High-level layout of the repository, with the purpose of each folder and key files.


## Root

- `RedEye.md` — Project vision, scope, requirements, and architecture.
- `status.md` — Running changelog of completed work and fixes.
- `structure.md` — This document: directory and file overview.
- `reports/` — Generated scan reports and AI summaries (e.g. `reports/network_recon/`).
- `config/` — User/application configuration and persisted state.
  - `ai_settings.json` — Persisted AI provider and API key.
  - `user_state.json` — Disclaimer acceptance and other local state.
- `src/` — All application source code.
  - `main.py` — Launcher entrypoint. Run the app with: `python3 src/main.py`


## src/gui — Application UI

- `__init__.py` — Marks `gui` as a package.
- `main_window.py` — Top-level window, left navigation, page registration, and layout framing.
- `dashboard.py` — Dashboard tab UI (Use AI button and AI status).
- `reports.py` — Reports tab UI (lists reports, preview, Analyze with AI).

### src/gui/core — Shared UI/Core Services

- `__init__.py` — Core package marker.
- `ai_manager.py` — Shared AI service: persistence, validation, and API calls (ChatGPT/Gemini).
- `disclaimer.py` — One-time disclaimer dialog and state persistence.
- `module_panel.py` — Reusable informational module panel (kept for future use).


## src/modules — Functional Sections (each isolated and self-contained)

Each section contains its own UI (`.py`) and a `scripts/` directory with shell scripts invoked by that UI. You can work inside any section without affecting others.

- `anonymity/`
  - `__init__.py`
  - `anonymity.py` — Anonymity & Evasion UI (Proxychains, TOR, OpenVPN).
  - `scripts/`
    - `configure_proxychains.sh`
    - `start_tor.sh`
    - `stop_tor.sh`
    - `tor_status.sh`
    - `start_openvpn.sh`
    - `stop_openvpn.sh`

- `network_recon/`
  - `__init__.py`
  - `recon.py` — Reconnaissance & Scanning UI (Nmap, TheHarvester, Recon-ng, Amass, Gobuster).
  - `scripts/`
    - `nmap_subnet.sh`
    - `nmap_custom.sh`
    - `theharvester.sh`
    - `reconng_basic.sh`
    - `amass_enum.sh`
    - `gobuster_scan.sh`

- `vulnerability_scanning/`
  - `__init__.py`
  - `vulnerability.py` — Vulnerability scanning UI (OpenVAS, Lynis).
  - `scripts/`
    - `openvas_start.sh`
    - `openvas_stop.sh`
    - `openvas_import_targets.sh`
    - `openvas_scan.sh`
    - `lynis_audit.sh`

- `wireless_attacks/`
  - `__init__.py`
  - `wireless.py` — Wireless attacks UI (Aircrack-ng stack).
  - `scripts/`
    - `list_interfaces.sh`
    - `airmon_start.sh`
    - `airmon_stop.sh`
    - `capture_start.sh`
    - `capture_stop.sh`
    - `deauth.sh`
    - `crack_handshake.sh`

- `network_attacks/`
  - `__init__.py`
  - `network_attacks.py` — Network attacks UI (ARP spoofing, MitM, capture).
  - `scripts/`
    - `arp_spoof_start.sh`
    - `arp_spoof_stop.sh`
    - `capture_start.sh`
    - `capture_stop.sh`
    - `bettercap_start.sh`
    - `bettercap_stop.sh`

- `system_hacking/`
  - `__init__.py`
  - `system_hacking.py` — System hacking UI (Responder, reverse shells, credentials).
  - `scripts/`
    - `responder_start.sh`
    - `responder_stop.sh`
    - `generate_shell.sh`
    - `start_listener.sh`
    - `view_credentials.sh`

- `password_cracking/`
  - `__init__.py`
  - `password_cracking.py` — Password cracking UI (John, Hashcat, Hydra, Crunch).
  - `scripts/`
    - `john_run.sh`
    - `john_stop.sh`
    - `hashcat_run.sh`
    - `hydra_run.sh`
    - `crunch_generate.sh`


## How to work on a section

1. Edit the UI in that section’s `.py` file under `src/modules/<section>/`.
2. Add/modify shell logic in `src/modules/<section>/scripts/` and wire buttons to scripts via the provided `_run`/`_run_script` helpers.
3. No changes to other sections are required; modules are isolated.


## Running

- From project root:

```
python3 src/main.py
```


