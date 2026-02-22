# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Specify template project** — a spec-driven development framework. There is no application source code yet; the repository contains workflow scaffolding for structured feature development using AI agents.

## Development Workflow

Features are developed through a phased pipeline using slash commands, executed in order:

1. `/speckit.specify "feature description"` — Create feature spec from natural language
2. `/speckit.clarify` — Resolve ambiguities (up to 5 questions across 8 dimensions)
3. `/speckit.plan` — Generate technical plan (research, data model, contracts, quickstart)
4. `/speckit.checklist "purpose"` — Generate domain-specific quality checklists
5. `/speckit.tasks` — Break plan into dependency-ordered, actionable tasks
6. `/speckit.analyze` — Non-destructive consistency analysis across spec/plan/tasks
7. `/speckit.implement` — Execute tasks in phases with checkpoint gates
8. `/speckit.taskstoissues` — Convert tasks to GitHub issues
9. `/speckit.constitution` — Create/update project governance principles

## Conventions

**Branch naming**: `###-short-name` (e.g., `001-user-auth`). The 3-digit prefix auto-increments from the highest existing feature number across branches and `specs/`.

**Feature artifacts** live under `specs/###-feature-name/`:
- `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`
- `contracts/` — API/CLI/UI interface definitions
- `checklists/` — Quality validation checklists

## Architecture

- `.specify/templates/` — Markdown templates that define the structure for each artifact type
- `.specify/scripts/bash/` — Automation scripts (feature creation, prerequisite checks, planning setup, agent context updates)
- `.specify/memory/constitution.md` — Project governance principles; plans are validated against these
- `.claude/commands/speckit.*.md` — Slash command definitions for the 9 workflow phases

All bash scripts use strict mode (`set -e -u -o pipefail`) and support both git and non-git repositories.

## Key Constraints

- Specifications must be user-focused and tech-agnostic (no implementation details in specs)
- Each user story must be independently testable and deployable
- Plans must comply with constitution principles; violations require explicit justification
- Tasks specify full file paths and mark parallel-safe items with `[P]`
