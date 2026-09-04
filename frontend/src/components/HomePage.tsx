import { KeyboardEvent, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CaseState,
  DepartmentRulesDocument,
  getDepartmentRules,
  listCases,
} from "../api";
import DashboardCharts, {
  DashboardSummary,
  summarizeCases,
} from "./DashboardCharts";
import { STEPS } from "./Stepper";

const DEMO_CASES = [
  {
    case_id: "wo_20260903T1820_m2bo",
    created_at: "2026-09-03T18:20:00",
    input: {},
    understanding: {
      demand: "某商场多户商家未明码标价，消费者要求查处",
      urgent: true,
    },
    reply: {},
    confirmed: false,
    audit_log: [],
  },
  {
    case_id: "wo_20260903T1623_82z1",
    created_at: "2026-09-03T16:23:00",
    input: {},
    understanding: {
      demand: "早晚高峰某路口拥堵严重，建议增设临时信号灯",
      urgent: false,
    },
    classification: {},
    confirmed: false,
    audit_log: [],
  },
  {
    case_id: "wo_20260903T1410_h4f7",
    created_at: "2026-09-03T14:10:00",
    input: {},
    understanding: {
      demand: "某小区电梯频繁故障停运，存在安全隐患",
      urgent: false,
    },
    work_order: { title: "某小区电梯频繁故障停运，存在安全隐患" },
    confirmed: false,
    audit_log: [],
  },
  {
    case_id: "wo_20260903T1105_a02x",
    created_at: "2026-09-03T11:05:00",
    input: {},
    understanding: {
      demand: "咨询老旧小区加装电梯的补贴政策与申请流程",
      urgent: false,
    },
    confirmed: false,
    audit_log: [],
  },
  {
    case_id: "wo_20260902T1642_e5q8",
    created_at: "2026-09-02T16:42:00",
    input: {},
    understanding: {
      demand: "反映某校外培训机构超范围经营并违规收费",
      urgent: false,
    },
    work_order: { title: "反映某校外培训机构超范围经营并违规收费" },
    confirmed: false,
    audit_log: [],
  },
  {
    case_id: "wo_20260902T1411_t3z6",
    created_at: "2026-09-02T14:11:00",
    input: {},
    understanding: {
      demand: "社区诊所预约挂号困难，老年人现场排队时间过长",
      urgent: false,
    },
    confirmed: false,
    audit_log: [],
  },
  {
    case_id: "wo_20260902T1030_p7w2",
    created_at: "2026-09-02T10:30:00",
    input: {},
    understanding: {
      demand: "举报某餐饮店后厨卫生条件差，要求核查",
      urgent: true,
    },
    classification: {},
    next_action: "human_review",
    confirmed: false,
    audit_log: [],
  },
  {
    case_id: "wo_20260901T1622_k9c4",
    created_at: "2026-09-01T16:22:00",
    input: {},
    understanding: {
      demand: "暴雨后某路段积水严重影响通行，等待生成工单",
      urgent: false,
    },
    confirmed: false,
    audit_log: [],
  },
] as unknown as CaseState[];

const DEMO_SUMMARY: DashboardSummary = {
  statusCounts: { 1: 130, 2: 4, 3: 58, 4: 6, 5: 9 },
  completed: 46,
  urgent: 38,
  total: 253,
  categories: [
    { name: "市场监管", count: 48 },
    { name: "卫生健康", count: 18 },
    { name: "交通运输", count: 17 },
    { name: "公共安全", count: 7 },
    { name: "城乡建设", count: 6 },
    { name: "经济财贸", count: 2 },
    { name: "公共服务", count: 2 },
    { name: "城市管理", count: 1 },
  ],
  unclassified: 152,
};

interface RuleOverview {
  count: number;
  version: string;
  updatedAt: string;
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
  }).format(parsed);
}

