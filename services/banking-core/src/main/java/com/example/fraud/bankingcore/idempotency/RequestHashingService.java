package com.example.fraud.bankingcore.idempotency;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

@Service
public class RequestHashingService {

    private final ObjectMapper objectMapper;

    public RequestHashingService(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public String hash(TransactionRequest request) {
        try {
            byte[] json = objectMapper.writeValueAsBytes(request);
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(json);
            return java.util.HexFormat.of().formatHex(digest);
        } catch (JsonProcessingException | NoSuchAlgorithmException ex) {
            throw new IllegalArgumentException("failed to hash request", ex);
        }
    }
}
