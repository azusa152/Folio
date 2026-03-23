# Folio

> **Audience:** External AI agents calling Folio's webhook API.
> For contributor/coding-assistant context (architecture, commands, key paths),
> see [`AGENTS.md`](../../AGENTS.md) at the repo root.

Self-hosted investment tracking. Backend: `http://localhost:8000`.

## Rules

- Keep responses concise and action-oriented.
- Branch on `error_code`, never on localized `detail`.
- For overview, start with webhook `dashboard`.
- For ticker deep-dive, use webhook `analyze` with `ticker`.
- If `is_rogue_wave=true`, warn about late-stage surge and avoid leveraged chasing.
- For market timing, use `fear_greed` and include JP/TW thresholds when relevant.
- For cash needs / what to sell, use `withdraw` with `amount` and `currency`.
- For asset review, use `analytics` then `insights`.
- For trade recording, use `add_transaction` with required `account_id`, `ticker`, `type`, `quantity`, `total_amount`, `date`; supported types: BUY/SELL/DIVIDEND/DEPOSIT/WITHDRAWAL/OPENING_BALANCE/ADJUSTMENT/TRANSFER_IN/TRANSFER_OUT.
- For NISA/iDeCo status, use `quota`; branch on `wrapper` field in response.
- For NISA contribution ledger review, use `GET /wrappers/contributions` with `wrapper`/`year` filters.
- NISA quotas use cost basis (簿價), not market value. Do not confuse the two.

## Auth

- If `FOLIO_API_KEY` is set, send `X-API-Key` header.
- If unset, dev mode is open (no API key required).

## Runtime Discovery

- Use webhook `help` to discover actions and recommended workflows.
- Use `docs/agents/folio/SKILL.md` for compact action guide.
- Use `docs/agents/folio/reference.md` only for detailed field specs.
