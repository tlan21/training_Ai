/* eslint-disable @next/next/no-img-element -- Preserve dynamic MinIO signatures without remote optimization. */
import { Icon } from "@/components/Icon";
import { errorMessage } from "@/lib/apiClient";
// Media URLs are dynamic MinIO signatures; a native img preserves them without a remote optimizer.
export function Thumbnail({ src, alt = "", className = "" }: {
    src?: string | null;
    alt?: string;
    className?: string;
}) { return <div className={`thumbnail ${className}`}>{src ? <img src={src} alt={alt} loading="lazy"/> : <Icon name="smart_display" size={32}/>}</div>; }
export function PageState({ loading, error, empty, retry }: {
    loading?: boolean;
    error?: unknown;
    empty?: string;
    retry?: () => void;
}) {
    return <div className={`page-state ${error ? "state-error" : ""}`} role={error ? "alert" : "status"}>
    {loading ? <><span className="skeleton block" style={{ height: 110 }}/>Đang tải…</> : error ? <><Icon name="error"/><p>{errorMessage(error)}</p>{retry && <button className="btn-outline" onClick={retry}><Icon name="refresh" size={18}/>Thử lại</button>}</> : <><Icon name="video_library" size={36}/><p>{empty}</p></>}
  </div>;
}
