import { KeyboardEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  DepartmentRule,
  DepartmentRuleUpdate,
  DepartmentRulesDocument,
  deleteDepartmentRule,
  getDepartmentRules,
  updateDepartmentRule,
} from "../api";

interface TagEditorProps {
  label: string;
  hint: string;
  values: string[];
  onChange: (values: string[]) => void;
}

function TagEditor({ label, hint, values, onChange }: TagEditorProps) {
  const [input, setInput] = useState("");

  const commit = (raw = input) => {
    const additions = raw
      .split(/[，,、]/)
      .map((item) => item.trim())
      .filter(Boolean);
    if (additions.length) {
      onChange(Array.from(new Set([...values, ...additions])));
    }
    setInput("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commit();
    }
    if (event.key === "Backspace" && !input && values.length) {
      onChange(values.slice(0, -1));
    }
  };

  return (
    <div className="field">
      <label className="field-label">{label}</label>
      <div className="tag-editor">
        {values.map((value) => (
          <span className="tag editable" key={value}>
            {value}
            <button
              type="button"
              aria-label={`删除标签 ${value}`}
              onClick={() => onChange(values.filter((item) => item !== value))}
            >
              ×
            </button>
          </span>
        ))}
        <input
          value={input}
          onChange={(event) => {
            const value = event.target.value;
            if (/[，,、]/.test(value)) commit(value);
            else setInput(value);
          }}
          onBlur={() => commit()}
          onKeyDown={onKeyDown}
          placeholder={values.length ? "继续添加" : "输入后按回车"}
        />
      </div>
      <p className="edit-hint">{hint}</p>
    </div>
  );
}

function blankDraft(rule: DepartmentRule): DepartmentRuleUpdate {
  return {
    category_name: rule.category_name,
    department: rule.department,
    co_departments: [...rule.co_departments],
    keywords: [...rule.keywords],
    responsibilities: rule.responsibilities,
  };
}

function errorMessage(error: unknown): string {
  const value = error as {
    response?: { data?: { detail?: string | Array<{ msg?: string }> } };
    message?: string;
  };
  const detail = value.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).filter(Boolean).join("；");
  }
  return value.message || "请求失败，请稍后重试";
}

