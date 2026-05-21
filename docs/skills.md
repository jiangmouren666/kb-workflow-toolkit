# Companion Skills

The CLI tools manage notes and maintenance reports. The companion skills tell an AI agent how to use the vault safely.

## Included Skills

### `kb-answer-with-citations`

Use this when asking the AI to answer from the knowledge base.

It requires the agent to:

- Read governance, routing rules, human-review registry, and domain standards.
- Prefer reviewed or registry-approved notes.
- Cite note paths for substantive claims.
- Separate source facts, inference, and uncertainty.
- Refuse to invent support when the vault does not contain enough evidence.

### `kb-import-and-maintain`

Use this when importing documents or maintaining the vault.

It requires the agent to:

- Save uncertain imports as low-trust drafts.
- Ask for human review when trust, placement, or future retrieval behavior changes.
- Run scan, improve, and maintain-plan flows safely.
- Avoid automatic note rewrites or trust upgrades.

## Install For Personal Use

```bash
mkdir -p ~/.cursor/skills
cp -R skills/kb-answer-with-citations ~/.cursor/skills/
cp -R skills/kb-import-and-maintain ~/.cursor/skills/
```

## Install For A Project

```bash
mkdir -p .cursor/skills
cp -R skills/kb-answer-with-citations .cursor/skills/
cp -R skills/kb-import-and-maintain .cursor/skills/
```

Project skills can be committed with the project so every agent working in that repository sees the same instructions.

## Example Prompts

```text
基于我的知识库回答这个问题，并给出引用路径
```

This should trigger `kb-answer-with-citations`.

```text
把这个 Obsidian 文档导入知识库，按低信任草稿处理
```

This should trigger `kb-import-and-maintain`.

## Why Skills Are Separate From CLI

The CLI checks files, produces reports, and records decisions. It does not control how an AI reads notes or cites evidence.

The skills cover the AI behavior layer:

```mermaid
flowchart TD
  userQuestion[UserQuestion] --> citationSkill[CitationSkill]
  citationSkill --> governance[GovernanceAndRegistry]
  citationSkill --> domainStandard[DomainStandard]
  citationSkill --> relevantNotes[RelevantNotes]
  relevantNotes --> citedAnswer[CitedAnswer]

  newMaterial[NewMaterial] --> importSkill[ImportSkill]
  importSkill --> draftNote[DraftNote]
  draftNote --> cliScan[CLIScan]
  cliScan --> maintainPlan[MaintainPlan]
```
