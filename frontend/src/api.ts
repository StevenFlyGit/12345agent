import axios from "axios";

// 与后端 Pydantic 模型保持一致
export interface CaseInput {
  text?: string | null;
  audio_filename?: string | null;
}

export interface UnderstandingResult {
  transcript: string;
  transcript_source: string;
  time?: string | null;
  location?: string | null;
  parties: string[];
  event?: string | null;
  demand?: string | null;
  other?: string | null;
  needs_clarification: boolean;
  missing_fields: string[];
  urgent: boolean;
  repeat_request: boolean;
  source: string;
}

export interface WorkOrder {
  title: string;
  summary: string;
  content: string;
  key_elements: string[];
  suggested_category?: string | null;
  source: string;
}

export interface DepartmentSuggestion {
  main: string;
  co: string[];
  reason: string;
}

export interface ClassificationResult {
  category?: string | null;
  category_name?: string | null;
  confidence: number;
  suggestions: DepartmentSuggestion[];
  needs_manual: boolean;
  manual_hint?: string | null;
  source: string;
}

export interface ReplyResult {
  acceptance_notice: string;
  handling_suggestion: string;
  pre_reply: string;
  callback_script: string;
  modification_tips: string[];
  source: string;
}

export interface AuditEntry {
  action: string;
  at: string;
  operator?: string;
  note?: string;
  text?: string;
}

export interface CaseState {
  case_id: string;
  created_at: string;
  input: CaseInput;
  understanding?: UnderstandingResult | null;
  work_order?: WorkOrder | null;
  classification?: ClassificationResult | null;
  reply?: ReplyResult | null;
  confirmed: boolean;
  audit_log: AuditEntry[];
  retrieved_contexts?: Record<string, unknown[]>;
  rag_status?: Record<string, unknown>;
  quality_flags?: string[];
  human_review_required?: boolean;
  next_action?: string | null;
  graph_trace?: Record<string, unknown>[];
}

export interface DepartmentRule {
  category_code: string;
  category_name: string;
  department: string;
  co_departments: string[];
  keywords: string[];
  responsibilities: string;
  source_name: string;
  version: string;
  note: string;
}

export interface DepartmentRulesDocument {
  filename: string;
  schema_version: string;
  notice: string;
  rule_fields: string[];
  rules: DepartmentRule[];
  updated_at: string;
}

export type DepartmentRuleUpdate = Pick<
  DepartmentRule,
  "category_name" | "department" | "co_departments" | "keywords" | "responsibilities"
>;

export interface TextSample {
  type: "text";
  id?: string;
  text: string;
}

export interface AudioSample {
  type: "audio";
  source_id: string;
  filename: string;
  category?: string;
  title?: string;
  preview: string;
}

export interface SamplesResponse {
  text_samples: TextSample[];
  audio_samples: AudioSample[];
  note: string;
}

export interface HistoryResult {
  source_id: string;
  category?: string;
  title?: string;
  request_content?: string;
  handling_departments: string[];
  reply_content?: string;
  score?: number;
}

const http = axios.create({
  baseURL: "",
  timeout: 100000,
});

export async function getMeta(): Promise<{ llm_available: boolean; engine_mode: string }> {
  const r = await http.get("/api/meta");
  return r.data;
}

export async function createCase(text: string): Promise<CaseState> {
  const r = await http.post("/api/cases", { text });
  return r.data;
}

export async function createCaseAudio(formData: FormData): Promise<CaseState> {
  const r = await http.post("/api/cases", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return r.data;
}

export async function getCase(id: string): Promise<CaseState> {
  const r = await http.get(`/api/cases/${id}`);
  return r.data;
}

export async function listCases(): Promise<CaseState[]> {
  const r = await http.get("/api/cases");
  return r.data;
}

export async function runWorkOrder(id: string): Promise<WorkOrder> {
  const r = await http.post(`/api/cases/${id}/workorder`);
  return r.data;
}

export async function runClassify(id: string): Promise<ClassificationResult> {
  const r = await http.post(`/api/cases/${id}/classify`);
  return r.data;
}

export async function runReply(id: string): Promise<ReplyResult> {
  const r = await http.post(`/api/cases/${id}/reply`);
  return r.data;
}

export async function confirmCase(
  id: string,
  operator: string,
  note?: string
): Promise<CaseState> {
  const r = await http.post(`/api/cases/${id}/confirm`, { operator, note });
  return r.data;
}

export async function recordHandling(id: string, text: string): Promise<CaseState> {
  const r = await http.post(`/api/cases/${id}/handling`, { text });
  return r.data;
}

export async function getSamples(): Promise<SamplesResponse> {
  const r = await http.get("/api/samples");
  return r.data;
}

export async function getHistory(q: string): Promise<{ query: string; results: HistoryResult[] }> {
  const r = await http.get("/api/history", { params: { q } });
  return r.data;
}

export async function getDepartmentRules(): Promise<DepartmentRulesDocument> {
  const r = await http.get("/api/departments/rules");
  return r.data;
}

export async function updateDepartmentRule(
  code: string,
  update: DepartmentRuleUpdate
): Promise<{ rule: DepartmentRule; updated_at: string; index_count: number }> {
  const r = await http.put(
    `/api/departments/rules/${encodeURIComponent(code)}`,
    update
  );
  return r.data;
}

export async function deleteDepartmentRule(
  code: string
): Promise<{
  deleted_code: string;
  rules_count: number;
  updated_at: string;
  index_count: number;
}> {
  const r = await http.delete(
    `/api/departments/rules/${encodeURIComponent(code)}`
  );
  return r.data;
}
