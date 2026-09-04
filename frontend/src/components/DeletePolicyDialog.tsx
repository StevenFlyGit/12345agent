import { useEffect } from "react";
import { PolicyFileItem } from "../api";

interface DeletePolicyDialogProps {
  item: PolicyFileItem;
  deleting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export default function DeletePolicyDialog({
  item,
  deleting,
  onCancel,
  onConfirm,
}: DeletePolicyDialogProps) {
  useEffect(() => {
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape" && !deleting) onCancel();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [deleting, onCancel]);

  return (
    <div className="modal-backdrop" role="presentation">
      <div
        className="confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-policy-title"
        aria-describedby="delete-policy-description"
      >
        <div className="danger-icon" aria-hidden="true">!</div>
        <h2 id="delete-policy-title">删除政策文件？</h2>
        <p id="delete-policy-description">
          将删除“{item.source_name}”及其检索索引，删除后无法恢复。
        </p>
        <div className="dialog-actions">
          <button
            className="btn-ghost"
            type="button"
            onClick={onCancel}
            disabled={deleting}
            autoFocus
          >
            取消
          </button>
          <button
            className="btn-danger"
            type="button"
            onClick={onConfirm}
            disabled={deleting}
          >
            {deleting ? "正在删除…" : "确认删除"}
          </button>
        </div>
      </div>
    </div>
  );
}
