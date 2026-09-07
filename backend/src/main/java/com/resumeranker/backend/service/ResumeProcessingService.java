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
                .append("* { box-sizing: border-box; }")
                .append("body { font-family: Helvetica, Arial, sans-serif; color: #1f2937; font-size: 11px; margin: 0; padding: 24px; }")
                .append(".report-header { border-bottom: 3px solid #2563eb; padding-bottom: 10px; margin-bottom: 20px; }")
                .append(".report-header h1 { font-size: 20px; color: #111827; margin: 0 0 4px 0; }")
                .append(".report-header .meta { color: #6b7280; font-size: 10px; }")
                .append(".candidate { border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px 16px; margin-bottom: 14px; }")
                .append(".cand-head { width: 100%; border-collapse: collapse; margin-bottom: 6px; }")
                .append(".cand-head td { vertical-align: middle; }")
                .append(".rank { color: #2563eb; font-weight: bold; font-size: 13px; width: 42px; }")
                .append(".name { font-size: 15px; font-weight: bold; color: #111827; }")
                .append(".score-cell { text-align: right; width: 72px; }")
                .append(".score-badge { background: #2563eb; color: #ffffff; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 12px; }")
                .append(".section { margin-top: 10px; }")
                .append(".section-title { font-size: 9px; font-weight: bold; color: #6b7280; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; }")
                .append(".pill { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin: 0 3px 3px 0; }")
                .append(".pill.matched { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }")
                .append(".pill.missing { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }")
                .append(".pill.neutral { background: #f3f4f6; color: #374151; border: 1px solid #e5e7eb; }")
                .append(".alert { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; padding: 6px 10px; border-radius: 6px; font-size: 10px; margin-bottom: 8px; }")
                .append(".muted { color: #9ca3af; font-size: 10px; }")
                .append(".text { font-size: 11px; color: #374151; line-height: 1.5; }")
                .append("ul { margin: 3px 0; padding-left: 16px; }")
                .append("li { margin: 2px 0; font-size: 11px; color: #374151; }")
                .append("table.meta { width: 100%; border-collapse: collapse; margin-top: 4px; }")
                .append("table.meta td { font-size: 10px; color: #374151; padding: 3px 0; vertical-align: top; }")
                .append("table.meta td.k { color: #6b7280; width: 32%; }")
                .append("</style></head><body>");

        html.append("<div class='report-header'>")
                .append("<h1>Resume Ranking Report</h1>")
                .append("<div class='meta'>Job ID: ").append(esc(jobId))
                .append("  ·  ").append(responses.size()).append(" candidate(s)")
                .append("</div></div>");

        for (ResumeResponse r : responses) {
            html.append("<div class='candidate'>");

            html.append("<table class='cand-head'><tr>")
                    .append("<td class='rank'>#").append(r.getRank()).append("</td>")
                    .append("<td class='name'>").append(esc(r.getName())).append("</td>")
                    .append("<td class='score-cell'><span class='score-badge'>")
                    .append(String.format("%.1f", r.getScore())).append("</span></td>")
                    .append("</tr></table>");

            if (hasInjection(r.getVerification())) {
                html.append("<div class='alert'><strong>Prompt injection detected.</strong> ")
                        .append("Attempt ignored — score reflects real skills only.</div>");
            }

            html.append("<div class='section'><div class='section-title'>Matched Skills</div>")
                    .append(pills(r.getMatchedSkills(), "matched")).append("</div>");
            html.append("<div class='section'><div class='section-title'>Missing Skills</div>")
                    .append(pills(r.getMissingSkills(), "missing")).append("</div>");

            if (r.getSummary() != null && !r.getSummary().isBlank()) {
                html.append("<div class='section'><div class='section-title'>Summary</div>")
                        .append("<div class='text'>").append(esc(r.getSummary())).append("</div></div>");
            }

            html.append(sectionList("Experience Highlights", r.getExperienceHighlights()));
            html.append(sectionList("Impact Highlights", r.getImpactHighlights()));
            html.append(sectionList("Project Highlights", r.getProjectHighlights()));
            html.append(sectionList("Experience", r.getExperiences()));
            html.append(sectionList("Projects", r.getProjects()));
            html.append(pillSection("Skills", r.getSkills(), "neutral"));
            html.append(sectionList("Certifications", r.getCertifications()));
            html.append(sectionList("Education", r.getEducation()));

            html.append("<div class='section'><div class='section-title'>Assessment</div>")
                    .append("<table class='meta'>")
                    .append(metaRow("Seniority", r.getSeniorityLevel()))
                    .append(metaRow("Career Trajectory", r.getCareerTrajectory()))
                    .append(metaRow("Experience Relevance", String.format("%.1f / 10", r.getExperienceRelevanceScore())))
                    .append(metaRow("ATS Compatibility", String.format("%.1f / 10", r.getAtsCompatibilityScore())))
                    .append(metaRow("Contact", contactLine(r.getContact())))
                    .append("</table></div>");

            html.append("</div>");
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

    // ---- PDF HTML helpers ----

    private static String esc(String s) {
        if (s == null) return "";
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }

    private static String pills(List<String> items, String cls) {
        if (items == null || items.isEmpty()) return "<span class='muted'>None</span>";
        StringBuilder sb = new StringBuilder();
        for (String it : items) {
            if (it == null || it.isBlank()) continue;
            sb.append("<span class='pill ").append(cls).append("'>").append(esc(it)).append("</span>");
        }
        return sb.length() == 0 ? "<span class='muted'>None</span>" : sb.toString();
    }

    private static String pillSection(String title, List<String> items, String cls) {
        if (items == null || items.isEmpty()) return "";
        return "<div class='section'><div class='section-title'>" + esc(title) + "</div>"
                + pills(items, cls) + "</div>";
    }

    private static boolean hasInjection(Map<String, Object> verification) {
        if (verification == null) return false;
        Object flags = verification.get("injectionFlags");
        return flags instanceof List && !((List<?>) flags).isEmpty();
    }

    private static String sectionList(String title, List<String> items) {
        if (items == null || items.isEmpty()) return "";
        StringBuilder sb = new StringBuilder();
        sb.append("<div class='section'><div class='section-title'>").append(esc(title)).append("</div><ul>");
        boolean any = false;
        for (String it : items) {
            if (it == null || it.isBlank()) continue;
            sb.append("<li>").append(esc(it)).append("</li>");
            any = true;
        }
        sb.append("</ul></div>");
        return any ? sb.toString() : "";
    }

    private static String metaRow(String k, String v) {
        String value = (v == null || v.isBlank()) ? "\u2014" : v;
        return "<tr><td class='k'>" + esc(k) + "</td><td>" + esc(value) + "</td></tr>";
    }

    private static String contactLine(Map<String, String> contact) {
        if (contact == null || contact.isEmpty()) return "\u2014";
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, String> e : contact.entrySet()) {
            if (e.getValue() == null || e.getValue().isBlank()) continue;
            if (sb.length() > 0) sb.append("  ·  ");
            sb.append(esc(e.getValue()));
        }
        return sb.length() == 0 ? "\u2014" : sb.toString();
    }
}
