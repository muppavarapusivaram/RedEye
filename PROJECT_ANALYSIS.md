# RedEye (ARTA) – Full Project Analysis

**Date:** 2025-02-21  
**Scope:** Red teaming automation – GUI (Python/PyQt5), automation (Bash).  
**Sources:** README.md, status.md, structure.md, and all code under `src/`.

---

## 1. Project Overview

- **Name:** Automated Red Teaming Assistant (ARTA) / RedEye  
- **Purpose:** Desktop GUI to orchestrate red-team tasks: run recon/attack tools via bash scripts, capture output, and use AI (ChatGPT/Gemini) for report analysis.  
- **Stack:** Python 3.10+, PyQt5, `requests`; bash scripts under `src/modules/<module>/scripts/`.  
- **Entry point:** `python3 src/main.py` (from repo root).  
- **Config/state:** `src/config/ai_settings.json`, `src/config/user_state.json`; reports under `reports/`.

---

## 2. Documentation Summary

### README.md
- Describes requirements (Python, PyQt5, requests, optional recon tools and AI API keys).
- Quick start: venv, `pip install` (no `requirements.txt` in repo – user must create or install PyQt5 + requests).
- Modules table: Dashboard, Anonymity, Recon, Vulnerability, Wireless, Network Attacks, System Hacking, Password Cracking, Reports.
- Reports & AI: reports under `reports/`, Refresh in Reports tab, “Analyze with AI” with API key from Dashboard.
- Customization: edit module `.py` and `scripts/` per module; styling in `main_window.py`.
- Troubleshooting: resize/maximize, reports path, greyed buttons, script errors.

### status.md
- Changelog from 2025-11-12 to 2025-11-13.
- Covers: GUI scaffold, theme, disclaimer, Anonymity (proxychains/TOR/OpenVPN), AI config (ChatGPT/Gemini), Nmap (subnet/custom, threading, cancel), AI report analysis, Reports tab, Gemini endpoints/model discovery, modular GUI (`gui/core/`, `gui/modules/`), Recon tools (TheHarvester, Recon-ng, Amass, Gobuster), recursive reports scan, window sizing.

### structure.md
- Directory map: root, `reports/`, `config/` (note: config lives under `src/config/` in code), `src/`, `src/gui/`, `src/gui/core/`, and each `src/modules/<section>/` with its `scripts/`.
- Explains how to work on a section (UI + scripts only, no cross-module edits).

---

## 3. Code Architecture

### 3.1 Entry and GUI layout

| File | Role |
|------|------|
| `src/main.py` | App entry: `QApplication`, global stylesheet, disclaimer, then `MainWindow`. Imports from `gui.core.disclaimer`, `gui.main_window`. |
| `src/gui/main.py` | **Duplicate** entry with imports `core.disclaimer`, `main_window` (for running from `src/gui/`). Not used by README; can be removed or kept as alternate launcher. |
| `src/gui/main_window.py` | Main window: left nav, stacked pages, registers all modules and tabs (Dashboard, Anonymity, Recon, Vuln, Wireless, Network Attacks, System Hacking, Password Cracking, Reports). Uses `gui.dashboard`, `gui.reports`, and all `modules.<name>.<name>`. On close, calls `anonymity_module.shutdown()`. |

**Active GUI files:** `src/gui/dashboard.py`, `src/gui/reports.py`, `src/gui/core/*`.  
**Legacy/duplicate:** `src/gui/modules/` (dashboard, reports, recon, anonymity) use `core.*` and different paths; not referenced by `main_window.py`. Safe to remove or consolidate later.

### 3.2 Core GUI (`src/gui/core/`)

| File | Role |
|------|------|
| `disclaimer.py` | One-time disclaimer dialog; state in `config/user_state.json` (`disclaimerAccepted`). Path: `parents[2]` from this file = project root if run from `src/` – but file lives under `src/gui/core/`, so `parents[2]` = `src/`; **config is under `src/config/`**, so path is correct. |
| `ai_manager.py` | AI config: load/save `config/ai_settings.json`, validate OpenAI/Gemini keys, `generate_analysis()` for report/scan text. Model discovery for Gemini. |
| `module_panel.py` | Generic placeholder panel (objectives, tools, “Configure Module”, “View Saved Results”). Not used by current main window; kept for future. |

### 3.3 Tabs used by main window

