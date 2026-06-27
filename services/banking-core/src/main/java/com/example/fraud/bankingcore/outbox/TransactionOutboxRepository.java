package com.example.fraud.bankingcore.outbox;

import java.sql.Timestamp;
import java.time.OffsetDateTime;
import java.util.UUID;

import com.example.fraud.bankingcore.kafka.TransactionEvent;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class TransactionOutboxRepository {

    private static final Logger LOGGER = LoggerFactory.getLogger(TransactionOutboxRepository.class);

    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;

    public TransactionOutboxRepository(JdbcTemplate jdbcTemplate, ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = objectMapper;
    }

    public String savePending(TransactionEvent event) {
        String outboxId = UUID.randomUUID().toString();
        try {
            jdbcTemplate.update("""
                    INSERT INTO core.transaction_outbox (
                        outbox_id, aggregate_id, event_type, event_payload, status, created_at
                    )
                    VALUES (?, ?, ?, ?::jsonb, 'PENDING', ?)
                    """,
                    outboxId,
                    event.transactionId(),
                    "TransactionAccepted",
                    toJson(event),
                    Timestamp.from(event.ingestionTimestamp().toInstant()));
        } catch (DataAccessException ex) {
            LOGGER.warn("outbox save skipped transaction_id={}", event.transactionId(), ex);
        }
        return outboxId;
    }

    public void markPublished(String outboxId, OffsetDateTime publishedAt) {
        try {
            jdbcTemplate.update("""
                    UPDATE core.transaction_outbox
                    SET status = 'PUBLISHED',
                        publish_attempts = publish_attempts + 1,
                        published_at = ?
                    WHERE outbox_id = ?
                    """,
                    Timestamp.from(publishedAt.toInstant()),
                    outboxId);
        } catch (DataAccessException ex) {
            LOGGER.warn("outbox publish mark skipped outbox_id={}", outboxId, ex);
        }
    }

    public void markFailed(String outboxId, Exception exception) {
        try {
            jdbcTemplate.update("""
                    UPDATE core.transaction_outbox
                    SET status = 'FAILED',
                        publish_attempts = publish_attempts + 1,
                        last_error = ?
                    WHERE outbox_id = ?
                    """,
                    exception.getMessage(),
                    outboxId);
        } catch (DataAccessException ex) {
            LOGGER.warn("outbox failure mark skipped outbox_id={}", outboxId, ex);
        }
    }

    private String toJson(TransactionEvent event) {
        try {
            return objectMapper.writeValueAsString(event);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("failed to serialize outbox event", ex);
        }
    }
}
