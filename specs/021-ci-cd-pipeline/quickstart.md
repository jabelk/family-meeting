# Quickstart: CI/CD Pipeline Validation

## Scenario 1: PR Check — Code Change

**Steps**:
1. Create a branch, modify a Python file in `src/`, push and open a PR
2. Observe GitHub Actions run

**Expected**: Lint (Ruff), test (pytest), and security scan (Trivy) jobs all run and report status on the PR.

## Scenario 2: PR Check — Docs Only

**Steps**:
1. Create a branch, modify only a `.md` file or file in `specs/`, push and open a PR
2. Observe GitHub Actions run

**Expected**: Change detection marks app changes as false; lint/test/scan jobs are skipped. Gate job still passes.

## Scenario 3: Merge to Main — Full Deploy

**Steps**:
1. Merge a PR to main (or push directly)
2. Observe GitHub Actions run

**Expected**: Checks run → Docker image built and pushed to GHCR with SHA tag + `latest` → Railway deployment triggered → Health check at `https://mombot.sierracodeco.com/health` returns 200.

## Scenario 4: Failing Test Blocks Merge

**Steps**:
1. Open a PR with a deliberately broken test (e.g., `assert False`)
2. Attempt to merge

**Expected**: CI check fails, branch protection prevents merge. Fix the test, push again, check passes.

## Scenario 5: Security Vulnerability Detection

**Steps**:
1. Add a dependency with a known CVE to `requirements.txt`
2. Push and open a PR

**Expected**: Trivy filesystem scan flags the vulnerability as CRITICAL or HIGH on the PR check.

## Scenario 6: Railway Deploy Failure

**Steps**:
1. Introduce a build error (e.g., missing import) that passes lint but fails at runtime
2. Merge to main

**Expected**: Docker build succeeds but Railway health check fails. Developer sees failed status on GitHub Actions. Previous Railway deployment remains running.

## Scenario 7: Image Cleanup

**Steps**:
1. Wait for weekly cleanup schedule (Sunday 3 AM UTC) or trigger manually
2. Check GHCR package versions

**Expected**: Images older than 30 days are removed, keeping the 20 most recent.
