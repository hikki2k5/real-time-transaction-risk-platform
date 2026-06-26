package com.example.fraud.bankingcore.api.dto;

import java.math.BigDecimal;
import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

public record TransactionAcceptedResponse(
        @JsonProperty("transaction_id") String transactionId,
        @JsonProperty("event_id") String eventId,
        String status,
        String decision,
        @JsonProperty("fraud_probability") BigDecimal fraudProbability,
        @JsonProperty("risk_level") String riskLevel,
        @JsonProperty("reason_codes") List<String> reasonCodes) {
}
