package com.portal.claims;

import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.List;

/**
 * A small CSV reader that follows RFC 4180.
 *
 * <p>Splitting each line on commas is not enough: a value such as a denial reason may itself
 * contain a comma, a quote or a line break. Such values are wrapped in double quotes, and a
 * quote inside them is written twice ("").
 */
public final class CsvParser {

    /** One row of the file and the line number it started on. */
    public record Row(int line, List<String> values) {
    }

    private CsvParser() {
    }

    public static List<Row> parse(Reader reader) throws IOException {
        List<Row> rows = new ArrayList<>();
        List<String> values = new ArrayList<>();
        StringBuilder value = new StringBuilder();
        boolean inQuotes = false;
        boolean rowHasContent = false;
        int line = 1;
        int rowStartLine = 1;

        int next = reader.read();
        while (next != -1) {
            char ch = (char) next;
            int following = reader.read();

            if (inQuotes) {
                if (ch == '"' && following == '"') {
                    value.append('"'); // "" inside quotes is one literal quote
                    following = reader.read();
                } else if (ch == '"') {
                    inQuotes = false;
                } else {
                    if (ch == '\n') {
                        line++;
                    }
                    value.append(ch);
                }
            } else if (ch == '"') {
                inQuotes = true;
                rowHasContent = true;
            } else if (ch == ',') {
                values.add(value.toString());
                value.setLength(0);
                rowHasContent = true;
            } else if (ch == '\n' || ch == '\r') {
                if (ch == '\r' && following == '\n') {
                    following = reader.read(); // treat \r\n as one line ending
                }
                if (rowHasContent) {
                    values.add(value.toString());
                    rows.add(new Row(rowStartLine, List.copyOf(values)));
                }
                values.clear();
                value.setLength(0);
                rowHasContent = false;
                line++;
                rowStartLine = line;
            } else {
                value.append(ch);
                rowHasContent = true;
            }
            next = following;
        }

        if (inQuotes) {
            throw new IOException("Unclosed quote in row starting on line " + rowStartLine);
        }
        if (rowHasContent) { // last row without a trailing line break
            values.add(value.toString());
            rows.add(new Row(rowStartLine, List.copyOf(values)));
        }
        return rows;
    }
}
