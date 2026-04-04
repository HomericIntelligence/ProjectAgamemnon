# Security Policy

## Reporting Security Vulnerabilities

**Do not open public issues for security vulnerabilities.**

We take security seriously. If you discover a security vulnerability, please report it responsibly.

## How to Report

### Email (Preferred)

Send an email to: **<4211002+mvillmow@users.noreply.github.com>**

Or use the GitHub private vulnerability reporting feature if available.

### What to Include

Please include as much of the following information as possible:

- **Description** - Clear description of the vulnerability
- **Impact** - Potential impact and severity assessment
- **Steps to reproduce** - Detailed steps to reproduce the issue
- **Affected files** - Which source files, endpoints, or configurations are affected
- **Suggested fix** - If you have a suggested fix or mitigation

### Example Report

```text
Subject: [SECURITY] Unauthenticated access to /v1/chaos/* fault injection endpoints

Description:
The /v1/chaos/* REST endpoints do not require authentication, allowing
any network-adjacent client to inject faults into the agent mesh.

Impact:
An attacker could disrupt agent coordination by injecting arbitrary
faults via the chaos testing API.

Steps to Reproduce:
1. Start ProjectAgamemnon server
2. curl -X POST http://<host>:8080/v1/chaos/inject -d '{"type":"kill"}'
3. Observe fault injected without any authentication

Affected Files:
src/routes.cpp (chaos route handlers)

Suggested Fix:
Add authentication middleware to /v1/chaos/* endpoints.
```

## Response Timeline

We aim to respond to security reports within the following timeframes:

| Stage                    | Timeframe              |
|--------------------------|------------------------|
| Initial acknowledgment   | 48 hours               |
| Preliminary assessment   | 1 week                 |
| Fix development          | Varies by severity     |
| Public disclosure        | After fix is released  |

## Severity Assessment

We use the following severity levels:

| Severity     | Description                          | Response           |
|--------------|--------------------------------------|--------------------|
| **Critical** | Remote code execution, data breach   | Immediate priority |
| **High**     | Privilege escalation, data exposure  | High priority      |
| **Medium**   | Limited impact vulnerabilities       | Standard priority  |
| **Low**      | Minor issues, hardening              | Scheduled fix      |

## Responsible Disclosure

We follow responsible disclosure practices:

1. **Report privately** - Do not disclose publicly until a fix is available
2. **Allow reasonable time** - Give us time to investigate and develop a fix
3. **Coordinate disclosure** - We will work with you on disclosure timing
4. **Credit** - We will credit you in the security advisory (if desired)

## What We Will Do

When you report a vulnerability:

1. Acknowledge receipt within 48 hours
2. Investigate and validate the report
3. Develop and test a fix
4. Release the fix
5. Publish a security advisory

## Scope

### In Scope

- C++ source code (routes, store, NATS client)
- REST API endpoints (`/v1/tasks`, `/v1/agents`, `/v1/chaos/*`, `/v1/workflows`)
- CMake build configuration
- Dockerfile and container configuration

### Out of Scope

- Odysseus meta-repo configurations (report to [Odysseus](https://github.com/HomericIntelligence/Odysseus))
- Other HomericIntelligence submodule repos (report to that repo directly)
- Third-party dependencies (report upstream to cpp-httplib, nlohmann_json, etc.)
- Social engineering attacks
- Physical security

## Security Best Practices

When contributing to ProjectAgamemnon:

- Validate all HTTP request input before processing
- Avoid buffer overflows and undefined behavior
- Use AddressSanitizer (ASAN) and ThreadSanitizer (TSAN) in CI builds
- Never commit secrets, API keys, tokens, or credentials
- Pin FetchContent dependency versions to known-good commits

## Contact

For security-related questions that are not vulnerability reports:

- Open a GitHub Discussion with the "security" tag
- Email: <4211002+mvillmow@users.noreply.github.com>

---

Thank you for helping keep HomericIntelligence secure!
