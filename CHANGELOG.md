# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-15

### Added
- **Member and provider directory.** Search, filters and pagination; member create, edit and deactivate (soft delete); provider create and edit with NPI check-digit validation.
- **Claims workflow.** Claim submission with CPT/HCPCS, ICD-10 and amount validation; status state machine (submitted, in review, approved, denied, paid) with appeal; row locking on status changes; status history; document upload and download (Amazon S3 or local disk).
- **Admin tools.** User management with three roles (admin, agent, viewer); audit log of sign-ins and every change; CSV claims export with formula-injection protection.
- **Dashboard.** Member, provider and claim totals, claims by status, approval rate, recent claims.
- **Authentication.** JWT access tokens, salted password hashes, role checks on every endpoint.
- **React frontend** for all of the above.
- **Claim file validator.** Java 17 command-line tool with JUnit 5 tests.
- **Tests.** PyTest unit and integration suites (168 tests), Vitest tests for frontend helpers.
- **CI/CD.** GitHub Actions workflows for tests (including a MySQL service container) and for deployment to S3 and EC2.
- **Deployment files.** nginx site, systemd unit, EC2 setup and deploy scripts with health check and rollback.
- **Documentation.** README, API reference, architecture notes, deployment guide.
