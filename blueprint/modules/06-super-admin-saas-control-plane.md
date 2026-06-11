# Module: Super-Admin / SaaS Control Plane

> Reverse-engineered from `atvantiq-people-prototype_2.html` (JS from line 1255). Product name in-app: **HCMPulse Control Center**. All `super-*` screens are gated by the platform role model (`SA_ROLES`, ~1324). Navigation: `NAV_DEFAULT.super='super-dashboard'`. `applySaRoleVisibility()` hides nav items unless `saRole==='owner'` or the item's `data-sa-role` allowlist contains the active role (or `all`).

Persona/role infra:
- `currentRole` toggles `company` ⇄ `super` via `toggleRole()`. `saRole` cycles via `cycleSaRole()`. `saRoleObj()` resolves active role.
- Global audit helper: `saAudit(action, tenant, detail)` pushes `{time, actor:'rohit@atvantiq.com', role, tenant, action, detail}` onto `SA_AUDIT_LOG` (in-memory array, starts empty).
- Global reusable drawer: `openSaDrawer(title,status,statusColor,meta,timeline,actions)` — meta grid + timeline pills + action buttons. `closeSaDrawer()`.
- Helpers: `saHealthColor(h)` → green≥90 / amber≥70 / rose>0 / mute. `saStatusColor(s)` → {active:green, attention:amber, trial:blue, suspended:rose, archived:mute}. `saPageHead(title,sub,actions)`. `twMeta(rows)` 2-col meta grid.

---

## Screen-by-Screen Audit

### 1. super-dashboard — "HCMPulse Control Center"
- **Purpose:** Platform operations landing; KPI bento + AI Platform Pulse + tenants table + recent activity feed.
- **Actors:** `all` roles (nav `data-sa-role="all"`).
- **Inputs:** hard-coded aggregate counters (tenants {total:12,active:11,trial:1,suspended:0}, users 3847, employees 3420, mrr 1,840,000, arr=mrr*12, failedInt 2, compliancePending 3, openTickets 7, secAlerts 0, aiUsagePct 72, storageGB 142, apiToday 48200).
- **Outputs/UI Elements:**
  - Page head: title, sub "`${total} tenants · ${users} users · all systems nominal`", pill `● Production`, buttons **Audit log** (→super-audit), **+ New tenant** (toast).
  - **AI Platform Pulse** ai-tile: 6 clickable insight rows (employee-limit upsell→tenants; compliance ack→compliance; 2 payroll integrations failed→integrations; 1 release rollback v4.8.1→releases; AI usage 80% budget→ai; NimbusCo trial expires 12 days→billing).
  - 4 KPI bento rows (`saCard(label,value,color,onclick)`): Total/Active/Trial/Suspended tenants; Active users/Employees managed/MRR (₹L)/ARR (₹Cr); Failed integrations (opens drawer)/Compliance pending (drawer)/Open tickets/Security alerts; AI usage (drawer)/Storage GB/API calls today (k)/Release health (✓ v4.8.2).
  - **Tenants** mini-table: Company | Employees | Plan | Last payroll | Status (4 hardcoded rows; row click → openSaDrawer with Impersonate action).
  - **Recent activity** feed: 6 items (compliance, integrations, billing, releases, security) → navigate super-<area>.
- **Actions:** navigate to sub-screens, open drawers, `showToast`.
- **Permissions:** visible to all SA roles.

### 2. super-tenants — "Tenant Registry"
- **Purpose:** Tenant registry + per-tenant workspace drawer.
- **Actors:** owner, ops, support.
- **State:** `saTenantFilter='all'`, `saTenantDrawer` (tenant id), `saTenantTab='profile'`.
- **Inputs/filters:** filter pills `['all','active','trial','attention','suspended','expiring']`; expiring = `renewal<'2026-09-01' && renewal!=='—'`.
- **UI Elements:** page head with **Export** (CSV toast), **Clone** (`saCloneTenant()`), **+ Create tenant** (`saCreateTenant()`); 5 KPI tiles (Total/Active/Trial/Suspended/Expiring soon, each sets filter); table columns: **ID, Company, Industry, Plan, Employees, Users, Modules (n/15), Version, Health (%), Renewal, Status**. Plan pill color by tier; health color by `saHealthColor`; status pill by `saStatusColor`.
- **Actions:** `saCreateTenant()` opens form schema `sa-tenant-create`; `saCloneTenant()`; row → opens `renderTenantWorkspace()`.
- **Business Rules:** module count capped 0..15. New tenant id = `TN-###` zero-padded from length+1.
- **Dependencies:** `SA_TENANTS`, `SA_MODULES`, `TA_FORM_SCHEMAS`.

