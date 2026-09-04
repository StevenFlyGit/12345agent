import { CaseState } from "../api";

export type ActiveStage = 1 | 2 | 3 | 4 | 5;
export type CaseStage = ActiveStage | 6;

export const STAGE_META: Record<
  ActiveStage,
  { name: string; sub: string; pipelineStep: number }
> = {
  1: { name: "已录入", sub: "待生成工单", pipelineStep: 1 },
  2: { name: "已生成工单", sub: "待分派", pipelineStep: 2 },
  3: { name: "已分派待处理", sub: "待生成回复", pipelineStep: 3 },
  4: { name: "已生成回复", sub: "待确认", pipelineStep: 4 },
  5: { name: "待最终确认", sub: "需人工复核", pipelineStep: 5 },
};

export interface DashboardSummary {
  statusCounts: Record<ActiveStage, number>;
  completed: number;
  urgent: number;
  total: number;
  categories: Array<{ name: string; count: number }>;
  unclassified: number;
}

export function getCaseStage(item: CaseState): CaseStage {
  if (item.confirmed === true) return 6;
  if (item.next_action === "human_review") return 5;
  if (item.reply) return 4;
  if (item.classification) return 3;
  if (item.work_order) return 2;
  return 1;
}

export function derivePipelineStep(item: CaseState): number {
  const stage = getCaseStage(item);
  if (stage === 6) return 5;
  if (stage === 5) return item.reply ? 5 : item.classification ? 3 : 1;
  return STAGE_META[stage].pipelineStep;
}

export function summarizeCases(items: CaseState[]): DashboardSummary {
  const statusCounts: Record<ActiveStage, number> = {
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
  };
  const categoryCounts = new Map<string, number>();
  let completed = 0;
  let urgent = 0;

  items.forEach((item) => {
    const stage = getCaseStage(item);
    if (stage === 6) completed += 1;
    else statusCounts[stage] += 1;

    if (item.understanding?.urgent) urgent += 1;
    const category =
      item.classification?.category_name || item.classification?.category;
    if (category) {
      categoryCounts.set(category, (categoryCounts.get(category) || 0) + 1);
    }
  });

  const categories = Array.from(categoryCounts, ([name, count]) => ({
    name,
    count,
  })).sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, "zh-CN"));

  return {
    statusCounts,
    completed,
    urgent,
    total: items.length,
    categories,
    unclassified: items.length - categories.reduce((sum, item) => sum + item.count, 0),
  };
}

interface Props {
  cases: CaseState[];
  summary: DashboardSummary;
  usingDemoData: boolean;
  showAll: boolean;
  onToggleAll: () => void;
  onTakeover: (caseId: string) => void;
}

function formatTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value || "—";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(parsed);
}

function caseTitle(item: CaseState): string {
  return (
    item.work_order?.title ||
    item.understanding?.demand ||
    item.understanding?.event ||
    item.understanding?.transcript ||
    item.input.text ||
    "未命名工单"
  );
}

