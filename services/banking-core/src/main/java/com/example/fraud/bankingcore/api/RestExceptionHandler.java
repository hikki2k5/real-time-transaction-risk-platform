package com.example.fraud.bankingcore.api;

import java.time.OffsetDateTime;
import java.util.List;

import com.example.fraud.bankingcore.account.AccountNotAvailableException;
import com.example.fraud.bankingcore.idempotency.IdempotencyConflictException;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class RestExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiErrorResponse> handleValidation(MethodArgumentNotValidException exception) {
        List<ApiErrorResponse.FieldErrorDetail> errors = exception.getBindingResult()
                .getFieldErrors()
                .stream()
                .map(error -> new ApiErrorResponse.FieldErrorDetail(error.getField(), error.getDefaultMessage()))
                .toList();

        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                .body(new ApiErrorResponse(
                        "BAD_REQUEST",
                        "request validation failed",
                        MDC.get(CorrelationIdFilter.MDC_KEY),
                        OffsetDateTime.now(),
                        errors));
    }

    @ExceptionHandler(AccountNotAvailableException.class)
    public ResponseEntity<ApiErrorResponse> handleAccountNotAvailable(AccountNotAvailableException exception) {
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(new ApiErrorResponse(
                        "ACCOUNT_NOT_AVAILABLE",
                        exception.getMessage(),
                        MDC.get(CorrelationIdFilter.MDC_KEY),
                        OffsetDateTime.now(),
                        List.of()));
    }

    @ExceptionHandler(IdempotencyConflictException.class)
    public ResponseEntity<ApiErrorResponse> handleIdempotencyConflict(IdempotencyConflictException exception) {
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(new ApiErrorResponse(
                        "IDEMPOTENCY_CONFLICT",
                        exception.getMessage(),
                        MDC.get(CorrelationIdFilter.MDC_KEY),
                        OffsetDateTime.now(),
                        List.of()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiErrorResponse> handleUnexpected(Exception exception) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(new ApiErrorResponse(
                        "INTERNAL_SERVER_ERROR",
                        "unexpected server error",
                        MDC.get(CorrelationIdFilter.MDC_KEY),
                        OffsetDateTime.now(),
                        List.of()));
    }
}
