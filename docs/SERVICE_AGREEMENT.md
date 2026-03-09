# Service Agreement

**Family Meeting Assistant — Managed Family Management Service**

---

**Service Provider:** [COMPANY NAME] ("Operator")
**Client:** [CLIENT NAME] ("Client")
**Effective Date:** [EFFECTIVE DATE]
**Service Tier:** [ ] Family ($99/month) | [ ] Enterprise (custom)

---

## 1. Service Description

The Operator provides a **family management assistant** — a WhatsApp-based service that helps families coordinate calendars, grocery lists, meal plans, budgets, chores, and reminders through natural language conversation.

The service operates through the Client's WhatsApp group chat and integrates with the Client's existing tools (Google Calendar, Notion, YNAB, AnyList) to provide a unified family coordination experience.

**The service includes:**

- Natural language conversation via WhatsApp for family coordination
- Calendar event creation, lookup, and conflict detection
- Grocery list management and delivery coordination
- Budget summaries and spending insights
- Meal planning and recipe recommendations
- Proactive daily briefings and reminders
- Action item tracking and follow-up
- White-glove onboarding, setup, and ongoing maintenance

**The service is described and positioned as a structured family management tool.** It is not marketed or represented as a general-purpose AI chatbot, in compliance with Meta's WhatsApp Business Platform policies.

---

## 2. Data Privacy & Isolation

### 2.1 Single-Tenant Architecture

Each Client receives a **fully separate deployment** of the service. The Client's instance runs in its own isolated environment with its own:

- Application server (Railway deployment or equivalent)
- Persistent data volume (JSON files)
- Notion workspace connection
- Google Calendar connection
- YNAB connection
- WhatsApp Business number or group

No infrastructure, data, or configuration is shared between Clients.

### 2.2 Data Isolation Guarantees

- Client data is **never shared** with other Clients.
- Client data is **never used for AI model training**. The service uses the Anthropic API, which does not train on API inputs per Anthropic's data usage policy.
- Conversation data is stored in the Client's own deployment volume and is not transmitted to any party other than the AI provider (Anthropic) for processing.

### 2.3 Operator Access to Client Data

The Operator does **not** routinely access Client data. Access is limited to the following:

- **Troubleshooting**: The Operator must request and receive **explicit written permission** (via WhatsApp, email, or other documented channel) from the Client before viewing any Client data for debugging or support purposes.
- **Maintenance**: Automated maintenance tasks (backups, updates) do not require viewing Client data content.
- **Security incidents**: In the event of a security incident, the Operator may access system logs (not conversation content) without prior consent, and will notify the Client within 24 hours.

---

## 3. Data Ownership

### 3.1 Client Owns Their Data

The Client retains full ownership of all data generated through or stored by the service, including but not limited to:

- Conversation history
- Meal plans and recipes
- Grocery lists and purchase history
- Calendar entries created through the service
- Budget data and spending summaries
- Action items and meeting notes
- Family profile information and preferences

### 3.2 Data Export

The Client may request a full export of their data at any time. The Operator will provide the export in JSON format within **7 business days** of the request.

### 3.3 Data Deletion

Upon cancellation of service, all Client data will be permanently deleted from the Operator's servers within **30 calendar days**. The Operator will provide written confirmation of deletion upon request.

---

## 4. Service Availability

### 4.1 Uptime Target

The Operator targets **99.5% uptime** for the service, measured monthly, excluding:

- Planned maintenance windows (see Section 4.2)
- Third-party service outages outside the Operator's control (see Section 10)

### 4.2 Planned Maintenance

