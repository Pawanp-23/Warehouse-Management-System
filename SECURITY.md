# Security policy

## Supported version

Security fixes are applied to the latest commit on `main`.

## Reporting a vulnerability

Do not open a public issue for suspected vulnerabilities. Use the repository's GitHub **Security → Report a vulnerability** flow so credentials, reproduction steps, and affected data remain private.

Include:

- Affected endpoint or component
- Reproduction steps
- Expected and observed behavior
- Potential tenant or data impact
- Suggested mitigation, if known

## Deployment requirements

Before exposing the service publicly:

- Use a secret manager for JWT, AI, payment, and webhook secrets.
- Set `APP_ENV=production`, `AUTH_REQUIRED=true`, and `DOCS_ENABLED=false`.
- Use explicit CORS origins and trusted hosts.
- Replace local MongoDB with a secured replica set and tested backups.
- Validate Stripe and carrier webhook signatures.
- Put a distributed rate limiter or managed gateway in front of every API instance.
- Use OIDC/JWKS, token rotation, MFA, and centralized audit retention.

Never commit `.env` files, access tokens, provider keys, customer documents, database exports, or production logs.
