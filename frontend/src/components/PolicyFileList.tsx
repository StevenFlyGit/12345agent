import { PolicyFileItem } from "../api";

interface PolicyFileListProps {
  items: PolicyFileItem[];
  total: number;
  loading: boolean;
  error: string;
  deletingId: string;
  onRetry: () => void;
  onDelete: (item: PolicyFileItem) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

export default function PolicyFileList({
  items,
  total,
  loading,
  error,
  deletingId,
  onRetry,
  onDelete,
}: PolicyFileListProps) {
  return (
    <section className="policy-files-card" aria-labelledby="policy-files-title">
      <div className="policy-files-head">
        <div>
          <h2 id="policy-files-title">已上传政策文件</h2>
          <p>仅展示文件信息，政策正文用于后台检索。</p>
        </div>
        <span className="policy-files-count">共 {total} 份</span>
      </div>

      {error ? (
        <div className="policy-files-error" role="alert">
          <span>{error}</span>
          <button type="button" onClick={onRetry}>重新加载</button>
        </div>
      ) : loading ? (
        <div className="policy-files-skeleton" aria-label="正在加载政策文件">
          {[0, 1, 2].map((item) => <span key={item} />)}
        </div>
      ) : items.length === 0 ? (
        <div className="policy-files-empty">
          <span aria-hidden="true">□</span>
          <p>尚未上传政策文件，可通过上方区域添加。</p>
        </div>
      ) : (
        <div className="policy-files-table-wrap">
          <table className="policy-files-table">
            <thead>
              <tr>
                <th>文件名称</th>
                <th>发布单位</th>
                <th>所属分类</th>
                <th>上传日期</th>
                <th>文件大小</th>
                <th><span className="sr-only">操作</span></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.upload_id}>
                  <td data-label="文件名称">
                    <strong className="policy-source-name">{item.source_name}</strong>
                    <span className="policy-original-name">{item.filename}</span>
                  </td>
                  <td data-label="发布单位">{item.publisher}</td>
                  <td data-label="所属分类">
                    <span className="policy-category-tag">{item.category_name}</span>
                  </td>
                  <td data-label="上传日期">{formatDate(item.uploaded_at)}</td>
                  <td data-label="文件大小">{formatFileSize(item.file_size)}</td>
                  <td className="policy-file-action">
                    <button
                      className="policy-delete-button"
                      type="button"
                      disabled={deletingId === item.upload_id}
                      onClick={() => onDelete(item)}
                      aria-label={`删除政策文件 ${item.source_name}`}
                    >
                      {deletingId === item.upload_id ? "正在删除…" : "删除"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