Planned maintenance windows will be communicated to the Client at least **48 hours in advance** via WhatsApp or email. Maintenance will be scheduled during low-usage hours when possible (typically 1:00 AM - 5:00 AM in the Client's local time zone).

### 4.3 Service Level Agreement

**Family Tier:** No formal SLA. The Operator provides uptime on a best-effort basis.

**Enterprise Tier:** Custom SLA available with defined uptime guarantees, response times, and remedies. Terms negotiated per contract.

### 4.4 Incident Communication

In the event of unplanned downtime:

- The Operator will acknowledge the issue within **4 hours** during business hours.
- The Operator will provide status updates at least every **4 hours** until resolution.
- A post-incident summary will be provided for outages exceeding 4 hours.

---

## 5. Payment Terms

### 5.1 Fees

| Fee | Amount | When Due |
|-----|--------|----------|
| One-time setup fee | $499 (Family) / Custom (Enterprise) | Before onboarding begins |
| Monthly service fee | $99 (Family) / Custom (Enterprise) | On billing anniversary date |
| Add-on integrations | As quoted | Added to monthly invoice |

### 5.2 Billing

- Monthly fees are billed on the anniversary of the service start date.
- Payment is accepted via invoice (Stripe or PayPal).
- Invoices are due within **15 calendar days** of issuance.
- Late payments exceeding 30 days may result in service suspension with 7 days written notice.

### 5.3 Money-Back Guarantee

The Operator offers a **30-day money-back guarantee on the setup fee**. If the Client is not satisfied with the service within 30 days of the onboarding completion date, the setup fee will be refunded in full. The first month's service fee is non-refundable.

---

## 6. Cancellation & Data Handling

### 6.1 Cancellation

- The Client may cancel the service at any time with **30 days written notice** (email or WhatsApp).
- There are **no cancellation fees** or early termination penalties.
- Service continues through the end of the current billing period after notice is given.

### 6.2 Post-Cancellation Data Handling

Upon cancellation:

1. The Operator will provide a **full data export** (JSON format) within **7 business days** of the Client's request.
2. All Client data will be **permanently deleted** from the Operator's servers within **30 calendar days** of the service end date.
3. The Operator will provide **written confirmation** of data deletion upon request.
4. Data stored in the Client's own accounts (Notion, Google Calendar, YNAB) remains under the Client's control and is unaffected by cancellation.

---

## 7. Meta WhatsApp Policy Compliance

### 7.1 Platform Compliance

The service is operated in compliance with Meta's WhatsApp Business Platform policies. Specifically:

- The service is positioned as a **structured family management tool**, not a general-purpose AI chatbot.
- **Message templates** are used for proactive outreach (daily briefings, reminders, scheduled notifications) and are submitted for Meta approval.
- **Conversation-based messaging** is used for interactive sessions initiated by the Client.
- The service does not send unsolicited marketing messages.
- The service does not impersonate a human — it is presented as an automated family management assistant.

### 7.2 Client Compliance

The Client agrees to:

- Maintain compliance with WhatsApp's Terms of Service and acceptable use policies.
- Not use the service to send spam, harassment, or prohibited content.
- Not share the WhatsApp group or number with unauthorized third parties.

### 7.3 Policy Changes

If Meta changes its WhatsApp Business Platform policies in a way that materially affects the service, the Operator will notify the Client within **14 days** and work with the Client to adapt. If the service can no longer be provided via WhatsApp, the Operator will offer migration to an alternative messaging platform or a pro-rated refund.

---

## 8. Operator Responsibilities

The Operator agrees to:

1. **Maintain service availability** consistent with the uptime targets in Section 4.
2. **Apply security updates** to the service infrastructure in a timely manner.
3. **Respond to Client support requests** within **24 hours** on business days (Monday-Friday, excluding US federal holidays).
4. **Notify the Client** of planned maintenance per Section 4.2.
5. **Protect Client data** in accordance with the privacy terms in Section 2.
6. **Provide data exports** within 7 business days of request.
7. **Maintain third-party API integrations** and update the service when APIs change.
8. **Not access Client data** without explicit permission, except as described in Section 2.3.

---

## 9. Client Responsibilities

The Client agrees to:

1. **Provide accurate family information** during onboarding (names, schedules, preferences) to enable effective service configuration.
2. **Maintain their own integration accounts** and subscriptions:
   - Google account (free) for Calendar integration
   - Notion account (free tier) for task management
   - YNAB subscription ($14.99/month) for budget tracking (if desired)
   - AnyList account for grocery management (if desired)
3. **Report issues promptly** to the Operator when the service is not functioning as expected.
4. **Not share the WhatsApp group or number** with unauthorized users.
5. **Not attempt to reverse-engineer**, modify, or directly access the service infrastructure.
6. **Keep login credentials secure** for all integrated accounts.

---

## 10. Limitations & Disclaimers

### 10.1 Third-Party Dependencies

The service depends on third-party APIs and platforms, including but not limited to:

- WhatsApp Business Platform (Meta)
- Claude AI (Anthropic)
- Google Calendar API (Google)
- Notion API (Notion Labs)
- YNAB API (You Need A Budget)
- Railway (hosting)

The Operator is **not liable** for outages, changes, or discontinuation of any third-party service. The Operator will make reasonable efforts to adapt to third-party changes and communicate impacts to the Client.

### 10.2 AI Limitations

The service uses AI (Claude by Anthropic) to process natural language and generate responses. The Client acknowledges that:

- AI responses are **assistive in nature** — the Client should verify critical information (dates, amounts, appointments) independently.
- The AI may occasionally misunderstand requests or provide incorrect information.
- The service is **not a replacement** for professional financial, medical, legal, tax, or therapeutic advice.

### 10.3 Liability

The Operator's total liability under this agreement shall not exceed the total fees paid by the Client in the **12 months preceding** the claim. The Operator is not liable for indirect, incidental, or consequential damages.

### 10.4 Force Majeure

Neither party shall be liable for failure to perform due to causes beyond their reasonable control, including natural disasters, government actions, internet outages, or third-party service failures.

---

## 11. Modifications to This Agreement

The Operator may modify this agreement with **30 days written notice** to the Client. Material changes (pricing, data handling, service scope) require the Client's written consent. Continued use of the service after the notice period constitutes acceptance of non-material changes.

---

## 12. Governing Law

This agreement is governed by the laws of the State of [STATE], United States. Any disputes shall be resolved through good-faith negotiation, and if necessary, binding arbitration in [CITY, STATE].

---

## 13. Contact Information

**Operator:**
- Company: [COMPANY NAME]
- Contact: [CONTACT NAME]
- Email: [CONTACT EMAIL]
- Support: [SUPPORT CHANNEL]

**Client:**
- Name: [CLIENT NAME]
- Email: [CLIENT EMAIL]
- WhatsApp: [CLIENT WHATSAPP NUMBER]

---

## Signatures

By signing below, both parties agree to the terms of this Service Agreement.

**Operator:**

Name: ___________________________
Title: ___________________________
Date: ___________________________
Signature: ___________________________

**Client:**

Name: ___________________________
Date: ___________________________
Signature: ___________________________

---

*This document is a template service agreement and does not constitute legal advice. Both parties are encouraged to review this agreement with their respective legal counsel before signing.*
