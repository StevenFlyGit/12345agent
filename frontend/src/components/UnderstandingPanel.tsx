import { useState } from "react";
import { UnderstandingResult } from "../api";

interface Props {
  understanding: UnderstandingResult;
  onNext: () => void;
}

const SOURCE_LABEL: Record<string, string> = {
  text: "文本录入",
  "sample-match": "样例精确匹配",
  whisper: "语音转写(Whisper)",
  simulated: "模拟转写",
};

function Field({ label, value, onChange }: { label: string; value: string; onChange?: (v: string) => void }) {
  return (
    <div className="field">
      <div className="field-label">{label}</div>
      {onChange ? (
        <input className="field-input" value={value} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <div className="field-value">{value || "（未识别）"}</div>
      )}
    </div>
  );
}

export default function UnderstandingPanel({ understanding, onNext }: Props) {
  const [u, setU] = useState<UnderstandingResult>(understanding);
  const set = (k: keyof UnderstandingResult, v: any) => setU({ ...u, [k]: v });

  return (
    <div className="panel">
      <div className="panel-head">
        <div className="panel-title">
          <h2>诉求理解 <span className="step-tag">STEP 02</span></h2>
          <p>系统已从原始诉求中抽取结构化要素，请核对修正后采纳。</p>
        </div>
        <span className={"badge src-" + u.source}>
          引擎：{u.source === "llm" ? "大模型" : "本地确定性引擎"}
        </span>
      </div>

      <div className="badge-group">
        <span className="badge">转写来源：{SOURCE_LABEL[u.transcript_source] || u.transcript_source}</span>
        {u.urgent && <span className="badge danger">紧急 / 安全</span>}
        {u.repeat_request && <span className="badge warn">重复反映</span>}
        {u.needs_clarification && <span className="badge warn">需补充信息</span>}
      </div>

      {u.needs_clarification && (
        <div className="alert">
          <span className="alert-ico">⚠</span>
          <div>缺字段：<b>{u.missing_fields.join("、") || "未知"}</b> —— 建议向群众补充核实后再行转办。</div>
        </div>
      )}

      {/* TODO(backend-gap): 人工修正后的要素（u 的本地编辑）目前仅保存在前端内存，
          后端无“更新 understanding”接口，采纳后不会回写。见设计缺口清单 G-02。 */}

      <div className="card-grid">
        <Field label="时间" value={u.time || ""} onChange={(v) => set("time", v)} />
        <Field label="地点" value={u.location || ""} onChange={(v) => set("location", v)} />
        <div className="field">
          <div className="field-label">涉及对象</div>
          <input
            className="field-input"
            value={u.parties.join("、")}
            onChange={(e) => set("parties", e.target.value.split("、").map((s) => s.trim()).filter(Boolean))}
          />
        </div>
        <Field label="事件" value={u.event || ""} onChange={(v) => set("event", v)} />
        <Field label="诉求" value={u.demand || ""} onChange={(v) => set("demand", v)} />
        <Field label="其他" value={u.other || ""} onChange={(v) => set("other", v)} />
      </div>

      <div className="transcript-box">
        <div className="field-label">转写/原文</div>
        <pre>{u.transcript}</pre>
      </div>

      <div className="panel-foot">
        <span className="foot-hint">修改内容仅在当前会话生效（见 TODO）</span>
        <div className="foot-btns">
          <button className="btn-primary" onClick={onNext}>
            采纳并生成工单 →
          </button>
        </div>
      </div>
    </div>
  );
}
