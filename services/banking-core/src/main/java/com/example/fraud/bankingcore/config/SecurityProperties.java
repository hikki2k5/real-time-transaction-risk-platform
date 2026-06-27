package com.example.fraud.bankingcore.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.security")
public record SecurityProperties(
        boolean enabled,
        String jwtSecret) {
}
