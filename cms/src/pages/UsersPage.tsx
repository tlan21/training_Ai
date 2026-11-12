import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { components } from "../api-types";
import { useCmsUsers, useResetUserPassword } from "../hooks/useCms";
import { useAuthStore } from "../stores/authStore";
import { Icon } from "../components/common/Icon";
import { Modal } from "../components/common/Modal";
import { Pagination } from "../components/common/Media";
import { Skeleton, Empty, ErrorState } from "../components/common/Skeleton";
import { useToast } from "../components/common/Toast";
import { errorMessage } from "../lib/apiClient";
import { fmtISO } from "../lib/time";

type User = components["schemas"]["User"];

export default function UsersPage() {
  const [params] = useSearchParams();
  const query = params.get("q") ?? "";
  const [page, setPage] = useState(1);
  const [resetting, setResetting] = useState<User | null>(null);
  useEffect(() => setPage(1), [query]);
  const list = useCmsUsers(page, query);
  const myId = useAuthStore((state) => state.user?.id);
  return <div><div className="page-header"><div><h2>Quản lý người dùng</h2><p>Danh sách tài khoản trong hệ thống. Quản trị viên có thể đặt lại mật khẩu; không tạo, phân quyền hay xóa tài khoản tại CMS.</p></div><button className="btn-secondary" onClick={() => list.refetch()} disabled={list.isFetching}><Icon name="refresh" size={18} />Tải lại danh sách</button></div>
    <section className="card table-card"><div className="table-scroll"><table className="data-table users-table"><thead><tr><th>Tên người dùng</th><th>Email</th><th>Ngày tạo</th><th>Thao tác</th></tr></thead><tbody>{list.data?.items?.map((user) => <tr key={user.id}><td><div className="account-row"><span className="avatar"><Icon name="person" size={20} /></span><div><strong>{user.username}</strong>{user.id === myId && <p className="micro">Tài khoản của bạn</p>}</div></div></td><td>{user.email}</td><td>{user.created_at ? fmtISO(user.created_at) : "—"}</td>
      <td><div className="row-actions"><button className="btn-text" disabled={user.id === myId} title={user.id === myId ? "Đổi mật khẩu của bạn tại Cài đặt › Bảo mật" : undefined} aria-label={`Đặt lại mật khẩu cho ${user.username}`} onClick={() => setResetting(user)}><Icon name="key" size={18} />Đặt lại mật khẩu</button></div></td></tr>)}</tbody></table></div>
      {list.isLoading ? <div className="panel-body"><Skeleton h={48} /><Skeleton h={48} /></div> : list.isError ? <ErrorState msg={errorMessage(list.error)} onRetry={() => list.refetch()} /> : !list.data?.items?.length && <Empty msg="Không có tài khoản khớp tìm kiếm" />}<Pagination page={page} total={list.data?.total ?? 0} onPage={setPage} />
    </section>
    {resetting && <ResetPasswordModal user={resetting} onClose={() => setResetting(null)} />}</div>;
}

function ResetPasswordModal({ user, onClose }: { user: User; onClose: () => void }) {
  const reset = useResetUserPassword();
  const toast = useToast();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [serverError, setServerError] = useState("");
  const bytes = new TextEncoder().encode(password).length;
  const error = !password ? "" : bytes < 8 ? "Mật khẩu tối thiểu 8 ký tự" : bytes > 72 ? "Mật khẩu quá dài (tối đa 72 byte)" : confirmPassword && confirmPassword !== password ? "Mật khẩu nhập lại không khớp" : "";
  const ready = !!password && confirmPassword === password && !error;
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!ready) return;
    try {
      await reset.mutateAsync({ id: user.id!, new_password: password });
      toast.ok(`Đã đặt lại mật khẩu cho ${user.username}. Mọi phiên của tài khoản này đã bị đăng xuất.`);
      onClose();
    } catch (err) { setServerError(errorMessage(err)); }
  };
  return <Modal onClose={() => { if (!reset.isPending) onClose(); }}><form className="card modal" aria-label="Đặt lại mật khẩu" onSubmit={submit} noValidate onClick={(event) => event.stopPropagation()}>
    <h3>Đặt lại mật khẩu</h3><p>{user.username} · {user.email}</p>
    <p className="micro">Mật khẩu mới có hiệu lực ngay; mọi phiên đăng nhập của tài khoản này bị đăng xuất. Hãy gửi mật khẩu cho người dùng qua kênh an toàn — hệ thống không gửi email.</p>
    <div className="field"><label htmlFor="reset-password">Mật khẩu mới</label><input id="reset-password" className="input" type="password" autoComplete="new-password" value={password} aria-invalid={!!error} onChange={(event) => { setPassword(event.target.value); setServerError(""); }} autoFocus /></div>
    <div className="field"><label htmlFor="reset-password-confirm">Nhập lại mật khẩu mới</label><input id="reset-password-confirm" className="input" type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></div>
    {(error || serverError) ? <p className="error-text" role="alert">{serverError || error}</p> : <p className="micro">Tối thiểu 8 ký tự.</p>}
    <div className="page-actions"><button type="button" className="btn-outline" onClick={onClose} disabled={reset.isPending}>Hủy</button><button className="btn-primary" disabled={!ready || reset.isPending}>{reset.isPending ? "Đang lưu…" : "Đặt lại mật khẩu"}</button></div>
  </form></Modal>;
}
