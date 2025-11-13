"""
Network Reconnaissance module package.

This package provides the ReconnaissanceModule class which implements:
- Nmap scanning (automatic subnet + custom mode)
- GUI sections for:
    • TheHarvester
    • Recon-ng
    • Amass
    • Gobuster

Only Nmap functionality is currently implemented.
The other tools include GUI groups and “Coming Soon” placeholders.
"""
from .recon import ReconnaissanceModule

__all__ = ["ReconnaissanceModule"]
