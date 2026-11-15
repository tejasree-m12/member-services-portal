package com.portal.claims;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Applies the business rules to one row of the claims export.
 *
 * <p>The rules mirror the Python backend. If the export ever contains a row that breaks them,
 * something is wrong in the application or the data was edited by hand, and the file should
 * not be sent on.
 */
public final class ClaimRowValidator {

    static final Set<String> STATUSES = Set.of("submitted", "in_review", "approved", "denied", "paid");

    private static final Pattern CLAIM_NUMBER = Pattern.compile("CLM-[A-Z0-9]{4,16}");
    private static final Pattern MEMBER_NUMBER = Pattern.compile("MBR-[A-Z0-9]{4,16}");
    private static final Pattern PROCEDURE_CODE = Pattern.compile("\\d{5}|[A-Z]\\d{4}");
    private static final Pattern DIAGNOSIS_CODE = Pattern.compile("[A-TV-Z]\\d[0-9A-Z](\\.[0-9A-Z]{1,4})?");
    private static final Pattern MONEY = Pattern.compile("\\d{1,8}(\\.\\d{1,2})?");

    private final Clock clock;

    /** The clock is passed in so tests can fix "today" to a known date. */
    public ClaimRowValidator(Clock clock) {
        this.clock = clock;
    }

    public List<ValidationIssue> validate(int line, Map<String, String> row) {
        List<ValidationIssue> issues = new ArrayList<>();

        requirePattern(issues, line, row, "claim_number", CLAIM_NUMBER, "must look like CLM-XXXXXX");
        requirePattern(issues, line, row, "member_number", MEMBER_NUMBER, "must look like MBR-XXXXXX");
        requirePattern(issues, line, row, "procedure_code", PROCEDURE_CODE, "must be a CPT or HCPCS code");
        requirePattern(issues, line, row, "diagnosis_code", DIAGNOSIS_CODE, "must be an ICD-10 code");

        String npi = value(row, "provider_npi");
        if (!NpiValidator.isValid(npi)) {
            issues.add(new ValidationIssue(line, "provider_npi", "is not a valid NPI"));
        }

        checkServiceDate(issues, line, value(row, "service_date"));

        String status = value(row, "status");
        boolean statusKnown = STATUSES.contains(status);
        if (!statusKnown) {
            issues.add(new ValidationIssue(line, "status", "is not a known status"));
        }

        BigDecimal billed = parseMoney(issues, line, "billed_amount", value(row, "billed_amount"));
        if (billed != null && billed.signum() <= 0) {
            issues.add(new ValidationIssue(line, "billed_amount", "must be greater than zero"));
        }

        if (statusKnown) {
            checkDecision(issues, line, row, status, billed);
        }
        return issues;
    }

    /** Rules that depend on the claim's status. */
    private void checkDecision(
            List<ValidationIssue> issues, int line, Map<String, String> row, String status, BigDecimal billed) {
        String approvedText = value(row, "approved_amount");
        boolean decidedInFavour = status.equals("approved") || status.equals("paid");

        if (decidedInFavour) {
            if (approvedText.isEmpty()) {
                issues.add(new ValidationIssue(line, "approved_amount", "is required when status is " + status));
            } else {
                BigDecimal approved = parseMoney(issues, line, "approved_amount", approvedText);
                if (approved != null && billed != null && approved.compareTo(billed) > 0) {
                    issues.add(new ValidationIssue(line, "approved_amount", "cannot be more than billed_amount"));
                }
            }
        } else if (!approvedText.isEmpty()) {
            issues.add(new ValidationIssue(line, "approved_amount", "must be empty when status is " + status));
        }

        if (status.equals("denied") && value(row, "denial_reason").isEmpty()) {
            issues.add(new ValidationIssue(line, "denial_reason", "is required when status is denied"));
        }
    }

    private void checkServiceDate(List<ValidationIssue> issues, int line, String text) {
        try {
            LocalDate date = LocalDate.parse(text); // ISO format: YYYY-MM-DD
            if (date.isAfter(LocalDate.now(clock))) {
                issues.add(new ValidationIssue(line, "service_date", "cannot be in the future"));
            }
        } catch (DateTimeParseException e) {
            issues.add(new ValidationIssue(line, "service_date", "must be a date in the form YYYY-MM-DD"));
        }
    }

    /**
     * Money is parsed into BigDecimal, never double: binary floating point cannot represent
     * most decimal fractions exactly, and comparisons such as approved &lt;= billed must be exact.
     */
    private static BigDecimal parseMoney(List<ValidationIssue> issues, int line, String field, String text) {
        if (!MONEY.matcher(text).matches()) {
            issues.add(new ValidationIssue(line, field, "must be an amount such as 150.00"));
            return null;
        }
        return new BigDecimal(text);
    }

    private static void requirePattern(
            List<ValidationIssue> issues, int line, Map<String, String> row, String field, Pattern pattern,
            String message) {
        if (!pattern.matcher(value(row, field)).matches()) {
            issues.add(new ValidationIssue(line, field, message));
        }
    }

    private static String value(Map<String, String> row, String field) {
        String value = row.get(field);
        return value == null ? "" : value.trim();
    }
}
