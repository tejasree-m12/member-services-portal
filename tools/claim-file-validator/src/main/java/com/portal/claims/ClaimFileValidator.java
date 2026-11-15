package com.portal.claims;

import java.io.IOException;
import java.io.Reader;
import java.time.Clock;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Checks a whole claims CSV file: the header, every row, and duplicate claim numbers. */
public final class ClaimFileValidator {

    /** Columns the file must contain. Extra columns and any column order are accepted. */
    static final List<String> REQUIRED_COLUMNS = List.of(
            "claim_number", "member_number", "provider_npi", "service_date", "procedure_code",
            "diagnosis_code", "billed_amount", "approved_amount", "status", "denial_reason");

    private final ClaimRowValidator rowValidator;

    public ClaimFileValidator(Clock clock) {
        this.rowValidator = new ClaimRowValidator(clock);
    }

    public ValidationReport validate(Reader reader) throws IOException {
        List<CsvParser.Row> rows = CsvParser.parse(reader);
        List<ValidationIssue> issues = new ArrayList<>();

        if (rows.isEmpty()) {
            issues.add(new ValidationIssue(1, "file", "the file is empty"));
            return new ValidationReport(0, issues);
        }

        List<String> header = rows.get(0).values().stream().map(String::trim).toList();
        for (String column : REQUIRED_COLUMNS) {
            if (!header.contains(column)) {
                issues.add(new ValidationIssue(1, "file", "missing column '" + column + "'"));
            }
        }
        if (!issues.isEmpty()) {
            // Without the right columns the row checks would only produce noise.
            return new ValidationReport(rows.size() - 1, issues);
        }

        Map<String, Integer> firstSeenOnLine = new HashMap<>();
        for (CsvParser.Row row : rows.subList(1, rows.size())) {
            if (row.values().size() != header.size()) {
                issues.add(new ValidationIssue(row.line(), "row",
                        "has " + row.values().size() + " values but the header has " + header.size()));
                continue;
            }
            Map<String, String> byColumn = new LinkedHashMap<>();
            for (int i = 0; i < header.size(); i++) {
                byColumn.put(header.get(i), row.values().get(i));
            }
            issues.addAll(rowValidator.validate(row.line(), byColumn));

            String claimNumber = byColumn.get("claim_number").trim();
            Integer earlierLine = firstSeenOnLine.putIfAbsent(claimNumber, row.line());
            if (earlierLine != null && !claimNumber.isEmpty()) {
                issues.add(new ValidationIssue(row.line(), "claim_number",
                        "duplicate of the claim on line " + earlierLine));
            }
        }
        return new ValidationReport(rows.size() - 1, issues);
    }
}
