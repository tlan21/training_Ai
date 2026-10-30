import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useCmsUsers } from "../hooks/useCms";
import { useAuthStore } from "../stores/authStore";
import { Icon } from "../components/common/Icon";
import { Pagination } from "../components/common/Media";
import { Skeleton, Empty, ErrorState } from "../components/common/Skeleton";
import { errorMessage } from "../lib/apiClient";
import { fmtISO } from "../lib/time";

export default function UsersPage() {
  const [params] = useSearchParams();
  const query = params.get("q") ?? "";
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [query]);
  const list = useCmsUsers(page, query);
  const myId = useAuthStore((state) => state.user?.id);
  return <div><div className="page-header"><div><h2>Quản lý người dùng</h2><p>Danh sách tài khoản trong hệ thống. CMS sử dụng tài khoản quản lý tạo sẵn.</p></div><button className="btn-secondary" onClick={() => list.refetch()} disabled={list.isFetching}><Icon name="refresh" size={18} />Tải lại danh sách</button></div>
    <section className="card table-card"><div className="table-scroll"><table className="data-table users-table"><thead><tr><th>Tên người dùng</th><th>Email</th><th>Ngày tạo</th></tr></thead><tbody>{list.data?.items?.map((user) => <tr key={user.id}><td><div className="account-row"><span className="avatar"><Icon name="person" size={20} /></span><div><strong>{user.username}</strong>{user.id === myId && <p className="micro">Tài khoản của bạn</p>}</div></div></td><td>{user.email}</td><td>{user.created_at ? fmtISO(user.created_at) : "—"}</td></tr>)}</tbody></table></div>
      {list.isLoading ? <div className="panel-body"><Skeleton h={48} /><Skeleton h={48} /></div> : list.isError ? <ErrorState msg={errorMessage(list.error)} onRetry={() => list.refetch()} /> : !list.data?.items?.length && <Empty msg="Không có tài khoản khớp tìm kiếm" />}<Pagination page={page} total={list.data?.total ?? 0} onPage={setPage} />
    </section></div>;
}
