# KB Workflow Toolkit

Local-first knowledge base workflow toolkit for Obsidian-style vaults and AI-assisted maintenance.

The core rule is simple:

> AI proposes. Humans and rules approve. Core knowledge is never silently modified.

This repository packages a clean starter vault, maintenance scripts, workflow docs, and sanitized examples. It is designed for users who want a reusable knowledge base process across domains such as fiction reasoning, programming, quant research, and machine learning.

## What Is Included

- `starter/`: an empty starter vault with domain standards, global governance docs, and CLI scripts.
- `docs/`: installation, usage, workflow, safety, and publishing notes.
- `examples/`: small sanitized examples that show import, review, and maintenance flows.

## What Is Not Included

- Private Obsidian notes.
- Raw source materials from your personal vault.
- Runtime state such as locks, JSONL queues, audit outputs, or local sync config.
- Credentials, API keys, cookies, or machine-specific paths.

## Quick Start

Copy the starter vault to your own location:

```bash
cp -R starter my-knowledge-vault
```

Run a diagnostic scan:

```bash
python my-knowledge-vault/00-global/scripts/kb.py --root my-knowledge-vault scan
```

Generate improvement suggestions without changing notes:

```bash
python my-knowledge-vault/00-global/scripts/kb.py --root my-knowledge-vault improve
```

After human review, generate a consolidated maintenance plan:

```bash
python my-knowledge-vault/00-global/scripts/kb.py --root my-knowledge-vault maintain plan
```

`maintain apply` is intentionally a safe stub in this version. It reports that apply is not implemented and does not modify notes.

## Recommended Daily Flow

1. Import material as a low-trust draft unless it has been reviewed.
2. Scan the vault for metadata, category, and governance issues.
3. Generate improvement candidates.
4. Record human decisions.
5. Generate a maintenance plan preview.
6. Apply changes only through a later explicit, checksum-verified workflow.

See [docs/workflow.md](docs/workflow.md) for the full flow.

## Safety Model

The toolkit is conservative by design:

- Scans and improvement loops are read-only by default.
- Review registries record decisions; they do not prove external truth.
- `reviewed` means useful within a human-approved scope.
- `verified` requires stronger evidence such as official docs, source code, experiments, backtests, or production results.
- Private knowledge should stay outside this public repository.

See [docs/safety.md](docs/safety.md) before publishing or syncing a vault.

## Repository Layout

```text
.
  README.md
  LICENSE
  docs/
  examples/
  starter/
```

## License

MIT. Use the toolkit freely, but review and adapt the rules before trusting it in high-risk domains.
