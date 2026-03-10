# Research: Siri Voice Access to Family Assistant

**Feature Branch**: `032-siri-voice-access`
**Date**: 2026-03-10

## R1: Apple Shortcuts HTTP Capabilities

### Decision: Apple Shortcuts "Get Contents of URL" is sufficient for server communication

**Rationale**: The action supports POST with JSON body, custom headers (for Bearer auth), and JSON response parsing. Combined with "Dictate Text" for voice input and "Speak Text" for audio output, a complete hands-free flow is possible without any third-party apps.

**Key capabilities confirmed**:
- HTTP methods: GET, POST, PUT, PATCH, DELETE
- JSON request bodies: Full support
- Custom headers: Full support (can set `Authorization: Bearer <token>`)
- JSON response parsing: Via "Get Dictionary Value" action
- Voice input: "Dictate Text" or "Ask for Input" (auto-voice when Siri-triggered)
- Spoken output: "Speak Text" action works hands-free
- Siri trigger: "Hey Siri, [Shortcut Name]" — fully hands-free
- CarPlay: Works via Siri voice only (no display icon)
- Lock screen: Works if shortcut doesn't need to open apps
- iCloud sync: Shortcuts sync across iPhone, iPad, Mac, Apple Watch

**Critical limitations**:
- **~25-second HTTP timeout** — not configurable. If the server doesn't respond in ~25 seconds, the Shortcut fails
- **Cannot read HTTP status codes** — must use response body fields (`success`, `error`) for error handling
- **No OAuth 2.0 support** — must use simple token auth
- **No streaming/SSE** — must return complete response
- **No Shortcut-level error catching for timeouts** — timeout kills the action

**Alternatives considered**:
- iMessage/SMS channel via Twilio — would work with native Siri but adds $15-30/month cost and a phone number. Rejected: unnecessary cost and complexity when Shortcuts works.
- Native iOS app with Siri Intents — better integration but requires App Store distribution, Xcode, ongoing maintenance. Rejected: massive overkill for 2 users.

---

## R2: Timeout Strategy

### Decision: Fast-acknowledge pattern with WhatsApp fallback for slow responses

**Rationale**: The assistant's Claude API calls can take 5-15 seconds. With tool use (calendar lookups, grocery list operations), end-to-end time can exceed 25 seconds. A pure synchronous approach will timeout on complex requests.

**Chosen approach — Hybrid sync/async**:
1. **Simple queries** (under ~20 seconds): Return the full response synchronously. The Shortcut speaks it immediately.
2. **Complex queries** (risk of timeout): The server returns a quick acknowledgment ("Working on it — I'll send the answer to WhatsApp") and processes the request in the background, delivering the full response via WhatsApp message.

**How the server decides**: Set an internal timeout (~18 seconds). If the Claude response completes within that window, return it directly. If not, return the acknowledgment and continue processing asynchronously, sending the result to WhatsApp.

**Alternatives considered**:
- Always async (acknowledge + WhatsApp) — simpler but defeats the purpose of instant voice feedback for quick questions like "what's for dinner?"
- Pre-computed cache for common queries — good optimization for Phase 2 but requires scheduled jobs; not needed for MVP
- Faster/smaller model for Shortcuts — would reduce quality; the current Haiku model is already fast

---

## R3: Authentication

### Decision: Per-user Bearer tokens in Authorization header

**Rationale**: Each parent gets a unique random token stored as an env var on the server. The token serves as both authentication (is this request legitimate?) and identification (who is making it?). This is consistent with how the WhatsApp webhook identifies users by phone number.

**Implementation**:
- Server env vars: `PARTNER1_API_TOKEN`, `PARTNER2_API_TOKEN` (format: `sc_p1_<64-char-hex>`)
- Shortcut sends: `Authorization: Bearer sc_p1_abc123...` header
- Server maps token → phone number → user name via existing `PHONE_TO_NAME`
- Existing `verify_n8n_auth` (X-N8N-Auth header) for automation endpoints remains unchanged

