# Quarterly Documentation Review Checklist

**Purpose:** Systematic review to maintain documentation quality and accuracy
**Frequency:** Quarterly (January, April, July, October)
**Duration:** ~2-3 hours
**Owner:** Documentation maintainer / Tech lead

---

## Pre-Review Setup

### Schedule and Prepare

- [ ] **Schedule review** for first week of quarter
- [ ] **Assign reviewer** (rotate among team members)
- [ ] **Create review branch:** `git checkout -b docs/quarterly-review-qN-YYYY`
- [ ] **Pull latest changes:** `git pull origin main`

### Gather Baseline Metrics

```bash
# Run validator
python3 scripts/validate_docs.py > quarterly_review_baseline.txt

# Count files
find docs -name "*.md" | wc -l

# Check git activity since last review
git log --since="3 months ago" --oneline --grep="docs:" | wc -l
```

---

## Section 1: Automated Validation (30 min)

### 1.1 Link Validation

```bash
# Run full link validation
python3 scripts/validate_docs.py
```

- [ ] **Zero broken links** ✅ or document exceptions
- [ ] **All relative paths resolve** correctly
- [ ] **Source code references** point to existing files
- [ ] **Document any false positives** in review notes

**Actions if failures found:**
- Fix broken links immediately
- Update moved/renamed files
- Document intentional exceptions

---

### 1.2 CI/CD Health Check

- [ ] **Check GitHub Actions:** `.github/workflows/docs-validation.yml`
- [ ] **Review recent workflow runs:** All passing? ✅
- [ ] **Check scheduled runs:** Weekly validation working? ✅
- [ ] **Review any ignored failures**

**Navigate to:** GitHub → Actions → Documentation Validation

---

### 1.3 Pre-commit Hook Status

```bash
# Test pre-commit hooks
pre-commit run --all-files
```

- [ ] **All hooks passing** ✅
- [ ] **Doc validation hook** executing correctly
- [ ] **No skipped checks**

---

## Section 2: Content Accuracy Review (60 min)

### 2.1 Configuration Documentation

**Verify against:** `src/config/settings.py`

```bash
# Count fields in settings.py
grep -c "Field(" src/config/settings.py

# Check environment.md has all fields
# Manual review required
```

- [ ] **All config fields** documented in `docs/4-configuration/environment.md`
- [ ] **Correct default values** listed
- [ ] **No deprecated fields** still documented
- [ ] **.env.example** matches current settings
- [ ] **Validation rules** accurately described

**Files to check:**
- `docs/4-configuration/environment.md`
- `docs/4-configuration/reference.md`
- `.env.example`

---

### 2.2 Tool Documentation

**Verify against:** `src/agent/unified_agent.py`

```bash
# List all agent tools
grep "@super_agent.tool" src/agent/unified_agent.py -A 2
```

- [ ] **All tools** listed in README.md (line ~290)
- [ ] **Tool names** match implementation
- [ ] **Parameters** correctly documented
- [ ] **Usage examples** accurate

**Files to check:**
- `README.md` (Tool Documentation section)
- `CLAUDE.md` (RAG tools section ~line 173)
- `docs/5-guides/usage.md` (Agent Tools Reference)
- `docs/5-guides/tool-usage-patterns.md`

---

### 2.3 API Endpoint Documentation

**Verify against:** `src/api/main.py` and routers

```bash
# Count API endpoints
grep -r "@router\.(get\|post\|delete\|patch)" src/api/ | wc -l
```

- [ ] **All endpoints** documented in README.md API section
- [ ] **Request/response schemas** accurate
- [ ] **Status codes** correct
- [ ] **Authentication** requirements clear

**Files to check:**
- `README.md` (API Reference section ~line 371)
- `docs/6-deployment/api-runbook.md`

---

### 2.4 Architecture Documentation

