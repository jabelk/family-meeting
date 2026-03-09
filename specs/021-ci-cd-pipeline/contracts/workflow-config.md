# Contract: GitHub Actions Workflow Configuration

## ci.yml — Main Pipeline

### Triggers

```yaml
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
```

### Jobs and Dependencies

```text
changes (detect changed paths)
  ├── lint-format (if app changed) ──────────┐
  ├── test (if app changed) ─────────────────┤
  ├── security-scan (if app changed) ────────┤
  ├── docker-build (main push + app changed) ┤
  │   └── deploy-railway (main push only) ───┤
  └── gate (aggregates all job statuses) ─────┘
```

### Path Filters

| Filter | Paths |
|--------|-------|
| app | `src/**`, `tests/**`, `requirements.txt`, `Dockerfile`, `pyproject.toml` |
| docs | `*.md`, `specs/**`, `.specify/**`, `data/schedules.json` |

### Job Specifications

**lint-format**:
- Runner: `ubuntu-latest`
- Python: 3.12
- Tool: Ruff (lint + format check)
- Cache: pip

**test**:
- Runner: `ubuntu-latest`
- Python: 3.12
- Tool: pytest
- Cache: pip

**security-scan**:
- Runner: `ubuntu-latest`
- Tool: Trivy filesystem scan
- Severity: CRITICAL, HIGH
- Exit code: 1 on findings (blocks PR)

**docker-build**:
- Runner: `ubuntu-latest`
- Condition: main branch push only
- Registry: ghcr.io
- Tags: `ghcr.io/{owner}/family-meeting:{sha}`, `ghcr.io/{owner}/family-meeting:latest`
- Cache: GitHub Actions cache (type=gha)

**deploy-railway**:
- Runner: `ubuntu-latest`
- Condition: main branch push, after docker-build
- Method: `railway up --detach` via RAILWAY_TOKEN
- Post-deploy: Health check via curl to production URL
- Concurrency: serial (no parallel deploys)

**gate**:
- Aggregates all job statuses
- Required for branch protection

### Required GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `RAILWAY_TOKEN` | Railway CLI authentication for deployment |

### Required GitHub Variables

None — all configuration is in the workflow file.

## cleanup-ghcr.yml — Image Cleanup

### Triggers

```yaml
on:
  schedule:
    - cron: '0 3 * * 0'  # Sunday 3 AM UTC
  workflow_dispatch:       # Manual trigger
```

### Job Specification

- Runner: `ubuntu-latest`
- Action: `snok/container-retention-policy@v3.0.0`
- Retention: Keep 20 most recent, delete older than 30 days
- Required secret: `PAT_PACKAGES` (GitHub PAT with `packages:delete` scope)

## pyproject.toml — Python Tooling Config

```toml
[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I"]  # pycodestyle errors, pyflakes, isort

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```
