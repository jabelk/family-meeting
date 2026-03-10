# Feature Specification: Siri Voice Access to Family Assistant

**Feature Branch**: `032-siri-voice-access`
**Created**: 2026-03-10
**Status**: Draft
**Input**: User description: "Erin wants a quick hands-free way to interact with the family assistant while on the go — without having to unlock and open WhatsApp. Siri can't send WhatsApp messages or recognize WhatsApp-only contacts. Apple Shortcuts and the broader iPhone/MacBook ecosystem should be explored creatively."

## Context & Problem

Erin's primary frustration: when she's driving, pushing a stroller, or has her hands full, she can't quickly talk to the family assistant. The current flow requires:

1. Unlock iPhone
2. Open WhatsApp
3. Navigate to the family group chat
4. Type or voice-dictate a message
5. Wait for the response to appear in WhatsApp

This defeats the purpose of an "always available" assistant for a busy mom on the go. Siri integration with WhatsApp is unreliable — it doesn't recognize WhatsApp-only contacts, and voice commands to "send a WhatsApp message to mombot" fail.

### Creative Approaches Considered

The following approaches were evaluated for this feature:

1. **Siri Shortcut with direct assistant access** — An Apple Shortcut named something like "Hey Siri, run our house" that takes voice input, sends it directly to the assistant's server, and speaks back the response. Bypasses WhatsApp entirely for quick interactions while still logging the conversation.

2. **iMessage/SMS as an alternative channel** — Adding SMS support so Siri's native "Send a message to..." works. Requires a phone number and SMS gateway service, adding ongoing cost.

3. **Apple Watch dictation** — If Erin has or gets an Apple Watch, a complication or Shortcut on the watch face for instant voice access.

4. **Lock screen widget + Action Button** — A widget on the iPhone lock screen for quick actions (e.g., "Add to grocery list", "What's for dinner?") plus assigning the iPhone Action Button to trigger the assistant Shortcut.

5. **Back Tap accessibility trigger** — Double-tap or triple-tap the back of the iPhone to activate the assistant Shortcut (works on iPhone 8 and later).

6. **Preset quick-action Shortcuts** — Purpose-built Shortcuts for the most common on-the-go tasks: "Add to grocery list", "What's on the calendar today?", "Set a reminder for..." — each optimized as a single Siri phrase.

## Clarifications

### Session 2026-03-10

- Q: Is voice access for Erin only, or should both parents have access? → A: Both parents — each gets their own Shortcuts with their identity attached. This should be generalized in the product template as partner 1 / partner 2 for any family deployment.
- Q: Should voice interactions echo into WhatsApp? → A: No — voice is a private per-user channel, consistent with existing behavior where each parent has their own separate WhatsApp conversation with the assistant and can't see each other's messages.
- Q: What Siri trigger phrase for the general-purpose Shortcut? → A: "Run our house" — matches the brand name. Invocation: "Hey Siri, run our house."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Voice Command via Siri (Priority: P1)

Either parent is on the go and wants to ask the family assistant a question or give it an instruction. They say "Hey Siri, run our house" (or a custom phrase). Siri prompts them to speak, they say their request naturally ("What's for dinner tonight?" or "Add milk to the grocery list"), the request is sent to the assistant, and Siri reads back the response — all hands-free. Each parent has their own Shortcut configured with their identity so the assistant knows who is speaking.

**Why this priority**: This is the core problem. Without hands-free voice access, the assistant is unusable during driving, errands, and any hands-full moment — which is when busy moms need it most.

**Independent Test**: Can be fully tested by saying "Hey Siri, run our house" followed by a request like "What's on the calendar tomorrow?" and hearing the assistant's response spoken back. Delivers immediate value as a hands-free assistant interface.

**Acceptance Scenarios**:

1. **Given** Erin's iPhone is nearby (locked or unlocked), **When** she says "Hey Siri, run our house" and then speaks a request, **Then** the assistant processes the request and Siri speaks the response aloud within 15 seconds.
2. **Given** Erin says a request that triggers an action (e.g., "add eggs to the grocery list"), **When** the assistant processes it, **Then** the action is performed (item added to AnyList) AND Siri confirms the action aloud.
3. **Given** the assistant's server is unreachable, **When** Erin tries to use the voice Shortcut, **Then** Siri speaks a friendly error message like "I couldn't reach your assistant right now. Try again in a moment."
4. **Given** Erin is connected to CarPlay or AirPods, **When** she uses the Siri Shortcut, **Then** it works identically — audio in, spoken response out.

