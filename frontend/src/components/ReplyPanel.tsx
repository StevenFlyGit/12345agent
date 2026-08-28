import { useState } from "react";
import { ReplyResult } from "../api";

interface Props {
  reply: ReplyResult;
  onNext: () => void;
}

export default function ReplyPanel({ reply, onNext }: Props) {
  const [preReply, setPreReply] = useState(reply.pre_reply);

  return (
    <div className="panel">
      <div className="panel-head">
        <div className="panel-title">
          <h2>回复辅助 <span className="step-tag">STEP 05</span></h2>
          <p>系统已生成受理提示、办理建议与预回复，请润色后进入审核确认。</p>
        </div>
        <span className={"badge src-" + reply.source}>
          引擎：{reply.source === "llm" ? "大模型" : "本地确定性引擎"}
        </span>
      </div>

      <div className="reply-card">
        <div className="field-label">受理提示</div>
        <pre className="content-box">{reply.acceptance_notice}</pre>
      </div>

      <div className="reply-card">
        <div className="field-label">办理建议</div>
        <pre className="content-box">{reply.handling_suggestion}</pre>
      </div>

      <div className="reply-card">
        <div className="field-label">预回复（可编辑）</div>
        <textarea className="big-input" rows={6} value={preReply} onChange={(e) => setPreReply(e.target.value)} />
      </div>

      <div className="reply-card">
        <div className="field-label">回访话术</div>
        <pre className="content-box">{reply.callback_script}</pre>
      </div>

      <div className="reply-card">
        <div className="field-label">修改建议</div>
        <ul className="key-elements">
          {reply.modification_tips.map((t, i) => (
            <li key={i}>{t}</li>
          ))}
        </ul>
      </div>

      <div className="panel-foot">
        {/* TODO(backend-gap): 预回复的人工编辑（preReply）目前仅存于前端内存，
            后端无“更新 reply”接口，确认提交时不会回写编辑结果。见设计缺口清单 G-03。 */}
        <span className="foot-hint">预回复的编辑仅在当前会话生效（见 TODO）</span>
        <div className="foot-btns">
          <button className="btn-primary" onClick={onNext}>
            进入审核确认 →
          </button>
        </div>
      </div>
    </div>
  );
}
