package com.example.fraud.bankingcore.account;

import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import org.springframework.stereotype.Service;

@Service
public class AccountValidationService {

    private final AccountRepository accountRepository;

    public AccountValidationService(AccountRepository accountRepository) {
        this.accountRepository = accountRepository;
    }

    public void validateAccountCanTransact(TransactionRequest request) {
        accountRepository.findByAccountId(request.accountId()).ifPresent(account -> {
            if (!account.userId().equals(request.userId())) {
                throw new AccountNotAvailableException("account does not belong to user");
            }
            if (!"ACTIVE".equals(account.status())) {
                throw new AccountNotAvailableException("account is " + account.status().toLowerCase());
            }
        });
    }
}
