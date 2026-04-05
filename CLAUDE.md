# Claude Code Instructions

## Git
- Never push to the remote repository unless the user explicitly says to push.
- Before pushing, print the diff summary (`git diff --stat HEAD~N HEAD` covering all commits being pushed) and confirm the file list looks right before proceeding.
- Before committing, run `git status` and verify no IDE/editor files or other unintended files are being staged.

## Actions requiring explicit human approval
- Pushing code to the remote repository.
- Modifying design documents (currently TODO.md). Describe the proposed change and ask first.

## Imports
- No function-level imports anywhere in the codebase except inside `create_app()` in `app/__init__.py`, where they are required to break circular imports.

## Validation
- UI guards (hiding buttons, disabling fields) are never a substitute for server-side validation. Any constraint enforced in the UI must also be enforced in the route handler.

## Retrospective hat
When asked to "put on your retrospective hat" or run a retro on the session, apply these lenses:
1. What mistakes did I (Claude) make, and why? What could be added to CLAUDE.md to prevent them next time?
2. What mistakes or habits did the user exhibit that cost time or quality? Be honest but constructive.
3. What slowed us down? Unnecessary back-and-forth, unclear requirements, tasks that had to be redone.
4. What did we defer that we probably shouldn't have? Technical debt accepted under pressure that will compound.
5. Did we over-engineer or over-specify anything? Time spent on things that didn't need it.
6. Did the tests give us genuine confidence, or just coverage? Were we testing the right things?
7. Where did communication break down? Misinterpreted instructions, repeated corrections, wrong assumptions.
8. What Claude features or workflows were available but unused that would have helped?
9. What would you tell a teammate starting this project tomorrow? Surfaces undocumented decisions and implicit knowledge.
10. Are there additions or corrections needed in CLAUDE.md based on this session?

Produce concrete, actionable takeaways — not a general summary. Flag proposed CLAUDE.md changes explicitly so the user can approve them.

## Reviewer hat
When asked to "put on your reviewer hat" or do an adversarial review, apply these lenses in order:
1. Does this actually do what it's supposed to do? Read the requirement, trace the code path, verify they match. Don't assume the author tested it.
2. What inputs, states, or sequences could break this that aren't tested?
3. What assumptions did the author make about callers or dependencies that aren't enforced?
4. What happens under failure — network down, DB error, empty result?
5. Are there missing server-side guards (UI-only validation)?
6. Is any dead code, unused import, or unreachable path present?
7. Does this introduce a security boundary crossing — unvalidated input, PII exposure, missing auth check?

Flag only genuine issues. Skip style, formatting, and nitpicks unless they indicate a real risk.

## Context management
- Warn the user when context usage exceeds 60% and suggest finding a checkpoint to /compact.

## Search and tooling
- Use Grep/Glob directly for targeted searches. Only spawn Explore agents for open-ended, multi-location exploration where the answer isn't a known pattern.
