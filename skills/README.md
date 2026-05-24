# Companion Cursor Skills

These skills are optional companions for the starter vault.

- `kb-answer-with-citations`: guides an AI agent to answer from the vault with source paths, evidence level, uncertainty, and misuse boundaries.
- `kb-import-and-maintain`: guides an AI agent through import, human review, scan, improvement, and maintain-plan workflows.
- `kb-conversation-distiller`: guides an AI agent to manually distill reusable insights from conversations without saving full transcripts.

## Install

For personal use, copy a skill directory into your Cursor skills folder:

```bash
mkdir -p ~/.cursor/skills
cp -R skills/kb-answer-with-citations ~/.cursor/skills/
cp -R skills/kb-import-and-maintain ~/.cursor/skills/
cp -R skills/kb-conversation-distiller ~/.cursor/skills/
```

For a project, copy them into `.cursor/skills/` inside that project.

Do not install these skills if you do not want AI agents to read from or operate on your vault. The tools still require explicit file access and should follow the safety rules in `docs/safety.md`.
