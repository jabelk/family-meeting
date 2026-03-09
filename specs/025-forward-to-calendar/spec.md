# Feature Specification: Forward-to-Calendar

**Feature Branch**: `025-forward-to-calendar`
**Created**: 2026-03-09
**Status**: Draft
**Input**: GitHub issue #28 — Forward-to-calendar: auto-create events from forwarded messages

## User Scenarios & Testing

### User Story 1 - Extract Event from Forwarded Text (Priority: P1)

Erin receives a text confirmation (doctor appointment, service visit, school event) and forwards it to the family WhatsApp group. The bot detects appointment-like content, extracts the date/time/location/details, and offers to create a calendar event. Erin confirms, and the event appears on the appropriate calendar with a reminder.

**Why this priority**: This is the core feature — Erin already manually converts forwarded confirmations into calendar entries. Eliminating that friction is the primary value.

**Independent Test**: Forward a message like "Your appointment with Dr. Smith is confirmed for March 10 at 2:00 PM at 1234 S Virginia St" to the bot. Bot responds with extracted details and asks for confirmation. After confirming, event appears in Google Calendar with reminder.

**Acceptance Scenarios**:

1. **Given** a forwarded text containing an appointment confirmation with date, time, and location, **When** Erin sends it to the bot, **Then** the bot extracts the event details and presents them for confirmation before creating a calendar event.
2. **Given** a forwarded text with an appointment confirmation, **When** Erin confirms the extracted details, **Then** the event is created on the family calendar with a 15-minute reminder and the bot confirms creation with the event summary.
3. **Given** a forwarded text with a location included, **When** the bot creates the event, **Then** the location is included in the calendar event details.

---

### User Story 2 - Extract Event from Screenshot/Image (Priority: P2)

Erin screenshots a confirmation screen from an app or email and sends the image to the bot. The bot reads the image, extracts appointment details, and offers to create a calendar event — same flow as text forwarding.

**Why this priority**: Some confirmations arrive as app notifications or emails that are easier to screenshot than copy-paste. The bot already has image/OCR capability, so this extends US1 to visual input.

**Independent Test**: Send a screenshot of an appointment confirmation (e.g., a doctor's office portal showing "March 15 at 3:30 PM"). Bot extracts details from the image and offers to create the event.

**Acceptance Scenarios**:

1. **Given** a screenshot containing appointment details (date, time, description), **When** Erin sends the image to the bot, **Then** the bot extracts the event details from the image and presents them for confirmation.
2. **Given** a low-quality or partially obscured screenshot, **When** the bot cannot confidently extract all details, **Then** the bot asks Erin to clarify the missing information rather than guessing.

---

### User Story 3 - Drive Time Buffer (Priority: P3)

When a forwarded message includes a location, the bot checks if drive time data is available for that destination and offers to add a travel buffer before the appointment. This ensures Erin leaves on time.

**Why this priority**: Nice-to-have enhancement. The system already has drive time data — this connects it to the forwarding flow for extra convenience.

**Independent Test**: Forward a message with a known location (e.g., a doctor's office address). Bot detects the location, looks up drive time, and offers to add a pre-appointment travel block.

**Acceptance Scenarios**:

1. **Given** a forwarded message with a recognized location and available drive time data, **When** the bot creates the event, **Then** it offers to add a travel buffer event before the appointment.
2. **Given** a forwarded message with a location but no drive time data available, **When** the bot creates the event, **Then** it includes the location in the event but does not offer a travel buffer.

---

### Edge Cases

- **Multiple dates in one message**: Forwarded message mentions several dates (e.g., "Your next appointments are March 10 and March 24"). Bot should ask which date(s) to create events for, or offer to create events for all.
- **Cancellation language**: Message says "Your appointment on March 10 has been cancelled." Bot should recognize this as a cancellation, not create a new event, and optionally offer to remove an existing matching event.
- **Ambiguous times**: Message says "tomorrow afternoon" or "next Thursday morning." Bot should ask for clarification on the specific time.
- **Time ranges**: Service windows like "between 1-3 PM on Thursday." Bot should create an event spanning the full range.
- **Recurring appointment mention**: "See you in 6 months for your next checkup." Bot should not create an event 6 months out unless explicitly asked.
- **Non-appointment forwarded messages**: Erin forwards a funny message or news article. Bot should not falsely detect an appointment — only act when appointment-like patterns are clearly present.
- **Past dates**: Forwarded message references a date that has already passed. Bot should flag this and ask if Erin still wants to create the event.

## Requirements

### Functional Requirements

- **FR-001**: System MUST detect appointment-like content in forwarded text messages by identifying patterns such as confirmed appointments, scheduled visits, reservations, and similar language.
- **FR-002**: System MUST extract structured event details from detected appointments: event title/description, date, time (start and optionally end), and location (if present).
- **FR-003**: System MUST present extracted details to the user for confirmation before creating any calendar event — never auto-create without user approval.
- **FR-004**: System MUST create the calendar event on the family calendar by default, with the option for the user to specify a different calendar (jason, erin) during confirmation.
- **FR-005**: System MUST handle image/screenshot input by reading the image content and extracting appointment details, using the same confirmation flow as text messages.
- **FR-006**: System MUST recognize cancellation language and offer to remove a matching existing event rather than creating a new one.
- **FR-007**: System MUST ask for clarification when dates or times are ambiguous rather than guessing incorrectly.
- **FR-008**: System MUST ignore forwarded messages that do not contain appointment-relevant content — no false positives on casual conversation, jokes, or news.
- **FR-009**: System MUST include any mentioned location in the calendar event's location field.
- **FR-010**: When drive time data is available for the event location, system SHOULD offer to add a travel buffer event before the appointment.

### Key Entities

- **Forwarded Message**: The raw text or image sent by the user, containing potential appointment information. Key attributes: message content, media type (text or image), sender context.
- **Extracted Event**: The structured appointment details parsed from the message. Key attributes: title, date, start time, end time (if applicable), location, description, source message.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 90% of forwarded appointment confirmations with explicit date and time are correctly extracted on the first attempt without user correction.
- **SC-002**: Users can go from forwarding a message to having a calendar event created in under 30 seconds (one confirmation step).
- **SC-003**: Zero calendar events are created without explicit user confirmation.
- **SC-004**: False positive rate (non-appointment messages incorrectly flagged as appointments) is below 5%.
- **SC-005**: Image-based appointment extraction succeeds for at least 80% of clearly legible screenshots.

## Assumptions

- Forwarded messages arrive through the existing WhatsApp message pipeline — no new intake channel is needed.
- The bot's existing natural language understanding is sufficient to detect appointment patterns — no custom NLP model is required.
- The bot's existing image/vision capability can read standard appointment confirmation screenshots.
- Drive time data in `data/drive_times.json` contains entries for common destinations (doctor, school, etc.) but coverage is not guaranteed for all locations.
- The user will always confirm before an event is created — the bot never auto-creates events from forwarded content.
- Most forwarded appointments are for the near future (within 90 days). Events more than 90 days out are still created but may warrant a double-check with the user.

## Out of Scope

- Automatic calendar event creation without user confirmation.
- Parsing complex multi-event itineraries (e.g., full travel itineraries with flights, hotels, activities).
- Integrating with external services to look up appointment details (e.g., calling a doctor's office API).
- Handling forwarded emails directly — only WhatsApp messages and images are in scope.
- Real-time address geocoding or map integration for drive time estimation — uses existing static drive time data only.