---

### User Story 2 - Quick-Action Preset Shortcuts (Priority: P2)

Erin uses the same 4-5 commands repeatedly while on the go. Instead of speaking a full request each time, she has preset Shortcuts for the most common tasks. She can say "Hey Siri, grocery list add" and then just name the item, or "Hey Siri, family calendar" to hear today's schedule — faster than a full conversational flow.

**Why this priority**: Reduces friction for the most frequent on-the-go tasks. A single phrase like "Hey Siri, what's for dinner" is faster than "Hey Siri, run our house... what are we having for dinner tonight?"

**Independent Test**: Can be tested by saying "Hey Siri, family calendar" and hearing today's schedule read aloud. Each preset Shortcut delivers targeted value for its specific use case.

**Acceptance Scenarios**:

1. **Given** Erin has the preset Shortcuts installed, **When** she says "Hey Siri, family calendar", **Then** Siri reads today's schedule from the family calendar within 10 seconds.
2. **Given** Erin says "Hey Siri, grocery add", **When** Siri prompts "What do you want to add?", **Then** she speaks the item and the assistant adds it to the grocery list and confirms.
3. **Given** Erin says "Hey Siri, what's for dinner", **When** the assistant has a meal plan for today, **Then** Siri reads tonight's planned meal. If no plan exists, the assistant suggests something.
4. **Given** Erin says "Hey Siri, remind me", **When** she speaks a reminder like "pick up dry cleaning tomorrow at 3", **Then** the assistant creates a calendar event and Siri confirms the time and date.

---

### User Story 3 - Conversation Logging (Priority: P3)

When Erin uses voice Shortcuts, the interaction should be logged in the same conversation history as WhatsApp messages, so the assistant maintains context across both channels. If Erin adds something to the grocery list via Siri, then later asks in WhatsApp "what's on the grocery list?", the Siri-added item should be there.

**Why this priority**: Without cross-channel context, the assistant becomes two separate systems. Context continuity is what makes it feel like a single "family brain."

**Independent Test**: Can be tested by adding an item via Siri Shortcut, then asking about it via WhatsApp and seeing the item reflected. Verifies the assistant treats both channels as one conversation.

**Acceptance Scenarios**:

1. **Given** Erin adds "bananas" to the grocery list via Siri, **When** she later asks in WhatsApp "what's on the grocery list?", **Then** bananas appears in the list.
2. **Given** Erin asks "what's for dinner?" via Siri at 3 PM, **When** Jason asks the same question in WhatsApp at 4 PM, **Then** the assistant gives a consistent answer informed by the earlier interaction.
3. **Given** an interaction via Siri, **When** an operator reviews conversation history, **Then** the Siri interaction is visible with a notation indicating it came via voice (not WhatsApp).

---

### User Story 4 - Lock Screen & Quick-Trigger Access (Priority: P4)

Erin can trigger the assistant from her iPhone lock screen without unlocking the phone — either via a lock screen widget, the Action Button (iPhone 15 Pro+), or Back Tap (double-tap the back of the phone). This provides even faster access than saying "Hey Siri."

**Why this priority**: Nice-to-have optimization. Siri voice commands (US1) already solve the core hands-free problem. Physical triggers are a polish feature for power users.

**Independent Test**: Can be tested by double-tapping the back of the iPhone and seeing the assistant Shortcut activate. Delivers faster physical access for users who prefer touch over voice.

**Acceptance Scenarios**:

1. **Given** Erin has configured Back Tap to trigger the assistant, **When** she double-taps the back of her iPhone, **Then** the assistant Shortcut activates and prompts for voice input.
2. **Given** the iPhone Action Button is assigned to the assistant Shortcut, **When** Erin presses and holds the Action Button, **Then** the Shortcut launches.

---

### Edge Cases

