package com.example.fraud.bankingcore.api;

import com.example.fraud.bankingcore.api.dto.TransactionAcceptedResponse;
import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import com.example.fraud.bankingcore.service.TransactionIngestionService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/transactions")
public class TransactionController {

    private final TransactionIngestionService transactionIngestionService;

    public TransactionController(TransactionIngestionService transactionIngestionService) {
        this.transactionIngestionService = transactionIngestionService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.ACCEPTED)
    public TransactionAcceptedResponse createTransaction(@Valid @RequestBody TransactionRequest request) {
        return transactionIngestionService.accept(request);
    }
}

