# Research: Holistic Family Intelligence

## R1: Cross-Domain Reasoning in System Prompts

**Decision**: Add a dedicated "Cross-Domain Thinking" section with 4-5 numbered rules after the existing 38 rules in the system prompt.

**Rationale**: The current system prompt has domain-specific rules (rules 1-38) that are excellent for single-domain tasks but contain no guidance on when or how to connect information across domains. Claude naturally dispatches to individual tools because that's what the rules teach. Adding explicit cross-domain reasoning rules will change this behavior without restructuring anything.

**Key insight from current architecture**: The system prompt is already the orchestrator — rules 9-16 (daily planner) demonstrate that Claude follows numbered instructions to chain multiple tool calls. Cross-domain rules follow the same proven pattern.

**Alternatives considered**:
- Pre-fetching data into a "context snapshot" tool: Rejected — adds code complexity, duplicates retrieval logic, violates constitution's simplicity principle
- Using a separate "strategist" Claude call before the main response: Rejected — doubles latency and cost, overengineered for 2 users
- Prompt chaining (gather phase → synthesize phase): Rejected — the agentic tool loop already handles multi-step gathering naturally

## R2: Cross-Domain Trigger Recognition

**Decision**: Define a list of "broad question" patterns in the system prompt that Claude should treat as cross-domain triggers.

**Rationale**: Claude needs to distinguish between "what's on the calendar today?" (single-domain) and "how's our week looking?" (cross-domain). Without explicit guidance, Claude defaults to the narrowest interpretation.

**Trigger patterns to include**:
- Status/overview questions: "how's our week", "how are we doing", "what's going on"
- Feeling/concern questions: "I feel behind", "I'm overwhelmed", "are we on track"
- Decision questions spanning domains: "can we afford to...", "should we...", "do we have time for..."
- Explicit multi-domain: "prep me for our family meeting", "give me the big picture"

**Non-triggers (stay single-domain)**:
- Specific tool requests: "what's on the calendar", "check the budget", "find a recipe"
- Action requests: "add an action item", "create a reminder"
- Entity lookups: "what did we spend at Costco", "when is Vienna's ski lesson"

## R3: Daily Briefing Enhancement Strategy

**Decision**: Expand the `generate_daily_plan()` prompt to ask for cross-domain synthesis while keeping the function signature unchanged.

**Current prompt** (lines 1120-1125 in assistant.py):
```
Generate today's daily plan for {target}. Check the routine templates, see who has
Zoey today, look at Jason's work calendar for meeting windows, check today's
Google Calendar events, pick a backlog item to suggest, and write the time blocks
to Erin's Google Calendar. Format the plan for WhatsApp.
```

**Enhanced prompt additions**:
- Check budget health (any categories significantly over/under)
- Check if meal plan exists for today and what's planned
- Check for overdue action items or pending grocery orders
- Weave insights together: "Tonight's dinner is [meal] (30 min prep) — good fit since you have Awana's at 6"
- Highlight the 1 most important non-calendar thing to address today

**Key constraint**: The briefing should stay concise for WhatsApp. Cross-domain insights are woven in, not appended as separate sections.

## R4: Meeting Prep Agenda Structure

**Decision**: The meeting prep follows the existing weekly agenda structure (Rule 3 in system prompt) but enhanced with actual data from each domain.

**Current Rule 3 agenda structure**:
1. This Week's Calendar
2. Review Last Week's Action Items
3. Chores
4. Meals
5. Finances
6. Backlog Review
7. Custom Topics
8. Goals

**Enhanced meeting prep approach**:
- Each section gets a **headline insight** (e.g., "Groceries $1 over budget — basically on track") followed by supporting details
- Action items section shows completed vs overdue with recommendations
- Calendar section covers both past week (what happened) and next week (what's coming)
- Priorities section synthesizes across all domains: "Top 3 things to decide this week"

**Delivery**: Both ad-hoc via WhatsApp ("prep me for our family meeting") and scheduled via n8n endpoint.

## R5: Context Window Budget

**Decision**: No special handling needed. The enhanced prompts fit comfortably within Claude's 200K context window.

**Estimate**:
- System prompt (current): ~4K tokens (207 lines)
- System prompt (with new rules): ~5K tokens (+20 lines)
- Tool definitions (47 tools): ~10K tokens
- Conversation history (10 turns max): ~15-30K tokens
- Cross-domain tool results (6-8 tool calls): ~5-10K tokens
- **Total**: ~35-55K tokens — well within 200K limit

**No concern**: Even with conversation memory loaded, there's ample room for cross-domain data gathering.