| Tab | Implementation | Notes |
|-----|----------------|------|
| Dashboard | `gui/dashboard.py` → `DashboardTab` | AI config dialog (ChatGPT/Gemini), API validation, roadmap list, quick actions, AI status. |
| Reports | `gui/reports.py` → `ReportsTab` | Recursive scan of `reports/` for `*.md`/`*.txt`, list + preview, “Analyze with AI” (background thread), “View Raw Report”, save AI summary as `*_ai_summary_<ts>.md`. `PROJECT_ROOT = Path(__file__).resolve().parents[2]` → from `src/gui/reports.py` = project root. |
| Anonymity | `modules.anonymity.anonymity` → `AnonymityModule` | Proxychains dialog, TOR start/stop/status, OpenVPN (file picker, QProcess). Runs scripts via `_run_script()` with optional sudo. |
| Recon | `modules.network_recon.recon` → `ReconnaissanceModule` | Nmap (auto subnet / custom), TheHarvester, Recon-ng, Amass, Gobuster. Dialogs for each; `ScanWorker` (QThread) for long runs; cancel support. **Fixed:** `REPORTS_DIR` was `parents[4]` (wrong); set to `parents[3]` so it points to project root then `reports/network_recon`. |
| Vulnerability | `modules.vulnerability_scanning.vulnerability` | OpenVAS start/stop, import targets, scan; Lynis audit. Buttons call `_run(script_name)` – blocking `subprocess.run` (no threading). |
| Wireless | `modules.wireless_attacks.wireless` | Interface list, monitor mode, capture start/stop, deauth, crack handshake. Same blocking `_run()` pattern. |
| Network Attacks | `modules.network_attacks.network_attacks` | ARP spoof start/stop, capture start/stop, Bettercap start/stop. Blocking `_run()`. |
| System Hacking | `modules.system_hacking.system_hacking` | Responder start/stop, generate shell, start listener, view credentials. Blocking `_run()`. |
| Password Cracking | `modules.password_cracking.password_cracking` | John run/stop, Hashcat, Hydra, Crunch. Blocking `_run()`. |

---

## 4. Module-by-Module Code Notes

### 4.1 Anonymity (`src/modules/anonymity/`)

- **anonymity.py:** Full UI and logic: proxy config dialog (SOCKS, chain mode, list), TOR/VPN controls, `_run_script(script_name, args, require_root)` with sudo prompt, OpenVPN via QProcess + optional sudo. Clean shutdown in `shutdown()`.
- **Scripts:** All six scripts are **stubs** – they only print `[TODO] ... not yet implemented.`  
  - `configure_proxychains.sh`, `start_tor.sh`, `stop_tor.sh`, `tor_status.sh`, `start_openvpn.sh`, `stop_openvpn.sh`.

### 4.2 Network Recon (`src/modules/network_recon/`)

- **recon.py:** Large module: NmapDialog, HarvesterDialog, ReconNgDialog, AmassDialog, GobusterDialog; `ScanWorker` (streaming output, cancel); `AIAnalysisWorker` (present but not wired to post-scan AI in current flow – reports are saved by scripts and analyzed from Reports tab). `REPORTS_DIR` fixed to `parents[3] / "reports" / "network_recon"`.
- **Scripts – implemented:**  
  - `nmap_subnet.sh`: Detects default interface and CIDR, runs `nmap -sS -sV -T4 ...`, saves to `reports/network_recon/nmap_subnet_<ts>.txt`.  
  - `nmap_custom.sh`: Target + extra args, `-sS -sV -O`, saves to `nmap_custom_<ts>.txt`.  
  - `theharvester.sh`: domain, sources, limit → theHarvester/theharvester, output to `theharvester_<domain>_<ts>.txt`.  
  - `reconng_basic.sh`: domain, workspace; RC file with workspaces + modules (brute_hosts, enum_simple, google_site_web), output to `reconng_<workspace>_<ts>.txt`.  
  - `amass_enum.sh`: domain, mode (passive/active/bruteforce), output to `amass_<mode>_<domain>_<ts>.txt`.  
  - `gobuster_scan.sh`: mode (dir/dns), target, wordlist, optional extensions; output to `gobuster_<mode>_<ts>.txt`.

### 4.3 Vulnerability Scanning (`src/modules/vulnerability_scanning/`)

- **vulnerability.py:** OpenVAS and Lynis groups; `_run(script_name, args)` with 600s timeout. No threading – GUI can freeze on long runs.
- **Scripts:** All **stubs**: `openvas_start.sh`, `openvas_stop.sh`, `openvas_import_targets.sh`, `openvas_scan.sh`, `lynis_audit.sh`.

### 4.4 Wireless Attacks (`src/modules/wireless_attacks/`)

- **wireless.py:** Four groups (interfaces, capture, attacks, cracking); same blocking `_run()`.
- **Scripts:** All **stubs**: `list_interfaces.sh`, `airmon_start.sh`, `airmon_stop.sh`, `capture_start.sh`, `capture_stop.sh`, `deauth.sh`, `crack_handshake.sh`.

### 4.5 Network Attacks (`src/modules/network_attacks/`)

- **network_attacks.py:** ARP, capture, Bettercap; blocking `_run()`.
- **Scripts:** All **stubs**: `arp_spoof_start.sh`, `arp_spoof_stop.sh`, `capture_start.sh`, `capture_stop.sh`, `bettercap_start.sh`, `bettercap_stop.sh`.

