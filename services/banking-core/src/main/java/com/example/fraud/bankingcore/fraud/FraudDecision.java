package com.example.fraud.bankingcore.fraud;

import java.math.BigDecimal;
import java.util.List;

public record FraudDecision(
        String decision,
        BigDecimal fraudProbability,
        String riskLevel,
        List<String> reasonCodes) {

    public static FraudDecision reviewFallback() {
        return new FraudDecision(
                "REVIEW",
                BigDecimal.ZERO,
                "MEDIUM",
                List.of("fraud service unavailable"));
    }
}
