package com.example.fraud.bankingcore.api;

import com.example.fraud.bankingcore.audit.TransactionAuditRepository;
import com.example.fraud.bankingcore.audit.TransactionAuditRepository.TransactionRecord;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/v1/transactions")
public class CustomerTransactionController {

    private final TransactionAuditRepository transactionAuditRepository;

    public CustomerTransactionController(TransactionAuditRepository transactionAuditRepository) {
        this.transactionAuditRepository = transactionAuditRepository;
    }

    @GetMapping
    public List<TransactionRecord> listTransactions(
            @AuthenticationPrincipal Jwt jwt,
            @RequestParam(name = "limit", defaultValue = "10") int limit) {
        return transactionAuditRepository.findRecentByUserId(currentUserId(jwt), limit);
    }

    private static String currentUserId(Jwt jwt) {
        if (jwt != null && jwt.getSubject() != null && !jwt.getSubject().isBlank()) {
            return jwt.getSubject();
        }
        return "user_001";
    }
}
