# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Jerry Non-QM List App** — a project built around Texas Non-QM (Non-Qualified Mortgage) lending broker data. The dataset ranks loan officers and branch managers by origination volume.

## Data

### TX-NON-Qm-Lending-Brokers.csv

Source: MortgageMetrix dashboard export. Contains ~500 Texas Non-QM lending brokers ranked by origination volume.

**Columns:**
| Column | Description |
|--------|-------------|
| NMLSID | Individual NMLS license ID |
| Name | Loan officer / branch manager name |
| LO Role | `LO` (Loan Officer) or `BM` (Branch Manager) |
| Company NMLS | Company-level NMLS ID |
| Company | Company name |
| Type | `M` (Mortgage company) or `B` (Bank) |
| City, State | Office location (all TX) |
| Office Type | `Main`, `Branch`, or `Work` |
| Company Details | MortgageMetrix dashboard URL (keyed by Company NMLS) |
| # | Rank by total volume |
| Volume | Total origination volume (formatted, e.g. `$36.1M`) |
| Units | Total loan count |
| Monthly Volume / Monthly Units | Averaged monthly figures |
| Purchase Percent | Purchase vs. refi mix |
| Volume Export / Monthly Volume Export | Raw numeric values (comma-formatted integers) |

## Repository

- **Remote:** https://github.com/ptolomea9/jerry_nonqm.git
- **Default branch:** main
