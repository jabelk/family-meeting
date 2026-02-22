<!--
Sync Impact Report
- Version change: 0.0.0 → 1.0.0
- Added principles:
  - I. Integration Over Building
  - II. Mobile-First Access
  - III. Simplicity & Low Friction
  - IV. Structured Output
  - V. Incremental Value
- Added sections:
  - Integration Landscape
  - Development Approach
- Removed sections: none
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes needed (Constitution Check section is dynamic)
  - .specify/templates/spec-template.md ✅ no changes needed (user story structure compatible)
  - .specify/templates/tasks-template.md ✅ no changes needed (phase structure compatible)
- Follow-up TODOs: none
-->

# Family Meeting Constitution

## Core Principles

### I. Integration Over Building

All features MUST leverage existing services the family already uses
(Google Calendar, Gmail, Notion, YNAB, Apple ecosystem) via their APIs
rather than reimplementing equivalent functionality. Custom code exists
only to orchestrate and connect these services. If a paid service
solves the problem well, prefer subscribing over building.

### II. Mobile-First Access

Every feature MUST be fully usable from an iPhone. The primary
interaction model is phone-based — desktop is a bonus, not the target.
Favor conversational or messaging-style interfaces that work naturally
on mobile (e.g., SMS, iMessage, chat-style agents) over complex web UIs.

### III. Simplicity & Low Friction

Both partners MUST be able to use any feature with zero technical setup.
No terminal commands, no config files, no developer tools for end users.
If a workflow requires more than 3 taps/steps to complete a common
action, it is too complex. Favor familiar tools and patterns over novel
interfaces.

### IV. Structured Output

All meeting-related output MUST produce clear, scannable lists and
action items. Agendas, chore assignments, meal plans, and weekly
summaries MUST be formatted as checklists or structured lists — never
walls of prose. This serves both partners: one who thrives on lists and
one who needs them to stay organized.

### V. Incremental Value

Each feature MUST deliver standalone value from day one. The weekly
meeting agenda generator is useful without meal planning; meal planning
is useful without chore tracking. No feature should require another
feature to function. Build the highest-impact workflow first, then layer
on additional capabilities.

## Integration Landscape

The family's existing tool ecosystem that features MUST integrate with
or at minimum not conflict with:

- **Communication**: Gmail / Google Workspace, iMessage, iPhones
- **Calendar**: Google Calendar (shared family calendar)
- **Finances**: YNAB (You Need A Budget)
- **Productivity**: Notion (or similar — open to subscriptions)
- **AI Assistants**: Claude, ChatGPT
- **Devices**: iPhones, MacBooks (Apple ecosystem)

When selecting a tech stack, prefer solutions that have well-documented
APIs for these services and that can be accessed from mobile devices.

## Development Approach

This project is built and maintained by Claude Code. Design decisions
MUST favor:

- **Maintainability**: Code that Claude can easily read, modify, and
  extend in future sessions without deep context rebuilding.
- **Small surface area**: Fewer files, fewer abstractions, fewer moving
  parts. A single well-structured file beats a framework of ten.
- **Standard patterns**: Use the most common, well-documented approach
  for the chosen tech stack. Avoid clever or novel architectures.
- **API-driven**: Backend logic exposed via clean APIs so the
  interaction layer (SMS, chat, web) can be swapped independently.

## Governance

This constitution governs all feature specifications, plans, and
implementations in the Family Meeting project. All specs and plans
MUST be validated against these principles during the Constitution
Check phase.

Amendments to this constitution require:
- Clear rationale for the change
- Version bump following semantic versioning (MAJOR for principle
  removal/redefinition, MINOR for additions, PATCH for clarifications)
- Review of all in-progress specs/plans for compliance with changes

**Version**: 1.0.0 | **Ratified**: 2026-02-21 | **Last Amended**: 2026-02-21
