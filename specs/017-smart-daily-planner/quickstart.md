# Quickstart Verification: Smart Daily Planner

**Feature**: 017-smart-daily-planner | **Date**: 2026-03-03

## Prerequisites

- Server running locally or on NUC
- Erin's Google Calendar has events for today (including recurring events like school drop-off/pickup)
- WhatsApp or direct API access for testing

---

## Scenario 1: Calendar events appear as fixed blocks (US1)

**Setup**: Ensure Vienna's school drop-off (9:00 AM) and pickup (3:00 PM) are on Erin's calendar for a weekday.

**Steps**:
1. Send "plan my day" via WhatsApp
2. Verify the response includes school drop-off and pickup as fixed blocks
3. Verify other activities are scheduled around them (not overlapping)

**Expected**: Plan shows drop-off and pickup without Erin mentioning them. No activities overlap with these time blocks.

---

## Scenario 2: Recurring events auto-included (US1)

**Setup**: Ensure a recurring weekly event (e.g., swim lesson Monday 4 PM) is on the calendar.

**Steps**:
1. Send "plan my Monday" on a day when the recurring event is active
2. Verify the recurring event appears in the plan

**Expected**: Swim lesson (or other recurring event) appears automatically.

---

## Scenario 3: Draft presented before calendar write (US2)

**Steps**:
1. Send "plan my day"
2. Verify the bot presents the plan as a draft with a confirmation prompt
3. Verify NO calendar events were created at this point

**Expected**: Bot shows plan and asks something like "Want me to add this to your calendar?" No calendar writes yet.

---

## Scenario 4: Plan modification before confirmation (US2)

**Steps**:
1. Send "plan my day" → bot shows draft
2. Send "move gym to 10 AM"
3. Verify bot shows updated draft, asks for confirmation again
4. Send "looks good"
5. Verify calendar blocks are now written

**Expected**: Calendar blocks written only after "looks good." Only one set of calendar entries (not multiple from revisions).

---

## Scenario 5: Rejection skips calendar write (US2)

**Steps**:
1. Send "plan my day" → bot shows draft
2. Send "never mind" or "skip the calendar"
3. Verify NO calendar events were created

**Expected**: Plan visible in chat but no calendar writes.

---

## Scenario 6: Morning briefing does not auto-write (US2)

**Steps**:
1. Trigger the morning briefing (n8n 7 AM trigger or manual API call)
2. Verify the plan is presented as a draft
3. Verify NO calendar events were created until Erin confirms

**Expected**: Morning briefing shows plan, waits for WhatsApp reply before writing.

---

## Scenario 7: Drive times auto-included in plan (US3)

**Setup**: Store drive times: `save_drive_time("gym", 5)` and `save_drive_time("school", 10)`.

**Steps**:
1. Send "plan my day" with gym and school pickup in the plan
2. Verify drive time buffers appear between activities at different locations

**Expected**: 5-minute buffer before gym activities, 10-minute buffer before school activities. No buffer between consecutive home activities.

---

## Scenario 8: Add drive time via conversation (US3)

**Steps**:
1. Send "the park is 15 minutes away"
2. Verify bot confirms the drive time was saved
3. Send "plan my Saturday" with a park visit
4. Verify 15-minute buffer appears for the park

**Expected**: Drive time stored persistently and used in future plans.

---

## Scenario 9: Update existing drive time (US3)

**Steps**:
1. Send "gym is actually 10 minutes now"
2. Verify bot confirms the update
3. Check `data/drive_times.json` — gym should show 10 minutes

**Expected**: Existing entry updated, not duplicated.

---

## Scenario 10: No buffer for unknown locations (US3)

**Steps**:
1. Send "plan my day" with an activity at a location with no stored drive time
2. Verify plan is generated without a buffer for that location

**Expected**: No error, no prompt to add drive time. Plan generated smoothly.

---

## Scenario 11: Plan a future day (Edge Case)

**Steps**:
1. Send "plan my Wednesday" (when today is not Wednesday)
2. Verify bot reads Wednesday's calendar events
3. Verify draft confirmation flow still applies

**Expected**: Wednesday's events shown, confirmation required before calendar write.

---

## Verification Checklist

- [ ] Existing calendar events appear as fixed blocks in daily plans
- [ ] Recurring events auto-included without user mentioning them
- [ ] Plans presented as drafts before calendar writes
- [ ] Modifications re-present draft without writing to calendar
- [ ] "Never mind" / rejection skips calendar write
- [ ] Morning briefing does not auto-write to calendar
- [ ] Stored drive times create travel buffers in plans
- [ ] Drive times can be added via conversation
- [ ] Drive times can be updated via conversation
- [ ] No errors when location has no stored drive time
- [ ] Future day planning reads correct calendar events
