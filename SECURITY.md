# Security policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for a security bug.

Instead, open a **GitHub Security Advisory** here:
<https://github.com/tanguychenier/Orbital-Collision-Risk-Dashboard/security/advisories/new>

Include:

- A description of the vulnerability and its potential impact.
- Steps to reproduce, ideally with a minimal proof of concept.
- The affected commit hash, branch, or release tag.
- Your name / handle if you would like to be credited in the fix.

You will receive an acknowledgement within **72 hours**. We aim to ship
a fix within **90 days** of the initial report; if that is not
achievable we will share status updates on a fortnightly cadence and
co-ordinate the disclosure timeline with you.

## Disclosure policy

This project follows a **90-day coordinated disclosure** window:

1. The reporter sends the report.
2. We acknowledge receipt and start the investigation.
3. We ship a fix in a non-public branch and back-port it to all
   supported releases.
4. After the fix lands and is publicly available, we publish a security
   advisory on GitHub crediting the reporter (unless they prefer
   anonymity).
5. If 90 days elapse without a fix, the reporter is free to disclose
   publicly. We will say so explicitly in the advisory.

## Supported versions

Only the latest tagged release on `main` is actively supported. Older
tags receive security fixes on a best-effort basis.

## Out of scope

- Vulnerabilities that require a malicious local user with root access.
- Self-XSS (issues that only the victim can trigger on themselves).
- Denial of service via volumetric attacks against public endpoints.
- Vulnerabilities in third-party dependencies that are already publicly
  known and tracked by Dependabot.

## Hall of fame

Reporters who responsibly disclose verified vulnerabilities will be
listed here unless they request otherwise.

(empty for now)
