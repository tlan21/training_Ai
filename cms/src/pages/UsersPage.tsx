import { useEffect, useState } from "react";
import type { components } from "../api-types";
import { useCmsUsers, useUpdateRole } from "../hooks/useCms";
import { useAuthStore } from "../stores/authStore";
import { Icon } from "../components/common/Icon";
import { Pagination } from "../components/common/Media";
import { Skeleton, Empty, ErrorState } from "../components/common/Skeleton";
import { useToast } from "../components/common/Toast";
import { errorMessage } from "../lib/apiClient";
export default function UsersPage() {
  const [page, setPage] = useState(1);
  const list = useCmsUsers(page);
  const myId = useAuthStore((state) => state.user?.id);
  return <div><div className="page-header"><div><h2>Quản lý người dùng</h2><p>Quản lý tài khoản và phân quyền truy cập CMS.</p></div></div><section className="card table-card"><div className="table-scroll"><table className="data-table users-table"><thead><tr><th>Tên người dùng</th><th>Email</th><th>Vai trò</th><th>Hành động</th></tr></thead><tbody>{list.data?.items?.map((user) => <UserRow key={user.id} user={user} isMe={user.id === myId} />)}</tbody></table></div>{list.isLoading ? <div className="panel-body"><Skeleton h={48} /><Skeleton h={48} /></div> : list.isError ? <ErrorState msg={errorMessage(list.error)} onRetry={() => list.refetch()} /> : !list.data?.items?.length && <Empty msg="Chưa có người dùng" />}<Pagination page={page} total={list.data?.total ?? 0} onPage={setPage} /></section></div>;
}
function UserRow({ user, isMe }: { user: components["schemas"]["User"]; isMe: boolean }) {
  const [role, setRole] = useState(user.role ?? "client");
  const update = useUpdateRole();
  const toast = useToast();
  useEffect(() => setRole(user.role ?? "client"), [user.role]);
  return <tr><td><div className="account-row"><span className="avatar"><Icon name="person" size={20} /></span><div><strong>{user.username}</strong>{isMe && <p className="micro">Tài khoản của bạn</p>}</div></div></td><td>{user.email}</td><td><select className="input compact-input" aria-label={`Vai trò của ${user.username}`} value={role} onChange={(event) => setRole(event.target.value as NonNullable<components["schemas"]["User"]["role"]>)} disabled={isMe || update.isPending}><option value="admin">Quản trị viên</option><option value="editor">Biên tập viên</option><option value="client">Người xem</option></select></td><td><button className="btn-text" disabled={isMe || update.isPending || role === user.role} onClick={() => user.id && update.mutate({ id: user.id, role }, { onSuccess: () => toast.ok("Đã cập nhật vai trò"), onError: (error) => toast.err(errorMessage(error)) })}><Icon name="save" size={18} />{update.isPending ? "Đang lưu…" : "Lưu"}</button></td></tr>;
}
