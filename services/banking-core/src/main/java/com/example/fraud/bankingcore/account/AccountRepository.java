package com.example.fraud.bankingcore.account;

import java.util.List;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class AccountRepository {

    private static final Logger LOGGER = LoggerFactory.getLogger(AccountRepository.class);

    private final JdbcTemplate jdbcTemplate;

    public AccountRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public Optional<AccountRecord> findByAccountId(String accountId) {
        try {
            List<AccountRecord> records = jdbcTemplate.query("""
                    SELECT account_id, user_id, status, currency
                    FROM core.accounts
                    WHERE account_id = ?
                    """,
                    (rs, rowNum) -> new AccountRecord(
                            rs.getString("account_id"),
                            rs.getString("user_id"),
                            rs.getString("status"),
                            rs.getString("currency")),
                    accountId);
            return records.stream().findFirst();
        } catch (DataAccessException ex) {
            LOGGER.warn("account lookup skipped account_id={}", accountId, ex);
            return Optional.empty();
        }
    }

    public List<AccountRecord> findByUserId(String userId) {
        try {
            return jdbcTemplate.query("""
                    SELECT account_id, user_id, status, currency
                    FROM core.accounts
                    WHERE user_id = ?
                    ORDER BY created_at, account_id
                    """,
                    (rs, rowNum) -> new AccountRecord(
                            rs.getString("account_id"),
                            rs.getString("user_id"),
                            rs.getString("status"),
                            rs.getString("currency")),
                    userId);
        } catch (DataAccessException ex) {
            LOGGER.warn("account list lookup skipped user_id={}", userId, ex);
            return List.of();
        }
    }

    public record AccountRecord(
            String accountId,
            String userId,
            String status,
            String currency) {
    }
}
