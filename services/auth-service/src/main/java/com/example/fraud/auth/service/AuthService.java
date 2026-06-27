package com.example.fraud.auth.service;

import com.example.fraud.auth.api.dto.AuthResponse;
import com.example.fraud.auth.api.dto.LoginRequest;
import com.example.fraud.auth.api.dto.RegisterRequest;
import com.example.fraud.auth.repository.UserRepository;
import com.example.fraud.auth.repository.UserRepository.UserRecord;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenService jwtTokenService;

    public AuthService(
            UserRepository userRepository,
            PasswordEncoder passwordEncoder,
            JwtTokenService jwtTokenService) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtTokenService = jwtTokenService;
    }

    public AuthResponse register(RegisterRequest request) {
        try {
            UserRecord user = userRepository.create(
                    request.email(),
                    request.fullName(),
                    passwordEncoder.encode(request.password()));
            return toResponse(user);
        } catch (DuplicateKeyException ex) {
            throw new AuthConflictException("email is already registered");
        }
    }

    public AuthResponse login(LoginRequest request) {
        UserRecord user = userRepository.findByEmail(request.email())
                .orElseThrow(() -> new AuthUnauthorizedException("invalid email or password"));
        if (!passwordEncoder.matches(request.password(), user.passwordHash())) {
            throw new AuthUnauthorizedException("invalid email or password");
        }
        return toResponse(user);
    }

    private AuthResponse toResponse(UserRecord user) {
        JwtTokenService.TokenResult token = jwtTokenService.issue(user);
        return new AuthResponse(
                token.accessToken(),
                "Bearer",
                token.expiresIn(),
                user.userId(),
                user.email(),
                user.role());
    }
}