**Tenant Workspace Drawer** (`renderTenantWorkspace`) — tabs: **Profile, Subscription, Modules, Users, Health, Support, Audit**. Header buttons: **Login as ↗** (`showToast` impersonate admin), **Sandbox** (`saCreateSandbox`). Footer: **Suspend**/**Activate** (toggle), **Archive**, **Close**.
- *Profile* (`twProfile`): Legal name, Display name, Country·Region, Industry, Admin, Billing contact, GST/Tax ID, Workspace URL, Data region, Deployment stamp, Environment=Production, Tenant ID.
- *Subscription* (`twSubscription`): Current plan, Contract start/end, PEPM rate (₹/mo or "Internal"), Billing cycle=Monthly, Min commitment (200 employees if emp>200), Add-ons, Overage rule="110% then alert", Renewal risk (High if renewal<2026-09-01). Buttons **Change plan**, **Renew**.
- *Modules* (`twModules`): grid over `SA_MODULES` (15) with toggle switches; label "Add-on"/"Included in plan"/"Not enabled"; `saToggleModule(tid,mod,enable)`.
- *Users* (`twUsers`): role breakdown Admin 1, HR 4, Manager 12, Finance 3, IT 2, Employees=users-22.
- *Health* (`twHealth`): Health score, Uptime 99.98%, Last incident, Payroll success 98.2%, API p95 124ms, Error rate 0.04%; recent events list.
- *Support* (`twSupport`): tickets (Payroll timeout/Custom report).
- *Audit* (`twAudit`): filtered SA_AUDIT_LOG entries for this tenant + synthetic events.

### 3. super-plans — "Plans & Product Catalog"
- **Actors:** owner, ops, billing, release.
- **State:** `saPlansTab='plans'`, `saPlanDrawer`, `saEntitlementMode`.
- **Tabs:** **Plans, Module Catalog, Entitlements, Compare Plans, Add-ons, Trials**.
  - *Plans* (`renderSaPlans`): table Plan | Pricing | Employees | Modules | AI tier | API | Support | Storage | Tenants | Status. Plan drawer (`renderPlanDrawer`) shows full meta + included modules + tenants on plan + **Edit plan**.
  - *Module Catalog*: 15 modules grid, "Included in N plans · v4.8.2".
  - *Entitlements* (`renderSaEntitlements`): Module × Plan matrix; cells Included/Add-on/—; click → `saAudit('Edit entitlement')`.
  - *Compare Plans*: feature-by-feature comparison table.
  - *Add-ons* (`renderSaAddons`): AI Pulse ₹15, API Access ₹10, Mobile App ₹8, Workflow Engine ₹12, Advanced Analytics ₹20 (per emp/mo).
  - *Trials* (`renderSaTrials`): active trials with Convert button (`saAudit('Convert trial')`).
- **Create flow:** header **+ Plan** opens plan builder (toast).

### 4. super-releases — "Release Management"
- **Actors:** owner, ops, release.
- **State:** `saRelTab='dashboard'`, `saFlagDrawer`, `saFlagDrawerTab='overview'`.
- **Tabs:** **Dashboard, Feature Flags, Version Rings, Rollouts, Rollbacks, Beta Programs, Release Notes**.
  - *Dashboard*: current version v4.8.2, flag counts, active rollouts, rollbacks available; Releases table (Version|Ring|Date|Tenants|Notes|Status).
  - *Feature Flags* (`renderRelFlags`): "LaunchDarkly-style targeting"; table Flag key|Module|Env|Status|Rollout|Targeting|Variation|Changed + toggle switch. Row → `renderFlagDrawer`.
  - *Version Rings* (`renderRelRings`): 7 rings grid + Tenant Ring Assignments table with **Change ring**.
  - *Rollouts* (`renderRelRollouts`): partial-rollout flags (0<rollout<100), progress bar, **+25%** / **100%** buttons.
  - *Rollbacks*: dark-mode→Off (Low/Auto), ai-pulse-v2→Off (Medium/Release Manager), v4.8.2→v4.8.1 (High/Platform Owner).
  - *Beta Programs*: AI Pulse V2 Beta, Payroll Autopilot.
  - *Release Notes*: cards per release.
- **Flag drawer** tabs: **Overview, Targeting, Rollout, Prerequisites, Tenants, Audit, Kill Switch**. Targeting dimensions: Tenant, Plan, Country, Region, Industry, Employee count, Module enabled, Beta group, Custom attribute. Rollout presets 0/10/25/50/75/100%. Kill Switch (`saKillFlag`): disables for all tenants, rollout→0, requires audit note.
- **Actions:** `saToggleFlag`, `saRolloutInc`, `saRollout100`, `saSetRollout`, `saKillFlag`.

### 5. super-billing — "Billing & Metering"
- **Actors:** owner, billing.
- **State:** `saBillingTab='overview'`, `saInvoiceDrawer`.
- **Computed:** mrr = Σ(pepm×employees) for non-suspended non-Internal; outstanding/overdue/paidMonth from `SA_INVOICES`.
- **Tabs:** **Overview, Subscriptions, Metering, Invoices, Payments, Disputes, Revenue**.
  - *Overview*: MRR/ARR/Outstanding/Overdue, Paid this month/Trials converting/Failed payments(attempts≥2)/Usage overage; Recent invoices + Metering alerts.
  - *Subscriptions*: Tenant|Plan|PEPM|Employees|Monthly|Contract end|Add-ons|Status.
  - *Metering* (`renderBillingMetering`): meters table Tenant|Meter|Period|Quantity|Limit|Overage|Status; row drawer.
  - *Invoices*: Invoice|Tenant|Period|Plan|Amount|GST|Total|Due|Status + View.
  - *Payments*: paid invoices only, gateway ref, attempts.
  - *Disputes*: "No active disputes".
  - *Revenue*: MRR/ARR/Avg rev per tenant + Revenue by plan (% of MRR).
- **Invoice drawer** (`renderInvoiceDrawer`): meta + line items (PEPM, GST@18%, Total). Buttons: **Mark as paid** (`saMarkPaid` → gateway RZP-MANUAL), **Send reminder**, **Credit note** (`saIssueCreditNote`), **Download PDF**, **Refund** (`saRefundInvoice`, paid only).

### 6. super-compliance — "Compliance Hub"
- **Actors:** owner, ops, compliance.
- **State:** `saCompTab='overview'`, `saCompDrawer`, `saCompDrawerTab='summary'`.
- **Tabs:** **Overview, Compliance Packs, Versions, Impact Analysis, Publish Queue, Acknowledgements, Evidence Bundles, Legal Sources, Rollback History**.
  - *Overview*: Compliance AI tile (DPDP approved pending publish; 3 tenants not acked EPF Q2; Min Wages H1 draft needs legal review; State Holidays 100% acked) + KPIs (Active packs, Draft updates, Pending ack, High-risk alerts, Evidence bundles=8, Legal sources, Failed pushes=0, Upcoming effective=2).
  - *Packs* (`renderCompPacks`): ID|Law|Country|State|Version|Effective|Modules|Tenants|Ack %|Risk|Status; **+ Pack**.
  - *Versions*: per-pack version, status, impact, rollback availability.
  - *Impact Analysis*: affected tenants/employees(3,420)/modules/risk + impacted modules + recommended actions (publish to sandbox first, schedule effective date, notify owners, prepare rollback).
  - *Publish Queue*: packs in draft/legal_review/approved with **Sandbox**, **Schedule**, **Publish**.
  - *Acknowledgements*: pending published packs, progress bar, **Remind** / **Send all reminders**.
  - *Evidence Bundles*: EVD-2026-Q2/Q1/2025-Annual, Download.
  - *Legal Sources*: Gazette/Circular per pack.
  - *Rollback History*: PT v2026.Q1→v2025.Q4 (Karnataka slab error), ESIC v2025.2→v2025.1.
- **Pack drawer** tabs: **Summary, Versions, Applicability, Modules, Tenants, Source, Evidence, Audit**. Footer **Publish**/**Rollback** + **Edit**.
- **Publish wizard** (`saCompPublishWizard`): 7 steps — Select version → Cohort → Impact → Date → Template → Approve → Publish.
- **Actions:** `saCompPublishPack` (→ tenants=12, ackPct=0), `saCompPublishSandbox`, `saCompSchedule`, `saCompRollback`.

