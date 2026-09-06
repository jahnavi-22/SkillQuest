import React, { useState } from "react";
import "./ResumeCardStyle.css";

const ResumeCard = ({ result }) => {
  const [expanded, setExpanded] = useState(false);

  const renderSection = (title, content) => {
    if (!content) return null;

    if (typeof content === "object" && !Array.isArray(content)) {
      return (
        <div className="nested-expandable">
          <h4 className="section-title">{title}</h4>
          <div className="section-content">
            {Object.entries(content).map(([key, value]) => {
              const displayValue =
                value === null || value === undefined || value === ""
                  ? "Not provided"
                  : String(value);
              return (
                <div key={key}>
                  <strong>{key.charAt(0).toUpperCase() + key.slice(1)}:</strong>{" "}
                  {displayValue}
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    const contentStr =
      content === null || content === undefined || content === ""
        ? "Not provided"
        : Array.isArray(content)
          ? content.join("\n")
          : String(content);

    return (
      <div className="nested-expandable">
        <h4 className="section-title">{title}</h4>
        <div className="section-content">
          {contentStr.split("\n").map((line, idx) => (
            <p key={idx}>{line}</p>
          ))}
        </div>
      </div>
    );
  };




  const renderSkillSection = (title, skills, type) => {
    if (!skills || skills.length === 0) return null;
    return (
      <div className="nested-expandable">
        <h4 className="section-title">{title}</h4>
        <div className="skills-section">
          {skills.map((skill, idx) => (
            <span key={idx} className={`skill-tag ${type}`}>
              {skill}
            </span>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="resume-card">
      <div className="card-header">
        <div className="header-grid">
          <span className="rank">#{result.rank}</span>
          <span className="name">
            {result.name}
            {result.verification?.injectionFlags?.length > 0 && (
              <span
                className="guardrail-flag"
                tabIndex={0}
                title="Prompt injection detected — this resume tried to manipulate the AI's scoring. The attempt was ignored; the score reflects real skills only."
              >
                &#9888;
                <span className="guardrail-tooltip">
                  Prompt injection detected. This resume tried to manipulate the
                  AI's scoring. The attempt was ignored — the score reflects real
                  skills only.
                </span>
              </span>
            )}
          </span>
          <div className="skills-column">
            {result.matchedSkills?.map((skill, idx) => (
              <span key={idx} className="skill-tag matched">{skill}</span>
            ))}
          </div>
          <div className="skills-column">
            {result.missingSkills?.map((skill, idx) => (
              <span key={idx} className="skill-tag missing">{skill}</span>
            ))}
          </div>
          <span className="score">{result.score}</span>
          <button className="expand-button" onClick={() => setExpanded(!expanded)}>
            {expanded ? "Close Stats" : "Load Stats"}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="expandable-section">
          {renderSection("Summary", result.summary)}
          {renderSection("Experience Highlights", result.experienceHighlights)}
          {renderSection("Impact Highlights", result.impactHighlights)}
          {renderSection("Experiences", result.experiences)}
          {renderSection("Projects", result.projects)}
          {renderSection("Project Highlights", result.projectHighlights)}
          {renderSkillSection("Skills", result.skills)}
          {renderSection("Certifications", result.certifications)}
          {renderSection("Education", result.education)}
          {renderSection("Seniority Level", result.seniorityLevel)}
          {renderSection("Career Trajectory", result.careerTrajectory)}
          {renderSection("Experience Relevance Score", typeof result.experienceRelevanceScore === "number"
            ? `${result.experienceRelevanceScore}/10`
            : result.experienceRelevanceScore)}
          {renderSection("ATS Compatibility Score", typeof result.atsCompatibilityScore === "number"
            ? `${result.atsCompatibilityScore}/10`
            : result.atsCompatibilityScore)}
          {renderSection("Contact", result.contact)}
        </div>
      )}
    </div>
  );
};

export default ResumeCard;