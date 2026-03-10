# Tasks: Siri Voice Access to Family Assistant

**Input**: Design documents from `/specs/032-siri-voice-access/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/voice-api.md, quickstart.md

**Tests**: Not explicitly requested. Tests omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Environment configuration and token generation

- [X] T001 Add PARTNER1_API_TOKEN, PARTNER2_API_TOKEN, PARTNER1_PHONE, PARTNER2_PHONE to src/config.py with os.environ.get() defaults
- [X] T002 [P] Generate example tokens and document env var format in config/family.yaml.example (add voice_access section with token placeholders)
- [X] T003 [P] Add PARTNER1_API_TOKEN and PARTNER2_API_TOKEN to .env.example with generation command comment

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story — auth dependency and voice module

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement verify_shortcut_auth FastAPI dependency in src/app.py — parse Authorization Bearer header, map token to phone via SHORTCUT_TOKEN_MAP dict built at startup from PARTNER1/2_API_TOKEN + PARTNER1/2_PHONE, return sender_phone or raise 401
- [X] T005 Create src/voice.py with VoiceRequest and VoiceResponse Pydantic models per data-model.md (VoiceRequest: text, channel, preset_action; VoiceResponse: success, message, error, sent_to_whatsapp)
- [X] T006 Add format_voice_response() helper in src/voice.py — truncate assistant responses to ~150 words for voice, return full text separately for WhatsApp fallback
- [X] T007 Add rate limiting for voice endpoints in src/app.py — reuse existing _check_rate_limit(phone) pattern, return 429 with spoken-friendly error message in JSON body

**Checkpoint**: Foundation ready — auth, models, response formatting, rate limiting all in place

---

## Phase 3: User Story 1 — Voice Command via Siri (Priority: P1) MVP

**Goal**: Either parent can say "Hey Siri, run our house", speak a request, and hear the assistant's response — fully hands-free

**Independent Test**: Say "Hey Siri, run our house" → "What's on the calendar tomorrow?" → hear spoken schedule response. Also test with curl: `curl -X POST https://<server>/api/v1/voice/message -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"text":"What is on the calendar tomorrow?","channel":"siri"}'`

### Implementation for User Story 1

- [X] T008 [US1] Implement POST /api/v1/voice/message endpoint in src/app.py — accept VoiceRequest body, authenticate with Depends(verify_shortcut_auth), resolve sender_phone, call handle_message(sender_phone, request.text) with channel annotation, format response via format_voice_response(), return VoiceResponse JSON
- [X] T009 [US1] Implement async timeout wrapper in src/voice.py — run handle_message with asyncio timeout of 18 seconds; if timeout fires, return acknowledgment VoiceResponse with sent_to_whatsapp=true and spawn background task to complete processing and send result via WhatsApp using existing send_message()
- [X] T010 [US1] Add channel parameter to conversation logging in src/assistant.py — when handle_message is called from voice endpoint, include channel="siri" or channel="preset:<action>" in the conversation log entry so operator can distinguish voice from WhatsApp interactions
- [X] T011 [US1] Create the "Run Our House" Apple Shortcut and export to shortcuts/run-our-house.shortcut — flow: Dictate Text → Get Contents of URL (POST /api/v1/voice/message with Bearer auth, JSON body {"text": input, "channel": "siri"}) → parse response → If success: Speak Text message, Else: Speak Text error fallback
- [X] T012 [US1] Write setup instructions in docs/siri-shortcut-setup.md — cover: generating tokens, adding env vars to Railway, creating/installing the "Run Our House" Shortcut on each parent's phone step-by-step with screenshots placeholders, testing with "Hey Siri, run our house", troubleshooting (timeout, auth failure, no response)

**Checkpoint**: General voice command works end-to-end. Both parents can "Hey Siri, run our house" and get spoken responses.

---

## Phase 4: User Story 2 — Quick-Action Preset Shortcuts (Priority: P2)

**Goal**: One-phrase Siri commands for the 4 most common tasks — "Hey Siri, family calendar", "Hey Siri, grocery add", "Hey Siri, what's for dinner", "Hey Siri, remind me"