### 7. super-statutory — "Statutory rates · master library"
- **Actors:** owner, ops, compliance.
- **Purpose:** Source-of-truth for India statutory rates (`STATUTORY_RATES`, `STATUTORY_RATES_HISTORY`). Page head shows FY, last synced, next review.
- **UI:** EPFO notification ai-tile (employer 12%→11.5% effective 1 Jun 2026) with **Apply & push to all tenants** / **Review per tenant** / **Snooze**. KPIs: Active tenants 12, Rate parameters (n + critical count), Last change 15 Jan, Pending changes 1.
- **Sections (grouped by `section`):** EPF, ESI, Income tax, Deduction caps, Gratuity, Perquisite — each a table Parameter|Field|Value|Effective from|Criticality + **Edit** (effective-dated). Plus **Income tax slabs** (new+old regime), **Surcharge schedule**, **Change history** (effective-dated audit trail Field|From|To|Effective from|Source|Note).
- **Buttons:** **Export rates JSON**, **Push to all tenants** (syncs to 12 tenants in 60s).

### 8. super-announcements — "Announcement Center"
- **Actors:** owner, ops, compliance.
- **State:** `saAnnTab='all'`, `saAnnDrawer`.
- **Tabs:** **All, Drafts, Scheduled, Published, Templates, Analytics**.
- **UI:** KPIs Published/Scheduled/Drafts/Total reach; list table Title|Type|Audience|Channels|Date|Reads(reads/sent)|Status + inline **Publish** for drafts.
  - *Templates*: 7 reusable templates (Platform update, Compliance alert, Payroll alert, Security alert, Feature release, Maintenance window, Billing notice).
  - *Analytics*: total announcements, reach, read rate, performance by type.
- **Announcement drawer:** meta + preview + Publish now/Schedule/Edit/Duplicate.
- **Create wizard** (`sa-announcement-create`): 7-step Type → Audience → Message → Channels → Schedule → Preview → Publish. Fields: title, type, audience, channels, message body, schedule.

