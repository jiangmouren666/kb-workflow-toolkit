---
type: standard
domain: global
status: reviewed
confidence: high
evidence_level: user_experience
source: system-design
updated: 2026-05-20
use_for:
  - write_policy
  - registry_source_of_truth
  - sync_conflict_prevention
scope: preventing stale agents or sync tools from overwriting knowledge-state metadata
should_not_use_for: replacing backups, version control, or external storage consistency guarantees
time_sensitivity: medium
review_cycle: 90d
human_review:
  reviewer: user
  decision: optimize stale writeback prevention
  reviewed_at: 2026-05-18
  result: accepted as reviewed write-protection policy
usage_count: 0
last_used:
last_feedback:
failure_modes: []
improvement_notes: []
---

# Write Protection Policy

## Core Rule

Do not treat individual note frontmatter as the only source of truth for human-reviewed status. Human review decisions must be recorded in `human-review-registry.md`.

## Source Of Truth

| State | Source Of Truth |
|---|---|
| Human-reviewed status | `00-global/human-review-registry.md` |
| Completed review snapshots | `00-global/review-batches/` |
| Pending human review | `00-global/review-queue-v2.md` |
| Domain verification rules | each domain's `10-standards/*standard.md` |
| Daily usage entry points | `00-global/usage-guide.md` |
| Vault root and optional target config | `00-global/state/vault-config.json` |

## Write Rules

1. A note can be edited for content, but status changes must also update the registry.
2. If note frontmatter says `draft` but registry says `reviewed`, treat the registry as authoritative.
3. If a stale agent overwrites note frontmatter, run registry drift repair before continuing curation.
4. Do not use old `review-queue.md` as the active queue; use `review-queue-v2.md`.
5. Prefer append-only review batch archives for auditability.
6. Prefer `00-global/scripts/kb.py` for maintenance writes so manifest checks and the advisory lock are applied.

## Manifest And Lock Rules

- Current manifest: `00-global/state/current-manifest.json`.
- Historical snapshots: `00-global/state/snapshots/`.
- Advisory lock: `00-global/state/kb.lock`.
- The lock protects new CLI-based writes from overlapping with each other.
- The manifest detects unexpected file drift before or after maintenance.
- The lock cannot stop external tools that ignore this policy; use `kb.py diff` to detect those changes.

## Repair Workflow

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> repair
```

Use `--write` only after reviewing the dry-run output.

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> repair --write
```

## Daily Commands

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> doctor
python <vault_root>/00-global/scripts/kb.py --root <vault_root> snapshot
python <vault_root>/00-global/scripts/kb.py --root <vault_root> diff
```

## Optional Export/Sync Target Policy

Auto-sync is opt-in and conservative. A vault with no Obsidian, cloud folder, WebDAV mount, or sync target is still a complete and valid knowledge base.

The local vault root is the source of truth:

- Source: `<vault_root>`
- Target: optional folder configured in `00-global/state/vault-config.json`
- Allowed direction: local to target only
- Forbidden direction: Obsidian/WebDAV to local

Do not re-enable `/usr/local/bin/sync-vaults.sh` or `knowledge-vaults-sync.timer`. That legacy flow pulled from Obsidian back into the local vault and restored stale copies of scripts and reviewed notes.

Initialize or configure:

```bash
python <vault_root>/00-global/scripts/kb.py init --root <vault_root>
python <vault_root>/00-global/scripts/kb.py configure --root <vault_root> --sync-target <target-path>
python <vault_root>/00-global/scripts/kb.py --root <vault_root> autosync enable --target <target-path>
```

Rules:

- Auto-sync uses the configured optional target.
- Auto-sync runs only after compliant `kb.py` write workflows.
- Auto-sync is skipped if strict scan reports blocking findings.
- Auto-sync is skipped if registry overlay drift is present.
- Auto-sync is skipped if protected critical files drift from their captured baseline.
- Sync writes must verify target content after copy; a successful copy call is not enough on WebDAV/FUSE mounts.
- Runtime state, manifest snapshots, `__pycache__`, and `.pyc` files should not be synced to optional targets.

Check sync safety:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> safety
python <vault_root>/00-global/scripts/kb.py --root <vault_root> protect status
```

If `safety` reports the target as `missing` or `unmounted`, keep auto-sync disabled:

```bash
python <vault_root>/00-global/scripts/kb.py --root <vault_root> autosync disable
```

Re-enable only after the mount is active and a hash-verified sync succeeds.
