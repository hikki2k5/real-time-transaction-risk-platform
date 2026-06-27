package com.example.fraud.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import java.time.OffsetDateTime;
import java.util.Optional;

import com.example.fraud.auth.api.dto.LoginRequest;
import com.example.fraud.auth.api.dto.RegisterRequest;
import com.example.fraud.auth.repository.UserRepository;
import com.example.fraud.auth.repository.UserRepository.UserRecord;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

class AuthServiceTest {

    @Test
    void loginReturnsJwtForValidPassword() {
        UserRepository repository = org.mockito.Mockito.mock(UserRepository.class);
        BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();
        JwtTokenService tokenService = org.mockito.Mockito.mock(JwtTokenService.class);
        when(repository.findByEmail("demo@example.com"))
                .thenReturn(Optional.of(user(passwordEncoder.encode("password123"))));
        when(tokenService.issue(org.mockito.Mockito.any()))
                .thenReturn(new JwtTokenService.TokenResult("jwt-token", 3600));
        AuthService service = new AuthService(repository, passwordEncoder, tokenService);

        var response = service.login(new LoginRequest("demo@example.com", "password123"));

        assertThat(response.accessToken()).isEqualTo("jwt-token");
        assertThat(response.email()).isEqualTo("demo@example.com");
    }

    @Test
    void loginRejectsInvalidPassword() {
        UserRepository repository = org.mockito.Mockito.mock(UserRepository.class);
        BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();
        JwtTokenService tokenService = org.mockito.Mockito.mock(JwtTokenService.class);
        when(repository.findByEmail(anyString()))
                .thenReturn(Optional.of(user(passwordEncoder.encode("password123"))));
        AuthService service = new AuthService(repository, passwordEncoder, tokenService);

        assertThatThrownBy(() -> service.login(new LoginRequest("demo@example.com", "wrong")))
                .isInstanceOf(AuthUnauthorizedException.class);
    }

    @Test
    void registerHashesPasswordAndReturnsToken() {
        UserRepository repository = org.mockito.Mockito.mock(UserRepository.class);
        BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();
        JwtTokenService tokenService = org.mockito.Mockito.mock(JwtTokenService.class);
        when(repository.create(anyString(), anyString(), anyString())).thenAnswer(invocation ->
                new UserRecord(
                        "user-1",
                        invocation.getArgument(0),
                        invocation.getArgument(1),
                        invocation.getArgument(2),
                        "CUSTOMER",
                        OffsetDateTime.now()));
        when(tokenService.issue(org.mockito.Mockito.any()))
                .thenReturn(new JwtTokenService.TokenResult("jwt-token", 3600));
        AuthService service = new AuthService(repository, passwordEncoder, tokenService);

        var response = service.register(new RegisterRequest("demo@example.com", "password123", "Demo User"));

        assertThat(response.accessToken()).isEqualTo("jwt-token");
        assertThat(response.email()).isEqualTo("demo@example.com");
    }

    private static UserRecord user(String passwordHash) {
        return new UserRecord(
                "user-1",
                "demo@example.com",
                "Demo User",
                passwordHash,
                "CUSTOMER",
                OffsetDateTime.now());
    }
}
