package com.portal.claims;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

class NpiValidatorTest {

    @ParameterizedTest
    @ValueSource(strings = {"1234567893", "1245319599"})
    void acceptsNumbersWithACorrectCheckDigit(String npi) {
        assertTrue(NpiValidator.isValid(npi));
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "1234567890",   // wrong check digit
        "1234567839",   // two digits swapped
        "123456789",    // too short
        "12345678931",  // too long
        "12345A7893",   // contains a letter
        " 1234567893"   // leading space
    })
    void rejectsInvalidNumbers(String npi) {
        assertFalse(NpiValidator.isValid(npi));
    }

    @ParameterizedTest
    @NullAndEmptySource
    void rejectsNullAndEmpty(String npi) {
        assertFalse(NpiValidator.isValid(npi));
    }

    @Test
    void exactlyOneCheckDigitIsValidForAnyNineDigits() {
        int valid = 0;
        for (int digit = 0; digit <= 9; digit++) {
            if (NpiValidator.isValid("987654321" + digit)) {
                valid++;
            }
        }
        assertTrue(valid == 1, "expected exactly one valid check digit but found " + valid);
    }
}