- What happens when the assistant takes longer than 15 seconds to respond? (Timeout with "Still thinking... I'll send the answer to WhatsApp" fallback)
- What happens when the voice input is garbled or unclear? (Assistant receives the transcription as-is — same as a poorly typed WhatsApp message — and responds naturally, possibly asking for clarification)
- What happens when Erin uses Siri while the assistant is already processing a WhatsApp message? (Requests are queued and processed in order)
- What happens when the assistant's response is very long (e.g., full weekly calendar)? (Siri speaks a summary and offers to send the full version to WhatsApp)
- What happens when the phone has no internet connection? (Siri speaks a "no connection" error before attempting the network call)
- What happens on Mac? (Siri Shortcuts sync via iCloud; the same Shortcuts should work on MacBook via "Hey Siri" or keyboard trigger)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept voice input via a Siri-invocable phrase and send it to the family assistant for processing
- **FR-002**: The system MUST return the assistant's response as spoken audio through Siri text-to-speech
- **FR-003**: The system MUST support a general-purpose voice command that accepts any natural language request (open-ended conversation)
- **FR-004**: The system MUST support preset voice commands for common tasks: schedule check, grocery list add, dinner question, and reminder creation
- **FR-005**: The system MUST log all voice-initiated interactions in the same conversation history as WhatsApp messages
- **FR-006**: The system MUST indicate in the conversation log whether an interaction originated from voice or WhatsApp
- **FR-007**: The system MUST provide a spoken error message when the assistant server is unreachable
- **FR-008**: The system MUST work with the phone locked, via CarPlay, via AirPods, and via Apple Watch (if available)
- **FR-009**: The system MUST truncate or summarize long responses for spoken output, with an option to send the full response to WhatsApp
- **FR-010**: The system MUST authenticate voice requests to prevent unauthorized access to the family assistant
- **FR-011**: The system MUST work without requiring any third-party apps beyond what the family already uses (no new app installs)
- **FR-012**: The system MUST support per-user Shortcuts so each parent's voice requests are attributed to the correct person (generalized as partner 1 / partner 2 for any deployment)

### Key Entities

- **Voice Request**: A user's spoken input captured via Siri, including the transcribed text, timestamp, requesting user identity (partner 1 or partner 2), and source channel identifier
- **Voice Response**: The assistant's reply formatted for spoken output — shorter and more conversational than text responses
- **Shortcut Configuration**: The set of installed Apple Shortcuts, their trigger phrases, and the server endpoint they connect to
- **Channel**: The input method used (WhatsApp group, WhatsApp DM, Siri voice, preset Shortcut) — tracked per interaction for context

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can go from "Hey Siri" to hearing the assistant's response in under 20 seconds for simple queries (calendar check, dinner question); typical responses return in 5-12 seconds
- **SC-002**: 90% of voice commands are correctly understood and produce the expected assistant action on first attempt
- **SC-003**: Voice-initiated actions (grocery adds, calendar events) are reflected in WhatsApp conversation and connected apps within 30 seconds
- **SC-004**: Setup of all Shortcuts takes under 10 minutes with provided instructions (non-technical user can self-install)
- **SC-005**: User reports reduced friction accessing the assistant while driving or hands-busy, compared to opening WhatsApp (qualitative — confirmed by Erin)
- **SC-006**: Voice channel handles at least 20 interactions per day without degradation or errors

## Assumptions

- Both parents use iPhones (iPhone 12 or later recommended for "Hey Siri" always-on and Back Tap)
- The family assistant server is publicly accessible (already true via Railway deployment with Cloudflare tunnel or public URL)
- Apple Shortcuts can make HTTP requests to external servers (confirmed — Shortcuts supports "Get Contents of URL" action)
- Siri can run custom Shortcuts by name without unlocking the phone (confirmed — Shortcuts can be configured to run from lock screen)
- The assistant's existing message handling can be called from a non-WhatsApp channel with minimal adaptation
- Long responses will need to be summarized for voice — a spoken response over ~30 seconds becomes tedious
- The existing authentication mechanism (webhook secret) can be reused or adapted for the voice channel

## Out of Scope

- Android/Google Assistant support (iPhone ecosystem only for now)
- Building a native iOS app (leveraging Apple Shortcuts instead)
- Real-time streaming of assistant responses (full response returned after processing)
- Multi-turn voice conversations (each Siri invocation is a single request-response; extended conversation continues in WhatsApp)
- Apple Watch standalone app (Watch support comes free via Shortcuts sync — no dedicated Watch app needed)
