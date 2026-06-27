package com.example.fraud.auth.api.dto;

public record MeResponse(
        String userId,
        String email,
        String role) {
}
