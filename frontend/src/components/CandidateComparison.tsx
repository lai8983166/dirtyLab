import { useEffect, useState } from "react";
import type { Artifact, Template } from "../api/types";
import { api } from "../api/client";
import { CandidateCard } from "./CandidateCard";

interface Props {
  artifacts: Artifact[];
  onChange: () => void;
}

export function CandidateComparison({ artifacts, onChange }: Props) {
  const [template, setTemplate] = useState<Template | null>(null);
  useEffect(() => {
    api.get<Template>("/scoring").then(setTemplate).catch(() => setTemplate(null));
  }, []);

  return (
    <div>
      <p className="muted">
        每个候选图独立打分。AI 确认的分数会标记来源，方便和你自己的评分区分开。
      </p>
      <div className="candidate-grid">
        {artifacts.map((a) => (
          <CandidateCard
            key={a.id}
            artifact={a}
            template={template}
            onChanged={onChange}
          />
        ))}
      </div>
    </div>
  );
}
