---
type: guide
domain: global
status: draft
confidence: high
source: starter-template
updated: 2026-05-21
evidence_level: user_experience
use_for:
  - starter_onboarding
scope: minimal entry point for copying or bootstrapping a local-first knowledge vault
should_not_use_for: replacing the full usage guide or maintenance rules
time_sensitivity: medium
review_cycle: 180d
---

# Knowledge Vault Starter

This starter initializes a local-first knowledge vault. The local folder is the source of truth; sync targets are optional.

```bash
python bootstrap-local-vault.py --root /path/to/my-knowledge-vaults
```