- [ ] **System diagrams** still accurate
- [ ] **SearchStrategy enum** matches `src/config/settings.py`
- [ ] **Database schema** matches SQL migration files
- [ ] **Neo4j structure** matches `src/agentic_rag/storage/neo4j_store.py`
- [ ] **Data flow diagrams** current

**Files to check:**
- `docs/3-architecture/index.md`
- `docs/3-architecture/agentic-rag.md`
- `docs/3-architecture/database-and-rag.md`

---

## Section 3: External References (20 min)

### 3.1 External Links

**Manually test critical external links:**

```bash
# Find all external links
grep -rh "](http" docs/ README.md CLAUDE.md | grep -oP 'http[^)]+' | sort -u > external_links.txt
```

**Test these high-priority links:**
- [ ] **Supabase docs** - Database setup links
- [ ] **Neo4j docs** - Graph database links
- [ ] **Pydantic AI docs** - Framework documentation
- [ ] **LLM provider docs** - OpenAI, Anthropic, Ollama
- [ ] **GitHub repo links** - If any self-references

**Mark as broken if:**
- Returns 404
- Redirects to unrelated content
- Site is down permanently

---

### 3.2 Version-Specific References

- [ ] **Python version** requirements match `pyproject.toml`
- [ ] **Dependency versions** match if specified
- [ ] **Framework versions** current
- [ ] **Docker image versions** in deployment docs

---

## Section 4: New Features & Changes (30 min)

### 4.1 Review Git Log

```bash
# Get commits affecting code since last review
git log --since="3 months ago" --oneline --no-merges src/

# Check if documented
```

**For each significant change:**
- [ ] **Is it documented?** If user-facing, must be in docs
- [ ] **README updated?** For major features
- [ ] **CHANGELOG updated?** For all notable changes
- [ ] **Migration guide needed?** For breaking changes

---

### 4.2 Check for Undocumented Features

```bash
# Find recently added files
git log --since="3 months ago" --diff-filter=A --name-only --pretty=format: src/ | sort -u

# Check if documented
```

- [ ] **New tools** documented
- [ ] **New configuration** options documented
- [ ] **New API endpoints** documented
- [ ] **New deployment options** documented

---

## Section 5: Quality & Usability (20 min)

### 5.1 Documentation Metrics

```bash
# File counts
find docs -name "*.md" | wc -l
find docs -name "*.md" -exec wc -w {} + | tail -1

# Largest files
find docs -name "*.md" -exec wc -w {} \; | sort -rn | head -10
```

**Track trends:**
- [ ] Total markdown files: ______
- [ ] Total word count: ______
- [ ] Average words per file: ______
- [ ] Largest file: ______ (should be <5000 words)

---

### 5.2 Readability Spot Check

**Randomly select 5 documentation files and review:**

- [ ] **Clear headers** and structure
- [ ] **Code examples** work and are relevant
- [ ] **No broken formatting** (tables, lists, code blocks)
- [ ] **Consistent style** (tone, formatting)
- [ ] **No outdated screenshots** or references

---

### 5.3 Common Issues Check

```bash
# Find TODO/FIXME in docs
grep -rn "TODO\|FIXME\|XXX" docs/

# Find outdated date references
grep -rn "202[0-3]" docs/ | grep -i "update"

# Find placeholder text
grep -rn "TODO\|TBD\|PLACEHOLDER\|XXX" docs/
```

- [ ] **No critical TODOs** left unresolved
- [ ] **"Last Updated" dates** recent
- [ ] **No placeholder** content

---

## Section 6: Documentation Gaps (15 min)

### 6.1 Missing Documentation

**Check if these exist and are complete:**

- [ ] **Troubleshooting guide** - Common errors covered?
- [ ] **Migration guides** - For major version upgrades?
- [ ] **Performance tuning** - Optimization tips?
- [ ] **Security hardening** - Production security?
- [ ] **Monitoring setup** - Observability guidance?

---

### 6.2 Frequently Asked Questions

