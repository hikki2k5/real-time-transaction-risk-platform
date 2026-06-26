package com.example.fraud.bankingcore.kafka;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

import com.example.fraud.bankingcore.api.dto.Channel;
import com.example.fraud.bankingcore.api.dto.CurrencyCode;
import com.example.fraud.bankingcore.api.dto.TransactionType;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonProperty;

public record TransactionEvent(
        @JsonProperty("event_id") String eventId,
        @JsonProperty("transaction_id") String transactionId,
        @JsonProperty("user_id") String userId,
        @JsonProperty("account_id") String accountId,
        BigDecimal amount,
        CurrencyCode currency,
        @JsonProperty("merchant_category") String merchantCategory,
        @JsonProperty("transaction_type") TransactionType transactionType,
        Channel channel,
        String country,
        String city,
        String status,
        @JsonProperty("event_timestamp")
        @JsonFormat(shape = JsonFormat.Shape.STRING)
        OffsetDateTime eventTimestamp,
        @JsonProperty("ingestion_timestamp")
        @JsonFormat(shape = JsonFormat.Shape.STRING)
        OffsetDateTime ingestionTimestamp) {
}
