# Claim file validator

A command-line tool, written in Java 17, that checks a claims CSV export from the Member Services Portal (`GET /api/v1/admin/reports/claims.csv`) before the file is passed to another system.

It reports every problem with its line number and sets an exit code a script can act on.

## Rules checked

- The file has all required columns (any order; extra columns are ignored).
- Claim and member numbers have the expected form.
- The provider NPI has a valid check digit (Luhn algorithm with the 80840 prefix).
- The service date is `YYYY-MM-DD` and not in the future.
- The procedure code is CPT or HCPCS shaped; the diagnosis code is ICD-10 shaped.
- The billed amount is a positive amount with at most two decimals.
- Approved and paid claims have an approved amount that is not more than the billed amount; other claims have none.
- Denied claims have a denial reason.
- No claim number appears twice.

## Build, test, run

Requires JDK 17+ and Maven.

```bash
mvn test                 # run the JUnit 5 tests
mvn package              # build target/claim-file-validator-1.0.0.jar

java -jar target/claim-file-validator-1.0.0.jar samples/claims_valid.csv
# OK: 5 rows checked, no problems found.

java -jar target/claim-file-validator-1.0.0.jar samples/claims_with_errors.csv
# 6 problem(s) found in 5 rows:
#   line 3, provider_npi: is not a valid NPI
#   line 4, procedure_code: must be a CPT or HCPCS code
#   line 4, approved_amount: cannot be more than billed_amount
#   line 5, service_date: must be a date in the form YYYY-MM-DD
#   line 5, denial_reason: is required when status is denied
#   line 6, claim_number: duplicate of the claim on line 2
```

| Exit code | Meaning |
|---|---|
| 0 | The file is valid |
| 1 | Problems were found |
| 2 | The tool could not run (wrong arguments, unreadable file) |

## Code map

| Class | Responsibility |
|---|---|
| `Main` | Reads the argument, prints the report, sets the exit code |
| `CsvParser` | Reads CSV, including quoted values with commas, quotes and line breaks |
| `ClaimFileValidator` | Checks the header, runs the row checks, finds duplicates |
| `ClaimRowValidator` | Business rules for one row |
| `NpiValidator` | NPI check digit |
| `ValidationIssue`, `ValidationReport` | Immutable result records |