**Why per-user tokens over shared secret**:
- Token = identity: no spoofable `user` parameter needed
- Per-user revocation without affecting the other user
- Clean separation from automation endpoints

**Security posture** (appropriate for threat model):
- In transit: HTTPS enforced by Railway/Cloudflare
- At rest on device: iOS encrypts Shortcut definitions; protected by passcode/Face ID
- If shared: Token goes with Shortcut. Acceptable risk for 2-person family; add "DO NOT SHARE" comment in Shortcut
- Worst case for leaked token: someone adds items to a grocery list

**Alternatives considered**:
- Reuse N8N_WEBHOOK_SECRET with user parameter — single shared secret, user param spoofable. Rejected.
- Basic Auth — Apple Shortcuts supports it but feels wrong for machine-to-machine. Rejected.
- OAuth 2.0 / JWT — massive overkill for 2 users. Apple Shortcuts doesn't support OAuth flows. Rejected.
- Mutual TLS — Shortcuts can't install client certificates. Not viable.

---

## R4: Response Formatting for Voice

### Decision: Server returns voice-optimized responses with structured JSON

**Rationale**: Spoken responses need to be shorter and more conversational than text. The server should return a JSON response with separate fields so the Shortcut can handle success/error and speak the right content.

**Response format**:
```json
{
  "success": true,
  "message": "You have 3 things today. Lily has swim at 10, then family lunch at noon, and you're picking up groceries at 4.",
  "full_response": "...(longer version if truncated)...",
  "sent_to_whatsapp": false
}
```

**Voice optimization rules**:
- Max spoken response: ~150 words (~45 seconds of speech). Beyond that, summarize and send full version to WhatsApp.
- Use conversational phrasing: "You have 3 things today" not "Here are the calendar events for March 10, 2026"
- Numbers spoken naturally: "about $380" not "$379.52"
- Lists kept to 5 items max for voice; longer lists summarized with count

**Why `success` field instead of HTTP status codes**: Apple Shortcuts cannot read HTTP status codes. The `success` boolean is the only reliable way to communicate errors. The server should return HTTP 200 even for application-level errors, with `success: false` and an `error` field.

---

## R5: Shortcut Distribution

### Decision: iCloud link sharing with import question for API token

**Rationale**: Apple Shortcuts supports "import questions" — prompts that appear when a user first installs a shared Shortcut. The operator (Jason) creates the Shortcut, adds an import question for the API token, shares via iCloud link, and provides the token separately.

**Setup flow for a new family member**:
1. Operator generates their API token and adds it to the server env
2. Operator shares the Shortcut iCloud link
3. Family member taps the link, enters their token when prompted
4. Shortcut is ready to use

**For this family (Jason + Erin)**: Jason can pre-configure both Shortcuts locally and AirDrop Erin's to her phone — even simpler than the iCloud flow.

**Alternatives considered**:
- "Secret" helper Shortcut pattern — stores token in a separate Shortcut. More modular but adds complexity for non-technical users. Rejected for MVP.
- Hardcode token in shared Shortcut — visible to recipient but acceptable for family trust level. Works as fallback.

---

## R6: Back Tap and Action Button

### Decision: Document as optional setup steps in user guide

**Rationale**: Both features simply trigger an existing Shortcut — no server-side work needed. Back Tap works on iPhone 8+ (double or triple tap). Action Button works on iPhone 15 Pro+ only.

**Back Tap**: Settings → Accessibility → Touch → Back Tap → assign to "Run Our House" Shortcut. Recommended: triple-tap (fewer accidental triggers than double-tap).

**Action Button**: Settings → Action Button → Shortcut → select "Run Our House". Only one Shortcut can be assigned, but a "menu" Shortcut could offer choices.

**No development work required** — purely a user configuration step documented in the setup guide.
