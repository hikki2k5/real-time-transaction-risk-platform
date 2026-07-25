package com.example.fraud.bankingcore.audit;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

import com.example.fraud.bankingcore.api.dto.Channel;
import com.example.fraud.bankingcore.api.dto.CurrencyCode;
import com.example.fraud.bankingcore.api.dto.TransactionAcceptedResponse;
import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import com.example.fraud.bankingcore.api.dto.TransactionType;
import com.example.fraud.bankingcore.kafka.TransactionEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.autoconfigure.jdbc.JdbcTest;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@JdbcTest
@Testcontainers(disabledWithoutDocker = true)
@Import({TransactionAuditRepository.class, TransactionAuditRepositoryTest.JacksonTestConfig.class})
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
class TransactionAuditRepositoryTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

    @DynamicPropertySource
    static void postgresProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private TransactionAuditRepository repository;

    @BeforeEach
    void setUp() {
        jdbcTemplate.execute("CREATE SCHEMA IF NOT EXISTS core");
        jdbcTemplate.execute("""
                CREATE TABLE IF NOT EXISTS core.transaction_requests (
                    transaction_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    amount NUMERIC(18, 2) NOT NULL,
                    currency CHAR(3) NOT NULL,
                    transaction_type TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    fraud_probability NUMERIC(8, 6) NOT NULL,
                    risk_level TEXT NOT NULL,
                    request_payload JSONB NOT NULL,
                    response_payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """);
        jdbcTemplate.execute("""
                CREATE TABLE IF NOT EXISTS core.transaction_audit_logs (
                    audit_id BIGSERIAL PRIMARY KEY,
                    transaction_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    detail JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """);
        jdbcTemplate.execute("TRUNCATE core.transaction_audit_logs, core.transaction_requests");
    }

    @Test
    void recordsAcceptedTransactionAndFindsItByTransactionId() {
        TransactionRequest request = validRequest();
        TransactionEvent event = validEvent();
        TransactionAcceptedResponse response = new TransactionAcceptedResponse(
                "tx-1",
                "evt-1",
                "ACCEPTED",
                "APPROVE",
                new BigDecimal("0.12"),
                "LOW",
                java.util.List.of("LOW_MODEL_SCORE"));

        repository.recordAccepted(event, request, response);

        Integer requestRows = jdbcTemplate.queryForObject("SELECT COUNT(*) FROM core.transaction_requests", Integer.class);
        Integer auditRows = jdbcTemplate.queryForObject("SELECT COUNT(*) FROM core.transaction_audit_logs", Integer.class);
        assertThat(requestRows).isEqualTo(1);
        assertThat(auditRows).isEqualTo(1);

        TransactionAuditRepository.TransactionRecord record = repository.findByTransactionId("tx-1").orElseThrow();
        assertThat(record.userId()).isEqualTo("user-1");
        assertThat(record.decision()).isEqualTo("APPROVE");
    }

    private static TransactionRequest validRequest() {
        return new TransactionRequest(
                "user-1",
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

    private static TransactionEvent validEvent() {
        return new TransactionEvent(
                "evt-1",
                "tx-1",
                "user-1",
                "acct-1",
                BigDecimal.TEN,
                CurrencyCode.AUD,
                "GROCERY",
                TransactionType.CARD_PAYMENT,
                Channel.MOBILE,
                "AU",
                "Sydney",
                "PENDING",
                OffsetDateTime.parse("2026-06-23T10:15:30Z"),
                OffsetDateTime.parse("2026-06-23T10:15:31Z"));
    }

    static class JacksonTestConfig {
        @Bean
        ObjectMapper objectMapper() {
            return new ObjectMapper().findAndRegisterModules();
        }
    }
}
