import { useMemo, useState } from "react";

type Skill = {
  display_id: string;
  name: string;
  description: string;
  category?: string;
  tags: string[];
  recommendation: string;
  confidence_flags: string[];
  last_updated: string;
  last_scanned: string;
};

function RecommendationPills({ recommendation, flags }: { recommendation: string; flags: string[] }) {
  return (
    <span className="pill-row">
      <span className={`risk recommendation-${recommendation.toLowerCase().replaceAll("_", "-")}`}>
        {formatRecommendation(recommendation)}
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

  const categories = useMemo(
    () => Array.from(new Set(skills.map((skill) => skill.category || "uncategorized"))).sort(),
    [skills]
  );

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
    <section>
      <div className="controls">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search skills" />
        <select value={recommendation} onChange={(event) => setRecommendation(event.target.value)}>
          <option value="all">All recommendations</option>
          <option value="DO_NOT_INSTALL">Do Not Install</option>
          <option value="CAUTION">Caution</option>
          <option value="SAFE">Safe</option>
          <option value="Unknown">Unknown</option>
        </select>
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          <option value="all">All categories</option>
          {categories.map((item) => (
            <option value={item} key={item}>{item}</option>
          ))}
        </select>
        <select value={sort} onChange={(event) => setSort(event.target.value)}>
          <option value="name">Sort by name</option>
          <option value="recommendation">Sort by recommendation</option>
          <option value="last_updated">Sort by last updated</option>
          <option value="last_scanned">Sort by last scanned</option>
        </select>
      </div>
      <table>
        <thead>
          <tr>
            <th>Skill</th>
            <th>Description</th>
            <th>Recommendation</th>
            <th>Category</th>
            <th>Last Updated</th>
            <th>Last Scanned</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((skill) => (
            <tr key={skill.display_id}>
              <td>
                <a href={`/skills/${skill.display_id}/`}>{skill.display_id}</a>
              </td>
              <td>{skill.description}</td>
              <td>
                <RecommendationPills recommendation={skill.recommendation} flags={skill.confidence_flags} />
              </td>
              <td>{skill.category || "uncategorized"}</td>
              <td>{formatDate(skill.last_updated)}</td>
              <td>{formatDate(skill.last_scanned)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function formatRecommendation(value: string) {
  if (value === "DO_NOT_INSTALL") {
    return "Do Not Install";
  }
  if (value === "CAUTION") {
    return "Caution";
  }
  if (value === "SAFE") {
    return "Safe";
  }
  return value;
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
