package com.example.fraud.bankingcore.kafka;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class TransactionEventPublisher {

    private final KafkaTemplate<String, TransactionEvent> kafkaTemplate;
    private final String topic;
    private final boolean publishEnabled;

    public TransactionEventPublisher(
            KafkaTemplate<String, TransactionEvent> kafkaTemplate,
            @Value("${app.kafka.transaction-events-topic}") String topic,
            @Value("${app.kafka.publish-enabled:true}") boolean publishEnabled) {
        this.kafkaTemplate = kafkaTemplate;
        this.topic = topic;
        this.publishEnabled = publishEnabled;
    }

    public boolean publish(TransactionEvent event) {
        if (!publishEnabled) {
            return false;
        }
        kafkaTemplate.send(topic, event.transactionId(), event);
        return true;
    }
}
