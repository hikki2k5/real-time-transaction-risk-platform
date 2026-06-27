package com.example.fraud.auth.config;

import javax.crypto.spec.SecretKeySpec;

import com.nimbusds.jose.jwk.source.ImmutableSecret;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;

@Configuration
public class JwtEncoderConfig {

    @Bean
    JwtEncoder jwtEncoder(JwtProperties properties) {
        SecretKeySpec secretKey = new SecretKeySpec(
                properties.secret().getBytes(java.nio.charset.StandardCharsets.UTF_8),
                "HmacSHA256");
        return new NimbusJwtEncoder(new ImmutableSecret<>(secretKey));
    }
}
