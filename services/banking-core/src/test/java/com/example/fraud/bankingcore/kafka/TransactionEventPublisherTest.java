package com.example.fraud.bankingcore.kafka;

import static org.mockito.Mockito.verify;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

import com.example.fraud.bankingcore.api.dto.Channel;
import com.example.fraud.bankingcore.api.dto.CurrencyCode;
import com.example.fraud.bankingcore.api.dto.TransactionType;
import org.junit.jupiter.api.Test;
import org.springframework.kafka.core.KafkaTemplate;

@SuppressWarnings("unchecked")
class TransactionEventPublisherTest {

    @Test
    void publishesTransactionEventToConfiguredTopicWithTransactionIdKey() {
        KafkaTemplate<String, TransactionEvent> kafkaTemplate = org.mockito.Mockito.mock(KafkaTemplate.class);
        TransactionEventPublisher publisher = new TransactionEventPublisher(kafkaTemplate, "transaction_events");
        TransactionEvent event = new TransactionEvent(
                "event-1",
                "transaction-1",
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
                OffsetDateTime.parse("2026-06-23T10:15:30Z"),
                OffsetDateTime.parse("2026-06-23T10:15:31Z"));

        publisher.publish(event);

        verify(kafkaTemplate).send("transaction_events", "transaction-1", event);
    }
}