export default function DashboardCharts({
  cases,
  summary,
  usingDemoData,
  showAll,
  onToggleAll,
  onTakeover,
}: Props) {
  const activeCases = cases
    .filter((item) => item.confirmed !== true)
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
  const visibleCases = showAll ? activeCases : activeCases.slice(0, 8);
  const categories = summary.categories.slice(0, 8);
  const maxCategory = Math.max(1, ...categories.map((item) => item.count));
  const chartHeight = Math.max(48, categories.length * 30 + 8);

  return (
    <section className="dash" aria-labelledby="dashboard-title">
      <div className="dash-head">
        <h2 className="dash-title" id="dashboard-title">
          工单数据统计大盘
        </h2>
        <span className="dash-src">
          数据来源：{usingDemoData ? "本地演示数据" : "实时工单数据"}
        </span>
      </div>

      {usingDemoData && (
        <div className="alert info compact-alert" role="status">
          <span className="alert-ico" aria-hidden="true">ℹ</span>
          <span>实时工单接口暂不可用，当前展示与原型一致的演示数据。</span>
        </div>
      )}

      <div
        className="kpi-row"
        role="list"
        aria-label="在途工单的五类业务状态"
      >
        {([1, 2, 3, 4, 5] as ActiveStage[]).map((stage) => (
          <div
            className={"kpi" + (stage >= 4 ? " mid" : "")}
            role="listitem"
            key={stage}
          >
            <div className="kpi-top">
              <span className="kpi-no" aria-hidden="true">{stage}</span>
              <span className="kpi-name">{STAGE_META[stage].name}</span>
            </div>
            <div className="kpi-num">{summary.statusCounts[stage]}</div>
            <div className="kpi-sub">{STAGE_META[stage].sub}</div>
          </div>
        ))}
      </div>

      <div className="dash-body">
        <div>
          <div className="dash-panel-title">
            <span>已开始执行的工单</span>
            {activeCases.length > 8 && (
              <button className="more" type="button" onClick={onToggleAll}>
                {showAll ? "收起列表 ↑" : `查看全部 ${activeCases.length} 条 →`}
              </button>
            )}
          </div>
          <p className="dash-sub">
            按创建时间倒序 · {showAll ? "完整列表" : "前 8 条"} · 点击可接管并继续处理
          </p>
          <div
            className={"case-list" + (showAll ? " expanded" : "")}
            role="list"
            aria-label="工单处理列表"
          >
            {visibleCases.length > 0 ? (
              visibleCases.map((item) => {
                const stage = getCaseStage(item) as ActiveStage;
                const meta = STAGE_META[stage];
                return (
                  <button
                    className={"case-item" + (stage >= 4 ? " mid" : "")}
                    type="button"
                    role="listitem"
                    key={item.case_id}
                    onClick={() => onTakeover(item.case_id)}
                  >
                    <span className="bar" aria-hidden="true" />
                    <span className="case-main">
                      <span className="case-line1">
                        <span className="case-id">{item.case_id}</span>
                        <span className="stage-badge">{meta.name}</span>
                        {item.understanding?.urgent && (
                          <span className="urgent-tag">急</span>
                        )}
                      </span>
                      <span className="case-title">{caseTitle(item)}</span>
                    </span>
                    <span className="case-time">{formatTime(item.created_at)}</span>
                    <span className="case-arrow" aria-hidden="true">›</span>
                  </button>
                );
              })
            ) : (
              <div className="empty-state">暂无在途工单，可从上方入口创建第一条工单。</div>
            )}
          </div>
        </div>

        <div>
          <div className="dash-panel-title">
            <span>分类分布</span>
          </div>
          <p className="dash-sub">
            已分类工单 n={summary.total - summary.unclassified} · 按数量降序
          </p>
          <div className="dist-box">
            {categories.length > 0 ? (
              <svg
                className="dist-chart"
                viewBox={`0 0 320 ${chartHeight}`}
                role="img"
                aria-label={`分类分布：${categories
                  .map((item) => `${item.name}${item.count}条`)
                  .join("、")}`}
              >
                <g fontFamily="inherit" fontSize="12">
                  {categories.map((item, index) => {
                    const y = index * 30 + 7;
                    const width = Math.max(5, Math.round((item.count / maxCategory) * 150));
                    return (
                      <g key={item.name}>
                        <text x="0" y={y + 14} fill="#667085">
                          {item.name}
                        </text>
                        <rect
                          x="104"
                          y={y + 2}
                          width={width}
                          height="14"
                          rx="4"
                          fill={index === 0 ? "#2e5cff" : "#7aa2ff"}
                        />
                        <text x={110 + width} y={y + 14} fill="#344054" fontWeight="600">
                          {item.count}
                        </text>
                      </g>
                    );
                  })}
                </g>
              </svg>
            ) : (
              <div className="empty-state">暂无已分类工单。</div>
            )}
            <p className="dist-note">
              另有 <b>{summary.unclassified} 条</b>工单尚未完成分类（处理中），不计入上图。
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
