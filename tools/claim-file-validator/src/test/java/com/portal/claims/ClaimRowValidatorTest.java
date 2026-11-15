package com.portal.claims;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ClaimRowValidatorTest {

    /** "Today" is fixed at 2026-06-15 so the tests give the same result on any day. */
    private static final Clock FIXED_CLOCK = Clock.fixed(Instant.parse("2026-06-15T12:00:00Z"), ZoneOffset.UTC);

    private final ClaimRowValidator validator = new ClaimRowValidator(FIXED_CLOCK);

    /** A row that passes every rule. Each test changes one thing. */
    private static Map<String, String> validRow() {
        Map<String, String> row = new HashMap<>();
        row.put("claim_number", "CLM-100001");
        row.put("member_number", "MBR-10001");
        row.put("provider_npi", "1234567893");
        row.put("service_date", "2026-05-20");
        row.put("procedure_code", "99213");
        row.put("diagnosis_code", "E11.9");
        row.put("billed_amount", "150.00");
        row.put("approved_amount", "");
        row.put("status", "submitted");
        row.put("denial_reason", "");
        return row;
    }

    private List<String> fieldsWithIssues(Map<String, String> row) {
        return validator.validate(2, row).stream().map(ValidationIssue::field).toList();
    }

    private void assertOnlyIssueIs(String field, Map<String, String> row) {
        assertEquals(List.of(field), fieldsWithIssues(row));
    }

    @Test
    void validRowHasNoIssues() {
        assertTrue(validator.validate(2, validRow()).isEmpty());
    }

    @Test
    void issueCarriesTheLineNumber() {
        Map<String, String> row = validRow();
        row.put("provider_npi", "1234567890");
        ValidationIssue issue = validator.validate(7, row).get(0);
        assertEquals(7, issue.line());
        assertEquals("line 7, provider_npi: is not a valid NPI", issue.toString());
    }

    @Test
    void rejectsBadIdentifiersAndCodes() {
        Map<String, String> row = validRow();
        row.put("claim_number", "100001");
        row.put("member_number", "");
        row.put("procedure_code", "9921");
        row.put("diagnosis_code", "11.9");
        assertEquals(
                List.of("claim_number", "member_number", "procedure_code", "diagnosis_code"),
                fieldsWithIssues(row));
    }

    @Test
    void rejectsServiceDateInTheFuture() {
        Map<String, String> row = validRow();
        row.put("service_date", "2026-06-16");
        assertOnlyIssueIs("service_date", row);
    }

    @Test
    void acceptsServiceDateOfToday() {
        Map<String, String> row = validRow();
        row.put("service_date", "2026-06-15");
        assertTrue(fieldsWithIssues(row).isEmpty());
    }

    @Test
    void rejectsServiceDateInTheWrongFormat() {
        Map<String, String> row = validRow();
        row.put("service_date", "05/20/2026");
        assertOnlyIssueIs("service_date", row);
    }

    @Test
    void rejectsBadBilledAmounts() {
        for (String amount : List.of("", "abc", "-5.00", "10.999", "0.00", "1,000.00")) {
            Map<String, String> row = validRow();
            row.put("billed_amount", amount);
            assertOnlyIssueIs("billed_amount", row);
        }
    }

    @Test
    void rejectsUnknownStatus() {
        Map<String, String> row = validRow();
        row.put("status", "archived");
        assertOnlyIssueIs("status", row);
    }

    @Test
    void approvedClaimNeedsAnApprovedAmount() {
        Map<String, String> row = validRow();
        row.put("status", "approved");
        assertOnlyIssueIs("approved_amount", row);

        row.put("approved_amount", "120.00");
        assertTrue(fieldsWithIssues(row).isEmpty());
    }

    @Test
    void approvedAmountCannotExceedBilledAmount() {
        Map<String, String> row = validRow();
        row.put("status", "paid");
        row.put("approved_amount", "150.01");
        assertOnlyIssueIs("approved_amount", row);

        row.put("approved_amount", "150.00"); // equal is allowed
        assertTrue(fieldsWithIssues(row).isEmpty());
    }

    @Test
    void amountsAreComparedAsNumbersNotText() {
        // As text "99.00" > "150.00"; as numbers it is smaller.
        Map<String, String> row = validRow();
        row.put("status", "approved");
        row.put("approved_amount", "99.00");
        assertTrue(fieldsWithIssues(row).isEmpty());
    }

    @Test
    void undecidedClaimMustNotHaveAnApprovedAmount() {
        Map<String, String> row = validRow();
        row.put("status", "in_review");
        row.put("approved_amount", "10.00");
        assertOnlyIssueIs("approved_amount", row);
    }

    @Test
    void deniedClaimNeedsAReason() {
        Map<String, String> row = validRow();
        row.put("status", "denied");
        assertOnlyIssueIs("denial_reason", row);

        row.put("denial_reason", "Duplicate claim.");
        assertTrue(fieldsWithIssues(row).isEmpty());
    }

    @Test
    void missingColumnsAreReportedNotThrown() {
        List<ValidationIssue> issues = validator.validate(2, new HashMap<>());
        assertTrue(issues.size() >= 7);
    }
}
