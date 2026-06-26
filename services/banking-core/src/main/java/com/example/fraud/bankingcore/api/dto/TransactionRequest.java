package com.example.fraud.bankingcore.api.dto;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record TransactionRequest(
        @JsonProperty("user_id")
        @NotBlank(message = "user_id is required")
        String userId,

        @JsonProperty("account_id")
        @NotBlank(message = "account_id is required")
        String accountId,

        @NotNull(message = "amount is required")
        @Positive(message = "amount must be greater than 0")
        BigDecimal amount,

        @NotNull(message = "currency is required")
        CurrencyCode currency,

        @JsonProperty("merchant_category")
        String merchantCategory,

        @JsonProperty("transaction_type")
        @NotNull(message = "transaction_type is required")
        TransactionType transactionType,

        @NotNull(message = "channel is required")
        Channel channel,

        @NotBlank(message = "country is required")
        String country,

        String city,

        String status,

        @JsonProperty("event_timestamp")
        @NotNull(message = "event_timestamp is required")
        OffsetDateTime eventTimestamp) {
}