export default function DataManagePage() {
  const [document, setDocument] = useState<DepartmentRulesDocument | null>(null);
  const [selectedCode, setSelectedCode] = useState("");
  const [keyword, setKeyword] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<DepartmentRuleUpdate | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "danger"; text: string } | null>(null);

  const load = () => {
    setLoading(true);
    setMessage(null);
    getDepartmentRules()
      .then((result) => {
        setDocument(result);
        setSelectedCode((current) =>
          result.rules.some((rule) => rule.category_code === current)
            ? current
            : result.rules[0]?.category_code || ""
        );
      })
      .catch((error) =>
        setMessage({ type: "danger", text: `规则数据加载失败：${errorMessage(error)}` })
      )
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const selected = useMemo(
    () => document?.rules.find((rule) => rule.category_code === selectedCode) || null,
    [document, selectedCode]
  );

  const filteredRules = useMemo(() => {
    const normalized = keyword.trim().toLocaleLowerCase("zh-CN");
    if (!normalized) return document?.rules || [];
    return (document?.rules || []).filter((rule) =>
      [
        rule.category_name,
        rule.department,
        ...rule.co_departments,
        ...rule.keywords,
      ]
        .join(" ")
        .toLocaleLowerCase("zh-CN")
        .includes(normalized)
    );
  }, [document, keyword]);

  const selectRule = (code: string) => {
    setSelectedCode(code);
    setEditing(false);
    setDraft(null);
    setMessage(null);
  };

  const startEdit = () => {
    if (!selected) return;
    setDraft(blankDraft(selected));
    setEditing(true);
    setMessage(null);
  };

  const save = async () => {
    if (!selected || !draft) return;
    if (
      !draft.category_name.trim() ||
      !draft.department.trim() ||
      !draft.responsibilities.trim()
    ) {
      setMessage({
        type: "danger",
        text: "分类名称、牵头部门和职责说明不能为空。",
      });
      return;
    }

    setSaving(true);
    setMessage(null);
    try {
      const result = await updateDepartmentRule(selected.category_code, {
        ...draft,
        category_name: draft.category_name.trim(),
        department: draft.department.trim(),
        responsibilities: draft.responsibilities.trim(),
      });
      setDocument((current) =>
        current
          ? {
              ...current,
              updated_at: result.updated_at,
              rules: current.rules.map((rule) =>
                rule.category_code === result.rule.category_code
                  ? result.rule
                  : rule
              ),
            }
          : current
      );
      setEditing(false);
      setDraft(null);
      setMessage({
        type: "ok",
        text: `规则已保存，部门规则检索索引已同步 ${result.index_count} 条记录。`,
      });
    } catch (error) {
      setMessage({ type: "danger", text: `保存失败：${errorMessage(error)}` });
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!selected || !document) return;
    setDeleting(true);
    setMessage(null);
    try {
      const deletingCode = selected.category_code;
      const result = await deleteDepartmentRule(deletingCode);
      const remaining = document.rules.filter(
        (rule) => rule.category_code !== deletingCode
      );
      setDocument({
        ...document,
        rules: remaining,
        updated_at: result.updated_at,
      });
      setSelectedCode(remaining[0]?.category_code || "");
      setEditing(false);
      setDraft(null);
      setConfirmDelete(false);
      setMessage({
        type: "ok",
        text: `规则已删除，当前共 ${result.rules_count} 条，检索索引已同步。`,
      });
    } catch (error) {
      setConfirmDelete(false);
      setMessage({ type: "danger", text: `删除失败：${errorMessage(error)}` });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <main>
      <div className="data-back">
        <Link className="back-link" to="/">← 返回首页</Link>
        <span className="breadcrumb">
          首页 / <b>数据管理</b>
        </span>
      </div>

      {document && (
        <div className="file-info" role="status">
          <span aria-hidden="true">ℹ</span>
          <span>
            {document.filename} · schema v{document.schema_version} ·
            {document.rules.length} 条规则 · {document.notice}
          </span>
        </div>
      )}

      {message && (
        <div className={`alert ${message.type}`} role="status">
          <span className="alert-ico" aria-hidden="true">
            {message.type === "ok" ? "✓" : "⚠"}
          </span>
          <span>{message.text}</span>
          {message.type === "danger" && !document && (
            <button className="alert-action" type="button" onClick={load}>
              重新加载
            </button>
          )}
        </div>
      )}

      <div className="data-body">
        <aside className="rule-list-card" aria-label="部门规则列表">
          <div className="rule-search">
            <input
              className="search-input"
              type="search"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="搜索：名称 / 关键词 / 部门"
              aria-label="搜索部门规则"
            />
          </div>
          <p className="rule-count">
            {loading
              ? "正在加载规则…"
              : `共 ${filteredRules.length} / ${document?.rules.length || 0} 条规则`}
          </p>
          <div className="rule-items" role="listbox" aria-label="规则条目">
            {filteredRules.map((rule) => (
              <button
                className={"rule-item" + (rule.category_code === selectedCode ? " sel" : "")}
                type="button"
                role="option"
                aria-selected={rule.category_code === selectedCode}
                key={rule.category_code}
                onClick={() => selectRule(rule.category_code)}
              >
                <span className="rn">{rule.category_name}</span>
                <span className="rd">{rule.department}</span>
              </button>
            ))}
            {!loading && filteredRules.length === 0 && (
              <div className="empty-state">
                {document?.rules.length
                  ? "没有匹配的规则，请换一个关键词。"
                  : "当前没有部门规则。"}
              </div>
            )}
          </div>
        </aside>

        <section className="panel rule-detail" aria-live="polite">
          {loading ? (
            <div className="empty-state">正在读取部门规则…</div>
          ) : selected ? (
            <>
              <div className="panel-head">
                <div className="panel-title">
                  <h1>{editing ? `编辑 · ${selected.category_name}` : selected.category_name}</h1>
                  <p>
                    {editing
                      ? "保存后将立即更新规则文件与部门规则检索索引"
                      : selected.department}
                  </p>
                </div>
                <div className="head-btns">
                  {editing ? (
                    <>
                      <button
                        className="btn-primary"
                        type="button"
                        onClick={save}
                        disabled={saving}
                      >
                        {saving ? "保存中…" : "保存修改"}
                      </button>
                      <button
                        className="btn-ghost"
                        type="button"
                        onClick={() => {
                          setEditing(false);
                          setDraft(null);
                          setMessage(null);
                        }}
                        disabled={saving}
                      >
                        取消
                      </button>
                    </>
                  ) : (
                    <>
                      <button className="btn-primary" type="button" onClick={startEdit}>
                        编辑
                      </button>
                      <button
                        className="btn-danger-ghost"
                        type="button"
                        onClick={() => setConfirmDelete(true)}
                      >
                        删除
                      </button>
                    </>
                  )}
                </div>
              </div>

              {editing && draft ? (
                <>
                  <div className="card-grid">
                    <div className="field">
                      <label className="field-label" htmlFor="category-name">
                        分类名称
                      </label>
                      <input
                        className="field-input"
                        id="category-name"
                        value={draft.category_name}
                        onChange={(event) =>
                          setDraft({ ...draft, category_name: event.target.value })
                        }
                      />
                    </div>
                    <div className="field">
                      <label className="field-label" htmlFor="department">
                        牵头部门
                      </label>
                      <input
                        className="field-input"
                        id="department"
                        value={draft.department}
                        onChange={(event) =>
                          setDraft({ ...draft, department: event.target.value })
                        }
                      />
                    </div>
                  </div>
                  <TagEditor
                    label="协同部门"
                    hint="输入部门名称后按回车，可点击标签上的 × 移除"
                    values={draft.co_departments}
                    onChange={(co_departments) =>
                      setDraft({ ...draft, co_departments })
                    }
                  />
                  <TagEditor
                    label="关键词"
                    hint="关键词用于分类与转派匹配，输入后按回车添加"
                    values={draft.keywords}
                    onChange={(keywords) => setDraft({ ...draft, keywords })}
                  />
                  <div className="field">
                    <label className="field-label" htmlFor="responsibilities">
                      职责说明
                    </label>
                    <textarea
                      className="field-input"
                      id="responsibilities"
                      rows={5}
                      value={draft.responsibilities}
                      onChange={(event) =>
                        setDraft({ ...draft, responsibilities: event.target.value })
                      }
                    />
                  </div>
                  <div className="field">
                    <div className="field-label">category_code（只读）</div>
                    <div className="field-value mono">{selected.category_code}</div>
                  </div>
                </>
              ) : (
                <>
                  <div className="card-grid">
                    <div className="field">
                      <div className="field-label">category_code</div>
                      <div className="field-value mono">{selected.category_code}</div>
                    </div>
                    <div className="field">
                      <div className="field-label">牵头部门</div>
                      <div className="field-value strong">{selected.department}</div>
                    </div>
                  </div>
                  <div className="field">
                    <div className="field-label">协同部门</div>
                    <div className="field-value">
                      <div className="tag-group">
                        {selected.co_departments.length ? (
                          selected.co_departments.map((item) => (
                            <span className="tag" key={item}>{item}</span>
                          ))
                        ) : (
                          <span className="muted">无</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="field">
                    <div className="field-label">
                      keywords（{selected.keywords.length}）
                    </div>
                    <div className="field-value">
                      <div className="tag-group">
                        {selected.keywords.map((item) => (
                          <span className="tag plain" key={item}>{item}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="field">
                    <div className="field-label">responsibilities</div>
                    <div className="field-value">{selected.responsibilities}</div>
                  </div>
                  <div className="field">
                    <div className="field-label">source / version</div>
                    <div className="field-value secondary-value">
                      {selected.source_name} · {selected.version}
                    </div>
                  </div>
                  <div className="alert" role="note">
                    <span className="alert-ico" aria-hidden="true">⚠</span>
                    <span>{selected.note}</span>
                  </div>
                </>
              )}
            </>
          ) : (
            <div className="empty-state">请选择左侧规则查看详情。</div>
          )}
        </section>
      </div>

      {confirmDelete && selected && (
        <div className="modal-backdrop" role="presentation">
          <div
            className="confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-title"
          >
            <div className="danger-icon" aria-hidden="true">!</div>
            <h2 id="delete-title">删除“{selected.category_name}”规则？</h2>
            <p>
              删除后会同步更新 department_rules.json 和部门规则检索索引。此操作不可撤销。
            </p>
            <div className="dialog-actions">
              <button
                className="btn-ghost"
                type="button"
                onClick={() => setConfirmDelete(false)}
                disabled={deleting}
              >
                取消
              </button>
              <button
                className="btn-danger"
                type="button"
                onClick={remove}
                disabled={deleting}
              >
                {deleting ? "删除中…" : "确认删除"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
