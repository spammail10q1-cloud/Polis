# Security & Privacy

**Status:** experimental research platform. POLIS does **not** claim GDPR, HIPAA, MDR or any other regulatory certification or compliance merely because these controls exist. A production deployment requires legal, security, clinical and regulatory review.

## 1. Assets and trust boundaries

Sensitive assets:

- identity and authentication data,
- health profile, laboratory records, genetic data, medications, wearable series,
- simulations and assistant transcripts,
- consent state, privacy budget and audit trail,
- model parameters and evidence corpus.

Trust boundaries:

```
Browser ── HTTPS/reverse proxy ── Next.js ── private network ── FastAPI ── database
                                                           └── optional LLM API (off by default)
```

The MVP runs all scientific processing server-side. There is no browser-local health store yet; the "local-first" label refers to the default deployment's absence of third-party data egress and the federated demonstration, not to a fully local/offline client. This should be stated accurately in any product materials.

## 2. Authentication and session security

- Passwords are hashed with **scrypt** (`N=2^14`, `r=8`, `p=1`) and a 16-byte random salt. Hashes are versioned and compared in constant time.
- Sessions use **HS256 JWTs** with `sub`, `iat`, `exp`, `iss` and `aud` claims.
- Browser sessions are delivered as an **HttpOnly, SameSite=Lax** cookie. API clients can send a Bearer token.
- `COOKIE_SECURE` must be `true` behind HTTPS.
- Production startup refuses the development `SECRET_KEY` placeholder.
- Login is rate-limited per client IP (in-memory). This is not a distributed limiter.
- A dummy password hash is verified for unknown emails to reduce timing-based user enumeration.
- Error messages do not reveal whether an email exists at login.

Residual risks:

- No account lockout, MFA, password-reset email flow or breached-password check in the MVP.
- JWT invalidation is expiry-based; logout clears the cookie but a stolen token remains valid until expiry.
- In-memory rate limiting is bypassed by restart and does not coordinate across instances.
- `SameSite=Lax` plus origin checking reduces, but does not eliminate, all CSRF risk. A dedicated CSRF token is not implemented.
- Session theft through XSS remains possible if any XSS existed; CSP is restrictive but includes `'unsafe-inline'` for Next runtime compatibility.

## 3. Authorization and tenant isolation

- Every protected endpoint resolves the current user from the cookie/Bearer token.
- Every patient-owned query filters by `user_id`.
- Cross-tenant deletion and retrieval return 404, not resource existence.
- Tests explicitly prove one user cannot read or delete another user's laboratory results, genetic samples, simulations, or include the other's values in assistant output or export.
- Roles exist in the schema (`member`, `demo`) but the MVP does not implement organisation-level RBAC or sharing. This is a single-account isolation model.

## 4. CSRF and browser protections

- CSRF defence in depth:
  - SameSite=Lax cookie,
  - JSON content types,
  - server-side Origin validation for cookie-authenticated unsafe methods.
