# Publishing Checklist

Run this checklist before pushing the repository to GitHub.

## Content

- [ ] The repository contains `starter/`, `docs/`, and `examples/`.
- [ ] The repository contains `skills/` if publishing the AI behavior layer.
- [ ] The starter is usable without private source notes.
- [ ] Examples use synthetic or very short placeholder content.
- [ ] No private Obsidian vault content is included.
- [ ] No copyrighted long excerpts are included.
- [ ] No personal research notes are included unless deliberately published.

## Runtime State

- [ ] No `00-global/state/` directory is committed.
- [ ] No `*.jsonl` queues are committed.
- [ ] No `kb.lock` file is committed.
- [ ] No generated audit reports or maintenance reports are committed.

## Secrets And Paths

- [ ] No `.env` files are committed.
- [ ] No API keys, cookies, tokens, credentials, or passwords appear.
- [ ] No local private paths from your machine appear in examples or starter files.

## Verification

Run:

```bash
python starter/00-global/scripts/kb.py --root starter scan
python starter/00-global/scripts/kb.py --root starter improve
python starter/00-global/scripts/kb.py --root starter maintain status
```

Then search for risky strings:

```bash
rg "replace-this-with-your-private-path-or-source-title" .
```

The search should return no private material.
