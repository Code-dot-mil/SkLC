import { useMemo, useState } from "react";

type Skill = {
  display_id: string;
  name: string;
  description: string;
  category?: string;
  tags: string[];
  risk: string;
  confidence_flags: string[];
};

export default function SkillCatalog({ skills }: { skills: Skill[] }) {
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState("all");

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return skills.filter((skill) => {
      const riskMatches = risk === "all" || skill.risk === risk;
      const text = [skill.display_id, skill.name, skill.description, skill.category, ...skill.tags].join(" ").toLowerCase();
      return riskMatches && (!normalized || text.includes(normalized));
    });
  }, [query, risk, skills]);

  return (
    <section>
      <div className="controls">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search skills" />
        <select value={risk} onChange={(event) => setRisk(event.target.value)}>
          <option value="all">All risk levels</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
          <option value="Unknown">Unknown</option>
        </select>
      </div>
      <div className="grid">
        {filtered.map((skill) => (
          <article className="card" key={skill.display_id}>
            <h2>
              <a href={`/skills/${skill.display_id}/`}>{skill.display_id}</a>
            </h2>
            <p>{skill.description}</p>
            <p>
              <strong>Risk:</strong> {skill.risk} {skill.confidence_flags.join(", ")}
            </p>
            <p className="muted">
              {skill.category || "uncategorized"} &middot; {skill.tags.join(", ")}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
