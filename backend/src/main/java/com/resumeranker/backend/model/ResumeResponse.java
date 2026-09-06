package com.resumeranker.backend.model;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class ResumeResponse {
    private String name;
    private double score;
    private int rank;
    private int total;
    private List<Double> topScores;

    private List<String> matchedSkills;
    private List<String> missingSkills;

    private String summary;

    private List<String> education;
    private List<String> experiences;
    private List<String> skills;
    private List<String> certifications;
    private List<String> projects;

    private double experienceRelevanceScore;
    private String seniorityLevel;
    private String careerTrajectory;

    private List<String> experienceHighlights;
    private List<String> impactHighlights;
    private List<String> projectHighlights;

    private double atsCompatibilityScore;

    private Map<String, String> contact;

    private Map<String, Object> verification;

    private List<Map<String, Object>> scoreBreakdown;
}
