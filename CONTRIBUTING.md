# Contributing

How work moves from an idea to the main branch in this project.

## Branches

- `main` is always deployable. Nobody commits to it directly.
- Create a short-lived branch per change, named after its ticket and purpose:
  `feature/PORTAL-42-claim-appeal`, `fix/PORTAL-57-npi-leading-zero`.

## Commits

Write the subject line as an instruction, under about 70 characters, and say why in the body when it is not obvious:

```
Reject approved amounts above the billed amount

Agents could approve more than was billed because the check compared
strings. Compare Decimals instead and add a regression test.
```

## Before opening a pull request

```bash
cd backend && pytest            # all green
cd frontend && npm test && npm run build
cd tools/claim-file-validator && mvn test    # if you touched the Java tool
```

- New behaviour comes with tests. A bug fix comes with a test that fails without the fix (a regression test).
- Update `docs/API.md` if an endpoint changed and add a line to `CHANGELOG.md`.

## Pull requests and code review

- Keep pull requests small; one purpose each. A reviewer should be able to read it in one sitting.
- Fill in the pull request template. Say how you tested.
- CI must pass and at least one other person must approve before merging.
- Reviewers look for: correctness, missing permission or validation checks, missing tests, unclear names, and anything that would surprise the next reader. Comment on the code, not the person; explain the reason for each request.

## Sprint workflow

Work is planned in two-week sprints. Each change has a ticket that moves through *To do*, *In progress*, *In review*, *Done*. A ticket is done when the code is merged, tests pass in CI, and the documentation is updated.

## Data rules

Use only synthetic data in code, tests, screenshots and tickets. Never commit secrets; `.env` files are git-ignored.