**Review:**
- GitHub Issues (documentation-related)
- Discussion forums
- Support tickets

**Identify:**
- [ ] **Common questions** not in docs
- [ ] **Frequent pain points** needing better docs
- [ ] **Missing examples**

---

## Section 7: Action Items & Reporting (15 min)

### 7.1 Compile Findings

Create `QUARTERLY_REVIEW_QN_YYYY.md`:

```markdown
# Quarterly Documentation Review - Q[N] YYYY

**Date:** YYYY-MM-DD
**Reviewer:** [Name]
**Duration:** [Hours]

## Summary

- Files reviewed: XX
- Issues found: XX
- Issues fixed: XX
- Issues deferred: XX

## Validation Results

- Link validation: ✅ / ❌ (X broken links)
- CI/CD status: ✅ / ❌
- Pre-commit hooks: ✅ / ❌

## Critical Issues Found

1. [Issue description] - Status: Fixed/Documented/Deferred
2. ...

## Non-Critical Issues

1. [Issue description] - Status: Fixed/Documented/Deferred
2. ...

## New Documentation Needed

1. [Topic] - Priority: High/Medium/Low
2. ...

## Metrics

| Metric | Previous Quarter | Current Quarter | Change |
|--------|------------------|-----------------|--------|
| Total files | XX | XX | +/-X |
| Total words | XX | XX | +/-X |
| Broken links | X | X | +/-X |
| External links | X | X | +/-X |
| Avg file size | XX | XX | +/-X |

## Recommendations

1. [Recommendation]
2. [Recommendation]

## Next Review

**Scheduled for:** [Date - 3 months from now]
**Assigned to:** [Name or TBD]
```

---

### 7.2 Create Issues for Deferred Items

For issues that can't be fixed immediately:

```bash
# Create GitHub issues
gh issue create --title "Docs: [Issue]" --label "documentation" --body "[Details]"
```

- [ ] **High priority issues** → Create issues
- [ ] **Assign owners**
- [ ] **Set due dates**

---

### 7.3 Update Documentation Audit Record

- [ ] **Add quarterly review entry** to `docs/a-changelogs/documentation-audit-2025-10.md`
- [ ] **Update metrics** if significant changes
- [ ] **Note any process improvements**

---

### 7.4 Commit and Create PR

```bash
# Commit all fixes
git add .
git commit -m "docs: Quarterly review Q[N] YYYY - Fix X issues

- Fixed X broken links
- Updated Y configuration references
- Added Z missing documentation
- See QUARTERLY_REVIEW_Q[N]_YYYY.md for details"

# Push and create PR
git push origin docs/quarterly-review-qN-YYYY
gh pr create --title "Quarterly Documentation Review Q[N] YYYY" \
  --body "Quarterly review findings and fixes. See QUARTERLY_REVIEW_Q[N]_YYYY.md"
```

---

## Post-Review Actions

### Schedule Next Review

- [ ] **Add calendar reminder** for next quarter
- [ ] **Assign next reviewer** (rotate)
- [ ] **Update this checklist** if process changed

### Share Results

- [ ] **Post summary** in team channel
- [ ] **Present findings** in team meeting
- [ ] **Archive review document** in appropriate location

---

## Quick Reference

**Run full validation:**
```bash
python3 scripts/validate_docs.py
pre-commit run --all-files
```

**Check recent doc changes:**
```bash
git log --since="3 months ago" --oneline -- docs/ "*.md"
```

**Find TODOs:**
```bash
grep -rn "TODO\|FIXME" docs/
```

**Test external links (manual):**
- Save list: `grep -rh "](http" docs/ | grep -oP 'http[^)]+' | sort -u`
- Test each important one

---

**Review Schedule:**
- **Q1:** January 1-15
- **Q2:** April 1-15
- **Q3:** July 1-15
- **Q4:** October 1-15

**Estimated Time:** 2-3 hours
**Recommended:** Block dedicated time, don't rush
