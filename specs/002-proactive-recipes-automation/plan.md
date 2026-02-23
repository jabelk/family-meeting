# Implementation Plan: Proactive Automations & Recipe Management

**Branch**: `002-proactive-recipes-automation` | **Date**: 2026-02-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-proactive-recipes-automation/spec.md`

## Summary

Add proactive scheduled automations and recipe cookbook management to the existing Mom Bot system. The feature extends the current reactive WhatsApp assistant with: (1) recipe photo capture via WhatsApp → Claude vision OCR → Notion recipe catalogue with Cloudflare R2 photo storage, (2) proactive grocery reorder suggestions based on purchase history intervals, (3) AI-generated weekly dinner plans with merged grocery lists, (4) 7 n8n scheduled workflows in a dedicated Docker instance, (5) multi-calendar conflict detection, (6) mid-week action item reminders, and (7) weekly budget summaries. All interactions stay in WhatsApp; all data lives in Notion.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK (Claude Haiku 4.5 + Claude vision for OCR), notion-client >=2.2.0,<2.3.0, boto3 (Cloudflare R2 S3-compatible API), httpx, google-api-python-client, google-auth-oauthlib, icalendar, recurring-ical-events, ynab, uvicorn
**Storage**: Notion (2 new databases: Recipes, Cookbooks) + Cloudflare R2 (recipe photo storage) + existing 5 Notion databases
**Testing**: pytest + manual WhatsApp integration testing
**Target Platform**: Linux server (Docker on home NUC) + Cloudflare Tunnel
**Project Type**: Web service (FastAPI) with scheduled automation (n8n)
**Performance Goals**: Recipe extraction <60s end-to-end; all scheduled workflows complete within 30s of trigger
**Constraints**: WhatsApp 24-hour messaging window (template messages for proactive sends); Notion free plan (unlimited blocks, 5MB file limit — photos go to R2); Meta Cloud API media URLs expire in 5 minutes
**Scale/Scope**: 2 users (Jason, Erin), ~20-50 recipes/month, 7 scheduled workflows, 1,348 grocery items

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Integration Over Building** | PASS | Leverages existing Notion, Google Calendar, YNAB, AnyList, WhatsApp. Uses Cloudflare R2 (managed service) for photo storage instead of building file server. n8n (existing tool) for scheduling instead of custom cron. Claude vision for OCR instead of separate Tesseract/Google Vision service. |
| **II. Mobile-First Access** | PASS | All interactions through WhatsApp (already on both phones). Recipe capture = send a photo in chat. Meal plan review/approval = WhatsApp reply. No new apps or interfaces. |
| **III. Simplicity & Low Friction** | PASS | Recipe: photograph → send → done. Grocery reorder: review list → approve → done. Meal plan: review → swap if needed → approve. All <3 steps. No setup needed from Erin. |
| **IV. Structured Output** | PASS | Grocery suggestions grouped by store with bullet lists. Meal plan as Mon-Sat table with recipe names. Budget summary as over/under category list. Conflict alerts with date/time/resolution. |
| **V. Incremental Value** | PASS | Each user story is independent: recipes work without meal planning, grocery reorder works without recipes, budget summary works without any of the above. Priority ordering (P1-P7) ensures highest-impact first. |

**Result**: All 5 principles PASS. No violations to track.

## Project Structure

### Documentation (this feature)

```text
specs/002-proactive-recipes-automation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── recipe-endpoints.md
│   ├── automation-endpoints.md
│   └── n8n-workflows.md
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── app.py                    # FastAPI routes (add recipe + automation endpoints)
├── assistant.py              # Claude tool definitions (add recipe tools + new proactive tools)
├── config.py                 # Environment config (add R2, n8n-mombot vars)
├── whatsapp.py               # WhatsApp client (add image download, template messages)
├── tools/
│   ├── notion.py             # Existing 19 functions (add recipe/cookbook CRUD)
│   ├── calendar.py           # Existing (no changes needed)
│   ├── ynab.py               # Existing (no changes needed)
│   ├── outlook.py            # Existing (no changes needed)
│   ├── anylist_bridge.py     # Existing (no changes needed)
│   ├── recipes.py            # NEW: Recipe extraction (Claude vision), R2 upload, search
│   └── proactive.py          # NEW: Reorder check, meal plan generation, conflict detection
├── mcp_server.py             # MCP server (add new tools)

anylist-sidecar/              # Existing Node.js sidecar (no changes)

docker-compose.yml            # Add n8n-mombot service

tests/                        # Future: pytest suite (not in initial tasks)
└── (empty — manual E2E validation per user story for v1)
```

**Structure Decision**: Extends existing single-project layout. Two new tool modules (`recipes.py`, `proactive.py`) keep new logic separated from existing Notion/calendar tools. New n8n instance added to docker-compose alongside existing services.

## Complexity Tracking

> No constitution violations — section not needed.