### 9. super-templates — "Template Marketplace"
- **Actors:** owner, ops, release.
- **State:** `saTplTab='all'`, `saTplDrawer`, `saTplFilter='All'`.
- **Tabs:** **Global Templates, HR, Payroll, Performance, Workflow, Compliance, Documents, Tenant Installs**. Category filter pills = `TPL_CATS`.
- **UI:** KPIs Total/Active/Draft/Total installs; table Name|Category|Type|Version|Installs|Modules|Updated|Status + inline **Install**.
- **Template drawer:** meta + installed-by tenants; buttons **Install to tenant**, **Duplicate**, **+ Version**, **Deprecate**/**Reactivate**.
- **Actions:** `saInstallTemplate`, `saDeprecateTemplate`, `saReactivateTemplate`.

### 10. super-integrations — "Integration Registry"
- **Actors:** owner, ops, support.
- **State:** `saIntTab='providers'`, `saIntDrawer`, `saIntDrawerTab='overview'`.
- **Tabs:** **Providers, Connected Tenants, Failed Syncs, Webhooks, API Keys, Logs**.
- **UI:** KPIs Providers/Healthy/Failed/Webhooks active; providers table Provider|Category|Auth|Status|Global|Tenants|Error %|Last sync|Webhooks + inline Retry/Pause/Resume.
  - *Webhooks*: endpoint `https://api.hcmpulse.in/hooks/<id>`, events "sync, error, status".
  - *API Keys*: prefix-masked keys (sk_live_…) with Rotate.
  - *Logs*: 24h sync log Time|Provider|Tenant|Event|Status|Duration.
- **Provider drawer** tabs: **Overview, Tenants, Auth, Webhooks, Sync Logs, Errors, Audit**. Footer Retry/Pause/Resume.
- **Actions:** `saRetryInt`, `saPauseInt`, `saResumeInt`.

### 11. super-security — "Security Center"
- **Actors:** owner, security.
- **State:** `saSecTab='overview'`, `saImpDrawer`.
- **Tabs:** **Overview, MFA, SSO / SAML, IP Restrictions, Sessions, Login-as, Data Masking, Secrets Vault, Incidents**.
  - *Overview*: MFA coverage 94%, Failed logins 24h=23, Active sessions, Login-as requests pending, High-risk admins=2, Secrets expiring=3, Security incidents=0, Tenants w/o SSO=4 + Security AI tile.
  - *MFA*: enforcement table (Platform users 100%, Tenant admins 94% Partial, Employees 62% Optional) + step-up MFA risky actions grid (Refund invoice, Compliance publish, Tenant suspension, Login-as write mode, Feature rollback, Backup restore, AI kill switch).
  - *SSO/SAML*: Azure AD/Okta/Google Workspace/OneLogin (SAML 2.0/OIDC/OAuth 2.0) + **Test**.
  - *IP Restrictions*: allowlist CIDR + geo + enforced.
  - *Sessions* (`SA_SESSIONS`): User|Role|Device|Location|IP|Started|Last activity|Status + **Revoke** (`saRevokeSession`).
  - *Login-as* (`SA_IMPERSONATIONS`): "Default read-only. Write mode requires approval. All sessions audited. Data masking on by default." Table Actor|Tenant|User|Mode|Duration|Masking|Ticket|Status + **Approve**. Imp drawer shows reason, ticket, actions performed; **Approve**/**Deny**/**Export evidence**.
  - *Data Masking*: PII fields (Aadhaar, PAN, Bank account, Salary/CTC, Phone, Email partial, Address, Medical records) all masked.
  - *Secrets Vault*: name/type/scope/expires/status + **Rotate**.
  - *Incidents*: brute force/suspicious login/cert expiry with severity.
- **Actions:** `saRevokeSession`, `saRequestLoginAs`, `saApproveLoginAs`, `saDenyLoginAs`.

### 12. super-ai — "AI Governance"
- **Actors:** owner, ai.
- **State:** `saAiTab='overview'`, `saAiKillTarget`.
- **Tabs:** **Overview, Providers, Models, Tenant Policies, Prompt Templates, Token Budgets, AI Usage, Redaction, AI Audit, Kill Switches**.
  - *Overview*: AI-enabled tenants, Monthly tokens, AI cost ₹1.73L, Budget breaches (used/cap>0.9); Disabled tenants, Prompt templates, Flagged outputs=1, Active kill switches=0.
  - *Providers*: Anthropic (Primary: Sonnet 4, Haiku 4.5), OpenAI (Secondary: GPT-4o), Google Gemini (standby), Azure OpenAI (standby), Local Model (not configured).
  - *Tenant Policies* (`SA_AI_POLICIES`): Tenant|Enabled|Providers|Token cap|Used|PII redact|Store prompts + Enable/Disable.
  - *Prompt Templates* (`SA_PROMPT_TEMPLATES`): Template|Module|Version|Owner|Tenants|Updated.
  - *Token Budgets*: cap/used/remaining/usage % progress bar.
  - *Kill Switches*: scopes — All platform AI, By tenant, By module, By provider, By model, By region; each logged + audit note.
- **Actions:** `saEnableAI`, `saDisableAI`, `saAiKillSwitch`.

### 13. super-support — "Support Center"
- **Actors:** owner, ops, support.
- **State:** `saSupTab='tickets'`, `saTicketDrawer`.
- **Tabs:** **Tickets, Tenant Health, Impersonation Requests, Incidents, RCA, Customer Notes**.
- **UI:** KPIs Open tickets/Avg response 2.4h/Escalated/P1 open; tickets table ID|Tenant|Severity|Category|Summary|Owner|SLA|Status (`SA_TICKETS`).
- **Ticket drawer:** meta + summary + timeline; buttons **Login-as ↗**, **Link to integration**, **Resolve**.

### 14. super-audit — "Audit & Logs"
- **Actors:** owner, security, compliance, auditor (read-only).
- **State:** `saAuditFilter='all'`.
- **Purpose:** "Immutable platform audit trail · 7-year retention". Combines `SA_AUDIT_LOG` + 10 synthetic events.
- **UI:** KPIs Total events / Today / High-risk actions (Kill/Suspend/Refund/write mode) / Retention 7 years; filter pills `['all','compliance','security','billing','login-as','feature','tenant','system']`; table Time|Actor|Role|Tenant|Action|Detail; row → drawer with Before/After diff placeholder + **Export evidence**.
- **Buttons:** **Export** (CSV), **Evidence bundle**.

### 15. super-observability — "Observability"
- **Actors:** owner, ops, support.
- **State:** `saObsTab='health'`.
- **Tabs:** **System Health, Jobs, Queues, API Logs, Integration Logs, Payroll Runs, Error Trends, Uptime**.
- **UI:** KPIs Uptime(30d) 99.97%, Failed jobs 24h=3, Queue backlog=12, API p95 142ms, Error rate 0.03%, Failed webhooks=4, Slow tenants=0, Payroll failures=1.
  - *System Health*: services table (API Gateway, Worker nodes, DB primary/replica, Redis, CDN, Email, SMS gateway=degraded) — Status|p95|Error rate|Pods|CPU|Memory.
  - *Jobs*: recent jobs Job|Tenant|Started|Duration|Status. Other tabs are placeholder "metrics and log aggregation view".

### 16. super-data — "Data Governance & Backups"
- **Actors:** owner, security.
- **State:** `saDataTab='retention'`.
- **Tabs:** **Retention, Residency, Data Export, Legal Hold, Deletion, PII Masking, Evidence, Backup Policies, Restore, DR Tests**.
- **UI:** KPIs Last backup Today 04:00, Retention 7 years, Storage 142 GB, Export requests=2; **Run backup**, **+ Export**.
  - *Retention*: datasets (Employee 7y, Payroll 8y, Attendance 3y, Audit logs 7y, AI prompts 90d, Documents 7y, Support tickets 5y, Backups 1y) with auto-purge/legal-hold.
  - *Backup Policies*: Full platform/Database/Documents/Audit logs — frequency, retention, last backup, last restore test.
  - *Restore*: "All restores go to sandbox first. Production restore requires dual approval (Platform Owner + Security Admin)." Restore requests table + **+ Restore to sandbox** (`saRestoreToSandbox`). Other tabs placeholder.

### 17. super-dev — "Developer Center"
- **Actors:** owner, release.
- **State:** `saDevTab='apikeys'`.
- **Tabs:** **API Keys, Webhooks, Events, API Usage, Documentation, Sandbox**.
  - *API Keys*: per-tenant keys with scope (e.g. `payroll:read,write`, `all:admin`) + **Rotate**.
  - *Webhooks*: `SA_WEBHOOK_EVENTS` (9 event types) with subscribers/last fired/status.
  - *Events*: recent delivery log Event|Tenant|Time|Delivered|Status. Docs/Sandbox placeholders.

### 18. super-settings — "Platform Settings"
- **Actors:** owner only.
- **State:** `saSettingsTab='countries'`.
- **Tabs:** **Countries, Currencies, Languages, Time Zones, Industries, Defaults, Notifications, Branding, Environment, Security Defaults, AI Defaults, Compliance Defaults**.
  - *Countries*: India/UAE/Singapore/USA/UK (code, region, currency, timezone, status).
  - *Currencies*: INR/AED/SGD/USD/GBP.
  - *Industries*: 10 industries.
  - *Defaults*: Default plan Starter, Default role Company Admin, Default timezone IST, Default currency INR, Default language English, Trial duration 30 days, Password policy "Min 12 chars + MFA", Session timeout 8 hours, Support SLA P1 1h / P2 4h, Data region ap-south-1, Backup frequency Daily 04:00. Remaining tabs use `saSettingsGeneric` (6 placeholder rows).

---

## Entities (Data Model)

### SA_TENANTS (`TN-###`)
`id, name, industry, country, region, plan, status, employees, users, modules, version, health, renewal, lastLogin, admin, billing, gst, workspace, dataRegion, stamp, contract_start, contract_end, pepm, addons[], color`
- `status` enum: **active | attention | trial | suspended | archived**.
- `plan`: Free/Starter/Growth/Premium/Professional/Enterprise/Enterprise+/Custom/Internal.
- `dataRegion`: ap-south-1, me-central-1, ap-southeast-1. `stamp` (deployment): IN-1, IN-2, ME-1, SG-1.
- `health` 0..100; `modules` 0..15. `addons`: ['AI Pulse','API Access','Mobile App','Workflow Engine'].

### SA_MODULES (15)
Core HR, Talent Acquisition, Payroll, Attendance, Leave, Timesheet, Assets, Performance & Growth, Exit & F&F, Helpdesk, Learning, Pulse AI, Workflow Engine, API Access, Mobile App.

### SA_INVOICES (`INV-YYYY-###`)
`id, tenant, period, plan, amount, gst, total, status, due, gateway, attempts`
- `status`: **pending | paid | overdue**. GST @18%. `gateway`: RZP-#### / RZP-MANUAL / —.

### SA_METERS
`tenant, meter, period, qty, limit, overage, amount, status` — `meter`: Employee count, AI tokens, Payroll runs, API calls, Storage GB, SMS messages. `status`: **nominal | warning**.

### SA_PLANS
`code, name, pepm, minEmp, maxEmp, modules[], addons(bool), ai, aiLabel, api(bool), support, storage, billing, status, tenants, color, combo, contactSales`
- `code`: FREE, STARTER, GROWTH, PREMIUM, ENTERPRISE. `ai`: basic/lite/standard/full. `status`: active | coming_soon. (Note: plan **names** in SA_TENANTS, e.g. "Internal", may not match SA_PLANS — see Gaps.)

### SA_FEATURE_FLAGS
`key, module, desc, env, status, rollout, targeting, variation, created, changed, prereq`
- `env`: production | staging. `status`: **on | off | beta**. `rollout` 0..100. `prereq`: another flag key or null.

### SA_RELEASES
`version, ring, date, tenants, status, notes` — `ring`: Stable/Beta/Archived. `status`: **live | staged | archived**.

### SA_VERSION_RINGS (7)
Internal, Alpha, Beta, Early Access, Stable, Enterprise Locked, Custom Tenant.

### SA_COMP_PACKS (`CP-###`)
`id, law, short, country, state, jurisdiction, version, effective, effectiveTo, status, modules[], source(bool), tenants, ackPct, risk`
- `status` ∈ **COMP_STATUSES** = draft, legal_review, sandbox_preview, impact_analysis, approved, published, acknowledged, archived. `risk`: low | medium | high. Laws: EPF, ESIC, PT, LWF, POSH, DPDP, CERT-In, Gratuity, Bonus, Minimum Wages, Shops & Establishment, State Holidays.

### SA_ANNOUNCEMENTS (`ANN-###`)
`id, title, type, audience, channels[], status, date, author, reads, sent`
- `type`: Maintenance, Feature release, Compliance alert, Platform update, Payroll alert, Security alert, Billing notice. `channels`: In-app, Email, SMS. `status`: **draft | scheduled | published**.

### SA_TEMPLATES (`TPL-###`)
`id, name, cat, type, version, installs, status, updated, modules[]`
- `cat` ∈ TPL_CATS (HR, Performance, Payroll, Leave, Assets, Compliance, Workflow, Document). `type`: Document, Workflow, KRA/KPI, Policy, Structure, Checklist. `status`: **active | draft | deprecated**.

### SA_INT_PROVIDERS (`INT-###`)
`id, name, cat, auth, status, global(bool), tenants, errorRate, lastSync, rateLimit, webhooks(bool)`
- `auth`: OAuth 2.0 | API Key. `status`: **healthy | error | paused**. cats: Productivity, Communication, Project Management, ITSM, Accounting, Payments, SMS, SMS/Voice, Messaging, AI, ERP.

### SA_SESSIONS (`SES-###`)
`id, user, role, device, location, ip, started, lastActivity, status` — `status`: **active | idle | revoked**.

### SA_IMPERSONATIONS (`IMP-###`)
`id, actor, tenant, user, reason, ticket, duration, mode, masking(bool), status, date, actions[]`
- `mode`: **read-only | write**. `status`: **completed | pending_approval | active | denied**.

### SA_AI_POLICIES
`tenant, enabled, providers[], models[], tokenCap, used, pii, storePrompts, optOut, review`

### SA_PROMPT_TEMPLATES (`PT-###`)
`id, name, module, version, owner, updated, tenants` — owner: Product/Finance/Legal.

### SA_TICKETS (`TKT-###`)
`id, tenant, severity, cat, status, owner, sla, updated, summary`
- `severity`: **P1 | P2 | P3 | P4**. `status`: investigating | in_progress | queued | resolved | escalated. `sla`: 1h/4h/8h/24h/72h.

### SA_AUDIT_LOG
`{time, actor, role, tenant, action, detail}` — in-memory, mutated by `saAudit()`.

### SA_WEBHOOK_EVENTS (9)
tenant.created, tenant.plan.changed, tenant.feature.enabled, tenant.invoice.paid, tenant.compliance.acknowledged, tenant.integration.failed, tenant.ai.budget.threshold.reached, support.impersonation.started, audit.critical-action.logged.

### STATUTORY_RATES / STATUTORY_RATES_HISTORY
EPF (employee/employer/eps pct, eps_wage_cap, pf_wage_ceiling, edli_pct), ESI (employee/employer pct, wage_threshold), std_deduction (new/old), cess_pct, surcharge_new_cap, sec_80c_cap, sec_80ccd_1b_cap, sec_24b_self_occupied_cap, gratuity (accrual_pct_monthly, exemption_cap), sbi_plr_pct, perquisite_threshold, tax_slabs_new[], tax_slabs_old[], surcharge[], fy, last_synced, next_review. History rows: `{field, from, to, effective_from, by, note}`.

### SA_ROLES (9)
owner (Platform Owner), ops (Platform Operations), release (Release Manager), compliance (Compliance Admin), billing (Billing Admin), security (Security Admin), ai (AI Admin), support (Support Admin), auditor (Read-only Auditor). Each `{key, label, dot, desc}`.

---

## Multi-Tenancy Model

- **Tenant lifecycle:** trial → active → attention → suspended → archived. `saSuspendTenant` (health→0, users→0, sessions terminated), `saActivateTenant` (health→85, users≈80% of employees). Archive = toast + audit only (no real state). Trial conversion via super-plans Trials tab.
- **Provisioning:** `sa-tenant-create` wizard auto-assigns workspace URL (`<name>.hcmpulse.in`), data region (ap-south-1 default), deployment stamp (IN-1 default), sends admin setup email (simulated). New tenant defaults: modules 5, pepm 48, plan Starter, 30-day contract.
- **Module entitlements:** per-tenant module toggles (`twModules`, capped 0..15); plan-level entitlement matrix (`renderSaEntitlements`); add-ons billed per emp/mo on top of plan.
- **Plans/add-ons:** PEPM pricing; plan tiers Free→Enterprise; add-ons AI Pulse/API Access/Mobile App/Workflow Engine/Advanced Analytics.
- **Metering & billing:** usage meters with limit + overage; MRR = Σ(pepm×employees); GST @18%; invoice lifecycle pending→paid (manual or gateway). Overage rule "110% then alert".
- **Data residency/isolation:** `dataRegion` (ap-south-1, me-central-1, ap-southeast-1) + deployment `stamp`; residency tab in super-data; per-tenant workspace subdomain; environment=Production.

---

## Platform Governance

- **Feature flags & rings & rollouts/rollbacks:** LaunchDarkly-style flags with env, % rollout, multi-dimension targeting, prerequisites, variations; 7 version rings; per-tenant ring assignment; partial rollout incrementing; rollback with risk + approval tier; per-flag **kill switch**.
- **Compliance publishing & acknowledgement:** 8-state pack lifecycle; 7-step publish wizard; sandbox preview before production; impact analysis; per-tenant ack tracking + reminders; evidence bundles; legal source registry; rollback history.
- **AI governance:** providers/models registry; per-tenant policies (enabled, providers, models, token cap, PII redaction, store prompts, opt-out, human review); prompt template library; token budgets with breach alerts; redaction; AI audit; **kill switches** (platform/tenant/module/provider/model/region).
- **Security:** MFA enforcement + step-up MFA for risky actions; SSO/SAML/OIDC/OAuth; IP allowlists + geo; session management + revoke; login-as/impersonation (read-only default, write requires approval, masking on by default, ticket-linked, fully audited); PII masking; secrets vault with rotation + expiry; incident log.
- **Data governance:** retention policies + auto-purge; residency; legal hold; deletion; DR tests; backup policies + restore (sandbox-first, dual-approval for prod); evidence.
- **Observability:** system health (services, pods, CPU/mem), jobs, queues, API logs, integration logs, payroll runs, error trends, uptime.
- **Developer:** API keys (scoped, rotatable), webhooks (9 event types), event delivery log, sandbox, docs.

---

## State Machines

- **Tenant lifecycle:** `trial → active ⇄ attention → suspended → (activate) → active`; `* → archived`. Suspend wipes users/health; activate restores ~80% users.
- **Invoice/billing:** `pending → paid` (manual mark or gateway); `pending → overdue` (past due); `paid → refunded` (refund). Credit note issued separately. attempts increments on retry.
- **Compliance pack:** `draft → legal_review → sandbox_preview → impact_analysis → approved → published → acknowledged → archived`. Rollback returns published → previous version. `saCompPublishPack` jumps to published (tenants=12, ackPct=0).
- **Feature flag:** `off ⇄ on` (toggle); rollout 0→…→100; `beta` is a distinct state; kill switch forces `→ off, rollout 0`.
- **Release rollout:** ring progression Internal/Alpha → Beta/Early Access → Stable → Enterprise Locked; release status `staged → live → archived`; rollback live→archived version.
- **Impersonation:** `pending_approval → active → completed` (write mode) or `pending_approval → denied`; read-only completes directly.
- **Integration:** `healthy ⇄ paused`; `healthy → error → (retry) → healthy`.
- **Template:** `draft → active → deprecated → (reactivate) → active`.
- **Announcement:** `draft → scheduled → published` (or draft → published directly).

---

## Platform Roles & Permissions

| Role (key) | Label | Screens (data-sa-role) |
|---|---|---|
| owner | Platform Owner | ALL (owner bypasses allowlist) |
| ops | Platform Operations | dashboard, tenants, plans, releases, compliance, announcements, templates, integrations, support, observability, statutory |
| release | Release Manager | dashboard, plans, releases, templates, dev |
| compliance | Compliance Admin | dashboard, compliance, announcements, audit, statutory |
| billing | Billing Admin | dashboard, plans, billing |
| security | Security Admin | dashboard, security, audit, data |
| ai | AI Admin | dashboard, ai |
| support | Support Admin | dashboard, tenants, integrations, support, observability |
| auditor | Read-only Auditor | dashboard, audit (read-only) |

Risky actions requiring **step-up MFA** (per super-security/MFA): Refund invoice, Compliance publish, Tenant suspension, Login-as write mode, Feature rollback, Backup restore, AI kill switch. Rollback approval tiers: Low→Auto, Medium→Release Manager, High→Platform Owner. Production restore → dual approval (Platform Owner + Security Admin).

---

## Feature Inventory (this module)

- **Tenant management:** registry, filters, create/clone/sandbox, 7-tab workspace, suspend/activate/archive, module entitlement toggles, login-as.
- **Plans/catalog:** 5 plans, 15-module catalog, entitlement matrix, plan comparison, 5 add-ons, trials/conversion.
- **Billing:** MRR/ARR, subscriptions, usage metering, invoices (GST), payments, disputes, revenue-by-plan, mark-paid/credit-note/refund/reminder/PDF.
- **Releases:** feature flags + targeting/rollout/kill-switch, 7 version rings, rollouts, rollbacks, beta programs, release notes.
- **Compliance:** 12 packs, 8-state lifecycle, 7-step publish wizard, impact analysis, publish queue, acknowledgements, evidence bundles, legal sources, rollback history.
- **Statutory rates:** India master library (EPF/ESI/income tax/deductions/gratuity/perquisite), tax slabs, surcharge, effective-dated change history, push-to-all-tenants.
- **Announcements:** multi-channel (In-app/Email/SMS), templates, analytics, 7-step wizard.
- **Templates:** marketplace, install/duplicate/version/deprecate.
- **Integrations:** 21 providers, webhooks, API keys, sync logs, retry/pause/resume.
- **Security:** MFA + step-up, SSO/SAML, IP, sessions, login-as/impersonation, PII masking, secrets vault, incidents.
- **AI governance:** providers/models, tenant policies, prompt templates, token budgets, redaction, audit, kill switches.
- **Support:** tickets (P1-P4/SLA), tenant health, impersonation requests, incidents/RCA/notes.
- **Audit:** immutable 7-year trail, filters, before/after diff, evidence export.
- **Observability:** health, jobs, queues, API, uptime.
- **Data governance:** retention, residency, legal hold, deletion, backups, restore, DR.
- **Developer:** API keys, webhooks (9 events), events, sandbox, docs.
- **Platform settings:** countries/currencies/languages/timezones/industries/defaults/branding/environment/security/AI/compliance defaults.

---

## Gaps (Missing but Required)

1. **Tenant provisioning automation** — create wizard only mutates an in-memory array; no real workspace/DB/stamp provisioning, no async job, no email delivery, no rollback on failure. Archive does nothing to state. A real control plane needs an orchestrated provisioning pipeline (DNS, schema/tenant isolation, seed data, region placement).
2. **Usage-based billing reconciliation** — `SA_METERS.overage`/`amount` are always 0; invoices are flat PEPM with no metered overage lines, no proration, no tax-jurisdiction logic beyond flat 18% GST, no dunning/retry automation, no revenue recognition. Metering is display-only and not wired to invoice generation.
3. **SLA monitoring & enforcement** — tickets carry SLA labels (1h/4h…) but there is no breach detection, timer, escalation automation, or SLA dashboard; "Avg response 2.4h" is hardcoded. Observability uptime/error figures are static, not computed.
4. **Audit immutability** — claims "immutable 7-year retention" but `SA_AUDIT_LOG` is a mutable in-memory array with no hash-chaining, WORM storage, signing, or tamper-evidence; before/after diffs are placeholders ("(previous value)"/"(new value)").
5. **SCIM / directory sync** — SSO/SAML config exists but no SCIM provisioning, just-in-time user creation, group-to-role mapping, or deprovisioning on offboarding; tenant user lists are static estimates (`twUsers` derives counts arithmetically).
6. **Public status page / incident comms** — incidents exist internally but there is no external status page, subscriber notifications, or maintenance-window publishing beyond an announcement record; observability has no alerting/on-call integration.
7. **Plan/entitlement consistency** — tenant `plan` values (e.g. "Internal", "Enterprise") do not all map to `SA_PLANS` codes; entitlement matrix edits only toast/audit; module toggles increment a counter rather than gate actual features. No single source of truth tying plan → entitlements → metering → billing.
8. **Compliance workflow enforcement** — the 8-state lifecycle and 7-step wizard are not enforced (publish jumps straight to `published`); no legal-review approvals, no per-tenant scheduling engine, no acknowledgement deadline enforcement or auto-escalation, no effective-date scheduler actually firing.
9. **AI governance depth** — kill switches and budgets are cosmetic (no real enforcement/throttling); no prompt/PII redaction engine, no model cost ledger reconciliation, no per-tenant data-processing agreements, no flagged-output review queue (count hardcoded to 1).
10. **DR/backup verification & RPO/RTO** — backups/restore are display-only; no real restore validation, no measured RPO/RTO, no DR-test results, no dual-approval enforcement in code (`saRestoreToSandbox` just toasts). Legal hold, deletion (DPDP erasure), and residency-move tabs are placeholders.

Additional notable gaps: no rate-limit/quota enforcement on API keys; webhook subscriber counts are randomized; many drawer sub-tabs (Targeting rules, Auth, Sync Logs, most observability/data/settings tabs) render placeholder text rather than functional forms.