**Independent Test**: Say "Hey Siri, family calendar" → hear today's schedule. Say "Hey Siri, grocery add" → "milk" → hear confirmation. Also test with curl targeting /api/v1/voice/preset.

### Implementation for User Story 2

- [X] T013 [US2] Implement POST /api/v1/voice/preset endpoint in src/app.py — accept VoiceRequest with preset_action field, authenticate with Depends(verify_shortcut_auth), route to optimized handlers based on preset_action value (calendar, grocery_add, dinner, remind)
- [X] T014 [US2] Implement preset_calendar handler in src/voice.py — call existing calendar tools directly (skip Claude classification), format today's schedule as voice-friendly summary ("You have N things today..."), return VoiceResponse
- [X] T015 [US2] Implement preset_grocery_add handler in src/voice.py — parse text for item names, call existing AnyList add tool directly, return confirmation VoiceResponse ("Added X to the grocery list")
- [X] T016 [US2] Implement preset_dinner handler in src/voice.py — check existing meal plan for today via Notion tools, return meal name or suggest one if no plan exists, format as VoiceResponse
- [X] T017 [US2] Implement preset_remind handler in src/voice.py — pass reminder text to handle_message with a pre-prompt that instructs the assistant to create a calendar event, return VoiceResponse with confirmation
- [X] T018 [P] [US2] Create "Family Calendar" Apple Shortcut and export to shortcuts/family-calendar.shortcut — flow: Get Contents of URL (POST /api/v1/voice/preset, body {"channel":"preset","preset_action":"calendar"}) → Speak Text response message
- [X] T019 [P] [US2] Create "Grocery Add" Apple Shortcut and export to shortcuts/grocery-add.shortcut — flow: Ask for Input "What do you want to add?" → Get Contents of URL (POST, body {"channel":"preset","preset_action":"grocery_add","text":input}) → Speak Text response
- [X] T020 [P] [US2] Create "What's for Dinner" Apple Shortcut and export to shortcuts/whats-for-dinner.shortcut — flow: Get Contents of URL (POST, body {"channel":"preset","preset_action":"dinner"}) → Speak Text response
- [X] T021 [P] [US2] Create "Remind Me" Apple Shortcut and export to shortcuts/remind-me.shortcut — flow: Ask for Input "What do you want to be reminded about?" → Get Contents of URL (POST, body {"channel":"preset","preset_action":"remind","text":input}) → Speak Text response
- [X] T022 [US2] Update docs/siri-shortcut-setup.md — add preset Shortcuts installation instructions for all 4 presets, with trigger phrases and expected behavior

**Checkpoint**: All 5 Shortcuts work (1 general + 4 presets). Preset commands are faster than general because they skip classification.

---

## Phase 5: User Story 3 — Conversation Logging (Priority: P3)

**Goal**: Voice interactions are logged alongside WhatsApp messages so the assistant maintains cross-channel context

**Independent Test**: Add "bananas" via "Hey Siri, grocery add", then ask in WhatsApp "what's on the grocery list?" — bananas should appear. Check conversation log shows Siri-originated entry.

### Implementation for User Story 3

- [X] T023 [US3] Ensure handle_message in src/assistant.py persists channel metadata in conversation log entries — voice interactions logged with channel field ("siri" or "preset:<action>") alongside existing WhatsApp entries (channel: "whatsapp")
- [X] T024 [US3] Add channel display to conversation log viewer (if exists) or add channel field to log format in src/assistant.py so operator can filter/view voice vs WhatsApp interactions
- [X] T025 [US3] Verify cross-channel context works — ensure that when a voice request adds a grocery item or creates a calendar event, subsequent WhatsApp queries reflect the change (this is inherent if both channels use the same handle_message and tool pipeline, but verify no channel-specific caching or isolation exists)

**Checkpoint**: Voice and WhatsApp share context seamlessly. Operator can distinguish channels in logs.

---

## Phase 6: User Story 4 — Lock Screen & Quick-Trigger Access (Priority: P4)

**Goal**: Physical triggers (Back Tap, Action Button) for even faster access than "Hey Siri"

**Independent Test**: Triple-tap back of iPhone → assistant Shortcut activates and prompts for voice input.

### Implementation for User Story 4

