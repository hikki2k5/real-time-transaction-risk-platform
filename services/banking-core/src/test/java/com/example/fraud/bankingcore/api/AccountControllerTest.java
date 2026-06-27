package com.example.fraud.bankingcore.api;

import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.fraud.bankingcore.account.AccountRepository;
import com.example.fraud.bankingcore.account.AccountRepository.AccountRecord;
import com.example.fraud.bankingcore.config.SecurityConfig;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(AccountController.class)
@Import(SecurityConfig.class)
@TestPropertySource(properties = {
        "app.security.enabled=true",
        "app.security.jwt-secret=local-test-secret-local-test-secret"
})
class AccountControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private AccountRepository accountRepository;

    @Test
    void listsAccountsForAuthenticatedUser() throws Exception {
        when(accountRepository.findByUserId("user-123"))
                .thenReturn(List.of(new AccountRecord("acct-1", "user-123", "ACTIVE", "AUD")));

        mockMvc.perform(get("/v1/accounts")
                        .with(jwt().jwt(token -> token.subject("user-123"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].accountId").value("acct-1"))
                .andExpect(jsonPath("$[0].currency").value("AUD"));
    }

    @Test
    void returnsDemoAccountsWhenNoLocalAccountsExist() throws Exception {
        when(accountRepository.findByUserId("user-123")).thenReturn(List.of());

        mockMvc.perform(get("/v1/accounts")
                        .with(jwt().jwt(token -> token.subject("user-123"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].accountId").value("acct_001"))
                .andExpect(jsonPath("$[0].userId").value("user-123"));
    }
}
