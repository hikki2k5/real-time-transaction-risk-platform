package com.example.fraud.bankingcore.account;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.Optional;

import com.example.fraud.bankingcore.api.dto.Channel;
import com.example.fraud.bankingcore.api.dto.CurrencyCode;
import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import com.example.fraud.bankingcore.api.dto.TransactionType;
import org.junit.jupiter.api.Test;

class AccountValidationServiceTest {

    @Test
    void allowsActiveAccountForMatchingUser() {
        AccountRepository repository = org.mockito.Mockito.mock(AccountRepository.class);
        when(repository.findByAccountId("acct-1"))
                .thenReturn(Optional.of(new AccountRepository.AccountRecord("acct-1", "user-1", "ACTIVE", "AUD")));
        AccountValidationService service = new AccountValidationService(repository);

        assertThatCode(() -> service.validateAccountCanTransact(validRequest()))
                .doesNotThrowAnyException();
    }

    @Test
    void rejectsFrozenAccount() {
        AccountRepository repository = org.mockito.Mockito.mock(AccountRepository.class);
        when(repository.findByAccountId("acct-1"))
                .thenReturn(Optional.of(new AccountRepository.AccountRecord("acct-1", "user-1", "FROZEN", "AUD")));
        AccountValidationService service = new AccountValidationService(repository);

        assertThatThrownBy(() -> service.validateAccountCanTransact(validRequest()))
                .isInstanceOf(AccountNotAvailableException.class)
                .hasMessage("account is frozen");
    }

    private static TransactionRequest validRequest() {
        return new TransactionRequest(
                "user-1",
                "acct-1",
                BigDecimal.TEN,
                CurrencyCode.AUD,
                "GROCERY",
                TransactionType.CARD_PAYMENT,
                Channel.MOBILE,
                "AU",
                "Sydney",
                "PENDING",
                OffsetDateTime.parse("2026-06-23T10:15:30Z"));
    }
}