- [X] T026 [US4] Document Back Tap setup in docs/siri-shortcut-setup.md — add section: Settings → Accessibility → Touch → Back Tap → Triple Tap → select "Run Our House" Shortcut. Include recommendation for triple-tap over double-tap to avoid accidental triggers.
- [X] T027 [US4] Document Action Button setup in docs/siri-shortcut-setup.md — add section for iPhone 15 Pro+ users: Settings → Action Button → Shortcut → select "Run Our House". Note this is device-specific.
- [X] T028 [US4] Document Lock Screen widget option in docs/siri-shortcut-setup.md — add section: add Shortcuts widget to lock screen, configure to show "Run Our House" for one-tap access

**Checkpoint**: Setup guide covers all physical trigger options. No server-side changes needed.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, hardening, and validation

- [X] T029 Add voice endpoint to health check in src/app.py — include voice_access integration status (checks if PARTNER1_API_TOKEN or PARTNER2_API_TOKEN is configured) in /health response
- [X] T030 [P] Add voice_access to integration registry in src/integrations.py — register as optional integration with env vars PARTNER1_API_TOKEN, PARTNER2_API_TOKEN and tools list
- [X] T031 [P] Update ONBOARDING.md with voice access setup section — brief mention of Siri Shortcuts capability with link to docs/siri-shortcut-setup.md
- [ ] T032 Run quickstart.md validation — manually test scenarios 1-6 from quickstart.md against deployed server (scenario 1: general voice, 2: grocery preset, 3: slow fallback, 4: server error, 5: cross-channel, 6: calendar preset)
- [ ] T033 Generate actual API tokens for Jason and Erin, add to Railway env vars, install all Shortcuts on both phones

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on T001 (config vars) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion — MVP target
- **US2 (Phase 4)**: Depends on Phase 2; benefits from US1 patterns but independently implementable
- **US3 (Phase 5)**: Depends on Phase 2; verifies cross-channel behavior from US1/US2
- **US4 (Phase 6)**: No server dependencies — documentation only, can run anytime after US1
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **US2 (P2)**: Can start after Phase 2 — uses same endpoint pattern as US1 but separate endpoint
- **US3 (P3)**: Can start after Phase 2 — verifies logging from US1/US2 interactions
- **US4 (P4)**: Documentation only — can start after US1 Shortcut exists

### Parallel Opportunities

- T002 and T003 can run in parallel (different files)
- T018, T019, T020, T021 can all run in parallel (separate Shortcut files)
- T026, T027, T028 can all run in parallel (separate doc sections)
- T029, T030, T031 can all run in parallel (different files)
- US4 (Phase 6) can run in parallel with US2 or US3 since it's documentation only

---

## Parallel Example: User Story 2

```bash
# After T013 (preset endpoint) is done, all Shortcut files can be created in parallel:
Task T018: "Create Family Calendar Shortcut in shortcuts/family-calendar.shortcut"
Task T019: "Create Grocery Add Shortcut in shortcuts/grocery-add.shortcut"
Task T020: "Create What's for Dinner Shortcut in shortcuts/whats-for-dinner.shortcut"
Task T021: "Create Remind Me Shortcut in shortcuts/remind-me.shortcut"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007)
3. Complete Phase 3: User Story 1 (T008-T012)
4. **STOP and VALIDATE**: Test "Hey Siri, run our house" end-to-end
5. Deploy to Railway and test on real phones

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test → Deploy (MVP — general voice command works)
3. Add User Story 2 → Test → Deploy (4 preset Shortcuts for common tasks)
4. Add User Story 3 → Verify → Deploy (cross-channel logging confirmed)
5. Add User Story 4 → Publish → Deploy (Back Tap / Action Button docs)
6. Polish → Validate → Done

---

## Notes

- Apple Shortcuts have a ~25-second HTTP timeout — the async fallback (T009) is critical
- Shortcuts cannot read HTTP status codes — always return 200 with success boolean (T005, T008)
- Preset handlers (T014-T017) can call existing tools directly, bypassing Claude for speed
- Shortcut files (.shortcut) may need to be created manually in the Shortcuts app and exported, or documented as step-by-step creation guides if export format is impractical
- Token format: `sc_p1_<64-char-hex>` / `sc_p2_<64-char-hex>` — prefix aids debugging
