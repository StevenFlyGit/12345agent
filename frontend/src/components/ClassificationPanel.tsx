import { ClassificationResult } from "../api";

interface Props {
  classification: ClassificationResult;
  onNext: () => void;
}

export default function ClassificationPanel({ classification, onNext }: Props) {
  const pct = Math.max(0, Math.min(100, Math.round(classification.confidence * 100)));
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="panel-title">
          <h2>分类与承办单位推荐 <span className="step-tag">STEP 04</span></h2>
          <p>根据工单内容推荐类别与承办单位，请确认后生成回复。</p>
        </div>
        <span className={"badge src-" + classification.source}>
          引擎：{classification.source === "llm" ? "大模型" : "本地确定性引擎"}
        </span>
      </div>

      <div className="field">
        <div className="field-label">建议类别</div>
        <div className="field-value strong">
          {classification.category_name || "（待定）"}
          <span className="muted small">（置信度 {pct}%）</span>
        </div>
        <div className="progress">
          <div className="progress-bar" style={{ width: pct + "%" }} />
        </div>
      </div>

      {classification.needs_manual && (
        <div className="alert">
          <span className="alert-ico">⚠</span>
          <div>建议人工复核：{classification.manual_hint || "职责交叉或信息不足，请工作人员确认承办单位。"}</div>
        </div>
      )}

      <div className="field-label">承办单位建议</div>
      {classification.suggestions.map((s, i) => (
        <div className="dept-card" key={i}>
          <div className="dept-main">
            主责：<b>{s.main}</b>
          </div>
          {s.co.length > 0 && (
            <div className="dept-co">协办：{s.co.join("、")}</div>
          )}
          <div className="dept-reason">{s.reason}</div>
        </div>
      ))}

      <div className="panel-foot">
        <span className="foot-hint">承办单位建议仅供参考，最终以人工确认为准</span>
        <div className="foot-btns">
          <button className="btn-primary" onClick={onNext}>
            采纳并生成回复 →
          </button>
        </div>
      </div>
    </div>
  );
}