### 4.6 System Hacking (`src/modules/system_hacking/`)

- **system_hacking.py:** Responder, reverse shell, listener, credentials; blocking `_run()`.
- **Scripts:** All **stubs**: `responder_start.sh`, `responder_stop.sh`, `generate_shell.sh`, `start_listener.sh`, `view_credentials.sh`.

### 4.7 Password Cracking (`src/modules/password_cracking/`)

- **password_cracking.py:** John, Hashcat, Hydra, Crunch; blocking `_run()`.
- **Scripts:** All **stubs**: `john_run.sh`, `john_stop.sh`, `hashcat_run.sh`, `hydra_run.sh`, `crunch_generate.sh`.

---

## 5. Issues and Recommendations

### 5.1 Bugs fixed in this pass

- **recon.py REPORTS_DIR:** Was `parents[4]` (one level above project root). Changed to `parents[3]` so `reports/network_recon` is under the project root.  
  - Note: `REPORTS_DIR` in recon.py is used for `REPORTS_DIR.mkdir(parents=True, exist_ok=True)` only; actual report paths are chosen by the bash scripts (which use their own `PROJECT_ROOT`). So this fix keeps Python and scripts aligned if any Python code were to write reports later.

### 5.2 Security / hygiene

- **API key in repo:** `src/config/ai_settings.json` contains a Gemini API key. It should be in `.gitignore` and loaded from environment or a non-committed config; consider adding `src/config/ai_settings.json` to `.gitignore` and documenting a template.

### 5.3 Consistency and UX

- **Blocking scripts:** Vulnerability, Wireless, Network Attacks, System Hacking, Password Cracking all use `subprocess.run(..., timeout=600)` with no threading. Long tasks will freeze the GUI. Recommend moving to a worker thread + streaming (or at least a “Running…” state) like Recon.
- **Debug prints:** `recon.py`, `vulnerability.py`, `wireless.py`, `network_attacks.py`, `system_hacking.py`, `password_cracking.py` contain `print("[DEBUG] Loading ...")`. Remove for production or gate behind a debug flag.
- **Duplicate launcher:** `src/gui/main.py` duplicates `src/main.py` with different imports. Prefer a single entry point (`src/main.py`) and remove or clearly document the other.
- **requirements.txt:** README references it but it’s missing. Add `requirements.txt` with PyQt5 and requests (and versions) so Quick Start works as stated.

### 5.4 Stub scripts (by area)

- **Anonymity:** 6 scripts – all stubs.  
- **Vulnerability:** 5 scripts – all stubs.  
- **Wireless:** 7 scripts – all stubs.  
- **Network Attacks:** 6 scripts – all stubs.  
- **System Hacking:** 5 scripts – all stubs.  
- **Password Cracking:** 5 scripts – all stubs.  
- **Recon:** 6 scripts – all implemented and writing to `reports/network_recon/`.

Implementing these stubs (or clearly marking them “optional / not implemented” in the UI) will align the GUI with user expectations.

### 5.5 Minor

- **structure.md:** Says config is at `config/` at root; actual path is `src/config/`. Update doc to `src/config/`.
- **Dashboard roadmap:** Text still says “Phase 1 – GUI foundation (in progress)” and “Phase 3 – Gemini AI integration”; status.md shows AI and Recon are already in place. Consider updating the roadmap text.

---

## 6. File Inventory (implementation status)

| Area | Python UI | Scripts |
|------|-----------|--------|
| Entry | `src/main.py` (canonical), `src/gui/main.py` (duplicate) | — |
| Main window | `src/gui/main_window.py` | — |
| Core | `disclaimer.py`, `ai_manager.py`, `module_panel.py` | — |
| Dashboard | `src/gui/dashboard.py` | — |
| Reports | `src/gui/reports.py` | — |
| Anonymity | Implemented | 6 stubs |
| Recon | Implemented | 6 implemented |
| Vulnerability | Implemented | 5 stubs |
| Wireless | Implemented | 7 stubs |
| Network Attacks | Implemented | 6 stubs |
| System Hacking | Implemented | 5 stubs |
| Password Cracking | Implemented | 5 stubs |

---

## 7. Summary

- **Working:** App launch, disclaimer, main window, Dashboard (AI config + validation), Reports (list, preview, AI analysis, save summary), Recon (Nmap auto/custom, TheHarvester, Recon-ng, Amass, Gobuster with dialogs and background workers), Anonymity UI (script calls work but scripts are stubs).  
- **Fixed:** `REPORTS_DIR` in `recon.py` (parents[3] for project root).  
- **To do:** Add `requirements.txt`; consider ignoring `ai_settings.json` and using env/template; implement or clearly label stub scripts; add background threading for Vulnerability/Wireless/Network/System/Password modules; remove debug prints; update structure.md and Dashboard roadmap text; optionally remove or document `src/gui/main.py` and `src/gui/modules/` duplicates.
