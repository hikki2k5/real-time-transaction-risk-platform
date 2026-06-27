package com.example.fraud.bankingcore.api;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.math.BigDecimal;
import java.util.List;

import com.example.fraud.bankingcore.api.dto.TransactionAcceptedResponse;
import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import com.example.fraud.bankingcore.config.SecurityConfig;
import com.example.fraud.bankingcore.service.TransactionIngestionService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(TransactionController.class)
@Import(SecurityConfig.class)
@TestPropertySource(properties = {
        "app.security.enabled=true",
        "app.security.jwt-secret=local-test-secret-local-test-secret"
})
class TransactionSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private TransactionIngestionService transactionIngestionService;

    @Test
    void rejectsTransactionRequestWithoutJwtWhenSecurityEnabled() throws Exception {
        mockMvc.perform(post("/v1/internal/transactions")
                        .contentType("application/json")
                        .content(validRequestJson()))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void acceptsTransactionRequestWithJwtWhenSecurityEnabled() throws Exception {
        when(transactionIngestionService.accept(any(), any()))
                .thenReturn(new TransactionAcceptedResponse(
                        "tx-1",
                        "evt-1",
                        "ACCEPTED",
                        "APPROVE",
                        new BigDecimal("0.12"),
                        "LOW",
                        List.of("LOW_MODEL_SCORE")));

        mockMvc.perform(post("/v1/internal/transactions")
                        .with(jwt().jwt(token -> token.subject("jwt-user-123")))
                        .contentType("application/json")
                        .content(validRequestJson()))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.transaction_id").value("tx-1"))
                .andExpect(jsonPath("$.decision").value("APPROVE"));

        ArgumentCaptor<TransactionRequest> requestCaptor = ArgumentCaptor.forClass(TransactionRequest.class);
        verify(transactionIngestionService).accept(requestCaptor.capture(), any());
        org.assertj.core.api.Assertions.assertThat(requestCaptor.getValue().userId()).isEqualTo("jwt-user-123");
    }

    private static String validRequestJson() {
        return """
                {
                  "user_id": "user-1",
                  "account_id": "acct-1",
                  "amount": 42.25,
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
