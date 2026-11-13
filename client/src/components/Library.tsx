"use client";
import { useEffect, useRef, useState } from "react";
import { errorMessage } from "@/lib/apiClient";
import { Icon } from "@/components/Icon";
import { listErrorMessage, useClipState, useListActions, useLists, useToggleMark } from "@/lib/library";

/** Real like / watch-later state for one clip (INT-61). Buttons stay page-specific; this is the shared behaviour. */
export function useClipActions(clipId: string | null | undefined, onMessage: (s: string) => void) {
    const state = useClipState(clipId);
    const like = useToggleMark("likes");
    const save = useToggleMark("saved");
    const liked = !!state.data?.liked;
    const saved = !!state.data?.saved;
    const fail = (e: unknown) => onMessage(errorMessage(e));
    return {
        liked, saved, inList: !!state.data?.list_ids.length, ready: !!clipId,
        toggleLike: () => { if (clipId) like.mutate({ clipId, on: !liked }, { onError: fail }); },
        toggleSave: () => { if (clipId) save.mutate({ clipId, on: !saved }, { onSuccess: () => onMessage(saved ? "Đã bỏ khỏi Xem sau." : "Đã thêm vào Xem sau."), onError: fail }); },
    };
}

/** "Thêm vào danh sách": one checkbox per user list + inline create. Opens as a modal while clipId is set. */
export function ListPicker({ clipId, onClose }: { clipId: string | null; onClose: () => void }) {
    const ref = useRef<HTMLDialogElement>(null);
    const lists = useLists();
    const state = useClipState(clipId);
    const actions = useListActions();
    const [name, setName] = useState("");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    useEffect(() => {
        if (clipId && !ref.current?.open) ref.current?.showModal();
        else if (!clipId && ref.current?.open) ref.current.close();
        setError("");
        setName("");
    }, [clipId]);
    const run = async (fn: () => Promise<unknown>) => {
        setBusy(true);
        setError("");
        try { await fn(); } catch (e) { setError(listErrorMessage(e)); } finally { setBusy(false); }
    };
    const create = (e: React.FormEvent) => {
        e.preventDefault();
        if (!clipId) return;
        if (!name.trim()) { setError("Nhập tên danh sách."); return; }
        void run(async () => { const list = await actions.create(name); await actions.setMember(list.id, clipId, true); setName(""); });
    };
    const member = new Set(state.data?.list_ids || []);
    return <dialog ref={ref} className="account-dialog list-picker" aria-labelledby="list-picker-title" onClose={onClose} onCancel={onClose}>
        <header><h2 id="list-picker-title">Thêm vào danh sách</h2><button className="icon-button" onClick={onClose} aria-label="Đóng"><Icon name="close"/></button></header>
        {lists.isPending ? <p className="list-picker-note">Đang tải…</p> : lists.error ? <p className="error-banner" role="alert">{errorMessage(lists.error)}</p>
            : !lists.data?.length ? <p className="list-picker-note">Chưa có danh sách. Tạo danh sách đầu tiên bên dưới.</p>
            : <ul className="list-picker-items">{lists.data.map(list => <li key={list.id}><label><input type="checkbox" checked={member.has(list.id)} disabled={busy || !clipId}
                onChange={e => clipId && void run(() => actions.setMember(list.id, clipId, e.target.checked))}/><span className="line-clamp-1">{list.name}</span><small>{list.item_count} clip</small></label></li>)}</ul>}
        <form className="list-picker-create" onSubmit={create}><input className="input" aria-label="Tên danh sách mới" placeholder="Tên danh sách mới" maxLength={60} value={name} onChange={e => setName(e.target.value)}/>
            <button className="btn-primary" disabled={busy}><Icon name="add" size={18}/>Tạo</button></form>
        {error && <p className="error-banner" role="alert">{error}</p>}
    </dialog>;
}
