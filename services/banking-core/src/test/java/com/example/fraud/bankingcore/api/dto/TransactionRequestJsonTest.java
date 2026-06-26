package com.example.fraud.bankingcore.api.dto;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.Test;

class TransactionRequestJsonTest {

    private final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule());

    @Test
    void rejectsUnsupportedCurrencyValues() {
        String json = validJson().replace("\"AUD\"", "\"EUR\"");

        assertThatThrownBy(() -> objectMapper.readValue(json, TransactionRequest.class))
                .hasMessageContaining("EUR");
    }

    @Test
    void rejectsUnsupportedTransactionTypeValues() {
        String json = validJson().replace("\"CARD_PAYMENT\"", "\"CRYPTO_PURCHASE\"");

        assertThatThrownBy(() -> objectMapper.readValue(json, TransactionRequest.class))
                .hasMessageContaining("CRYPTO_PURCHASE");
    }

    @Test
    void rejectsUnsupportedChannelValues() {
        String json = validJson().replace("\"MOBILE\"", "\"KIOSK\"");

        assertThatThrownBy(() -> objectMapper.readValue(json, TransactionRequest.class))
                .hasMessageContaining("KIOSK");
    }

    private static String validJson() {
        return """
                {
                  "user_id": "user-1",
                  "account_id": "acct-1",
                  "amount": 10.00,
                  "currency": "AUD",
                  "merchant_category": "GROCERY",
                  "transaction_type": "CARD_PAYMENT",
                  "channel": "MOBILE",
                  "country": "AU",
                  "city": "Sydney",
                  "status": "PENDING",
                  "event_timestamp": "2026-06-23T10:15:30Z"
                }
                """;
    }
}

