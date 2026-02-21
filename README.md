# RedEye

PyQt5 desktop prototype for orchestrating red-team reconnaissance tasks (Phase 1). The GUI focuses on operational scaffolding: launching tools via bash scripts, capturing outputs, and wiring results into the interface for rapid analysis and reporting.

---

## Requirements

- Python 3.10+
- PyQt5 (`pip install PyQt5`)
- `requests` for AI integration (`pip install requests`)
- Recon tooling (install any you plan to use):
  - `nmap`
  - `theHarvester`
  - `recon-ng`
  - `amass`
  - `gobuster`
  - `openvpn`, `proxychains`, `tor`, etc., for other modules

Optional (AI workflows):
- OpenAI or Google Generative AI API key

**Privacy:** API keys and generated reports are **not** committed to the repo. Copy `src/config/ai_settings.json.example` to `src/config/ai_settings.json` and add your key locally. The `reports/` directory is gitignored.

---

## Quick Start

```bash
git clone <repo>
cd RedEye
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # create your own, or install PyQt5 + requests
python3 src/main.py
```

The app stores generated reports under `reports/`. Recon tools automatically create subfolders such as `reports/network_recon/`.

---

## Modules & Workflow

Navigation lives on the left side of the main window. Each section has a dedicated `.py` UI file and bash scripts under `src/modules/<module>/scripts/`. Modifying a module is completely isolated—edit its Python UI and scripts without touching the rest of the app.

| Module | Purpose | Key Scripts |
| --- | --- | --- |
| Dashboard | Configure AI (ChatGPT/Gemini) and view status | — |
| Anonymity & Evasion | Proxychains, TOR, OpenVPN controls | `configure_proxychains.sh`, `start_tor.sh`, `start_openvpn.sh`, etc. |
| Reconnaissance & Scanning | Nmap (auto/custom), TheHarvester, Recon-ng, Amass, Gobuster | scripts under `src/modules/network_recon/scripts/` |
| Vulnerability Scanning | OpenVAS service, Lynis audit | `openvas_*.sh`, `lynis_audit.sh` |
| Wireless Attacks | Aircrack-ng workflow helpers | `list_interfaces.sh`, `airmon_start.sh`, `deauth.sh`, etc. |
| Network Attacks | ARP spoofing, traffic capture, Bettercap | `arp_spoof_*.sh`, `bettercap_*.sh` |
| System Hacking | Reverse shells (msfvenom) | `generate_shell.sh`, `start_listener.sh` |
| Password Cracking | John, Hashcat, Hydra, Crunch | `john_*.sh`, `hashcat_run.sh`, `hydra_run.sh`, `crunch_generate.sh` |
| Reports | Browse every `.txt` / `.md` report under `reports/`, preview, run AI analysis | — |

Each script writes tool output to `reports/<module>/...` using timestamped filenames so the Reports tab picks them up automatically.

---

## Reports & AI Analysis

- All outputs are saved under the project root `reports/` directory.
- The Reports tab scans recursively; click **Refresh** after generating a report.
- **Analyze with AI** sends the selected report’s content to the configured provider. Requires an API key (configured via Dashboard → “Use AI…”). AI responses are saved alongside the original report in Markdown format.
- **View Raw Report** toggles back to the source file.

---

## Customizing / Extending

- **UI changes**: edit the module’s `.py` file in `src/modules/<module>/`.
- **Automation logic**: edit or create scripts in `src/modules/<module>/scripts/`, then wire buttons to them via the helper methods already in each module.
- **Adding a new tool**: follow the pattern used in the Recon module—create a small dialog for inputs, add a button, and use `_start_tool(...)` or equivalent to run the script in a background thread.
- **Styling**: adjust `src/gui/main_window.py` or module layouts. Size policies are set to allow full resize/maximize.

---

## Troubleshooting

- **Window won’t resize/maximize**: ensure you’re running the latest code—size policies were added in `src/gui/main_window.py`.
- **Reports tab is empty**: make sure the app is restarted; the tab looks in `/home/<user>/RedEye/reports/`. After generating a report click **Refresh**.
- **Tool buttons greyed out**: buttons enable after selecting a report or configuring AI. Re-select the file if necessary.
- **Scripts not running**: confirm the external tool is installed and accessible in `$PATH`. Scripts display clear error messages in the GUI output panel.

---

## Repository Map

See `structure.md` for a full directory-by-directory breakdown, and `status.md` for the development changelog.

---

Happy hacking—customize each module’s tooling and scripts to fit your red-team workflow!

