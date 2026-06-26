package com.example.fraud.bankingcore.api.dto;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.Set;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class TransactionRequestValidationTest {

    private static Validator validator;

    @BeforeAll
    static void setUpValidator() {
        validator = Validation.buildDefaultValidatorFactory().getValidator();
    }

    @Test
    void validRequestPassesValidation() {
        Set<ConstraintViolation<TransactionRequest>> violations = validator.validate(validRequest());

        assertThat(violations).isEmpty();
    }

    @Test
    void requiresUserId() {
        TransactionRequest request = validRequestWithUserId("");

        assertThat(validator.validate(request))
                .extracting(violation -> violation.getPropertyPath().toString())
                .contains("userId");
    }

    @Test
    void requiresAccountId() {
        TransactionRequest request = new TransactionRequest(
                "user-1",
                "",
                BigDecimal.TEN,
                CurrencyCode.AUD,
                "GROCERY",
                TransactionType.CARD_PAYMENT,
                Channel.MOBILE,
                "AU",
                "Sydney",
                "PENDING",
                OffsetDateTime.parse("2026-06-23T10:15:30Z"));

        assertThat(validator.validate(request))
                .extracting(violation -> violation.getPropertyPath().toString())
                .contains("accountId");
    }

    @Test
    void requiresPositiveAmount() {
        TransactionRequest request = new TransactionRequest(
                "user-1",
                "acct-1",
                BigDecimal.ZERO,
                CurrencyCode.AUD,
                "GROCERY",
                TransactionType.CARD_PAYMENT,
                Channel.MOBILE,
                "AU",
                "Sydney",
                "PENDING",
                OffsetDateTime.parse("2026-06-23T10:15:30Z"));

        assertThat(validator.validate(request))
                .extracting(violation -> violation.getPropertyPath().toString())
                .contains("amount");
    }

    @Test
    void requiresCurrencyTransactionTypeChannelCountryAndEventTimestamp() {
        TransactionRequest request = new TransactionRequest(
                "user-1",
                "acct-1",
                BigDecimal.TEN,
                null,
                "GROCERY",
                null,
                null,
                "",
                "Sydney",
                "PENDING",
                null);

        assertThat(validator.validate(request))
                .extracting(violation -> violation.getPropertyPath().toString())
                .contains("currency", "transactionType", "channel", "country", "eventTimestamp");
    }

    private static TransactionRequest validRequest() {
        return validRequestWithUserId("user-1");
    }

    private static TransactionRequest validRequestWithUserId(String userId) {
        return new TransactionRequest(
                userId,
                "acct-1",
                BigDecimal.TEN,
                CurrencyCode.AUD,
                "GROCERY",
                TransactionType.CARD_PAYMENT,
                Channel.MOBILE,
                "AU",
                "Sydney",
                "PENDING",
                OffsetDateTime.parse("2026-06-23T10:15:30Z"));
    }
}

