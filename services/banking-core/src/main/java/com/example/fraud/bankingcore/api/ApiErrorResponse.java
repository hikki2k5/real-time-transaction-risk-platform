package com.example.fraud.bankingcore.api;

import java.time.OffsetDateTime;
import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

public record ApiErrorResponse(
        String status,
        String message,
        @JsonProperty("correlation_id") String correlationId,
        OffsetDateTime timestamp,
        List<FieldErrorDetail> errors) {

    public record FieldErrorDetail(String field, String message) {
    }
}
