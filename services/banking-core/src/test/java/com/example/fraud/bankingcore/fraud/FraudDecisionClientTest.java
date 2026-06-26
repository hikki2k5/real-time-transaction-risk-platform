package com.example.fraud.bankingcore.fraud;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.jsonPath;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

import com.example.fraud.bankingcore.api.dto.Channel;
import com.example.fraud.bankingcore.api.dto.CurrencyCode;
import com.example.fraud.bankingcore.api.dto.TransactionRequest;
import com.example.fraud.bankingcore.api.dto.TransactionType;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

class FraudDecisionClientTest {

    @Test
    void returnsFraudDecisionFromSuccessfulHttpCall() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        FraudDecisionClient client = new FraudDecisionClient(restTemplate, "http://fraud-api");
        server.expect(once(), requestTo("http://fraud-api/v1/fraud-score"))
                .andExpect(jsonPath("$.transaction_id").value("tx-1"))
                .andExpect(jsonPath("$.user_id").value("user-1"))
                .andRespond(withSuccess("""
                        {
                          "transaction_id": "tx-1",
                          "fraud_probability": 0.82,
                          "risk_level": "HIGH",
                          "decision": "BLOCK",
                          "model_name": "fraud-risk-model",
                          "model_version": "xgboost",
                          "reason_codes": ["HIGH_MODEL_SCORE"]
                        }
                        """, MediaType.APPLICATION_JSON));

        FraudDecision decision = client.score("tx-1", validRequest());

        assertThat(decision.decision()).isEqualTo("BLOCK");
        assertThat(decision.fraudProbability()).isEqualByComparingTo("0.82");
        assertThat(decision.riskLevel()).isEqualTo("HIGH");
        assertThat(decision.reasonCodes()).containsExactly("HIGH_MODEL_SCORE");
        server.verify();
    }

    @Test
    void returnsReviewFallbackWhenFraudApiFails() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        FraudDecisionClient client = new FraudDecisionClient(restTemplate, "http://fraud-api");
        server.expect(once(), requestTo("http://fraud-api/v1/fraud-score"))
                .andRespond(withServerError());

        FraudDecision decision = client.score("tx-1", validRequest());

        assertThat(decision.decision()).isEqualTo("REVIEW");
        assertThat(decision.fraudProbability()).isEqualByComparingTo("0");
        assertThat(decision.riskLevel()).isEqualTo("MEDIUM");
        assertThat(decision.reasonCodes()).containsExactly("fraud service unavailable");
        server.verify();
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
