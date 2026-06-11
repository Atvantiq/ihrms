# 20 — Security Architecture

The control plane already *models* the security posture (MFA, SSO/SAML, IP restrictions, sessions, impersonation, masking, secrets vault, incidents, AI governance, data residency, legal hold, DR). This document turns that model into an enforceable architecture. Drivers: enterprise procurement, **DPDP Act 2023 (India)**, **GDPR (EU)**, **SOC 2 Type II**, ISO 27001.

## 20.1 Identity & authentication

- **SSO-first**: OIDC + SAML 2.0; password is fallback only. Per-tenant IdP config (the control plane models SSO/SAML per tenant).
- **MFA**: TOTP/WebAuthn; step-up auth for sensitive actions (bank change, payroll approve, F&F pay, impersonation) — the design already routes bank changes HR-only and gates compensation by tiers.
- **SCIM 2.0** provisioning/deprovisioning from enterprise directories (closes gap G-S5); exit auto-deprovisions.
- **Session management**: short-lived JWT + rotating refresh; device/session registry (modeled in `SA_SESSIONS`); forced logout; idle + absolute timeouts; IP allowlists per tenant.

## 20.2 Authorization (RBAC + ABAC)

- **Role → capability → scope** model (§18.2). Scope ∈ {self, team, dept, location, establishment, tenant}.
- **Policy engine** (OPA/Cedar) externalises authorization; every API call passes `(subject, action, resource, context)` to a decision point.
- **Field-level masking**: salary, PAN, Aadhaar, bank masked unless role+scope permits; enforced server-side, not UI-only (closes the prototype's UI-only gating).
- **Segregation of duties**: approver ≠ requester; maker ≠ checker on payroll; enforced as policy (closes G-RBAC-2/G-S10).
- **Delegation**: bounded by type + window; acting approver recorded; principal accountable.

## 20.3 Tenant isolation

- **Postgres RLS** binds every query to the session `tenant_id` — a hard backstop beyond app logic.
- **Region pinning**: tenant data physically resides in its region's cluster (India/EU/US); no cross-region movement; gateway routes by tenant→region.
- **Large-tenant option**: dedicated schema/DB for isolation-sensitive enterprises.
- **No ambient cross-tenant access.** Platform-operator access only via §20.6.

## 20.4 Data protection

| Layer | Control |
|-------|---------|
| In transit | TLS 1.3 everywhere; mTLS service-to-service. |
| At rest | Disk/volume encryption + **app-layer envelope encryption (KMS)** for high-sensitivity PII (Aadhaar, PAN, bank, salary). |
| Key mgmt | KMS + **HashiCorp Vault** (control plane models a secrets vault); rotation; dynamic DB creds. |
| Masking | Dynamic masking by role; deterministic tokenization where joins needed. |
| Backups | Encrypted, region-local, tested restores (sandbox-first, dual-approval — modeled in control plane). |
| Secrets | Never in code/env files; Vault-issued; audited access. |

## 20.5 Privacy & compliance (DPDP / GDPR)

- **Consent records** (`consent_record`) captured at candidate stage and for BGV data sharing; purpose-bound; expiry; evidence retained.
- **Data subject rights**: export (`data_export_request`), rectification, erasure — gated by **legal hold** and statutory retention (e.g. payroll records 7 yrs).
- **Retention policies** per data class, centrally governed; automated deletion after retention + no-hold.
- **Data residency** enforced per tenant region.
- **Processor/sub-processor register** (BGV vendors, banks, e-sign, AI) with DPAs.
- **PII minimisation & redaction** in logs, analytics, and AI prompts.

## 20.6 Privileged access & impersonation

- Platform-operator "login-as" requires an **approved, time-boxed, reason-logged** impersonation session with **mandatory data masking** (modeled in `SA_IMPERSONATIONS`: `pending_approval → active → completed/denied`).
- All impersonation actions tagged in audit as operator-on-behalf; tenant admins can view operator access history.
- Break-glass procedures with dual-approval and automatic post-incident review.

## 20.7 Audit & evidence

- **Immutable, append-only audit** (`audit_event`) with **hash-chaining** (each row hashes the previous) → tamper-evident; archived to WORM object storage; 7-yr retention (closes G-F6/G-S4).
- Every mutating action and every workflow transition emits an audit event with before/after.
- **Evidence bundles** for compliance acknowledgements and statutory filings (modeled in control plane).
- Critical actions emit `audit.critical-action.logged` webhook.

## 20.8 AI governance (from control-plane model)

- All AI calls routed through a **governed gateway** enforcing: per-tenant **policies**, **token budgets**, **PII redaction** before provider calls, **kill switches**, model allowlists, and **AI audit** of prompts/responses.
- No tenant data leaves to a provider without redaction + policy check; budget threshold → webhook + throttle.

## 20.9 Application security

- OWASP ASVS baseline; input validation framework (closes G-F9); output encoding; parameterized queries (RLS + ORM).
- Rate limiting + WAF + bot protection at the gateway; per-tenant quotas.
- File uploads: type/size validation + **AV scanning** + isolated storage + signed URLs.
- Dependency scanning (SCA), SAST/DAST in CI, secret scanning, container image signing.
- CSRF protection, secure cookies, CSP, HSTS for web.

## 20.10 Operational security

- **Observability/SIEM**: security events streamed to SIEM; anomaly detection on impersonation, mass-export, off-hours payroll/F&F changes.
- **Incident management & RCA** (modeled in control plane: incidents, RCA); status page + comms (closes G-S6).
- **DR**: defined RPO/RTO; periodic DR tests (modeled); backup verification.
- **Pen-testing** and red-team before GA; bug bounty post-GA.

## 20.11 Compliance mapping

| Control | DPDP | GDPR | SOC2 | ISO 27001 |
|---------|------|------|------|-----------|
| Consent & purpose | ✔ | ✔ (lawful basis) | — | A.18 |
| Residency | ✔ | ✔ (transfer) | — | — |
| Encryption/KMS | ✔ | ✔ | CC6 | A.10 |
| RBAC/SoD | — | ✔ | CC6 | A.9 |
| Immutable audit | ✔ | ✔ | CC7 | A.12 |
| Retention/erasure | ✔ | ✔ (RTBF) | — | A.18 |
| Impersonation control | — | ✔ | CC6 | A.9 |
| DR/backup | — | ✔ (availability) | A1/CC | A.17 |
| Vendor/DPA register | ✔ | ✔ (Art.28) | CC9 | A.15 |

## 20.12 Security build priorities (tie to roadmap)

1. **M0**: SSO/MFA, RBAC+policy engine, RLS isolation, audit service, secrets vault, encryption, validation framework.
2. **M1**: consent lifecycle, field masking, SCIM.
3. **M3**: maker-checker on payroll, step-up auth on money actions.
4. **M7**: pen-test, SIEM, DR drills, status page, SOC2 audit readiness.
