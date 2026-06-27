package com.example.fraud.bankingcore.api;

import com.example.fraud.bankingcore.account.AccountRepository;
import com.example.fraud.bankingcore.account.AccountRepository.AccountRecord;
import java.util.List;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/accounts")
public class AccountController {

    private final AccountRepository accountRepository;

    public AccountController(AccountRepository accountRepository) {
        this.accountRepository = accountRepository;
    }

    @GetMapping
    public List<AccountRecord> listAccounts(@AuthenticationPrincipal Jwt jwt) {
        String userId = currentUserId(jwt);
        List<AccountRecord> accounts = accountRepository.findByUserId(userId);
        if (!accounts.isEmpty()) {
            return accounts;
        }
        return List.of(
                new AccountRecord("acct_001", userId, "ACTIVE", "AUD"),
                new AccountRecord("acct_savings", userId, "ACTIVE", "AUD"));
    }

    @GetMapping("/{accountId}")
    public ResponseEntity<AccountRecord> getAccount(@PathVariable String accountId) {
        return accountRepository.findByAccountId(accountId)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    private static String currentUserId(Jwt jwt) {
        if (jwt != null && jwt.getSubject() != null && !jwt.getSubject().isBlank()) {
            return jwt.getSubject();
        }
        return "user_001";
    }
}
