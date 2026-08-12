# AGENTS.md

Guidance for agent tooling operating in this repository.

## Communication language

Prose and explanations are written in Bahasa Indonesia. Code, identifiers, and
technical terms (MQTT, Supabase, RLS, command, batch, session, ...) stay in
English. This applies to explanations, work summaries, commit messages, and
issue-tracker updates.

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Skills apply five canonical label strings to issues: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `CONTEXT.md` at the repo root plus `docs/adr/`. See `docs/agents/domain.md`.