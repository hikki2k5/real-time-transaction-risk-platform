package com.example.fraud.auth.api;

import java.time.OffsetDateTime;
import java.util.List;

import com.example.fraud.auth.service.AuthConflictException;
import com.example.fraud.auth.service.AuthUnauthorizedException;
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
                .body(new ApiErrorResponse("BAD_REQUEST", "request validation failed", OffsetDateTime.now(), errors));
    }

    @ExceptionHandler(AuthConflictException.class)
    public ResponseEntity<ApiErrorResponse> handleConflict(AuthConflictException exception) {
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(new ApiErrorResponse("AUTH_CONFLICT", exception.getMessage(), OffsetDateTime.now(), List.of()));
    }

    @ExceptionHandler(AuthUnauthorizedException.class)
    public ResponseEntity<ApiErrorResponse> handleUnauthorized(AuthUnauthorizedException exception) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(new ApiErrorResponse("AUTH_UNAUTHORIZED", exception.getMessage(), OffsetDateTime.now(), List.of()));
    }

    public record ApiErrorResponse(
            String status,
            String message,
            OffsetDateTime timestamp,
            List<FieldErrorDetail> errors) {

        public record FieldErrorDetail(String field, String message) {
        }
    }
}
