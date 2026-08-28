import { CaseState } from "../api";

export const STEPS = ["录入", "理解", "工单", "分类转派", "回复", "确认"];

/** 节点状态：done 已完成 / active 进行中 / todo 待处理 / attention 需注意 */
export type NodeStatus = "done" | "active" | "todo" | "attention";

interface Props {
  current: number;
  caseState: CaseState | null;
  onJump: (step: number) => void;
}

const STATUS_TEXT: Record<NodeStatus, string> = {
  done: "已完成",
  active: "进行中",
  todo: "待处理",
  attention: "需补充",
};

/**
 * 推导某节点的展示状态。
 * 状态完全由现有 CaseState 字段推导，不依赖后端新增数据。
 */
function statusOf(i: number, current: number, cs: CaseState | null): NodeStatus {
  if (i < current) {
    // 已完成的“理解”节点若仍缺字段，用 attention 提示（业务上可回溯补录）
    if (i === 1 && cs?.understanding?.needs_clarification) return "attention";
    return "done";
  }
  if (i === current) {
    // 当前节点存在待补充信息 / 需人工复核时高亮警示
    if (i === 1 && cs?.understanding?.needs_clarification) return "attention";
    if (i === 3 && cs?.classification?.needs_manual) return "attention";
    return "active";
  }
  return "todo";
}

export default function Stepper({ current, caseState, onJump }: Props) {
  const doneCount = Math.min(current, STEPS.length);
  return (
    <section className="pipeline" aria-label="工单流水线">
      <div className="pipeline-meta">
        <span className="case-chip">
          当前工单
          <span className={"case-id" + (caseState ? "" : " empty")}>
            {caseState ? caseState.case_id : "未创建"}
          </span>
        </span>
        <span className="pipeline-progress">
          流转进度 <b>{doneCount} / {STEPS.length}</b> · {STEPS[current]}
        </span>
      </div>

      <div className="track" role="list">
        {STEPS.map((label, i) => {
          const st = statusOf(i, current, caseState);
          return (
            <button
              key={label}
              type="button"
              role="listitem"
              className={"node-wrap " + st}
              onClick={() => onJump(i)}
              aria-current={i === current ? "step" : undefined}
            >
              <span className="node">
                {st === "done" ? <span className="check-ico">✓</span> : i + 1}
              </span>
              <span className="node-label">{label}</span>
              <span className="node-status">
                {st === "active" && <span className="sdot" />}
                {STATUS_TEXT[st]}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
