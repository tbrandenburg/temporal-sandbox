# AGENTS.md

Project-specific notes for agents working in this repository. See `docs/INITIAL.md` for the full
plan and architecture rationale.

## Lessons Learned

- 2026-08-26: The host `temporal` CLI fails with `context deadline exceeded` against
  `localhost:PORT` because `localhost` resolves to `::1` (IPv6) first while the dev server only
  binds IPv4. Always pass `--address 127.0.0.1:7233` explicitly (CLI invocations, Makefile
  targets, Docker healthchecks) — never bare `localhost`. Verify server connectivity issues
  against `127.0.0.1` before assuming the server itself is broken.
- 2026-08-26: A written implementation plan (`docs/INITIAL.md` §10) listed `make worker`/`make
  run`/`make ui` targets that later build steps never actually added, and this went unnoticed
  until the final documentation step cross-checked the plan against the real `Makefile`. When a
  plan enumerates specific interface surface (CLI flags, make targets, file paths), verify it was
  actually implemented — don't assume prior steps completed everything listed, especially for
  convenience wrappers that no test exercises directly.
