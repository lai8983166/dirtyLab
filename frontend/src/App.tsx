import { Routes, Route, NavLink } from "react-router-dom";
import { ExperimentsPage } from "./pages/ExperimentsPage";
import { ExperimentDetailPage } from "./pages/ExperimentDetailPage";
import { NewExperimentPage } from "./pages/NewExperimentPage";
import { ConnectionPage } from "./pages/ConnectionPage";
import { ScoringTemplatePage } from "./pages/ScoringTemplatePage";
import { ProviderPage } from "./pages/ProviderPage";
import { AppIcon } from "./components/AppIcon";
import { LiquidGlassFilters } from "./components/LiquidGlassFilters";

export function App() {
  return (
    <>
      <LiquidGlassFilters />
      <div className="ambient-scene" aria-hidden="true">
        <span className="ambient-orb ambient-orb-one" />
        <span className="ambient-orb ambient-orb-two" />
        <span className="ambient-orb ambient-orb-three" />
        <span className="ambient-ribbon" />
      </div>

      <div className="app-shell">
        <nav className="app-nav">
          <div className="brand-lockup">
            <div className="brand-mark">
              <AppIcon name="provider" />
            </div>
            <div>
              <strong>dirtyLab</strong>
              <span>实验工作台</span>
            </div>
          </div>

          <div className="nav-section-label">工作台</div>
          <NavLink to="/" end>
            <span className="nav-icon"><AppIcon name="experiments" /></span>
            实验列表
          </NavLink>
          <NavLink to="/new">
            <span className="nav-icon"><AppIcon name="new" /></span>
            新建实验
          </NavLink>

          <div className="nav-section-label">设置</div>
          <NavLink to="/connection">
            <span className="nav-icon"><AppIcon name="connection" /></span>
            AutoDL 连接
          </NavLink>
          <NavLink to="/template">
            <span className="nav-icon"><AppIcon name="template" /></span>
            评分模板
          </NavLink>
          <NavLink to="/provider">
            <span className="nav-icon"><AppIcon name="provider" /></span>
            AI 服务商
          </NavLink>

          <div className="nav-footer">
            <span className="status-dot" aria-hidden="true" />
            本地模式 · 数据不出机
          </div>
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
    </>
  );
}
