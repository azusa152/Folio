## Summary

<!-- What changed and why? Link to the relevant issue if applicable. -->

-
-

Closes #

## Type of change

- [ ] feature — new capability
- [ ] fix — bug fix (include regression test)
- [ ] refactor — no behaviour change
- [ ] docs — documentation only
- [ ] chore — dependency update, tooling, CI

## Test plan

<!-- How was this change verified? Tick all that apply. -->

- [ ] `make ci` passes locally
- [ ] Added / updated unit tests for new logic
- [ ] Manually tested in Docker (`make up` + browser or `curl`)
- [ ] `make seed-demo` still produces a working portfolio (if portfolio code changed)

## Checklist

- [ ] Relevant docs updated (README, ADR, agent docs, in-page help)
- [ ] `make generate-api` run and `openapi.json` committed (if backend schemas changed)
- [ ] No secrets added (`.env`, tokens, credentials, API keys)
- [ ] Architecture boundaries respected (`make ci` includes `test_architecture.py`)
