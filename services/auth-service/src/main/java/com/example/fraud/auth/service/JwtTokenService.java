package com.example.fraud.auth.service;

import java.time.Instant;
import java.util.Map;

import com.example.fraud.auth.config.JwtProperties;
import com.example.fraud.auth.repository.UserRepository.UserRecord;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Service;

@Service
public class JwtTokenService {

    private final JwtEncoder jwtEncoder;
    private final JwtProperties properties;

    public JwtTokenService(JwtEncoder jwtEncoder, JwtProperties properties) {
        this.jwtEncoder = jwtEncoder;
        this.properties = properties;
    }

    public TokenResult issue(UserRecord user) {
        Instant now = Instant.now();
        Instant expiresAt = now.plusSeconds(properties.ttlMinutes() * 60);
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(properties.issuer())
                .issuedAt(now)
                .expiresAt(expiresAt)
                .subject(user.userId())
                .claims(extraClaims -> extraClaims.putAll(Map.of(
                        "email", user.email(),
                        "role", user.role())))
                .build();
        String token = jwtEncoder.encode(JwtEncoderParameters.from(
                JwsHeader.with(MacAlgorithm.HS256).build(),
                claims)).getTokenValue();
        return new TokenResult(token, properties.ttlMinutes() * 60);
    }

    public record TokenResult(String accessToken, long expiresIn) {
    }
}
