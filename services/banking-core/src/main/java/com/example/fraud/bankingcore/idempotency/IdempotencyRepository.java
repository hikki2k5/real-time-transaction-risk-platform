package com.example.fraud.bankingcore.idempotency;

import java.util.List;
import java.util.Optional;

import com.example.fraud.bankingcore.api.dto.TransactionAcceptedResponse;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class IdempotencyRepository {

    private static final Logger LOGGER = LoggerFactory.getLogger(IdempotencyRepository.class);

    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;

    public IdempotencyRepository(JdbcTemplate jdbcTemplate, ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = objectMapper;
    }

    public Optional<IdempotencyRecord> find(String key) {
        try {
            List<IdempotencyRecord> records = jdbcTemplate.query("""
                    SELECT idempotency_key, request_hash, response_payload
                    FROM core.idempotency_keys
                    WHERE idempotency_key = ?
                    """,
                    (rs, rowNum) -> new IdempotencyRecord(
                            rs.getString("idempotency_key"),
                            rs.getString("request_hash"),
                            fromJson(rs.getString("response_payload"))),
                    key);
            return records.stream().findFirst();
        } catch (DataAccessException ex) {
            LOGGER.warn("idempotency lookup skipped key={}", key, ex);
            return Optional.empty();
        }
    }

    public void save(String key, String requestHash, TransactionAcceptedResponse response) {
        try {
            jdbcTemplate.update("""
                    INSERT INTO core.idempotency_keys (
                        idempotency_key, request_hash, transaction_id, response_payload
                    )
                    VALUES (?, ?, ?, ?::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    """,
                    key,
                    requestHash,
                    response.transactionId(),
                    toJson(response));
        } catch (DataAccessException ex) {
            LOGGER.warn("idempotency save skipped key={}", key, ex);
        }
    }

    private String toJson(TransactionAcceptedResponse response) {
        try {
            return objectMapper.writeValueAsString(response);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("failed to serialize idempotency response", ex);
        }
    }

    private TransactionAcceptedResponse fromJson(String value) {
        try {
            return objectMapper.readValue(value, TransactionAcceptedResponse.class);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("failed to parse idempotency response", ex);
        }
    }

    public record IdempotencyRecord(
            String key,
            String requestHash,
            TransactionAcceptedResponse response) {
    }
}
