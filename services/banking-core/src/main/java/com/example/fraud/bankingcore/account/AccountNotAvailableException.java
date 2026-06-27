package com.example.fraud.bankingcore.account;

public class AccountNotAvailableException extends RuntimeException {

    public AccountNotAvailableException(String message) {
        super(message);
    }
}
