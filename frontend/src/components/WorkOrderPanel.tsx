import { WorkOrder } from "../api";

interface Props {
  workOrder: WorkOrder;
  onNext: () => void;
}

export default function WorkOrderPanel({ workOrder, onNext }: Props) {
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="panel-title">
          <h2>工单生成 <span className="step-tag">STEP 03</span></h2>
          <p>系统已生成标准化工单，请审阅后进入分类转派。</p>
        </div>
        <span className={"badge src-" + workOrder.source}>
          引擎：{workOrder.source === "llm" ? "大模型" : "本地确定性引擎"}
        </span>
      </div>

      <div className="field">
        <div className="field-label">标题</div>
        <div className="field-value strong">{workOrder.title}</div>
      </div>
      <div className="field">
        <div className="field-label">摘要</div>
        <div className="field-value">{workOrder.summary}</div>
      </div>
      <div className="field">
        <div className="field-label">正文</div>
        <pre className="content-box">{workOrder.content}</pre>
      </div>

      <div className="field">
        <div className="field-label">关键要素</div>
        <ul className="key-elements">
          {workOrder.key_elements.map((k, i) => (
            <li key={i}>{k}</li>
          ))}
        </ul>
      </div>

      <div className="field">
        <div className="field-label">建议类别</div>
        <div className="field-value">{workOrder.suggested_category || "（待分类）"}</div>
      </div>

      <div className="panel-foot">
        <span className="foot-hint">确认无误后进入分类转派</span>
        <div className="foot-btns">
          <button className="btn-primary" onClick={onNext}>
            采纳并分类转派 →
          </button>
        </div>
      </div>
    </div>
  );
}
