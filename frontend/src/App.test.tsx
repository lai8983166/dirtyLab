import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "./App";

describe("App", () => {
  it("renders the navigation shell", () => {
    const { getAllByText } = render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    // 中文导航标签
    expect(getAllByText("实验列表").length).toBeGreaterThan(0);
    expect(getAllByText("新建实验").length).toBeGreaterThan(0);
    expect(getAllByText("AutoDL 连接").length).toBeGreaterThan(0);
    expect(getAllByText("评分模板").length).toBeGreaterThan(0);
    expect(getAllByText("AI 服务商").length).toBeGreaterThan(0);
  });
});
