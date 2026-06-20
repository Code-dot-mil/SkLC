import { useEffect, useMemo, useState } from "react";

import { readQueryValue, replaceQueryState } from "../lib/url-state.mjs";

type Skill = {
  display_id: string;
  name: string;
  description: string;
  category?: string;
  tags: string[];
  recommendation: string;
  recommendation_label?: string;
  risk?: string;
  risk_reason?: string;
  confidence_flags: string[];
  last_updated: string;
  last_scanned: string;
  owner?: string;
  scanner_provenance?: {
    name?: string;
    version?: string;
    scan_mode?: string;
    provider?: string;
    model?: string;
  };
};

const RECOMMENDATION_VALUES = ["all", "DO_NOT_INSTALL", "CAUTION", "REVIEW", "SAFE", "Unknown"];
const SORT_VALUES = ["name", "recommendation", "last_updated", "last_scanned"];

function RecommendationPills({
  recommendation,
  label,
  flags,
}: {
  recommendation: string;
  label?: string;
  flags: string[];
}) {
  return (
    <span className="pill-row">
      <span className={`risk recommendation-${recommendation.toLowerCase().replaceAll("_", "-")}`}>
        {label || formatRecommendation(recommendation)}
      </span>
      {flags.map((flag) => (
        <span className="risk flag" key={flag}>
          {flag}
        </span>
      ))}
    </span>
  );
}

export default function SkillCatalog({ skills }: { skills: Skill[] }) {
  const [query, setQuery] = useState("");
  const [recommendation, setRecommendation] = useState("all");
  const [category, setCategory] = useState("all");
  const [sort, setSort] = useState("name");
  const [queryStateReady, setQueryStateReady] = useState(false);

  const categories = useMemo(
    () => Array.from(new Set(skills.map((skill) => skill.category || "uncategorized"))).sort(),
    [skills]
  );
  const categoryValues = useMemo(() => ["all", ...categories], [categories]);

  useEffect(() => {
    setQuery(readQueryValue(window.location.search, "q", ""));
    setRecommendation(readQueryValue(window.location.search, "recommendation", "all", RECOMMENDATION_VALUES));
    setCategory(readQueryValue(window.location.search, "category", "all", categoryValues));
    setSort(readQueryValue(window.location.search, "sort", "name", SORT_VALUES));
    setQueryStateReady(true);
  }, [categoryValues]);

  useEffect(() => {
    if (!queryStateReady) {
      return;
    }
    replaceQueryState(
      { q: query, recommendation, category, sort },
      { q: "", recommendation: "all", category: "all", sort: "name" }
    );
  }, [category, query, queryStateReady, recommendation, sort]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const recommendationRank: Record<string, number> = { DO_NOT_INSTALL: 3, CAUTION: 2, SAFE: 1, Unknown: 0 };
    return skills.filter((skill) => {
      const recommendationMatches = recommendation === "all" || skill.recommendation === recommendation;
      const categoryMatches = category === "all" || (skill.category || "uncategorized") === category;
      const text = [skill.display_id, skill.name, skill.description, skill.category, ...skill.tags].join(" ").toLowerCase();
      return recommendationMatches && categoryMatches && (!normalized || text.includes(normalized));
    }).sort((left, right) => {
      if (sort === "recommendation") {
        return (
          (recommendationRank[right.recommendation] ?? 0) - (recommendationRank[left.recommendation] ?? 0) ||
          left.display_id.localeCompare(right.display_id)
        );
      }
      if (sort === "last_updated") {
        return Date.parse(right.last_updated || "") - Date.parse(left.last_updated || "") || left.display_id.localeCompare(right.display_id);
      }
      if (sort === "last_scanned") {
        return Date.parse(right.last_scanned || "") - Date.parse(left.last_scanned || "") || left.display_id.localeCompare(right.display_id);
      }
      return left.display_id.localeCompare(right.display_id);
    });
  }, [category, query, recommendation, skills, sort]);

  return (
    <section className="catalog-shell">
      <div className="catalog-summary">
        <div>
          <p className="eyebrow">Skill catalog</p>
          <h2>Assessed skills for mission work</h2>
        </div>
        <p>{filtered.length} of {skills.length} skills shown</p>
      </div>

      <div className="controls catalog-controls">
        <label>
          <span>Search</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Skill name, purpose, tag" />
        </label>
        <label>
          <span>Recommendation</span>
          <select value={recommendation} onChange={(event) => setRecommendation(event.target.value)}>
            <option value="all">All recommendations</option>
            <option value="DO_NOT_INSTALL">Avoid installing</option>
            <option value="CAUTION">Use caution</option>
            <option value="REVIEW">Use caution</option>
            <option value="SAFE">Safe to use</option>
            <option value="Unknown">Unknown</option>
          </select>
        </label>
        <label>
          <span>Category</span>
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="all">All categories</option>
            {categories.map((item) => (
              <option value={item} key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Sort</span>
          <select value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="name">Name</option>
            <option value="recommendation">Recommendation</option>
            <option value="last_updated">Last updated</option>
            <option value="last_scanned">Last scanned</option>
          </select>
        </label>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">
          <h3>No skills match those filters.</h3>
          <p>Clear the search or choose a broader recommendation/category filter.</p>
        </div>
      ) : (
        <div className="skill-grid">
          {filtered.map((skill) => (
            <article className="skill-card" key={skill.display_id}>
              <div className="skill-card-topline">
                <RecommendationPills
                  recommendation={skill.recommendation}
                  label={skill.recommendation_label}
                  flags={skill.confidence_flags}
                />
                <span className="category-chip">{skill.category || "uncategorized"}</span>
              </div>
              <h3><a href={`/skills/${skill.display_id}/`}>{skill.display_id}</a></h3>
              <p>{skill.description}</p>
              {skill.tags.length > 0 && (
                <div className="tag-row">
                  {skill.tags.map((tag) => (
                    <span className="tag" key={tag}>{tag}</span>
                  ))}
                </div>
              )}
              <dl className="trust-list compact">
                <div>
                  <dt>Risk</dt>
                  <dd>{skill.risk || recommendationToRisk(skill.recommendation)}</dd>
                </div>
                <div>
                  <dt>Last scanned</dt>
                  <dd>{formatDate(skill.last_scanned)}</dd>
                </div>
                <div>
                  <dt>Owner</dt>
                  <dd>{skill.owner || "Not declared"}</dd>
                </div>
                <div>
                  <dt>Scanner</dt>
                  <dd>{skill.scanner_provenance?.name || "SkillSpector"}</dd>
                </div>
              </dl>
              <a className="card-action" href={`/skills/${skill.display_id}/`}>View skill instructions</a>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function formatRecommendation(value: string) {
  if (value === "DO_NOT_INSTALL") {
    return "Avoid installing";
  }
  if (value === "CAUTION") {
    return "Use caution";
  }
  if (value === "REVIEW") {
    return "Use caution";
  }
  if (value === "SAFE") {
    return "Safe to use";
  }
  if (value === "BLOCK") {
    return "Avoid installing";
  }
  return value;
}

function recommendationToRisk(value: string) {
  if (value === "DO_NOT_INSTALL" || value === "BLOCK") {
    return "High";
  }
  if (value === "CAUTION" || value === "REVIEW") {
    return "Medium";
  }
  if (value === "SAFE") {
    return "Low";
  }
  return "Unknown";
}

function formatDate(value: string) {
  if (!value) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
