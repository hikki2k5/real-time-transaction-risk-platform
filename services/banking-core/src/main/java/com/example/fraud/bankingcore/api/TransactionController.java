package com.example.fraud.bankingcore.api;

import com.example.fraud.bankingcore.api.dto.TransactionAcceptedResponse;
import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import com.example.fraud.bankingcore.audit.TransactionAuditRepository.TransactionRecord;
import com.example.fraud.bankingcore.service.TransactionIngestionService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping({"/internal/transactions", "/v1/internal/transactions"})
public class TransactionController {

    private final TransactionIngestionService transactionIngestionService;

    public TransactionController(TransactionIngestionService transactionIngestionService) {
        this.transactionIngestionService = transactionIngestionService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.ACCEPTED)
    public TransactionAcceptedResponse createTransaction(
            @RequestHeader(name = "Idempotency-Key", required = false) String idempotencyKey,
            @AuthenticationPrincipal Jwt jwt,
            @Valid @RequestBody TransactionRequest request) {
        return transactionIngestionService.accept(requestForAuthenticatedUser(request, jwt), idempotencyKey);
    }

    @GetMapping("/{transactionId}")
    public ResponseEntity<TransactionRecord> getTransaction(@PathVariable String transactionId) {
        return transactionIngestionService.findByTransactionId(transactionId)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    private static TransactionRequest requestForAuthenticatedUser(TransactionRequest request, Jwt jwt) {
        if (jwt == null || jwt.getSubject() == null || jwt.getSubject().isBlank()) {
            return request;
        }
        return new TransactionRequest(
                jwt.getSubject(),
                request.accountId(),
                request.amount(),
                request.currency(),
                request.merchantCategory(),
                request.transactionType(),
                request.channel(),
                request.country(),
                request.city(),
                request.status(),
                request.eventTimestamp());
    }
}
