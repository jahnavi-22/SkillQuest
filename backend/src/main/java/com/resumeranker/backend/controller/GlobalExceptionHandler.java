package com.resumeranker.backend.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.HttpStatusCodeException;

import java.util.HashMap;
import java.util.Map;

/**
 * Turns opaque 500s into meaningful responses. Instead of a blank
 * "Internal Server Error", the client gets the real status code and message —
 * including the exact error the ML service (and OpenAI beneath it) returned.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    // Errors from the ML service call (RestTemplate) — pass through its status + body.
    @ExceptionHandler(HttpStatusCodeException.class)
    public ResponseEntity<Map<String, Object>> handleDownstream(HttpStatusCodeException e) {
        Map<String, Object> body = new HashMap<>();
        body.put("error", "ML service error");
        body.put("status", e.getStatusCode().value());
        body.put("detail", e.getResponseBodyAsString());
        return ResponseEntity.status(e.getStatusCode()).body(body);
    }

    // Anything else — return the exception type + message rather than a blank 500.
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleGeneric(Exception e) {
        Map<String, Object> body = new HashMap<>();
        body.put("error", e.getClass().getSimpleName());
        body.put("detail", e.getMessage() != null ? e.getMessage() : "Unexpected error");
        return ResponseEntity.status(500).body(body);
    }
}
