package com.portal.claims;

/**
 * One problem found in the file.
 *
 * @param line    line number in the file where the row starts (the header is line 1)
 * @param field   column name, or "file" / "row" for problems not tied to one column
 * @param message what is wrong
 */
public record ValidationIssue(int line, String field, String message) {

    @Override
    public String toString() {
        return "line " + line + ", " + field + ": " + message;
    }
}
