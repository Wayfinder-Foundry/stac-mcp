# ADR 0017: Label-Based Version Bumping for Copilot Agent PRs

Status: Accepted
Date: 2025-01-08

## Context

The current semantic version bumping workflow relies solely on branch prefixes (e.g., `release/`, `feature/`, `hotfix/`) to determine the appropriate version increment for PRs. However, GitHub Copilot Agent and other automated tools do not consistently use these prefixes when generating branches and PRs, limiting their ability to autonomously control the version bump type (major, minor, patch) in automated workflows.

Key challenges:
- Copilot Agent PRs and branches typically don't use the required prefix convention
- Non-agent contributors still rely on branch prefixes as the source of truth
- Automated agents need an explicit mechanism to declare version bump intent

## Decision

Enhance the CI/version automation (`.github/workflows/container.yml`) to support PR labels as an alternative mechanism for specifying version bumps, with the following design:

1. **Label-Based Version Bumping (Primary for Automated Agents)**:
   - Support labels: `bump:major`, `bump:minor`, `bump:patch`
   - Support alias labels: `bump:release`, `bump:feature`, `bump:hotfix`
   - Labels are detected using GitHub CLI (`gh pr view`) in the workflow

2. **Priority Order**:
   - PR labels take precedence over branch prefixes
   - If no labels present, fall back to existing branch prefix detection
   - If neither labels nor recognized prefixes exist, no version bump occurs

3. **Backward Compatibility**:
   - Existing branch prefix logic remains unchanged
   - Human contributors can continue using branch prefixes
   - No breaking changes to current workflows

4. **Documentation**:
   - Update AGENTS.md with label-based instructions
   - Create CONTRIBUTING.md with comprehensive guidelines
   - Update README.md to document both approaches
   - Create this ADR to document the decision

## Consequences

### Positive
- **Automated agent autonomy**: Copilot Agent can explicitly control version bumping via labels
- **Flexibility**: Both humans (branch prefixes) and agents (labels) have clear pathways
- **Predictability**: Labels provide explicit, visible version bump intent in PRs
- **Auditability**: Version bump decisions are visible in PR metadata
- **Backward compatible**: No disruption to existing contributor workflows

### Negative
- **Dual mechanisms**: Two ways to specify version bumps (though labels take priority)
- **Label management**: Requires proper label configuration in repository
- **Documentation overhead**: Need to maintain docs for both approaches

### Neutral
- **Label creation**: Requires one-time setup of bump labels in repository
- **CI complexity**: Slight increase in workflow logic to check both labels and prefixes

## Implementation Details

### Workflow Changes (container.yml)
```bash
# Check for version bump labels first (highest priority)
if echo "$LABELS" | grep -q "bump:major\|bump:release"; then
  INCREMENT_TYPE="major"
elif echo "$LABELS" | grep -q "bump:minor\|bump:feature"; then
  INCREMENT_TYPE="minor"
elif echo "$LABELS" | grep -q "bump:patch\|bump:hotfix"; then
  INCREMENT_TYPE="patch"
# Fall back to branch prefix detection
elif [[ "$BRANCH_NAME" == hotfix/* ]] || ...; then
  INCREMENT_TYPE="patch"
...
fi
```

### Label Naming Convention
- **Primary labels**: `bump:patch`, `bump:minor`, `bump:major`
- **Alias labels**: `bump:hotfix`, `bump:feature`, `bump:release`
- Rationale: Prefix prevents collision, colon separator is GitHub convention

## Alternatives Considered

1. **Commit Message Tokens**: Parse commit messages for `[bump:minor]` tokens
   - Rejected: Less visible than labels, harder to change after commit
   - Labels are more discoverable and can be added/removed easily

2. **Separate Workflow for Agents**: Create dedicated workflow for agent PRs
   - Rejected: Increases maintenance burden, harder to keep in sync
   - Single workflow with dual mechanisms is simpler

3. **Environment Variable in PR Description**: Parse PR body for version bump directive
   - Rejected: Less structured, harder to parse reliably
   - Labels provide better UX and are more machine-readable

4. **Branch Prefix Requirements for All**: Mandate branch prefixes for agents
   - Rejected: Limits agent flexibility, doesn't solve the core problem
   - Agents may not have control over branch naming

## Migration Path

No migration required - this is an additive change:
1. Deploy updated workflow to main branch
2. Create bump labels in repository settings (if not already present)
3. Update documentation (AGENTS.md, CONTRIBUTING.md, README.md)
4. Communicate changes to contributors via issue/discussion
5. Copilot Agent automatically benefits from label support

## Success Criteria

- [x] Copilot Agent PRs can specify version bump type using labels
- [x] Non-agent PRs continue to use branch prefixes without changes
- [x] CI workflow passes with label detection logic
- [x] Documentation is comprehensive and clear
- [x] No regressions for existing contributors
- [x] Version bumping remains predictable and auditable

## Addendums

- 2025-01-08: Initial implementation with label detection in container.yml workflow
