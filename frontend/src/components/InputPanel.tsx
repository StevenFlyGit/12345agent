import { useEffect, useRef, useState } from "react";
import { CaseState, createCase, createCaseAudio, getSamples, SamplesResponse, TextSample, AudioSample } from "../api";

interface Props {
  onCreated: (c: CaseState) => void;
}

const HINT = "上传官方样例录音（保持原文件名 source_id.mp3）可按文件名精确转写；其他录音若无 ASR 引擎则返回模拟示例文本。";

export default function InputPanel({ onCreated }: Props) {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [samples, setSamples] = useState<SamplesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getSamples().then(setSamples).catch(() => setSamples(null));
  }, []);

  const submit = async () => {
    setErr("");
    if (!text.trim() && !file) {
      setErr("请填写诉求文本或上传录音");
      return;
    }
    setLoading(true);
    try {
      let c: CaseState;
      if (file) {
        const fd = new FormData();
        if (text.trim()) fd.append("text", text);
        fd.append("audio", file);
        c = await createCaseAudio(fd);
      } else {
        c = await createCase(text.trim());
      }
      onCreated(c);
    } catch (e: any) {
      setErr("创建失败：" + (e?.message || "未知错误"));
    } finally {
      setLoading(false);
    }
  };

  const loadTextSample = (s: TextSample) => {
    setText(s.text);
    setFile(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const loadAudioSample = (s: AudioSample) => {
    // 仅提交文件名，后端按 source_id 精确匹配转写
    setText("");
    setFile(null);
    if (fileRef.current) fileRef.current.value = "";
    setLoading(true);
    setErr("");
    // 用 audio_filename 提交（后端按 source_id 精确匹配转写）
    fetch("/api/cases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio_filename: s.filename }),
    })
      .then((r) => r.json())
      .then((c: CaseState) => onCreated(c))
      .catch((e) => setErr("样例录音加载失败：" + e))
      .finally(() => setLoading(false));
  };

  return (
    <div className="panel">
      <div className="panel-head">
        <div className="panel-title">
          <h2>群众诉求录入 <span className="step-tag">STEP 01</span></h2>
          <p>支持文本录入或上传录音（mp3/wav）。录音可保留官方样例文件名以精确转写。</p>
        </div>
      </div>

      <textarea
        className="big-input"
        placeholder="请粘贴或输入群众诉求文本……"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={8}
      />

      <div className="row">
        <input
          ref={fileRef}
          type="file"
          accept="audio/*"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        {file && <span className="badge">已选：{file.name}</span>}
      </div>

      <div className="row wrap">
        <label className="muted">载入示例：</label>
        <select
          defaultValue=""
          onChange={(e) => {
            const v = e.target.value;
            if (!v) return;
            const [kind, idx] = v.split(":");
            if (kind === "t" && samples) loadTextSample(samples.text_samples[Number(idx)]);
            if (kind === "a" && samples) loadAudioSample(samples.audio_samples[Number(idx)]);
            e.target.value = "";
          }}
        >
          <option value="">— 选择文本/录音样例 —</option>
          {samples?.text_samples.map((s, i) => (
            <option key={s.id || i} value={`t:${i}`}>
              [文本] {String(s.text).slice(0, 24)}…
            </option>
          ))}
          {samples?.audio_samples.map((s, i) => (
            <option key={s.source_id} value={`a:${i}`}>
              [录音] {s.title?.slice(0, 20) || s.source_id}
            </option>
          ))}
        </select>
        <span className="muted small">{HINT}</span>
      </div>

      {err && <div className="alert danger"><span className="alert-ico">⚠</span><div>{err}</div></div>}

      <div className="panel-foot">
        <span className="foot-hint">提交后系统将自动完成转写与要素抽取</span>
        <div className="foot-btns">
          <button className="btn-primary" onClick={submit} disabled={loading}>
            {loading ? "分析中…" : "开始分析 →"}
          </button>
        </div>
      </div>
    </div>
  );
}
