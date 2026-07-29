import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import type { Artifact } from "../api/types";
import { AnalysisPanel } from "./AnalysisPanel";

const candidate: Artifact = {
  id: "artifact-1",
  snapshot_id: "snapshot-1",
  relative_path: "output/candidate-1.png",
  kind: "saved_image",
  checksum: "abcdef1234567890",
  size_bytes: 42,
  transfer_status: "transferred",
  error_detail: null,
  extracted_metadata: [],
};

describe("AnalysisPanel", () => {
  it("sends the selected candidate to the analysis request", async () => {
    const request = vi.spyOn(api, "post").mockResolvedValue({} as never);

    render(
      <AnalysisPanel
        experimentId="experiment-1"
        candidates={[candidate]}
        analyses={[]}
        onChanged={vi.fn()}
      />,
    );

    const requestButton = screen.getByRole("button", { name: "请求 AI 分析" });
    expect(requestButton).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: /候选图 1/ }));
    expect(requestButton).not.toBeDisabled();
    fireEvent.click(requestButton);

    await waitFor(() => {
      expect(request).toHaveBeenCalledWith(
        "/analyses/experiments/experiment-1/request",
        {
          artifact_ids: ["artifact-1"],
          goal_override: null,
          include_comparison_context: false,
        },
      );
    });
  });
});
