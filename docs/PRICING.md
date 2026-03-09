# Pricing & Positioning

Sierra Story Co. — Family Meeting Assistant

---

## Pricing Tiers

### Family Tier

| Item | Cost |
|------|------|
| Monthly fee | $99/month |
| One-time setup fee | $499 |

**Includes:**

- WhatsApp family assistant with natural language conversation
- Calendar management (Google Calendar sync for all family members)
- Grocery list management (AnyList integration)
- Budget tracking (YNAB integration)
- Meal planning and recipe recommendations
- Daily briefings and proactive reminders
- Action item tracking (Notion)
- White-glove onboarding and setup (we configure everything)

**Per-Client Infrastructure Cost:** $12-28/month

**Margin:** 65-72%

---

### Corporate / Enterprise Tier

| Item | Cost |
|------|------|
| Monthly fee | Starting at $149/month per family unit |
| Setup fee | Custom quote |

**Includes everything in Family Tier, plus:**

- Volume discounts for 5+ families
- Dedicated support channel (Slack, email, or phone)
- Custom integration development
- Priority feature requests
- API access for internal tools
- White-label branding options
- Custom SLA with uptime guarantees

Contact sales for enterprise pricing.

---

## Competitive Positioning

### vs Human Virtual Assistants ($380-3,000/month)

- **75-90% cheaper** than hiring a human VA
- 24/7 availability — no business hours, no time zones, no PTO
- Instant responses (seconds, not hours)
- Consistent quality — no training ramp-up, no turnover
- Handles the mundane coordination that VAs are overqualified for

### vs DIY Tools (Todoist $19/mo, Cozi free, OurHome free)

- More integrated — one interface instead of five apps
- No setup burden on the family (we configure everything)
- Proactive vs reactive — the assistant reaches out with reminders and briefings
- Natural language — no learning a new app UI
- WhatsApp-native — families already use it, nothing new to install

### vs AI Chatbot Services ($25-50/month, requires technical setup)

- White-glove setup — client never touches a terminal or config file
- Family-specific — tuned to each family's schedule, preferences, and routines
- WhatsApp-native — no app to download, no website to visit
- Integrated with real tools (calendar, budget, grocery) — not just a chatbot
- Ongoing support and maintenance included

---

## Cost Breakdown

Infrastructure costs per client per month:

| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| Railway hosting | ~$5-10 | Single-tenant FastAPI deployment |
| Anthropic API (Claude Haiku 4.5) | ~$3-8 | Depends on conversation volume |
| WhatsApp messaging | ~$2-5 | Meta conversation-based pricing |
| Notion API | $0 | Free tier sufficient per family |
| Google Calendar API | $0 | Free tier sufficient per family |
| YNAB API | $0 | Included with client's YNAB subscription |

**Total infrastructure per client: $12-28/month**

At $99/month revenue, this yields a **65-72% gross margin** before labor and overhead.

---

## Add-On Integrations

| Integration | Cost | Notes |
|-------------|------|-------|
| Notion task management | Included | Action items, meal plans, meeting notes |
| Google Calendar sync | Included | Read/write for all family calendars |
| YNAB budget tracking | Included | Budget summaries and spending insights |
| Daily briefings & reminders | Included | Proactive morning briefings, weekly calendar |
| AnyList grocery delivery | +$10/month | Requires Node.js sidecar service |
| Custom integrations | Custom quote | Per-client development and maintenance |

---

## What's NOT Included

The following costs are the client's responsibility:

- **YNAB subscription**: $14.99/month (required for budget tracking features)
- **Notion account**: Free tier is sufficient
- **Google account**: Free tier is sufficient (Gmail/Calendar)
- **WhatsApp Business number verification fees** (if any, typically free)
- **Phone number costs**: Client provides their own number, or we provision one (cost varies by country)
- **AnyList subscription**: If using grocery delivery features

---

## Pricing Rationale

The $99/month price point is positioned to feel like a no-brainer for dual-income families who value their time:

- **Less than $3.30/day** for a 24/7 family coordinator
- **Less than one hour of babysitting** per month buys unlimited coordination
- **Setup fee ($499) covers 4-6 hours** of white-glove onboarding, API configuration, family profile setup, and training

The enterprise tier at $149+/month reflects additional support overhead, custom development capacity, and SLA commitments.
