package com.example.fraud.bankingcore.fraud;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;

import com.example.fraud.bankingcore.api.dto.Channel;
import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import com.fasterxml.jackson.annotation.JsonProperty;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.retry.annotation.Retry;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

@Component
public class FraudDecisionClient {

    private final RestTemplate restTemplate;
    private final String fraudScoreUrl;

    @Autowired
    public FraudDecisionClient(
            RestTemplateBuilder restTemplateBuilder,
            @Value("${app.fraud-api.base-url}") String fraudApiBaseUrl,
            @Value("${app.fraud-api.connect-timeout-ms}") long connectTimeoutMs,
            @Value("${app.fraud-api.read-timeout-ms}") long readTimeoutMs) {
        this.restTemplate = restTemplateBuilder
                .setConnectTimeout(java.time.Duration.ofMillis(connectTimeoutMs))
                .setReadTimeout(java.time.Duration.ofMillis(readTimeoutMs))
                .build();
        this.fraudScoreUrl = fraudApiBaseUrl + "/v1/fraud-score";
    }

    FraudDecisionClient(RestTemplate restTemplate, String fraudApiBaseUrl) {
        this.restTemplate = restTemplate;
        this.fraudScoreUrl = fraudApiBaseUrl + "/v1/fraud-score";
    }

    @Retry(name = "fraudDecisionApi", fallbackMethod = "fallback")
    @CircuitBreaker(name = "fraudDecisionApi", fallbackMethod = "fallback")
    public FraudDecision score(String transactionId, TransactionRequest request) {
        FraudScoreRequest fraudRequest = new FraudScoreRequest(
                transactionId,
                request.userId(),
                request.amount(),
                request.merchantCategory(),
                request.country(),
                request.channel(),
                request.eventTimestamp());

        try {
            FraudScoreResponse response = restTemplate.postForObject(fraudScoreUrl, fraudRequest, FraudScoreResponse.class);
            if (response == null) {
                return FraudDecision.reviewFallback();
            }
            return new FraudDecision(
                    response.decision(),
                    response.fraudProbability(),
                    response.riskLevel(),
                    response.reasonCodes() == null ? List.of() : response.reasonCodes());
        } catch (RestClientException ex) {
            return FraudDecision.reviewFallback();
        }
    }

    @SuppressWarnings("unused")
    private FraudDecision fallback(String transactionId, TransactionRequest request, Throwable throwable) {
        return FraudDecision.reviewFallback();
    }

    private record FraudScoreRequest(
            @JsonProperty("transaction_id") String transactionId,
            @JsonProperty("user_id") String userId,
            BigDecimal amount,
            @JsonProperty("merchant_category") String merchantCategory,
            String country,
            Channel channel,
            @JsonProperty("event_timestamp") OffsetDateTime eventTimestamp) {
    }

    private record FraudScoreResponse(
            @JsonProperty("fraud_probability") BigDecimal fraudProbability,
            @JsonProperty("risk_level") String riskLevel,
            String decision,
            @JsonProperty("reason_codes") List<String> reasonCodes) {
    }
}
