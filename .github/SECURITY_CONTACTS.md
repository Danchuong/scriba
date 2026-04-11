# Security Contacts

**Status:** pre-release stub. Scriba is not yet deployed in a public
mirror; this file will be populated when the GitHub repository goes
public. `SECURITY.md` references this file as the canonical contact
list.

## Reporting a vulnerability

Until the public mirror exists, security issues should be reported via
the private channels described in [`../SECURITY.md`](../SECURITY.md)
("Reporting a vulnerability"). Once the public mirror lands, switch to
GitHub Security Advisories (Settings → Security → Advisories → "New
draft advisory") on the mirror repository.

Do not open a public issue or PR for security reports.

## Coordinated disclosure SLA

| Phase                       | Target                               |
|-----------------------------|--------------------------------------|
| Initial acknowledgement     | within 2 business days               |
| Triage + severity assignment| within 5 business days               |
| Fix + disclosure (HIGH/CRIT)| within 90 days                       |
| Fix + disclosure (MED/LOW)  | within 180 days                      |

Severity is assigned using the categories in `SECURITY.md` "In scope"
(XSS/HTML injection, subprocess sandbox escape, resource-exhaustion cap
bypass, path traversal, Starlark sandbox escape). Findings outside that
list are still tracked, but usually handled on the normal release
cadence rather than under an embargoed advisory.

## Primary contacts

TODO — populate with GitHub usernames at public-release time.

At least two maintainers should be listed so that reports are never
gated on a single person being available. Rotate this list when
responsibilities change.

## Escalation

If a reported issue is not acknowledged within the SLA above, escalate
through the OJCloud private channel referenced in `SECURITY.md`.

## Last updated

2026-04-11 — Wave 4A Cluster 10 (pre-release stub).