- Security headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy` disabling camera, microphone, geolocation
  - `Cache-Control: no-store` on API responses
  - Content-Security-Policy on the web app (Next.js requires inline styles and inline bootstrap scripts; this is not the strongest possible CSP)
- HSTS is emitted by the API only in production over an HTTPS-forwarded request. HSTS should also be set at the TLS reverse proxy.
- TLS termination is **not** included. Deploy behind a properly configured proxy or platform with modern TLS.

## 5. Input, upload and injection controls

- Pydantic validates all request bodies, lengths, dates, numeric bounds and relationships (e.g., reference low < high).
- Unsupported laboratory units are rejected; units are never guessed.
- Measurement dates cannot be in the future.
- Upload types are limited to CSV, FHIR JSON and text PDF for labs; VCF for genetics.
- Size limits: lab CSV 2 MB, FHIR 8 MB, PDF 12 MB, VCF 25 MB, whole request 30 MB.
- PDF parsing is text-only; scanned image PDFs fail rather than invoking uncontrolled OCR.
- Filenames are stored as metadata only and not used as filesystem paths.
- SQLAlchemy parameterises queries; no raw SQL is constructed from user input.
- File content is processed in memory by parsers with validation and time/size limits. A production deployment should add malware scanning and sandboxed workers.
- Prompt-injection detection returns a safety boundary for common attempts. The default assistant is deterministic and does not follow user-supplied instructions as system instructions. External LLM context is delimited as untrusted data.

## 6. Consent and data-subject controls

Independent toggles:

- AI processing,
- research participation,
- federated learning,
- product analytics.

Terms acceptance is required at registration. Consent changes are audited. Consent enforcement is server-side:

- assistant endpoints return 403 without AI consent;
- federated rounds return 403 without federated consent;
- demo account deletion is blocked because it is shared.

User rights implemented:

- machine-readable JSON export of all health records, consents, simulations, wearable samples and audit log,
- deletion of health data while retaining the account,
- full account deletion with cascade,
- audit log review,
- consent withdrawal.

Retention is user-controlled in the MVP. Backups, legal holds and derived analytics are **not** implemented; any production deployment must define and document these separately.

## 7. Audit logging and metadata minimisation

- Audit entries record who did what to which resource type/ID, with structured details that avoid free-text health content.
- Assistant audit records intent, message length, citation count and engine, not the question text.
- No IP addresses are stored in audit entries.
- No third-party analytics is enabled by default.
- Cookies, JWTs and secrets are never logged.

Residual risks: timing, request-size and error patterns can themselves be sensitive metadata; the MVP does not provide a separate metadata minimisation guarantee.

## 8. Encryption

Implemented in transit / at the application layer:

- HTTPS is expected at the reverse proxy; cookies and HSTS support secure deployment.
- Password hashing and signed session tokens.
- No raw health data is sent to third-party services in the default configuration.

**Not implemented:**

- Application-level field or database encryption.
- Customer-managed keys.
- Encrypted browser storage (health data is not persisted client-side).
- Encrypted backups.

For production, use encrypted disks/volumes, managed database encryption, key rotation, encrypted backups and TLS everywhere. Do not describe the MVP as "encrypted at rest" solely because SQLite/PostgreSQL can be deployed that way.

## 9. AI and model-provider data flow

Default (`LLM_PROVIDER=deterministic`):

- Retrieval and answer composition run locally.
- No raw records or prompts leave the system.
- Every cited source comes from the local corpus.

Optional OpenAI-compatible provider:

- The server sends the user's prepared personal context and retrieved evidence snippets to the configured endpoint.
- This requires explicit AI-processing consent. Operators must update privacy documentation and obtain any additional consent required in their jurisdiction.
- Responses are parsed as JSON, citations are filtered against the retrieved set, and any failure falls back to deterministic synthesis.
- No guarantee is made that an external provider does not retain or process data beyond the request. A production deployment must negotiate appropriate terms or use a local model.

## 10. Federated-learning demonstration risks

The demo implements clipping, Gaussian noise, simulated additive masks, FedAvg and a privacy ledger over synthetic clients. It is **not** production privacy infrastructure.

- Federated learning does not automatically guarantee anonymity.
- Gradients/updates can leak training information, especially across repeated rounds.
- Masks are simulated in-process; no cryptographic secure-aggregation protocol or honest-but-curious security proof exists.
- The epsilon figure uses simple composition and is not a formal end-to-end DP guarantee.
- Poisoning detection, robust aggregation, dropout handling and participant authentication are not implemented.
- Participation metadata remains linkable to the account in the demo ledger.
- No real participant data is used.

A production system needs a threat model, cryptographic protocol, formal DP accountant, update validation, poisoning defences, consent management and independent testing.

## 11. Model and clinical safety

- No diagnosis, prescribing, dose calculation or treatment recommendation.
- Simulation output is normalized and does not report absolute concentrations or personalized doses.
- High-risk medicines return structured refusals rather than estimates.
- VCF uploads do not produce clinical phenotypes.
- No model is clinically validated; the model registry says so.
- The digital body is a navigation interface, not an image or functional measurement of the user's organs.

## 12. Regulatory readiness mapping (not certification)

### GDPR / EU data protection

Implemented design elements:

- purpose-specific, independent consent,
- access, export, erasure and consent withdrawal,
- data minimisation in audit metadata,
- privacy-by-design separation of research/federated participation,
- documented processing and limitations.

Still required for a real deployment:

- lawful basis and controller/processor mapping,
- DPIA and DPO review,
- records of processing,
- subprocessor agreements (including any LLM provider),
- international transfer assessment,
- retention schedule and backup erasure,
- breach notification process,
- security testing and independent audit.

### Medical Device Regulation (EU MDR)

POLIS makes no diagnostic or treatment claims in this prototype. If any feature were marketed for diagnosis, prevention, monitoring, prediction, prognosis or treatment, it could fall within MDR scope. A future assessment must cover intended purpose, classification, clinical evaluation, post-market surveillance, quality management and technical documentation. The current research prototype is **not** a CE-marked medical device.

### HIPAA (US)

POLIS is not represented as a covered entity or business associate. Production use in a HIPAA context would require scoping, policies, workforce training, BAAs, risk analysis, audit controls, contingency planning, encryption, access management and independent assessment. The presence of audit logs and consent does not establish HIPAA compliance.

## 13. Deployment hardening checklist

- [ ] Generate a strong unique `SECRET_KEY`; never ship the demo secret.
- [ ] Set `ENVIRONMENT=production`, `COOKIE_SECURE=true`, and configure the public HTTPS origin in `CORS_ORIGINS`.
- [ ] Set `DEMO_SEED=false` unless a synthetic demo is intentionally public.
- [ ] Use PostgreSQL with encrypted storage, restricted network access and a dedicated least-privilege database user.
- [ ] Run `alembic upgrade head` and verify a restore from backup.
- [ ] Put the API and web behind a TLS reverse proxy; set HSTS, request limits and network egress rules.
- [ ] Add MFA / SSO, password reset and account lockout for real users.
- [ ] Replace in-memory rate limiting with Redis and add per-account quotas.
- [ ] Add a real CSRF token for browser forms if changing cookie/session architecture.
- [ ] Scan dependencies (`pip-audit`, `npm audit --omit=dev`) and container images.
- [ ] Add malware scanning and sandboxed workers for uploads.
- [ ] Define retention, backup and incident-response policies.
- [ ] Complete DPIA, legal, clinical and regulatory reviews before handling real patient data.
- [ ] Independently test tenant isolation, encryption, deletion and federated privacy claims.

## 14. Reporting security issues

This repository is a research demonstration. Do not deploy it with real health data without an independent security review. If you adapt it, establish a private security contact and coordinated disclosure process.
