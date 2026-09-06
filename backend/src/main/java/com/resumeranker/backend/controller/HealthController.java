package com.resumeranker.backend.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * Lightweight liveness endpoint. Maps both "/" and "/health" so the root URL
 * returns a clean 200 instead of Spring's default Whitelabel 404.
 */
@RestController
public class HealthController {

    @GetMapping({"/", "/health"})
    public Map<String, String> health() {
        return Map.of(
                "status", "ok",
                "service", "resume-ranker-backend"
        );
    }
}
