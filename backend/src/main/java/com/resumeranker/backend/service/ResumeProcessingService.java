package com.resumeranker.backend.service;

import com.resumeranker.backend.model.ResumeRequest;
import com.resumeranker.backend.model.ResumeResponse;
import com.resumeranker.backend.util.FileDownloaderUtil;
import com.resumeranker.backend.util.FileParserUtil;
import org.apache.tika.exception.TikaException;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.beans.factory.annotation.Value;

import java.io.IOException;
import java.io.InputStream;
import java.util.*;

import com.openhtmltopdf.pdfboxout.PdfRendererBuilder;
import java.io.ByteArrayOutputStream;


@Service
public class ResumeProcessingService {

    @Value("${ml.service.url}")
    private String mlServiceUrl;

    private final Map<String, List<ResumeResponse>> jobResults = new HashMap<>();

    private final RestTemplate restTemplate = new RestTemplate();

    public List<ResumeResponse> process(ResumeRequest request) throws TikaException, IOException {
        String jdText = extractJobDescription(request);

        List<String> resumeTexts = new ArrayList<>();
        List<String> resumeNames = new ArrayList<>();

        //in case of resume files
        if(request.getResumeFiles() != null){
            for(MultipartFile resume : request.getResumeFiles()){
                try{
                    resumeTexts.add(FileParserUtil.extractText(resume));
                    resumeNames.add(Objects.requireNonNull(resume.getOriginalFilename()));
                } catch(IOException | TikaException e){
                    throw new RuntimeException("Error processing resume file", e);
                }
            }
        }

        //in case of resume urls
        if(request.getResumeUrls() != null){
            for(String url : request.getResumeUrls()){
                try(InputStream stream = FileDownloaderUtil.downloadFile(url)){
                    resumeTexts.add(FileParserUtil.extractText(stream));
                    resumeNames.add(url.substring(url.lastIndexOf('/') + 1));
                }
            }
        }

        Map<String, Object> payload = new HashMap<>();
        payload.put("jobId", request.getJobId());
        payload.put("jobDescription", jdText);
        payload.put("resumeTexts", resumeTexts);
        payload.put("resumeNames", resumeNames);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(payload, headers);

        System.out.println("Sending payload to ML service:");
        System.out.println("Job ID: " + request.getJobId());
        System.out.println("Job Description:\n" + jdText);

        System.out.println("\nResumes:");
        for (int i = 0; i < resumeNames.size(); i++) {
            System.out.println("[" + resumeNames.get(i) + "]");
            System.out.println(resumeTexts.get(i));
            System.out.println("----------------------");
        }


        ResponseEntity<ResumeResponse[]> response = restTemplate.exchange(
                mlServiceUrl + "/rank", HttpMethod.POST, entity, ResumeResponse[].class
        );

        List<ResumeResponse> responses = List.of(Objects.requireNonNull(response.getBody()));
        jobResults.put(request.getJobId(), responses);
        return responses;

    }

    private String extractJobDescription(ResumeRequest request) throws TikaException, IOException {
        try{
            if(request.getJdText() != null)
                return request.getJdText();
            else if(request.getJdFile() != null)
                return FileParserUtil.extractText(request.getJdFile());
            else if(request.getJdUrl() != null){
                InputStream stream = FileDownloaderUtil.downloadFile(request.getJdUrl());
                return FileParserUtil.extractText(stream);
            }
        }catch(Exception e){
            throw new RuntimeException("Error processing job description", e);
        }
        return "Empty JD";
    }

    public List<ResumeResponse> getResultsForJob(String jobId){
        return jobResults.get(jobId);
    }

    public byte[] generateResultsPDF(String jobId){
        List<ResumeResponse> responses = getResultsForJob(jobId);
        if(responses == null || responses.isEmpty())
            throw new IllegalArgumentException("No results found for job ID: " + jobId);

        StringBuilder html = new StringBuilder();
        html.append("<html><head><style>")
                .append("body { background-color: #0c1b3a; color: #FFD93D; font-family: 'Press Start 2P', monospace; font-size: 8px; }")
                .append("h1 { font-size: 12px; text-align: center; color: #FFD93D; text-shadow: 2px 2px #000000; }")
                .append("h2 { font-size: 10px; color: #7FDBFF; text-align: center; text-shadow: 1px 1px #000000; }")
                .append("div.resume-card { border: 2px solid #F24E1E; padding: 10px; margin: 10px; background-color: #12264d; box-shadow: 4px 4px #000; }")
                .append("b { color: #F24E1E; }")
                .append("ul { margin: 5px 0; padding-left: 15px; }")
                .append("li { margin: 2px 0; }")
                .append("</style></head><body>");

        html.append("<h1>🎮 SKILL QUEST RANKINGS 🎮</h1>");
        html.append("<h2>Results for Job ID: ").append(jobId).append("</h2>");

        for (ResumeResponse r : responses) {
            html.append("<div class='resume-card'>")
                    .append("<b>Rank #").append(r.getRank()).append(" — ").append(r.getName()).append("</b><br/>")
                    .append("# Matched Skills: ").append(String.join(", ", r.getMatchedSkills())).append("<br/>")
                    .append("# Missing Skills: ").append(String.join(", ", r.getMissingSkills())).append("<br/>")
                    .append("# Score: ").append(String.format("%.2f", r.getScore())).append("<br/><br/>")

                    .append("# Summary:<br/>").append(r.getSummary()).append("<br/><br/>")

                    .append("# Experience Highlights:<br/><ul>");
            for (String item : r.getExperienceHighlights()) html.append("<li>").append(item).append("</li>");
            html.append("</ul># Impact Highlights:<br/><ul>");
            for (String item : r.getImpactHighlights()) html.append("<li>").append(item).append("</li>");
            html.append("</ul># Experiences:<br/><ul>");
            for (String item : r.getExperiences()) html.append("<li>").append(item).append("</li>");
            html.append("</ul># Projects:<br/><ul>");
            for (String item : r.getProjects()) html.append("<li>").append(item).append("</li>");
            html.append("</ul># Project Highlights:<br/><ul>");
            for (String item : r.getProjectHighlights()) html.append("<li>").append(item).append("</li>");
            html.append("</ul># Skills:<br/><ul>");
            for (String item : r.getSkills()) html.append("<li>").append(item).append("</li>");
            html.append("</ul># Certifications:<br/><ul>");
            for (String item : r.getCertifications()) html.append("<li>").append(item).append("</li>");
            html.append("</ul># Education:<br/><ul>");
            for (String item : r.getEducation()) html.append("<li>").append(item).append("</li>");
            html.append("</ul>")
                    .append("# Seniority Level: ").append(r.getSeniorityLevel()).append("<br/>")
                    .append("# Career Trajectory: ").append(r.getCareerTrajectory()).append("<br/>")
                    .append("# Experience Relevance Score: ").append(String.format("%.2f", r.getExperienceRelevanceScore())).append("<br/>")
                    .append("# ATS Compatibility Score: ").append(String.format("%.2f", r.getAtsCompatibilityScore())).append("<br/>")
                    .append("# Contact: ").append(r.getContact()).append("<br/>")
                    .append("</div>");
        }

        html.append("</body></html>");

        try (ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            PdfRendererBuilder builder = new PdfRendererBuilder();
            builder.withHtmlContent(html.toString(), null);
            builder.toStream(out);
            builder.run();
            return out.toByteArray();
        } catch (Exception e) {
            throw new RuntimeException("PDF generation failed", e);
        }
    }
}
