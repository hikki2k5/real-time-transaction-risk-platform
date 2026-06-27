package com.example.fraud.auth.repository;

import java.sql.Timestamp;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class UserRepository {

    private final JdbcTemplate jdbcTemplate;

    public UserRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public UserRecord create(String email, String fullName, String passwordHash) {
        UserRecord user = new UserRecord(
                UUID.randomUUID().toString(),
                email.toLowerCase(),
                fullName,
                passwordHash,
                "CUSTOMER",
                OffsetDateTime.now());
        try {
            jdbcTemplate.update("""
                    INSERT INTO security.users (
                        user_id, email, full_name, password_hash, role, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    user.userId(),
                    user.email(),
                    user.fullName(),
                    user.passwordHash(),
                    user.role(),
                    Timestamp.from(user.createdAt().toInstant()));
        } catch (DuplicateKeyException ex) {
            throw ex;
        }
        return user;
    }

    public Optional<UserRecord> findByEmail(String email) {
        List<UserRecord> records = jdbcTemplate.query("""
                SELECT user_id, email, full_name, password_hash, role, created_at
                FROM security.users
                WHERE email = ?
                """,
                (rs, rowNum) -> new UserRecord(
                        rs.getString("user_id"),
                        rs.getString("email"),
                        rs.getString("full_name"),
                        rs.getString("password_hash"),
                        rs.getString("role"),
                        rs.getObject("created_at", OffsetDateTime.class)),
                email.toLowerCase());
        return records.stream().findFirst();
    }

    public record UserRecord(
            String userId,
            String email,
            String fullName,
            String passwordHash,
            String role,
            OffsetDateTime createdAt) {
    }
}
