package com.example.fraud.bankingcore.service;

import java.time.Clock;
import java.time.OffsetDateTime;
import java.util.UUID;

import com.example.fraud.bankingcore.api.dto.TransactionAcceptedResponse;
import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import com.example.fraud.bankingcore.fraud.FraudDecision;
import com.example.fraud.bankingcore.fraud.FraudDecisionClient;
import com.example.fraud.bankingcore.kafka.TransactionEvent;
import com.example.fraud.bankingcore.kafka.TransactionEventPublisher;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class TransactionIngestionService {

    private final TransactionEventPublisher transactionEventPublisher;
    private final FraudDecisionClient fraudDecisionClient;
    private final Clock clock;

    @Autowired
    public TransactionIngestionService(
            TransactionEventPublisher transactionEventPublisher,
            FraudDecisionClient fraudDecisionClient) {
        this(transactionEventPublisher, fraudDecisionClient, Clock.systemUTC());
    }

    TransactionIngestionService(
            TransactionEventPublisher transactionEventPublisher,
            FraudDecisionClient fraudDecisionClient,
            Clock clock) {
        this.transactionEventPublisher = transactionEventPublisher;
        this.fraudDecisionClient = fraudDecisionClient;
        this.clock = clock;
    }

    public TransactionAcceptedResponse accept(TransactionRequest request) {
        String eventId = UUID.randomUUID().toString();
        String transactionId = UUID.randomUUID().toString();
        OffsetDateTime ingestionTimestamp = OffsetDateTime.now(clock);

        TransactionEvent event = new TransactionEvent(
                eventId,
                transactionId,
                request.userId(),
                request.accountId(),
                request.amount(),
                request.currency(),
                request.merchantCategory(),
                request.transactionType(),
                request.channel(),
                request.country(),
                request.city(),
                request.status(),
                request.eventTimestamp(),
                ingestionTimestamp);

        transactionEventPublisher.publish(event);
        FraudDecision fraudDecision = fraudDecisionClient.score(transactionId, request);

        return new TransactionAcceptedResponse(
                transactionId,
                eventId,
                "ACCEPTED",
                fraudDecision.decision(),
                fraudDecision.fraudProbability(),
                fraudDecision.riskLevel(),
                fraudDecision.reasonCodes());
    }
}
