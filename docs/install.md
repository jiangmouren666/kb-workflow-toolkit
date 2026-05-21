# Installation

## Requirements

- Python 3.10 or newer.
- A local folder for your knowledge vault.
- Optional: Obsidian, Git, WebDAV, or another sync layer.

The toolkit does not require a database or hosted service.

## Clone

```bash
git clone https://github.com/your-name/kb-workflow-toolkit.git
cd kb-workflow-toolkit
```

## Create A Vault From The Starter

```bash
cp -R starter ~/my-knowledge-vault
```

Run the initial scan:

```bash
python ~/my-knowledge-vault/00-global/scripts/kb.py --root ~/my-knowledge-vault scan
```

You should see an audit report. A clean starter may still contain draft templates; that is normal.

## Optional Initialization

If you want the toolkit to write local config for a new vault:

```bash
python ~/my-knowledge-vault/00-global/scripts/kb.py init --root ~/my-knowledge-vault
```

This creates local state under `00-global/state/`. Do not commit that state to a public repository.

## Useful Commands

```bash
python ~/my-knowledge-vault/00-global/scripts/kb.py --root ~/my-knowledge-vault scan
python ~/my-knowledge-vault/00-global/scripts/kb.py --root ~/my-knowledge-vault improve
python ~/my-knowledge-vault/00-global/scripts/kb.py --root ~/my-knowledge-vault review-improvements --limit 5
python ~/my-knowledge-vault/00-global/scripts/kb.py --root ~/my-knowledge-vault maintain plan
python ~/my-knowledge-vault/00-global/scripts/kb.py --root ~/my-knowledge-vault maintain status
python ~/my-knowledge-vault/00-global/scripts/kb.py --root ~/my-knowledge-vault maintain apply --plan-id <plan-id>
python ~/my-knowledge-vault/00-global/scripts/trust-drift-report.py --root ~/my-knowledge-vault
```

Add `--write` only after reviewing dry-run output.

## Optional Companion Skills

Install the AI behavior layer if you want Cursor agents to answer from the vault with citations or help with safe import and maintenance:

```bash
mkdir -p ~/.cursor/skills
cp -R skills/kb-answer-with-citations ~/.cursor/skills/
cp -R skills/kb-import-and-maintain ~/.cursor/skills/
```

See `docs/skills.md` for details.

To avoid editing skill files when changing machines, set a vault root environment variable in your shell profile:

```bash
export KNOWLEDGE_VAULT_ROOT="$HOME/my-knowledge-vault"
```

The skills also accept an explicit `vault_root` in your prompt, which takes priority over the environment variable.
