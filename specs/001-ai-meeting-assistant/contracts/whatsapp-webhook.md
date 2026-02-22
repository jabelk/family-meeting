# Contract: WhatsApp Webhook

**Type**: Inbound webhook (Meta → our server) + Outbound API (our server → Meta)

## Inbound: Receive Messages

Meta sends a POST to our webhook URL when a message arrives in the group chat.

**Endpoint**: `POST /webhook`

**Verification** (one-time setup): Meta sends a GET request with a challenge.

```
GET /webhook?hub.mode=subscribe&hub.verify_token=OUR_TOKEN&hub.challenge=CHALLENGE
→ Return: CHALLENGE (plain text, 200 OK)
```

**Message payload** (simplified — relevant fields only):

```json
{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "from": "15551234567",
          "type": "text",
          "text": { "body": "prepare this week's agenda" },
          "timestamp": "1708700000"
        }],
        "contacts": [{
          "profile": { "name": "Jason" },
          "wa_id": "15551234567"
        }]
      }
    }]
  }]
}
```

**Our server must**:
1. Return `200 OK` immediately (before processing)
2. Extract `from` (phone number) and `text.body` (message content)
3. Map phone number to family member name
4. Pass to Claude for processing
5. Send response back via outbound API

## Outbound: Send Messages

**Endpoint**: `POST https://graph.facebook.com/v21.0/{phone-number-id}/messages`

**Headers**:
```
Authorization: Bearer {PERMANENT_ACCESS_TOKEN}
Content-Type: application/json
```

**Text message body**:
```json
{
  "messaging_product": "whatsapp",
  "to": "GROUP_CHAT_ID_OR_PHONE",
  "type": "text",
  "text": {
    "body": "*Weekly Agenda — Feb 23*\n\n*📅 Calendar*\n• Monday: Vienna school pickup 3pm\n• Wednesday: Dentist appointment\n\n*✅ Action Review*\n• ✅ Jason: grocery shopping\n• ⬜ Erin: schedule swim class\n\n*🍽 Meals*\n• Plan not yet created — want me to suggest one?"
  }
}
```

**Formatting available**:
- `*bold*` for section headers
- `_italic_` for emphasis
- `- item` or `• item` for bullet lists
- `1. item` for numbered lists
- Max 1,600 characters per message (split longer responses)

## Template Messages (for proactive outreach)

Required for messages sent outside the 24-hour reply window (e.g., Sunday
morning meeting reminder).

**Template name**: `weekly_meeting_reminder`
**Category**: Utility
**Body**: "Hi! Your weekly family meeting is coming up. Want me to prepare the agenda?"

Templates must be pre-approved by Meta (typically approved within hours).

## Error Handling

- If webhook returns non-200, Meta retries with exponential backoff for 7 days
- If outbound API returns 429 (rate limit), wait and retry
- If outbound API returns 401, access token needs refresh
