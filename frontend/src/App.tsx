import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import Stepper, { STEPS } from "./components/Stepper";
import InputPanel from "./components/InputPanel";
import UnderstandingPanel from "./components/UnderstandingPanel";
import WorkOrderPanel from "./components/WorkOrderPanel";
import ClassificationPanel from "./components/ClassificationPanel";
import ReplyPanel from "./components/ReplyPanel";
import ConfirmPanel from "./components/ConfirmPanel";
import HomePage from "./components/HomePage";
import DataManagePage from "./components/DataManagePage";
import { derivePipelineStep } from "./components/DashboardCharts";
import {
  CaseState,
  getCase,
  getMeta,
  runClassify,
  runReply,
  runWorkOrder,
} from "./api";

function Header({
  engineMode,
}: {
  engineMode: string;
}) {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    "nav-tab" + (isActive ? " active" : "");

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand-group">
          <NavLink className="brand" to="/" aria-label="返回首页">
            <span className="brand-logo" aria-hidden="true">政</span>
            <span>
              12345 热线工单智能辅助工作台
              <span className="brand-sub">Gov Hotline Copilot</span>
            </span>
          </NavLink>
          <nav className="nav-tabs" aria-label="主导航">
            <NavLink className={linkClass} to="/" end>首页</NavLink>
            <NavLink className={linkClass} to="/pipeline">工单工作台</NavLink>
            <NavLink className={linkClass} to="/data">数据管理</NavLink>
          </nav>
        </div>
        <div className="top-right">
          <span
            className={"engine-badge " + (engineMode === "llm" ? "llm" : "local")}
            title={engineMode === "llm" ? "大模型引擎正在运行" : "当前使用本地确定性引擎"}
          >
            <span className="dot" aria-hidden="true" />
            <span className="engine-text">
              {engineMode === "llm" ? "大模型引擎 · 运行中" : "本地确定性引擎"}
            </span>
          </span>
        </div>
      </div>
    </header>
  );
}

function PipelinePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const caseId = searchParams.get("case");
  const [step, setStep] = useState(0);
  const [caseState, setCaseState] = useState<CaseState | null>(null);
  const [busy, setBusy] = useState(false);
  const [takeoverLoading, setTakeoverLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (!caseId) {
      setCaseState(null);
      setStep(0);
      setError("");
      return;
    }

    setTakeoverLoading(true);
    setError("");
    getCase(caseId)
      .then((item) => {
        if (cancelled) return;
        setCaseState(item);
        setStep(derivePipelineStep(item));
      })
      .catch((loadError) => {
        if (cancelled) return;
        const message =
          (loadError as { response?: { data?: { detail?: string } } }).response
            ?.data?.detail || "无法加载该工单，请返回首页重新选择。";
        setCaseState(null);
        setStep(0);
        setError(message);
      })
      .finally(() => {
        if (!cancelled) setTakeoverLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [caseId]);

  const onCreated = (item: CaseState) => {
    setCaseState(item);
    setStep(1);
    setError("");
  };

  const update = (partial: Partial<CaseState>) => {
    setCaseState((previous) =>
      previous ? { ...previous, ...partial } : previous
    );
  };

  const reset = () => {
    setCaseState(null);
    setStep(0);
    setError("");
    if (caseId) navigate("/pipeline", { replace: true });
  };

  const runStage = async (
    fn: () => Promise<unknown>,
    partialKey: keyof CaseState,
    nextStep: number
  ) => {
    if (!caseState) return;
    setBusy(true);
    setError("");
    try {
      const result = await fn();
      update({ [partialKey]: result } as Partial<CaseState>);
      setStep(nextStep);
    } catch (stageError) {
      const message =
        (stageError as { response?: { data?: { detail?: string } } }).response
          ?.data?.detail || "当前步骤处理失败，请稍后重试。";
      setError(message);
    } finally {
      setBusy(false);
    }
  };

  const jump = (target: number) => {
    if (target === 0) {
      reset();
      return;
    }
    if (!caseState) return;
    const reachable =
      (target === 1 && !!caseState.understanding) ||
      (target === 2 && !!caseState.work_order) ||
      (target === 3 && !!caseState.classification) ||
      (target === 4 && !!caseState.reply) ||
      (target === 5 && (!!caseState.reply || caseState.confirmed));
    if (reachable) setStep(target);
  };

  return (
    <main className="main pipeline-page">
      {caseId && !takeoverLoading && caseState && (
        <div className="takeover" role="status">
          <span aria-hidden="true">✓</span>
          <span>
            已接管工单 <span className="case-id">{caseState.case_id}</span>，
            定位到第 {step + 1} 步“{STEPS[step]}”，可继续处理
          </span>
        </div>
      )}

      {takeoverLoading && (
        <div className="alert info takeover-loading" role="status">
          <span className="spinner small-spinner" aria-hidden="true" />
          <span>正在加载并定位工单…</span>
        </div>
      )}

      {error && (
        <div className="alert danger" role="alert">
          <span className="alert-ico" aria-hidden="true">⚠</span>
          <span>{error}</span>
          {caseId && !caseState && (
            <button className="alert-action" type="button" onClick={() => navigate("/")}>
              返回首页
            </button>
          )}
        </div>
      )}

      {!takeoverLoading && (
        <>
          <Stepper current={step} caseState={caseState} onJump={jump} />

          {step === 0 && <InputPanel onCreated={onCreated} />}

          {step === 1 && caseState?.understanding && (
            <UnderstandingPanel
              understanding={caseState.understanding}
              onNext={() =>
                runStage(
                  () => runWorkOrder(caseState.case_id),
                  "work_order",
                  2
                )
              }
            />
          )}

          {step === 2 && caseState?.work_order && (
            <WorkOrderPanel
              workOrder={caseState.work_order}
              onNext={() =>
                runStage(
                  () => runClassify(caseState.case_id),
                  "classification",
                  3
                )
              }
            />
          )}

          {step === 3 && caseState?.classification && (
            <ClassificationPanel
              classification={caseState.classification}
              onNext={() =>
                runStage(() => runReply(caseState.case_id), "reply", 4)
              }
            />
          )}

          {step === 4 && caseState?.reply && (
            <ReplyPanel reply={caseState.reply} onNext={() => setStep(5)} />
          )}

          {step === 5 && caseState && (
            <ConfirmPanel caseState={caseState} onConfirmed={setCaseState} />
          )}
        </>
      )}

      {busy && (
        <div className="busy-mask" role="status" aria-live="polite">
          <span className="spinner" />
          处理中…
        </div>
      )}
    </main>
  );
}

function Application() {
  const [engineMode, setEngineMode] = useState("local-engine");

  useEffect(() => {
    getMeta()
      .then((meta) => setEngineMode(meta.engine_mode))
      .catch(() => setEngineMode("local-engine"));
  }, []);

  return (
    <div className="app">
      <Header engineMode={engineMode} />
      <div className="layout">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/pipeline" element={<PipelinePage />} />
          <Route path="/data" element={<DataManagePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Application />
    </BrowserRouter>
  );
}
