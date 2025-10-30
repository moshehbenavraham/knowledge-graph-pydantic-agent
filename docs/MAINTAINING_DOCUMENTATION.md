# Documentation Maintenance Guide

**Purpose:** Ensure documentation stays accurate, current, and high-quality.
**Owner:** Development team
**Last Updated:** 2025-10-17

---

## Quick Reference

### Before Every Commit

```bash
# Validate documentation links
python3 scripts/validate_docs.py

# Run pre-commit checks (includes doc validation)
pre-commit run --all-files
```

### After Major Changes

```bash
# Regenerate any auto-generated docs
make docs  # If applicable

# Update audit log if needed (see docs/a-changelogs/)
# Run full validation
python3 scripts/validate_docs.py
```

---

## Documentation Update Procedures

### 1. When Adding New Features

**Required Documentation Updates:**

- [ ] **README.md** - Add feature to features list if user-facing
- [ ] **CLAUDE.md** - Update if it affects agent behavior or tools
- [ ] **docs/5-guides/usage.md** - Add usage examples
- [ ] **docs/3-architecture/** - Update architecture if needed
- [ ] **CHANGELOG.md** - Document the change

**Example Workflow:**
```bash
# 1. Create feature branch
git checkout -b feature/new-awesome-feature

# 2. Implement feature
# ... code changes ...

# 3. Update documentation
vim docs/5-guides/usage.md
vim README.md

# 4. Validate documentation
python3 scripts/validate_docs.py

# 5. Commit with both code and docs
git add .
git commit -m "feat: Add awesome new feature

- Implement feature logic
- Add usage documentation
- Update README"
```

---

### 2. When Changing Configuration

**Required Updates:**

- [ ] **.env.example** - Add/update environment variables
- [ ] **docs/4-configuration/environment.md** - Document new settings
- [ ] **docs/4-configuration/reference.md** - Update reference if needed
- [ ] **src/config/settings.py** - Ensure Pydantic model is updated
- [ ] **CLAUDE.md** - Update configuration section if significant

**Validation:**
```bash
# Check all config fields are documented
grep -r "Field(" src/config/settings.py | wc -l
# Compare with documented fields count in environment.md
```

---

### 3. When Changing Tool Names or Signatures

**Critical Files to Update:**

- [ ] **README.md** - Tool reference section
- [ ] **CLAUDE.md** - Tool system documentation
- [ ] **docs/5-guides/usage.md** - Tool usage examples
- [ ] **docs/5-guides/tool-usage-patterns.md** - Tool patterns
- [ ] **docs/8-development/testing-guide.md** - Tool naming convention section

**Validation Command:**
```bash
# Find all tool references
grep -r "retrieve_documents\|list_all_documents\|get_full_document" docs/ README.md CLAUDE.md

# Verify against actual implementation
grep "@super_agent.tool" src/agent/unified_agent.py -A 2
```

---

### 4. When Updating Dependencies

**Required Updates:**

- [ ] **README.md** - Update requirements if needed
- [ ] **docs/2-getting-started/installation.md** - Update installation steps
- [ ] **pyproject.toml** - Update dependency versions
- [ ] **requirements.txt** - Regenerate if used

**Check for Breaking Changes:**
```bash
# Review changelogs for breaking changes
# Update migration guides if needed
```

---

### 5. When Deprecating Features

**Required Steps:**

1. **Add deprecation warnings** in code
2. **Update documentation:**
   - [ ] Add ⚠️ deprecation notices to relevant docs
   - [ ] Update README.md to mark as deprecated
   - [ ] Document migration path in docs/
3. **Update CHANGELOG.md** with deprecation notice
4. **Set removal date** (recommended: 2 major versions)

**Example Deprecation Notice:**
```
> **⚠️ DEPRECATED:** This feature is deprecated as of v1.2.0 and will be removed in v2.0.0.
> Use [new-feature](2-getting-started/installation-reference.md) instead. See [migration guide](2-getting-started/installation-reference.md) for details.
```

*Note: Replace the example links with actual paths to your new feature and migration documentation.*

---

## File Organization Rules

### Structure

```
docs/
├── README.md                    # Documentation index
├── 1-overview/                  # Project overview
├── 2-getting-started/           # Installation, quickstart
├── 3-architecture/              # System design
├── 4-configuration/             # Configuration reference
├── 5-guides/                    # Usage guides
├── 6-deployment/                # Deployment guides
├── 7-operations/                # Operational runbooks
├── 8-development/               # Development guides
├── 9-security/                  # Security documentation
├── 10-troubleshooting/          # Troubleshooting
└── a-changelogs/                # Historical changelogs
```

### Naming Conventions

- **Use lowercase with hyphens:** `my-feature-guide.md` ✅
- **Not camelCase or underscores:** `myFeatureGuide.md` ❌ `my_feature_guide.md` ❌
- **Be descriptive:** `database-setup.md` ✅ not `db.md` ❌
- **Index files:** Use `index.md` for directory indices

### Link Guidelines

**Relative Links:**

Syntax: `&#91;Link Text&#93;(relative/path/to/file.md)`

Working examples from this file (docs/MAINTAINING_DOCUMENTATION.md):
- Configuration: [environment.md](4-configuration/environment.md)
- Installation: [installation-reference.md](2-getting-started/installation-reference.md)
- Agent source: [unified_agent.py](../src/agent/unified_agent.py)

**Internal Links:**
- Always use relative paths
- Include `.md` extension
- Test with `python3 scripts/validate_docs.py`

**External Links:**
- Use full URLs for external resources
- Prefer HTTPS
- Link to stable documentation versions when possible

---

## Quality Checklist

Before committing documentation changes, verify:

### Content

- [ ] **Accuracy**: Information matches actual implementation
- [ ] **Clarity**: Clear, concise, unambiguous language
- [ ] **Completeness**: Covers all necessary details
- [ ] **Examples**: Includes practical examples where helpful
- [ ] **Links**: All links work (run validator)

### Style

- [ ] **Consistent formatting**: Headers, lists, code blocks
- [ ] **Proper grammar**: No typos or grammatical errors
- [ ] **Code blocks**: Use appropriate language tags
- [ ] **Screenshots**: Included and up-to-date if needed

### Technical

- [ ] **Links validated**: `python3 scripts/validate_docs.py` passes
- [ ] **Pre-commit hooks**: All checks pass
- [ ] **No broken references**: All file paths exist
- [ ] **Version info**: Update "Last Updated" dates where applicable

---

## Automated Validation

### Local Validation

```bash
# Quick validation
python3 scripts/validate_docs.py

# Full pre-commit check
pre-commit run --all-files

# Manual link check for specific file
python3 scripts/validate_docs.py | grep "filename.md"
```

### CI/CD Validation

Documentation validation runs automatically on:
- Every push to `main` or `develop`
- Every pull request
- Weekly on Mondays at 9 AM UTC
- Manual workflow dispatch

**Workflow:** `.github/workflows/docs-validation.yml`

**What it checks:**
- Broken internal links
- Markdown syntax (markdownlint)
- Required files exist
- Documentation metrics

---

## Common Maintenance Tasks

### Adding a New Documentation File

1. **Create file in appropriate directory**
2. **Add frontmatter if using docs generator**
3. **Update parent directory's `index.md`**
4. **Add links from related documentation**
5. **Run validator**: `python3 scripts/validate_docs.py`

### Moving or Renaming Files

1. **Use git mv to preserve history:**
   ```bash
   git mv docs/old-name.md docs/new-name.md
   ```

2. **Find and update all references:**
   ```bash
   grep -r "old-name.md" docs/ *.md
   # Update each file
   ```

3. **Validate all links:**
   ```bash
   python3 scripts/validate_docs.py
   ```

4. **Consider adding redirect** if file was publicly linked

### Fixing Broken Links

1. **Run validator to find broken links:**
   ```bash
   python3 scripts/validate_docs.py
   ```

2. **Review each broken link:**
   - Does target file exist?
   - Is the path correct (relative vs absolute)?
   - Should it be `../` or `../../`?

3. **Fix and revalidate:**
   ```bash
   # Fix links in editor
   python3 scripts/validate_docs.py
   ```

### Updating Code Examples

1. **Test code examples** in actual environment
2. **Update version-specific details** (Python versions, package versions)
3. **Verify outputs match** what users will see
4. **Update comments** if code logic changed

---

## Quarterly Review Process

**Schedule:** Beginning of each quarter (January, April, July, October)

### Review Checklist

1. **Run full audit:**
   ```bash
   python3 scripts/validate_docs.py
   ```

2. **Check for outdated content:**
   - Version numbers
   - Deprecated features still documented
   - Screenshots (if any)
   - External links (manually test important ones)

3. **Verify against current codebase:**
   - Tool names match implementation
   - Configuration matches `src/config/settings.py`
   - API endpoints match routers

4. **Update audit log** (if major changes):
   - Note any issues found in `docs/a-changelogs/documentation-audit-2025-10.md`
   - Record fixes applied
   - Update metrics during quarterly reviews

5. **Review metrics:**
   - Documentation file count
   - Broken links trend
   - Most accessed docs (if tracking available)

6. **Update this guide** if processes changed

### Quarterly Review Template

```markdown
## Quarterly Review Q[N] 2025

**Date:** YYYY-MM-DD
**Reviewer:** [Name]

### Validation Results
- [ ] Link validator: X/Y files, Z broken links
- [ ] All critical docs present
- [ ] Code examples tested

### Issues Found
1. Issue description - Fixed/Documented/Deferred
2. ...

### Metrics
- Total markdown files: XX
- Documentation files: XX
- Broken links fixed: XX
- New documentation added: XX

### Recommendations
- [ ] Recommendation 1
- [ ] Recommendation 2

### Next Review
Scheduled for: [Date]
```

---

## Troubleshooting

### Validator Reports False Positives

**Issue:** Validator flags valid links as broken

**Common Causes:**
- Links in code blocks (shouldn't be validated)
- Anchor links to sections (#heading)
- External links (not validated)

**Solution:**
- Review the specific link
- If it's in a code block, it's safe to ignore
- Manually verify external links if needed

### Pre-commit Hook Fails

**Issue:** Documentation validation fails on commit

**Solution:**
```bash
# Run validator to see details
python3 scripts/validate_docs.py

# Fix broken links
# Then retry commit

# Or skip hook if intentional (use sparingly)
git commit --no-verify
```

### CI/CD Workflow Fails

**Issue:** GitHub Actions docs-validation workflow fails

**Solution:**
1. Check workflow run output in GitHub Actions tab
2. Review the "Documentation Link Validation Results" summary
3. Fix issues locally
4. Run validator locally to verify: `python3 scripts/validate_docs.py`
5. Push fixes

---

## Contact and Questions

- **Documentation Issues:** Open GitHub issue with `documentation` label
- **Urgent Fixes:** Contact dev team lead
- **Suggestions:** Open discussion in GitHub Discussions

---

**Remember:** Good documentation is code. Treat it with the same care as your source code!
