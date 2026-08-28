import { useEffect, useState } from "react";
import Stepper from "./components/Stepper";
import InputPanel from "./components/InputPanel";
import UnderstandingPanel from "./components/UnderstandingPanel";
import WorkOrderPanel from "./components/WorkOrderPanel";
import ClassificationPanel from "./components/ClassificationPanel";
import ReplyPanel from "./components/ReplyPanel";
import ConfirmPanel from "./components/ConfirmPanel";
import {
  CaseState,
  getMeta,
  runClassify,
  runReply,
  runWorkOrder,
} from "./api";

export default function App() {
  const [step, setStep] = useState(0);
  const [caseState, setCaseState] = useState<CaseState | null>(null);
  const [engineMode, setEngineMode] = useState<string>("local-engine");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getMeta()
      .then((m) => setEngineMode(m.engine_mode))
      .catch(() => setEngineMode("local-engine"));
  }, []);

  const onCreated = (c: CaseState) => {
    setCaseState(c);
    // 以首次理解结果的 source 判定引擎模式（更准确）
    if (c.understanding) setEngineMode(c.understanding.source);
    setStep(1);
  };

  const update = (partial: Partial<CaseState>) => {
    setCaseState((prev) => (prev ? { ...prev, ...partial } : prev));
  };

  const reset = () => {
    setCaseState(null);
    setStep(0);
  };

  const runStage = async (fn: () => Promise<any>, partialKey: keyof CaseState) => {
    if (!caseState) return;
    setBusy(true);
    try {
      const res = await fn();
      update({ [partialKey]: res } as Partial<CaseState>);
    } finally {
      setBusy(false);
    }
  };

  const handleWorkOrder = async () => {
    await runStage(() => runWorkOrder(caseState!.case_id), "work_order");
    setStep(2);
  };
  const handleClassify = async () => {
    await runStage(() => runClassify(caseState!.case_id), "classification");
    setStep(3);
  };
  const handleReply = async () => {
    await runStage(() => runReply(caseState!.case_id), "reply");
    setStep(4);
  };

  const onConfirmed = (c: CaseState) => {
    setCaseState(c);
  };

  /** 节点跳转：仅允许回到已可达的步骤（数据已就绪），防止空面板 */
  const jump = (s: number) => {
    if (s === 0) {
      reset();
      return;
    }
    if (!caseState) return;
    const reachable =
      (s === 1 && !!caseState.understanding) ||
      (s === 2 && !!caseState.work_order) ||
      (s === 3 && !!caseState.classification) ||
      (s === 4 && !!caseState.reply) ||
      (s === 5 && !!caseState.reply);
    if (reachable) setStep(s);
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <span className="brand-logo">政</span>
            <span>
              12345 热线工单智能辅助工作台
              <span className="brand-sub">Gov Hotline Copilot</span>
            </span>
          </div>
          <div className="top-right">
            <span className={"engine-badge " + (engineMode === "llm" ? "llm" : "local")}>
              <span className="dot" />
              {engineMode === "llm" ? "大模型引擎 · 运行中" : "本地确定性引擎"}
            </span>
          </div>
        </div>
      </header>

      <div className="layout">
        <main className="main">
          <Stepper current={step} caseState={caseState} onJump={jump} />

          {step === 0 && <InputPanel onCreated={onCreated} />}

          {step === 1 && caseState?.understanding && (
            <UnderstandingPanel understanding={caseState.understanding} onNext={handleWorkOrder} />
          )}

          {step === 2 && caseState?.work_order && (
            <WorkOrderPanel workOrder={caseState.work_order} onNext={handleClassify} />
          )}

          {step === 3 && caseState?.classification && (
            <ClassificationPanel classification={caseState.classification} onNext={handleReply} />
          )}

          {step === 4 && caseState?.reply && (
            <ReplyPanel reply={caseState.reply} onNext={() => setStep(5)} />
          )}

          {step === 5 && caseState && (
            <ConfirmPanel caseState={caseState} onConfirmed={onConfirmed} />
          )}

          {busy && (
            <div className="busy-mask">
              <span className="spinner" />
              处理中…
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
