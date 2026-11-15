package com.portal.claims;

import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;

/**
 * Command-line entry point.
 *
 * <pre>
 *   java -jar claim-file-validator-1.0.0.jar claims_report.csv
 * </pre>
 *
 * Exit codes, so scripts and CI jobs can react: 0 = file is valid, 1 = problems found,
 * 2 = the tool could not run (wrong arguments or unreadable file).
 */
public final class Main {

    private Main() {
    }

    public static void main(String[] args) {
        System.exit(run(args));
    }

    static int run(String[] args) {
        if (args.length != 1) {
            System.err.println("Usage: java -jar claim-file-validator.jar <claims.csv>");
            return 2;
        }

        ValidationReport report;
        try (Reader reader = Files.newBufferedReader(Path.of(args[0]), StandardCharsets.UTF_8)) {
            report = new ClaimFileValidator(Clock.systemDefaultZone()).validate(reader);
        } catch (IOException e) {
            System.err.println("Could not read " + args[0] + ": " + e.getMessage());
            return 2;
        }

        if (report.isValid()) {
            System.out.println("OK: " + report.rowCount() + " rows checked, no problems found.");
            return 0;
        }
        System.out.println(report.issues().size() + " problem(s) found in " + report.rowCount() + " rows:");
        for (ValidationIssue issue : report.issues()) {
            System.out.println("  " + issue);
        }
        return 1;
    }
}
