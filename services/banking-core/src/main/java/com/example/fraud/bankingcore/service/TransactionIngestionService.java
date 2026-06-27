package com.example.fraud.bankingcore.service;

import java.time.Clock;
import java.time.OffsetDateTime;
import java.util.Optional;
import java.util.UUID;

import com.example.fraud.bankingcore.api.dto.TransactionAcceptedResponse;
import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import com.example.fraud.bankingcore.account.AccountValidationService;
import com.example.fraud.bankingcore.audit.TransactionAuditRepository;
import com.example.fraud.bankingcore.fraud.FraudDecision;
import com.example.fraud.bankingcore.fraud.FraudDecisionClient;
import com.example.fraud.bankingcore.idempotency.IdempotencyConflictException;
import com.example.fraud.bankingcore.idempotency.IdempotencyRepository;
import com.example.fraud.bankingcore.idempotency.RequestHashingService;
import com.example.fraud.bankingcore.kafka.TransactionEvent;
import com.example.fraud.bankingcore.kafka.TransactionEventPublisher;
import com.example.fraud.bankingcore.outbox.TransactionOutboxRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class TransactionIngestionService {

    private final TransactionEventPublisher transactionEventPublisher;
    private final FraudDecisionClient fraudDecisionClient;
    private final TransactionAuditRepository transactionAuditRepository;
    private final AccountValidationService accountValidationService;
    private final IdempotencyRepository idempotencyRepository;
    private final RequestHashingService requestHashingService;
    private final TransactionOutboxRepository transactionOutboxRepository;
    private final Clock clock;

    @Autowired
    public TransactionIngestionService(
            TransactionEventPublisher transactionEventPublisher,
            FraudDecisionClient fraudDecisionClient,
            TransactionAuditRepository transactionAuditRepository,
            AccountValidationService accountValidationService,
            IdempotencyRepository idempotencyRepository,
            RequestHashingService requestHashingService,
            TransactionOutboxRepository transactionOutboxRepository) {
        this(
                transactionEventPublisher,
                fraudDecisionClient,
                transactionAuditRepository,
                accountValidationService,
                idempotencyRepository,
                requestHashingService,
                transactionOutboxRepository,
                Clock.systemUTC());
    }

    TransactionIngestionService(
            TransactionEventPublisher transactionEventPublisher,
            FraudDecisionClient fraudDecisionClient,
            TransactionAuditRepository transactionAuditRepository,
            AccountValidationService accountValidationService,
            IdempotencyRepository idempotencyRepository,
            RequestHashingService requestHashingService,
            TransactionOutboxRepository transactionOutboxRepository,
            Clock clock) {
        this.transactionEventPublisher = transactionEventPublisher;
        this.fraudDecisionClient = fraudDecisionClient;
        this.transactionAuditRepository = transactionAuditRepository;
        this.accountValidationService = accountValidationService;
        this.idempotencyRepository = idempotencyRepository;
        this.requestHashingService = requestHashingService;
        this.transactionOutboxRepository = transactionOutboxRepository;
        this.clock = clock;
    }

    public TransactionAcceptedResponse accept(TransactionRequest request, String idempotencyKey) {
        String requestHash = requestHashingService.hash(request);
        Optional<String> normalizedIdempotencyKey = normalize(idempotencyKey);
        if (normalizedIdempotencyKey.isPresent()) {
            Optional<IdempotencyRepository.IdempotencyRecord> existing =
                    idempotencyRepository.find(normalizedIdempotencyKey.get());
            if (existing.isPresent()) {
                if (!existing.get().requestHash().equals(requestHash)) {
                    throw new IdempotencyConflictException("idempotency key was already used with a different request");
                }
                return existing.get().response();
            }
        }

        accountValidationService.validateAccountCanTransact(request);

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

        FraudDecision fraudDecision = fraudDecisionClient.score(transactionId, request);

        TransactionAcceptedResponse response = new TransactionAcceptedResponse(
                transactionId,
                eventId,
                "ACCEPTED",
                fraudDecision.decision(),
                fraudDecision.fraudProbability(),
                fraudDecision.riskLevel(),
                fraudDecision.reasonCodes());

        transactionAuditRepository.recordAccepted(event, request, response);
        normalizedIdempotencyKey.ifPresent(key -> idempotencyRepository.save(key, requestHash, response));
        String outboxId = transactionOutboxRepository.savePending(event);
        try {
            boolean published = transactionEventPublisher.publish(event);
            if (published) {
                transactionOutboxRepository.markPublished(outboxId, OffsetDateTime.now(clock));
            }
        } catch (RuntimeException ex) {
            transactionOutboxRepository.markFailed(outboxId, ex);
            throw ex;
        }
        return response;
    }

    public java.util.Optional<TransactionAuditRepository.TransactionRecord> findByTransactionId(String transactionId) {
        return transactionAuditRepository.findByTransactionId(transactionId);
    }

    private static Optional<String> normalize(String value) {
        if (value == null || value.isBlank()) {
            return Optional.empty();
        }
        return Optional.of(value.trim());
    }
}
