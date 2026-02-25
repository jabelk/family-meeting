# Implementation Plan: Email-YNAB Smart Sync (PayPal, Venmo, Apple)

**Branch**: `011-email-ynab-sync` | **Date**: 2026-02-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-email-ynab-sync/spec.md`

## Summary

Extend the existing Amazon-YNAB sync (Feature 010) to also parse PayPal, Venmo, and Apple confirmation emails from Gmail, match them to YNAB transactions, enrich memos with actual merchant/service names, and classify into budget categories. Reuses the core infrastructure (Gmail API, matching algorithm, category mappings, sync records, suggestion flow, WhatsApp direct send) with provider-specific email parsers. Runs on the same nightly n8n schedule.

## Technical Context

**Language/Version**: Python 3.12 (existing codebase)
**Primary Dependencies**: FastAPI, anthropic SDK (Claude Haiku 4.5 for email parsing/classification), httpx (YNAB API), google-api-python-client (Gmail API), existing WhatsApp/n8n infrastructure
**Storage**: JSON files in `data/` directory (extends existing `category_mappings.json`, `amazon_sync_records.json` pattern) + YNAB API for transaction writes
**Testing**: Manual end-to-end testing via WhatsApp trigger and nightly n8n cron
**Target Platform**: Docker container on NUC (Ubuntu 24.04)
**Project Type**: Extension of existing web-service
**Performance Goals**: Sync completes within 3 minutes for all providers combined
**Constraints**: Gmail API rate limits (~250 quota units/sec), YNAB API rate limit (200 req/min), WhatsApp 1600-char message limit
**Scale/Scope**: ~10-30 PayPal/Venmo/Apple transactions per month; 3 new email sender patterns to parse

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Integration Over Building | PASS | Leverages Gmail API, YNAB API, WhatsApp API — no equivalent paid service exists for this orchestration |
| II. Mobile-First Access | PASS | All interaction via WhatsApp (approve/adjust/skip categories). No desktop UI needed |
| III. Simplicity & Low Friction | PASS | Zero setup for Erin — transactions auto-enriched, suggestions delivered to WhatsApp. 1-tap "yes" to approve |
| IV. Structured Output | PASS | Suggestion messages use numbered lists with clear category assignments. Same scannable format as Amazon sync |
| V. Incremental Value | PASS | US1 (PayPal/Venmo/Apple memo enrichment) works standalone without Amazon sync. Each provider works independently |

No constitution violations. No Complexity Tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/011-email-ynab-sync/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api-endpoints.md # n8n endpoint contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── tools/
│   ├── amazon_sync.py       # Existing — import shared utilities from here
│   └── email_sync.py        # NEW — PayPal/Venmo/Apple email parsing + sync orchestration
├── assistant.py             # MODIFY — add email_sync tool definitions + system prompt rules
└── app.py                   # MODIFY — add n8n endpoint for email sync
```

**Structure Decision**: Single new file `src/tools/email_sync.py` for the provider-specific parsing logic. Shared infrastructure (Gmail API, matching, category mappings, sync records, WhatsApp direct send) is imported from `amazon_sync.py`. No abstract base class or shared module extraction — keep it simple, import and call existing functions directly.

## Architecture

### Provider Email Parsing

Each provider gets a dedicated parser function that takes stripped HTML text and returns structured transaction data:

- **PayPal**: `_parse_paypal_email(text, email_date)` — extracts merchant name, amount, item details. PayPal emails use `service@paypal.com` and `paypal@mail.paypal.com`.
- **Venmo**: `_parse_venmo_email(text, email_date)` — extracts recipient/sender name, payment note, amount. Venmo emails use `venmo@venmo.com`.
- **Apple**: `_parse_apple_email(text, email_date)` — extracts subscription/service name, amount. Apple receipt emails use `no_reply@email.apple.com`.

All parsers follow the same pattern as `amazon_sync._parse_order_email()`: Claude Haiku parses stripped text → validated JSON → list of transaction dicts.

### Reused Infrastructure from Feature 010

| Component | Source | How Reused |
|-----------|--------|------------|
| Gmail API auth | `amazon_sync._get_gmail_service()` | Import directly — same token.json, same scopes |
| HTML extraction | `amazon_sync._extract_html_body()` | Import directly |
| HTML stripping | `amazon_sync._strip_html()` | Import directly |
| Transaction matching | `amazon_sync.match_orders_to_transactions()` | Adapted — same ±3 day + penny-match algorithm, different payee filter |
| Category classification | `amazon_sync.classify_item()` | Import directly — same LLM + learned mappings |
| Category mappings | `amazon_sync.load_category_mappings()` / `save_category_mapping()` | Shared across all providers |
| Sync records | `amazon_sync.SyncRecord` / persistence functions | Reused — add `provider` field to distinguish |
| Suggestion formatting | Pattern from `amazon_sync.format_suggestion_message()` | Adapted for provider-specific labels |
| WhatsApp direct send | `assistant._send_sync_message_direct()` | Import directly |
| Pending suggestions | `amazon_sync.set_pending_suggestions()` / `_load_pending_suggestions()` | Extended to include email sync suggestions |

### Sync Flow

1. n8n cron triggers `POST /api/v1/email/sync` (5 min after Amazon sync)
2. Check YNAB for unprocessed PayPal/Venmo/Apple transactions (fast)
3. If none → return silently
4. For each provider with unprocessed transactions:
   a. Search Gmail for matching emails
   b. Parse emails with Claude Haiku (provider-specific parser)
   c. Match to YNAB transactions by date + amount
5. Classify items, enrich memos, apply auto-categorizations
6. Send consolidated suggestion message to Erin
7. Return status

### Reply Handling

Extends the existing `handle_sync_reply()` pattern. Erin's replies ("1 yes", "2 adjust", etc.) work the same way — pending suggestions stored to disk, loaded on reply.
