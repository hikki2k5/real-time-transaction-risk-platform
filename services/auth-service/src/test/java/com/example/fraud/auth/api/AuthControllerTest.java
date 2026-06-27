package com.example.fraud.auth.api;

import static org.hamcrest.Matchers.not;
import static org.hamcrest.Matchers.blankOrNullString;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.fraud.auth.api.dto.AuthResponse;
import com.example.fraud.auth.config.SecurityConfig;
import com.example.fraud.auth.service.AuthService;
import com.example.fraud.auth.service.AuthUnauthorizedException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(AuthController.class)
@Import(SecurityConfig.class)
@TestPropertySource(properties = {
        "app.jwt.secret=local-test-secret-local-test-secret",
        "app.jwt.issuer=test-auth",
        "app.jwt.ttl-minutes=60"
})
class AuthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private AuthService authService;

    @Test
    void registersUserAndReturnsTokenResponse() throws Exception {
        when(authService.register(any())).thenReturn(authResponse());

        mockMvc.perform(post("/v1/auth/register")
                        .contentType("application/json")
                        .content("""
                                {
                                  "email": "demo@example.com",
                                  "password": "password123",
                                  "fullName": "Demo User"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.access_token", not(blankOrNullString())))
                .andExpect(jsonPath("$.token_type").value("Bearer"))
                .andExpect(jsonPath("$.email").value("demo@example.com"));
    }

    @Test
    void loginFailureReturnsUnauthorized() throws Exception {
        when(authService.login(any())).thenThrow(new AuthUnauthorizedException("invalid email or password"));

        mockMvc.perform(post("/v1/auth/login")
                        .contentType("application/json")
                        .content("""
                                {
                                  "email": "demo@example.com",
                                  "password": "wrong-password"
                                }
                                """))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.status").value("AUTH_UNAUTHORIZED"));
    }

    @Test
    void meRequiresJwt() throws Exception {
        mockMvc.perform(get("/v1/auth/me"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void meReturnsJwtClaims() throws Exception {
        mockMvc.perform(get("/v1/auth/me")
                        .with(jwt()
                                .jwt(token -> token
                                        .subject("user-1")
                                        .claim("email", "demo@example.com")
                                        .claim("role", "CUSTOMER"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value("user-1"))
                .andExpect(jsonPath("$.email").value("demo@example.com"))
                .andExpect(jsonPath("$.role").value("CUSTOMER"));
    }

    private static AuthResponse authResponse() {
        return new AuthResponse(
                "jwt-token",
                "Bearer",
                3600,
                "user-1",
                "demo@example.com",
                "CUSTOMER");
    }
}
