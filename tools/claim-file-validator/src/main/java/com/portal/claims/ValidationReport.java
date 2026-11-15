package com.portal.claims;

import java.util.List;

/**
 * The result of checking one file.
 *
 * @param rowCount number of data rows read (the header is not counted)
 * @param issues   every problem found, in file order
 */
public record ValidationReport(int rowCount, List<ValidationIssue> issues) {

    public ValidationReport {
        issues = List.copyOf(issues); // defensive copy: the report cannot be changed afterwards
    }

    public boolean isValid() {
        return issues.isEmpty();
    }
}
