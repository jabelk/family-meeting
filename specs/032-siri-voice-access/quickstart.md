# Quickstart Scenarios: Siri Voice Access

**Feature Branch**: `032-siri-voice-access`
**Date**: 2026-03-10

## Scenario 1: General Voice Command — Calendar Question

**Setup**: Partner 1 has the "Run Our House" Shortcut installed with their Bearer token.

**Steps**:
1. Partner 1 says "Hey Siri, run our house"
2. Siri activates the Shortcut and prompts for voice input
3. Partner 1 says "What's on the calendar tomorrow?"
4. Shortcut sends POST to `/api/v1/voice/message` with `{"text": "What's on the calendar tomorrow?", "channel": "siri"}`
5. Server authenticates via Bearer token, resolves Partner 1 identity
6. Server calls `handle_message()` with Partner 1's phone and the transcribed text
7. Assistant checks Google Calendar, returns voice-optimized summary
8. Server responds: `{"success": true, "message": "Tomorrow you have swim lessons at 10 and a playdate at 1.", "sent_to_whatsapp": false}`
9. Shortcut speaks: "Tomorrow you have swim lessons at 10 and a playdate at 1."

**Expected duration**: 5-12 seconds end-to-end

---

## Scenario 2: Preset Shortcut — Add to Grocery List

**Setup**: Partner 2 has the "Grocery Add" preset Shortcut installed.

**Steps**:
1. Partner 2 says "Hey Siri, grocery add"
2. Siri activates the Shortcut, asks "What do you want to add?"
3. Partner 2 says "milk and bananas"
4. Shortcut sends POST to `/api/v1/voice/preset` with `{"channel": "preset", "preset_action": "grocery_add", "text": "milk and bananas"}`
5. Server routes directly to grocery list tool (skips classification)
6. Assistant adds items to AnyList
7. Server responds: `{"success": true, "message": "Added milk and bananas to the grocery list.", "sent_to_whatsapp": false}`
8. Shortcut speaks: "Added milk and bananas to the grocery list."

**Expected duration**: 3-8 seconds

---

## Scenario 3: Slow Response — WhatsApp Fallback

**Setup**: Partner 1 uses the general voice command for a complex request.

**Steps**:
1. Partner 1 says "Hey Siri, run our house"
2. Says "Plan meals for next week based on what's on sale at Whole Foods"
3. Shortcut sends POST to `/api/v1/voice/message`
4. Server starts processing — this requires multiple tool calls (check meal history, check budget, generate plan)
5. Internal timeout (~18 seconds) fires before Claude finishes
6. Server responds: `{"success": true, "message": "Working on that — I'll send the meal plan to WhatsApp.", "sent_to_whatsapp": true}`
7. Shortcut speaks: "Working on that — I'll send the meal plan to WhatsApp."
8. Background: server completes processing and sends full meal plan via WhatsApp message to Partner 1

**Expected Shortcut duration**: 18-20 seconds (then WhatsApp message arrives later)

---

## Scenario 4: Server Unreachable

**Setup**: Any parent tries to use voice while the server is down.

**Steps**:
1. Partner says "Hey Siri, run our house"
2. Says "What's for dinner?"
3. Shortcut sends POST to `/api/v1/voice/message`
4. HTTP request times out after ~25 seconds (server unreachable)
5. Shortcut's error handling path activates
6. Shortcut speaks: "Sorry, I couldn't reach your assistant right now. Try again in a moment."

---

## Scenario 5: Cross-Channel Context

**Setup**: Partner 2 adds a grocery item via Siri, then Partner 1 asks about groceries via WhatsApp.

**Steps**:
1. Partner 2 says "Hey Siri, grocery add" → "eggs"
2. Server processes, adds eggs to AnyList, logs interaction with channel "preset:grocery_add"
3. 30 minutes later, Partner 1 texts in WhatsApp: "What's on the grocery list?"
4. Assistant sees the full list including eggs (added via AnyList, regardless of channel)
5. Conversation log shows the Siri-initiated add for operator visibility

---

## Scenario 6: Preset — Today's Calendar (No Input Needed)

**Setup**: Partner 1 has the "Family Calendar" preset Shortcut.

**Steps**:
1. Partner 1 says "Hey Siri, family calendar"
2. Shortcut sends POST to `/api/v1/voice/preset` with `{"channel": "preset", "preset_action": "calendar"}`
3. Server routes directly to calendar summary tool
4. Server responds with today's schedule as voice-optimized text
5. Shortcut speaks: "Today you have 2 things. Dentist at 9:30 and pickup at 3:15."

**Expected duration**: 3-6 seconds (preset skips classification, calendar data is fast)

---

## Scenario 7: Setup — Installing Shortcuts on a New Phone

**Setup**: Operator (Jason) needs to set up Erin's phone with voice access.

**Steps**:
1. Operator generates a token: `python -c "import secrets; print('sc_p2_' + secrets.token_hex(32))"`
2. Operator adds `PARTNER2_API_TOKEN=sc_p2_<generated>` to Railway env vars
3. Operator creates the "Run Our House" Shortcut on Erin's phone (or shares via AirDrop/iCloud link with import question)
4. Operator configures the Bearer token in the Shortcut's Authorization header
5. Operator creates 4 preset Shortcuts (family calendar, grocery add, what's for dinner, remind me)
6. Operator optionally configures Back Tap: Settings → Accessibility → Touch → Back Tap → Triple Tap → "Run Our House"
7. Total setup time: under 10 minutes

---

## Scenario 8: Rate Limiting

**Steps**:
1. Partner rapidly fires 6+ requests within 60 seconds (accidental or testing)
2. Server returns HTTP 429: `{"detail": "Rate limit exceeded. Try again in a moment."}`
3. Shortcut's error path speaks: "Sorry, I couldn't reach your assistant right now. Try again in a moment."
