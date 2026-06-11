# 21 — Integration Strategy

The prototype references a large external surface (BGV vendors, job boards, video/calendar, banks, statutory portals, e-sign, AI, accounting, comms, SSO). This strategy standardises how all of them connect.

## 21.1 Integration architecture

- **Adapter pattern per provider** behind a stable internal interface (e.g. `BgvProvider`, `BankPayoutProvider`, `EsignProvider`, `VideoProvider`). Swapping AuthBridge↔IDfy changes config, not code.
- **Integration Hub** (the control plane already models providers, connected tenants, failed syncs, webhooks, API keys, logs) governs credentials, health, direction (pull/push/bidirectional), and retry.
- **Outbox + event-driven**: outbound integrations triggered by domain events (offer.accepted → BGV initiate); idempotent, retried, dead-lettered.
- **Inbound webhooks** normalised at the edge into domain events (BGV result → `bgv.completed`).
- **Per-tenant credentials** in Vault; per-tenant enable/disable via entitlements.
- **Circuit breakers + backoff**; health surfaced in observability; `tenant.integration.failed` webhook on breach.

## 21.2 Integration catalogue

| Category | Providers (from design) | Direction | Trigger / pattern | Priority |
|----------|------------------------|-----------|-------------------|----------|
| **Identity / SSO** | OIDC/SAML IdPs, SCIM | bidirectional | login, provisioning | M0 |
| **E-signature** | Leegality, Digio, DocuSign (Aadhaar e-sign) | push + webhook | offer/onboarding/exit docs | M0/M4 |
| **Email/SMS/WhatsApp** | SES/Postmark, MSG91/Gupshup | push | notifications | M0 |
| **BGV** | AuthBridge, IDfy, OnGrid, SpringVerify, First Advantage, HireRight | push + webhook | offer accepted → checks | M4 |
| **Job boards** | LinkedIn, Naukri, Indeed, Monster, Foundit | bidirectional | post jobs / pull applicants | M4 |
| **Video interview** | Zoom, Meet, Teams, Webex | push | interview scheduled | M4 |
| **Calendar** | Google, Outlook (Graph) | bidirectional | interview slots, availability | M4 |
| **Banking (payouts)** | NEFT/RTGS H2H per bank, RazorpayX, Cashfree | push + reconcile | payroll bankfile → disburse → UTR | M3 |
| **Statutory portals** | EPFO (ECR), ESIC, TRACES (24Q/Form16), state PT | push/file | monthly/quarterly filings | M3 |
| **Accounting / ERP** | Tally, Zoho Books, SAP | push | payroll → GL journal | M3 |
| **Payments (billing)** | Stripe, Razorpay | bidirectional | PEPM invoices (control plane) | M0/TB1 |
| **Biometric devices** | ESSL, ZKTeco, cloud APIs | pull | attendance events | M2 |
| **AI / LLM** | Claude, OpenAI, Azure OpenAI (governed gateway) | push | JD gen, scoring, summaries, Pulse | M4/M7 |
| **Accounting of assets / procurement** | PO systems | push | asset request → procurement | M2/M6 |
| **Observability** | OTel collectors, SIEM | push | telemetry | M7 |

## 21.3 Canonical integration flows

**BGV (offer → vendor → adjudication):**
```
offer.accepted ─► BGV adapter: create case + push consent + checks
              ◄─ webhook: per-check results ─► bgv.check.completed events
              ─► adjudication workflow ─► bgv.case.cleared|discrepancy
```

**Payroll disbursement (bankfile → bank → reconcile):**
```
payroll.run.bankfile ─► BankPayout adapter: generate H2H file / payout API
                    ◄─ status + UTR webhook ─► reconcile bank_txn ─► run.paid
```

**Statutory filing:**
```
payroll.finalized ─► aggregate establishment-level ─► generate ECR/ESIC/PT/24Q artifacts
                  ─► (manual upload or portal API) ─► record challan_ref + evidence bundle
```

## 21.4 Public API & webhooks (inbound ecosystem)

- Public REST/GraphQL + webhooks let customers and partners integrate (HRIS data sync, custom apps, mobile).
- Sandbox environment (modeled in super-dev) for partner testing.
- API keys scoped per tenant; usage metered (feeds PEPM/usage billing).

## 21.5 Data import / migration

- The prototype includes import wizards (`AE_STEPS`, `BI_STEPS`: upload → column-map → validate → confirm). Productionise as:
  - Bulk import service (employees, candidates, leave balances, assets, comp) with **column mapping, validation, dry-run preview, partial-failure reporting, and rollback** (closes the gap that the wizards lack validation/rollback).
  - Reusable for tenant onboarding migrations.

## 21.6 Integration governance

- Every provider has: owner adapter, config schema, health check, retry/DLQ policy, audit, and a kill switch.
- Failed syncs queue + alert (control plane "Failed Syncs" tab).
- Versioned webhook payloads; HMAC-signed; replayable.
- Sub-processor DPAs tracked (security §20.5).
