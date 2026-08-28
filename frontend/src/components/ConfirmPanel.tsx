import { useState } from "react";
import { CaseState, confirmCase } from "../api";

interface Props {
  caseState: CaseState;
  onConfirmed: (c: CaseState) => void;
}

export default function ConfirmPanel({ caseState, onConfirmed }: Props) {
  const [operator, setOperator] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const doConfirm = async () => {
    if (!operator.trim()) {
      setErr("请填写操作人");
      return;
    }
    setLoading(true);
    setErr("");
    try {
      const c = await confirmCase(caseState.case_id, operator.trim(), note.trim());
      onConfirmed(c);
    } catch (e: any) {
      setErr("确认失败：" + (e?.message || "未知错误"));
    } finally {
      setLoading(false);
    }
  };

  const u = caseState.understanding;
  const w = caseState.work_order;
  const cl = caseState.classification;

  return (
    <div className="panel">
      <div className="panel-head">
        <div className="panel-title">
          <h2>工作人员审核确认 <span className="step-tag">STEP 06</span></h2>
          <p>请核对全流程产出物，填写操作人后提交审核。</p>
        </div>
        {caseState.confirmed && <span className="badge ok">已确认 ✓</span>}
      </div>
      <div className="alert info">
        <span className="alert-ico">ℹ</span>
        <div>系统仅提供辅助建议，最终由工作人员确认。点击「确认并提交审核」将写入 audit_log。</div>
      </div>

      <div className="preview">
        <div className="field-label">工单预览</div>
        <div className="field-value strong">{w?.title}</div>
        <div className="muted small">
          {u?.location ? "地点：" + u.location + "  " : ""}
          {cl?.category_name ? "类别：" + cl.category_name : ""}
        </div>
        {u && (
          <pre className="content-box">{u.transcript}</pre>
        )}
        {caseState.reply && (
          <pre className="content-box">{caseState.reply.pre_reply}</pre>
        )}
      </div>

      <div className="row">
        <input
          className="field-input"
          placeholder="操作人姓名"
          value={operator}
          onChange={(e) => setOperator(e.target.value)}
        />
      </div>
      <div className="row">
        <input
          className="field-input"
          placeholder="审核备注（可选）"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </div>

      {err && <div className="alert danger"><span className="alert-ico">⚠</span><div>{err}</div></div>}

      <div className="panel-foot">
        <span className="foot-hint">提交后不可撤回，请仔细核对</span>
        <div className="foot-btns">
          <button className="btn-primary" onClick={doConfirm} disabled={loading || caseState.confirmed}>
            {caseState.confirmed ? "已确认 ✓" : loading ? "提交中…" : "确认并提交审核"}
          </button>
        </div>
      </div>

      <div className="field-label">操作日志（audit_log）</div>
      <ul className="audit-list">
        {caseState.audit_log.map((a, i) => (
          <li key={i}>
            <b>[{a.action}]</b> {a.at}
            {a.operator ? " · 操作人：" + a.operator : ""}
            {a.note ? " · 备注：" + a.note : ""}
            {a.text ? " · " + a.text : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}