export default function HomePage() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseState[]>([]);
  const [caseLoadFailed, setCaseLoadFailed] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [ruleOverview, setRuleOverview] = useState<RuleOverview>({
    count: 12,
    version: "demo-0.1",
    updatedAt: "",
  });

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([listCases(), getDepartmentRules()]).then(
      ([caseResult, ruleResult]) => {
        if (cancelled) return;
        if (caseResult.status === "fulfilled") {
          setCases(caseResult.value);
          setCaseLoadFailed(false);
        } else {
          setCases(DEMO_CASES);
          setCaseLoadFailed(true);
        }

        if (ruleResult.status === "fulfilled") {
          const doc: DepartmentRulesDocument = ruleResult.value;
          setRuleOverview({
            count: doc.rules.length,
            version: doc.rules[0]?.version || doc.schema_version,
            updatedAt: doc.updated_at,
          });
        }
      }
    );
    return () => {
      cancelled = true;
    };
  }, []);

  const summary = useMemo(
    () => (caseLoadFailed ? DEMO_SUMMARY : summarizeCases(cases)),
    [caseLoadFailed, cases]
  );
  const active = summary.total - summary.completed;
  const activePct = summary.total ? Math.round((active / summary.total) * 100) : 0;

  const enterPipeline = () => navigate("/pipeline");
  const handleHeroKey = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      enterPipeline();
    }
  };

  return (
    <main>
      <section
        className="home-hero"
        role="link"
        tabIndex={0}
        aria-label="进入工单工作流，从录入开始"
        onClick={enterPipeline}
        onKeyDown={handleHeroKey}
      >
        <div className="hero-head">
          <div>
            <h1 className="hero-title">工单智能处理工作流</h1>
            <p className="hero-desc">
              LangChain + LangGraph + RAG 执行链路 ·
              语音/文本一键生成规范工单并智能分类转派
            </p>
          </div>
          <button
            className="hero-cta"
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              enterPipeline();
            }}
          >
            开始处理工单 →
          </button>
        </div>
        <div className="hero-track" aria-hidden="true">
          {STEPS.map((label, index) => (
            <div className="hero-node" key={label}>
              <span className="n">{index + 1}</span>
              <span className="l">{label}</span>
            </div>
          ))}
        </div>
      </section>

      <div className="home-row2">
        <section className="entry-card">
          <div className="entry-head">
            <h2 className="entry-title">部门规则数据管理</h2>
            <span className="entry-num">{ruleOverview.count}</span>
          </div>
          <p className="entry-desc">
            department_rules.json · {ruleOverview.count} 条部门权责规则 ·
            支持列表查看、详情预览与在线编辑
          </p>
          <div className="entry-meta">
            <span>
              规则版本 <b>{ruleOverview.version}</b>
            </span>
            <span>
              支持格式 <b>.json</b>
            </span>
            <span>
              最近更新 <b>{formatDate(ruleOverview.updatedAt)}</b>
            </span>
          </div>
          <div className="entry-actions">
            <button
              className="btn-ghost"
              type="button"
              onClick={() => navigate("/data")}
            >
              打开数据管理 →
            </button>
          </div>
        </section>

        <section className="entry-card">
          <div className="entry-head">
            <h2 className="entry-title">工单概览</h2>
          </div>
          <div className="mini-stats">
            <div className="mini-stat">
              <b>{active}</b>
              <span>在途工单</span>
            </div>
            <div className="mini-stat ok">
              <b>{summary.completed}</b>
              <span>已确认完成</span>
            </div>
            <div className="mini-stat">
              <b>{summary.urgent}</b>
              <span>紧急工单</span>
            </div>
          </div>
          <div className="mini-bar" aria-hidden="true">
            <i style={{ width: `${activePct}%` }} />
          </div>
          <p className="entry-foot-note">
            工单总数 {summary.total} · 大盘详情见下方
          </p>
        </section>
      </div>

      <DashboardCharts
        cases={cases}
        summary={summary}
        usingDemoData={caseLoadFailed}
        showAll={showAll}
        onToggleAll={() => setShowAll((value) => !value)}
        onTakeover={(caseId) =>
          navigate(`/pipeline?case=${encodeURIComponent(caseId)}`)
        }
      />
    </main>
  );
}
