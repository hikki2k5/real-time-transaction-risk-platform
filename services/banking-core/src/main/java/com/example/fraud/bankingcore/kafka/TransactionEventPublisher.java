package com.example.fraud.bankingcore.kafka;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class TransactionEventPublisher {

    private final KafkaTemplate<String, TransactionEvent> kafkaTemplate;
    private final String topic;

    public TransactionEventPublisher(
            KafkaTemplate<String, TransactionEvent> kafkaTemplate,
            @Value("${app.kafka.transaction-events-topic}") String topic) {
        this.kafkaTemplate = kafkaTemplate;
        this.topic = topic;
    }

    public void publish(TransactionEvent event) {
        kafkaTemplate.send(topic, event.transactionId(), event);
    }
}

