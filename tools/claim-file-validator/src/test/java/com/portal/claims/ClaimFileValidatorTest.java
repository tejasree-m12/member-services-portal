package com.portal.claims;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.StringReader;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.Test;

class ClaimFileValidatorTest {

    private static final Clock FIXED_CLOCK = Clock.fixed(Instant.parse("2026-06-15T12:00:00Z"), ZoneOffset.UTC);
    private static final String HEADER =
            "claim_number,member_number,member_name,provider_npi,provider_name,service_date,"
                    + "procedure_code,diagnosis_code,billed_amount,approved_amount,status,denial_reason\n";
    private static final String GOOD_ROW =
            "CLM-100001,MBR-10001,Sample Member,1234567893,Dr. Test,2026-05-20,99213,E11.9,150.00,,submitted,\n";

    private final ClaimFileValidator validator = new ClaimFileValidator(FIXED_CLOCK);

    private ValidationReport check(String csv) throws IOException {
        return validator.validate(new StringReader(csv));
    }

    @Test
    void validFilePasses() throws IOException {
        ValidationReport report = check(HEADER + GOOD_ROW
                + "CLM-100002,MBR-10002,Other Member,1245319599,Dr. Two,2026-05-21,99214,I10,220.00,200.00,paid,\n");
        assertTrue(report.isValid());
        assertEquals(2, report.rowCount());
    }

    @Test
    void headerOnlyFileIsValidWithZeroRows() throws IOException {
        ValidationReport report = check(HEADER);
        assertTrue(report.isValid());
        assertEquals(0, report.rowCount());
    }

    @Test
    void emptyFileIsReported() throws IOException {
        ValidationReport report = check("");
        assertFalse(report.isValid());
        assertEquals("the file is empty", report.issues().get(0).message());
    }

    @Test
    void missingColumnsStopRowChecks() throws IOException {
        ValidationReport report = check("claim_number,member_number\nnot-checked,not-checked\n");
        assertEquals(8, report.issues().size());
        assertTrue(report.issues().stream().allMatch(issue -> issue.field().equals("file")));
    }

    @Test
    void columnOrderDoesNotMatter() throws IOException {
        String csv = "status,denial_reason,approved_amount,billed_amount,diagnosis_code,procedure_code,"
                + "service_date,provider_npi,member_number,claim_number\n"
                + "submitted,,,150.00,E11.9,99213,2026-05-20,1234567893,MBR-10001,CLM-100001\n";
        assertTrue(check(csv).isValid());
    }

    @Test
    void duplicateClaimNumbersAreReportedWithBothLines() throws IOException {
        ValidationReport report = check(HEADER + GOOD_ROW + GOOD_ROW);
        assertEquals(1, report.issues().size());
        ValidationIssue issue = report.issues().get(0);
        assertEquals(3, issue.line());
        assertEquals("duplicate of the claim on line 2", issue.message());
    }

    @Test
    void rowWithWrongNumberOfValuesIsReported() throws IOException {
        ValidationReport report = check(HEADER + "CLM-100001,MBR-10001\n" + GOOD_ROW);
        assertEquals(List.of("row"), report.issues().stream().map(ValidationIssue::field).toList());
        assertEquals(2, report.issues().get(0).line());
    }

    @Test
    void quotedValuesMayContainCommasQuotesAndLineBreaks() throws IOException {
        String csv = HEADER
                + "CLM-100001,MBR-10001,\"Member, Sample\",1234567893,\"Dr. \"\"Test\"\"\",2026-05-20,99213,E11.9,"
                + "150.00,,denied,\"Not covered,\nsee policy.\"\n"
                + "CLM-100002,MBR-10002,Other,1234567890,Dr. Two,2026-05-21,99214,I10,220.00,,submitted,\n";
        ValidationReport report = check(csv);
        assertEquals(2, report.rowCount());
        // Only the second row has a problem. It starts on line 4 because the
        // first row's quoted value spans two lines.
        assertEquals(1, report.issues().size());
        assertEquals(4, report.issues().get(0).line());
        assertEquals("provider_npi", report.issues().get(0).field());
    }

    @Test
    void windowsLineEndingsAndBlankLinesAreHandled() throws IOException {
        String csv = (HEADER + GOOD_ROW).replace("\n", "\r\n") + "\r\n\r\n";
        ValidationReport report = check(csv);
        assertTrue(report.isValid());
        assertEquals(1, report.rowCount());
    }

    @Test
    void lastRowWithoutLineBreakIsRead() throws IOException {
        assertEquals(1, check(HEADER + GOOD_ROW.trim()).rowCount());
    }

    @Test
    void unclosedQuoteIsAnError() {
        assertThrows(IOException.class, () -> check(HEADER + "CLM-100001,\"never closed\n"));
    }

    @Test
    void reportCannotBeModified() throws IOException {
        ValidationReport report = check(HEADER + GOOD_ROW);
        assertThrows(UnsupportedOperationException.class,
                () -> report.issues().add(new ValidationIssue(1, "x", "y")));
    }
}
