interface Props {
  caseId?: string;
  onReset: () => void;
}

export default function CaseBar({ caseId, onReset }: Props) {
  const copy = () => {
    if (caseId) {
      navigator.clipboard?.writeText(caseId);
    }
  };
  return (
    <div className="case-bar">
      <span className="case-bar-label">当前案件</span>
      {caseId ? (
        <code className="case-id" title={caseId}>
          {caseId}
        </code>
      ) : (
        <span className="case-id empty">尚未创建</span>
      )}
      <button className="btn-xs" onClick={copy} disabled={!caseId} type="button">
        复制 ID
      </button>
      <button className="btn-xs" onClick={onReset} type="button">
        重置
      </button>
    </div>
  );
}
