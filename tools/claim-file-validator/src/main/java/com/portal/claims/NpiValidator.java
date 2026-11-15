package com.portal.claims;

/**
 * Checks National Provider Identifiers (NPI).
 *
 * <p>An NPI is 10 digits. The last digit is a check digit, calculated with the Luhn algorithm
 * over the first nine digits prefixed with 80840. The Python backend applies the same rule in
 * {@code app/validation.py}; the two implementations must agree.
 */
public final class NpiValidator {

    private static final String PREFIX = "80840";

    private NpiValidator() {
        // utility class: no instances
    }

    public static boolean isValid(String npi) {
        if (npi == null || !npi.matches("\\d{10}")) {
            return false;
        }
        String digits = PREFIX + npi;
        int total = 0;
        boolean doubleIt = false; // the check digit itself (rightmost) is not doubled
        for (int i = digits.length() - 1; i >= 0; i--) {
            int digit = digits.charAt(i) - '0';
            if (doubleIt) {
                digit *= 2;
                if (digit > 9) {
                    digit -= 9;
                }
            }
            total += digit;
            doubleIt = !doubleIt;
        }
        return total % 10 == 0;
    }
}
