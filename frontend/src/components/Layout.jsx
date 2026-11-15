import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

// The frame around every signed-in page: sidebar on the left, page on the right.
// <Outlet /> is where React Router renders the current page.
export default function Layout() {
  const { user, logout, isAdmin } = useAuth();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">Member Services Portal</div>
        <nav>
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/members">Members</NavLink>
          <NavLink to="/providers">Providers</NavLink>
          <NavLink to="/claims">Claims</NavLink>
          {isAdmin && (
            <>
              <div className="nav-heading">Admin</div>
              <NavLink to="/admin/users">Users</NavLink>
              <NavLink to="/admin/audit-log">Audit log</NavLink>
              <NavLink to="/admin/reports">Reports</NavLink>
            </>
          )}
        </nav>
        <div className="sidebar-footer">
          <div className="user-name">{user.full_name}</div>
          <div className="muted-light">{user.role}</div>
          <button className="btn btn-block" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
