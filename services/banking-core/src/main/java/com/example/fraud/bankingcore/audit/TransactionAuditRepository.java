package com.example.fraud.bankingcore.audit;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

import com.example.fraud.bankingcore.api.dto.TransactionAcceptedResponse;
import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import com.example.fraud.bankingcore.kafka.TransactionEvent;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class TransactionAuditRepository {

    private static final Logger LOGGER = LoggerFactory.getLogger(TransactionAuditRepository.class);

    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;

    public TransactionAuditRepository(JdbcTemplate jdbcTemplate, ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = objectMapper;
    }

    public void recordAccepted(TransactionEvent event, TransactionRequest request, TransactionAcceptedResponse response) {
        try {
            jdbcTemplate.update("""
                    INSERT INTO core.transaction_requests (
                        transaction_id, event_id, user_id, account_id, amount, currency,
                        transaction_type, channel, decision, fraud_probability, risk_level,
                        request_payload, response_payload, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?::jsonb, ?)
                    ON CONFLICT (transaction_id) DO NOTHING
                    """,
                    response.transactionId(),
                    response.eventId(),
                    request.userId(),
                    request.accountId(),
                    request.amount(),
                    request.currency().name(),
                    request.transactionType().name(),
                    request.channel().name(),
                    response.decision(),
                    response.fraudProbability(),
                    response.riskLevel(),
                    toJson(request),
                    toJson(response),
                    Timestamp.from(event.ingestionTimestamp().toInstant()));

            jdbcTemplate.update("""
                    INSERT INTO core.transaction_audit_logs (
                        transaction_id, event_id, action, detail, created_at
                    )
                    VALUES (?, ?, ?, ?::jsonb, ?)
                    """,
                    response.transactionId(),
                    response.eventId(),
                    "TRANSACTION_ACCEPTED",
                    toJson(response),
                    Timestamp.from(event.ingestionTimestamp().toInstant()));
        } catch (DataAccessException ex) {
            LOGGER.warn("transaction audit persistence failed transaction_id={}", response.transactionId(), ex);
        }
    }

    public Optional<TransactionRecord> findByTransactionId(String transactionId) {
        try {
            List<TransactionRecord> records = jdbcTemplate.query("""
                    SELECT transaction_id, event_id, user_id, account_id, amount, currency,
                           transaction_type, channel, decision, fraud_probability, risk_level, created_at
                    FROM core.transaction_requests
                    WHERE transaction_id = ?
                    """,
                    (rs, rowNum) -> new TransactionRecord(
                            rs.getString("transaction_id"),
                            rs.getString("event_id"),
                            rs.getString("user_id"),
                            rs.getString("account_id"),
                            rs.getBigDecimal("amount"),
                            rs.getString("currency"),
                            rs.getString("transaction_type"),
                            rs.getString("channel"),
                            rs.getString("decision"),
                            rs.getBigDecimal("fraud_probability"),
                            rs.getString("risk_level"),
                            rs.getObject("created_at", OffsetDateTime.class)),
                    transactionId);
            return records.stream().findFirst();
        } catch (DataAccessException ex) {
            LOGGER.warn("transaction lookup failed transaction_id={}", transactionId, ex);
            return Optional.empty();
        }
    }

    public List<TransactionRecord> findRecentByUserId(String userId, int limit) {
        try {
            return jdbcTemplate.query("""
                    SELECT transaction_id, event_id, user_id, account_id, amount, currency,
                           transaction_type, channel, decision, fraud_probability, risk_level, created_at
                    FROM core.transaction_requests
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (rs, rowNum) -> new TransactionRecord(
                            rs.getString("transaction_id"),
                            rs.getString("event_id"),
                            rs.getString("user_id"),
                            rs.getString("account_id"),
                            rs.getBigDecimal("amount"),
                            rs.getString("currency"),
                            rs.getString("transaction_type"),
                            rs.getString("channel"),
                            rs.getString("decision"),
                            rs.getBigDecimal("fraud_probability"),
                            rs.getString("risk_level"),
                            rs.getObject("created_at", OffsetDateTime.class)),
                    userId,
                    Math.max(1, Math.min(limit, 50)));
        } catch (DataAccessException ex) {
            LOGGER.warn("transaction history lookup failed user_id={}", userId, ex);
            return List.of();
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("failed to serialize audit payload", ex);
        }
    }

    public record TransactionRecord(
            String transactionId,
            String eventId,
            String userId,
            String accountId,
            BigDecimal amount,
            String currency,
            String transactionType,
            String channel,
            String decision,
            BigDecimal fraudProbability,
            String riskLevel,
            OffsetDateTime createdAt) {
    }
}
