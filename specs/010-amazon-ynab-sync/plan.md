# Implementation Plan: Amazon-YNAB Smart Sync

**Branch**: `010-amazon-ynab-sync` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-amazon-ynab-sync/spec.md`

## Summary

Automated Amazon order categorization for YNAB: fetches Amazon order history via the `amazon-orders` scraping library, matches orders to YNAB transactions by date (±3 days) and exact amount, enriches transaction memos with item names, uses Claude to classify items into YNAB budget categories, and sends Erin split suggestions via WhatsApp for approval. Starts in suggestion mode (US1/US2), graduates to auto-split (US3) after 80%+ acceptance rate over 2 weeks.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK (Claude Haiku 4.5 for classification), httpx (YNAB API), amazon-orders>=4.0.18, existing WhatsApp/n8n infrastructure
**Storage**: JSON files in `data/` for sync records & category mappings; YNAB API for transaction writes
**Testing**: pytest + manual integration testing against live APIs
**Target Platform**: Docker on NUC (warp-nuc), scheduled via n8n
**Project Type**: Extension to existing web-service (new tool module + n8n endpoint)
**Performance Goals**: Sync completes within 5 minutes for a typical day's transactions
**Constraints**: Amazon scraping is slow with `full_details=True` (~1 req/order); YNAB API rate limit 200 req/hour; amazon-orders english amazon.com only
**Scale/Scope**: ~15-25 Amazon transactions per month, 1 user (Erin)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Integration Over Building | ✅ PASS | Leverages Amazon (existing shopping), YNAB (existing budget), WhatsApp (existing messaging). No custom budgeting or order tracking UI built. |
| II. Mobile-First Access | ✅ PASS | All interaction through WhatsApp — approve/adjust/skip, undo, mode toggle. No desktop-only features. |
| III. Simplicity & Low Friction | ✅ PASS | Erin replies "yes", "adjust", or "skip" — 1 tap/message. Auto-split reduces to zero taps. No setup beyond initial Amazon credentials. |
| IV. Structured Output | ✅ PASS | Split suggestions formatted as scannable lists: "$25 Healthcare, $43 Kids, $18 Electronics". Consolidated messages for batches. |
| V. Incremental Value | ✅ PASS | US1 (memo enrichment + suggestions) delivers standalone value. US2 (scheduling), US3 (auto-split), US4 (coaching) each layer independently. |

All gates pass. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/010-amazon-ynab-sync/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api-endpoints.md # New n8n endpoint contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── tools/
│   ├── amazon_sync.py       # NEW — Amazon order fetching, matching, sync orchestration
│   └── ynab.py              # MODIFIED — add split_transaction(), update_transaction_memo()
├── assistant.py             # MODIFIED — register new tools, add sync-related tool definitions
├── app.py                   # MODIFIED — add /api/v1/amazon/sync endpoint
└── config.py                # MODIFIED — add AMAZON_* env var validation

data/
├── amazon_sync_records.json # NEW — processed transaction log (prevents duplicates)
├── category_mappings.json   # NEW — learned item→category associations
└── amazon_sync_config.json  # NEW — auto-split mode flag, acceptance stats
```

**Structure Decision**: New `amazon_sync.py` tool module follows existing pattern (one module per integration domain). Sync state persists as JSON files in `data/` rather than Notion — this is internal bot state, not user-facing data. YNAB split support added to existing `ynab.py` since it's a general YNAB capability.

## Complexity Tracking

No constitution violations to justify. Feature follows existing patterns exactly.
