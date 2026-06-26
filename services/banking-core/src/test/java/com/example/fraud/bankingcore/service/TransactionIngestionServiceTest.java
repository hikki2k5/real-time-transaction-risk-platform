package com.example.fraud.bankingcore.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;

import com.example.fraud.bankingcore.api.dto.Channel;
import com.example.fraud.bankingcore.api.dto.CurrencyCode;
import com.example.fraud.bankingcore.api.dto.TransactionAcceptedResponse;
import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import com.example.fraud.bankingcore.api.dto.TransactionType;
import com.example.fraud.bankingcore.fraud.FraudDecision;
import com.example.fraud.bankingcore.fraud.FraudDecisionClient;
import com.example.fraud.bankingcore.kafka.TransactionEvent;
import com.example.fraud.bankingcore.kafka.TransactionEventPublisher;
import org.junit.jupiter.api.Test;

class TransactionIngestionServiceTest {

    @Test
    void generatesIdsAndPublishesAcceptedTransactionEvent() {
        TransactionEventPublisher publisher = org.mockito.Mockito.mock(TransactionEventPublisher.class);
        FraudDecisionClient fraudDecisionClient = org.mockito.Mockito.mock(FraudDecisionClient.class);
        Clock clock = Clock.fixed(Instant.parse("2026-06-23T10:15:31Z"), ZoneOffset.UTC);
        when(fraudDecisionClient.score(any(String.class), any(TransactionRequest.class)))
                .thenReturn(new FraudDecision("APPROVE", new BigDecimal("0.12"), "LOW", java.util.List.of("LOW_MODEL_SCORE")));
        TransactionIngestionService service = new TransactionIngestionService(publisher, fraudDecisionClient, clock);

        TransactionAcceptedResponse response = service.accept(validRequest());

        assertThat(response.status()).isEqualTo("ACCEPTED");
        assertThat(response.eventId()).isNotBlank();
        assertThat(response.transactionId()).isNotBlank();
        assertThat(response.decision()).isEqualTo("APPROVE");
        assertThat(response.fraudProbability()).isEqualByComparingTo("0.12");
        assertThat(response.riskLevel()).isEqualTo("LOW");
        assertThat(response.reasonCodes()).containsExactly("LOW_MODEL_SCORE");
        verify(publisher).publish(any(TransactionEvent.class));
    }

    @Test
    void returnsFraudDecisionFromSuccessfulFraudApiCall() {
        TransactionEventPublisher publisher = org.mockito.Mockito.mock(TransactionEventPublisher.class);
        FraudDecisionClient fraudDecisionClient = org.mockito.Mockito.mock(FraudDecisionClient.class);
        TransactionIngestionService service = new TransactionIngestionService(
                publisher,
                fraudDecisionClient,
                Clock.fixed(Instant.parse("2026-06-23T10:15:31Z"), ZoneOffset.UTC));
        when(fraudDecisionClient.score(any(String.class), any(TransactionRequest.class)))
                .thenReturn(new FraudDecision(
                        "BLOCK",
                        new BigDecimal("0.91"),
                        "HIGH",
                        java.util.List.of("HIGH_MODEL_SCORE", "HIGH_AMOUNT")));

        TransactionAcceptedResponse response = service.accept(validRequest());

        assertThat(response.decision()).isEqualTo("BLOCK");
        assertThat(response.fraudProbability()).isEqualByComparingTo("0.91");
        assertThat(response.riskLevel()).isEqualTo("HIGH");
        assertThat(response.reasonCodes()).containsExactly("HIGH_MODEL_SCORE", "HIGH_AMOUNT");
    }

    @Test
    void returnsReviewFallbackWhenFraudApiTimesOutAndStillPublishesKafkaEvent() {
        TransactionEventPublisher publisher = org.mockito.Mockito.mock(TransactionEventPublisher.class);
        FraudDecisionClient fraudDecisionClient = org.mockito.Mockito.mock(FraudDecisionClient.class);
        TransactionRequest request = validRequest();
        TransactionIngestionService service = new TransactionIngestionService(
                publisher,
                fraudDecisionClient,
                Clock.fixed(Instant.parse("2026-06-23T10:15:31Z"), ZoneOffset.UTC));
        when(fraudDecisionClient.score(any(String.class), eq(request)))
                .thenReturn(FraudDecision.reviewFallback());

        TransactionAcceptedResponse response = service.accept(request);

        assertThat(response.decision()).isEqualTo("REVIEW");
        assertThat(response.fraudProbability()).isEqualByComparingTo("0");
        assertThat(response.riskLevel()).isEqualTo("MEDIUM");
        assertThat(response.reasonCodes()).containsExactly("fraud service unavailable");
        verify(publisher).publish(any(TransactionEvent.class));
        verify(fraudDecisionClient).score(eq(response.transactionId()), eq(request));
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
