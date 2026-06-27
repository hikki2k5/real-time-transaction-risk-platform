package com.example.fraud.bankingcore.api;

import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.fraud.bankingcore.audit.TransactionAuditRepository;
import com.example.fraud.bankingcore.audit.TransactionAuditRepository.TransactionRecord;
import com.example.fraud.bankingcore.config.SecurityConfig;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(CustomerTransactionController.class)
@Import(SecurityConfig.class)
@TestPropertySource(properties = {
        "app.security.enabled=true",
        "app.security.jwt-secret=local-test-secret-local-test-secret"
})
class CustomerTransactionControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private TransactionAuditRepository transactionAuditRepository;

    @Test
    void listsRecentTransactionsForAuthenticatedUser() throws Exception {
        when(transactionAuditRepository.findRecentByUserId("user-123", 10))
                .thenReturn(List.of(new TransactionRecord(
                        "tx-1",
                        "evt-1",
                        "user-123",
                        "acct-1",
                        new BigDecimal("125.50"),
                        "AUD",
                        "CARD_PAYMENT",
                        "WEB",
                        "APPROVE",
                        new BigDecimal("0.120000"),
                        "LOW",
                        OffsetDateTime.parse("2026-06-23T10:15:30Z"))));

        mockMvc.perform(get("/v1/transactions")
                        .with(jwt().jwt(token -> token.subject("user-123"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].transactionId").value("tx-1"))
                .andExpect(jsonPath("$[0].decision").value("APPROVE"));
    }
}
