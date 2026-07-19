import { Routes, Route, NavLink } from "react-router-dom";
import { ExperimentsPage } from "./pages/ExperimentsPage";
import { ExperimentDetailPage } from "./pages/ExperimentDetailPage";
import { NewExperimentPage } from "./pages/NewExperimentPage";
import { ConnectionPage } from "./pages/ConnectionPage";
import { ScoringTemplatePage } from "./pages/ScoringTemplatePage";
import { ProviderPage } from "./pages/ProviderPage";

export function App() {
  return (
    <div className="app-shell">
      <nav className="app-nav">
        <NavLink to="/" end>实验列表</NavLink>
        <NavLink to="/new">新建实验</NavLink>
        <NavLink to="/connection">AutoDL 连接</NavLink>
        <NavLink to="/template">评分模板</NavLink>
        <NavLink to="/provider">AI 服务商</NavLink>
      </nav>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<ExperimentsPage />} />
          <Route path="/new" element={<NewExperimentPage />} />
          <Route path="/experiments/:id" element={<ExperimentDetailPage />} />
          <Route path="/connection" element={<ConnectionPage />} />
          <Route path="/template" element={<ScoringTemplatePage />} />
          <Route path="/provider" element={<ProviderPage />} />
        </Routes>
      </main>
    </div>
  );
}
