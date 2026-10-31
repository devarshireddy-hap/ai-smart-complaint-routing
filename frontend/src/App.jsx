import React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, Building2,
  Check, ChevronDown, CircleHelp, Clock3, FilePlus2, Filter, LayoutDashboard,
  LogOut, MessageSquareText, Plus, RotateCcw, Search, ShieldCheck,
  Sparkles, Trash2, Users, Wrench, X,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL
  || (import.meta.env.VITE_API_ORIGIN
    ? `${import.meta.env.VITE_API_ORIGIN.replace(/\/$/, "")}/api/v1`
    : "http://localhost:5000/api/v1");
const DEPARTMENTS = ["TECHNICAL", "FINANCE", "ELECTRICAL", "PLUMBING", "SECURITY"];
const STATUS_LABELS = {
  SUBMITTED: "Submitted", ASSIGNED: "Assigned", IN_PROGRESS: "In progress",
  RESOLVED: "Resolved", REJECTED: "Rejected",
};

function googleAccessToken() {
  if (!window.location.hash.startsWith("#access_token=")) return sessionStorage.getItem("campuscare_access_token") || "";
  const token = new URLSearchParams(window.location.hash.slice(1)).get("access_token") || "";
  if (token) sessionStorage.setItem("campuscare_access_token", token);
  window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
  return token;
}

function csrfToken() {
  const match = document.cookie.match(/(?:^|; )csrf_access_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const accessToken = googleAccessToken();
  const headers = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    ...(options.headers || {}),
  };
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) headers["X-CSRF-TOKEN"] = csrfToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  });
  if (response.redirected) return { redirect: response.url };
  const contentType = response.headers.get("content-type") || "";
  const result = response.status === 204 ? {} : contentType.includes("application/json")
    ? await response.json()
    : { error: await response.text() };
  if (!response.ok) {
    const error = new Error(result.error || result.msg || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return result;
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

function initials(name = "") {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function StatusBadge({ status }) {
  return <span className={`status-badge status-${(status || "").toLowerCase()}`}>{STATUS_LABELS[status] || status}</span>;
}

function AuthScreen({ onSignedIn, initialError }) {
  const [portal, setPortal] = useState("");
  const [department, setDepartment] = useState("");
  const [mode, setMode] = useState("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [googleEnabled, setGoogleEnabled] = useState(false);
  const [form, setForm] = useState({ full_name: "", email: "", password: "", user_type: "STUDENT" });
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("department_request") === "pending") {
      setMessage("Your department access request was submitted. An administrator must approve it before you can access the department portal.");
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);
  useEffect(() => {
    api("/auth/options").then((result) => setGoogleEnabled(result.google_enabled)).catch((requestError) => setError(requestError.message));
  }, []);
  useEffect(() => setError(initialError || ""), [initialError]);
  const update = (event) => setForm({ ...form, [event.target.name]: event.target.value });
  const choosePortal = (nextPortal) => {
    setPortal(nextPortal);
    setMode("login");
    setMessage("");
  };
  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result = await api(`/auth/${mode === "login" ? "login" : "register"}`, {
        method: "POST",
        body: JSON.stringify({
          ...form,
          portal,
          ...(portal === "department" ? { department } : {}),
        }),
      });
      if (mode === "register" && portal === "department") {
        await api("/auth/logout", { method: "POST" });
        setMode("login");
        setMessage("Your account request is pending. An administrator must assign you to the selected department before you can access its portal.");
        setForm({ full_name: "", email: "", password: "", user_type: "STUDENT" });
        return;
      }
      onSignedIn(result.user);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="auth-page">
      <section className="auth-visual">
        <div className="auth-brand"><span className="brand-mark"><Sparkles size={18} /></span> CampusCare</div>
        <div className="auth-hero">
          <div className="eyebrow light-eyebrow"><span /> CAMPUS, HEARD.</div>
          <h1>Every issue deserves<br />a clear path forward.</h1>
          <p>One thoughtful place to report a concern, find the right team, and follow it through to a resolution.</p>
          <div className="visual-card">
            <div className="visual-card-top"><span className="pulse-dot" /> LIVE ROUTING PREVIEW <span className="visual-code">AI / 01</span></div>
            <p>“Water is leaking near the east residence hall.”</p>
            <div className="route-preview"><span className="route-icon"><Wrench size={15} /></span><span><b>Plumbing</b><small>Selected department · High priority</small></span><span className="route-confidence">94%</span></div>
          </div>
          <div className="trust-line"><ShieldCheck size={15} /> Private by design <i /> Routed with care <i /> Track every step</div>
        </div>
        <div className="auth-footer">A better campus starts with listening.</div>
      </section>
      <section className="auth-panel">
        <div className="auth-form-wrap">
          <div className="mobile-brand"><span className="brand-mark"><Sparkles size={18} /></span> CampusCare</div>
          <div className="eyebrow">WELCOME TO CAMPUSCARE</div>
          {!portal ? <>
            <h2>Choose your portal.</h2>
            <p className="auth-subtitle">Select how you want to access CampusCare.</p>
            {message && <div className="success-banner">{message}</div>}
            {error && <div className="error-banner">{error}</div>}
            <div className="portal-options">
              <button className="portal-option" onClick={() => choosePortal("student")}><span><MessageSquareText size={18} /></span><b>User portal</b><small>Submit and track campus concerns</small><ArrowRight size={15} /></button>
              <button className="portal-option" onClick={() => choosePortal("admin")}><span><ShieldCheck size={18} /></span><b>Admin portal</b><small>Manage access and campus routing</small><ArrowRight size={15} /></button>
              <button className="portal-option" onClick={() => choosePortal("department")}><span><Building2 size={18} /></span><b>Department portal</b><small>Review concerns assigned to your team</small><ArrowRight size={15} /></button>
            </div>
          </> : <>
          <button className="portal-back" onClick={() => { setPortal(""); setError(""); }}>← All portals</button>
          <div className="eyebrow portal-label">{portal === "student" ? "USER PORTAL" : portal === "admin" ? "ADMIN PORTAL" : "DEPARTMENT PORTAL"}</div>
          <h2>{portal === "admin" ? "Good to have you back." : portal === "department" && mode === "register" ? "Request department access." : portal === "student" && mode === "register" ? "Let's get you started." : "Continue with Google."}</h2>
          <p className="auth-subtitle">{portal === "admin" ? "Sign in to manage campus access and routing." : portal === "department" && mode === "register" ? "Use your verified VIT Google account. An administrator must approve your request." : portal === "department" ? "Sign in with the Google account approved for your department." : "Use your verified VIT Google account to sign in or create your account."}</p>
          {message && <div className="success-banner">{message}</div>}
          {error && <div className="error-banner">{error}</div>}
          {portal === "admin" ? <>
            {googleEnabled && <><a className="button button-google" href={`${API_BASE}/auth/google?${new URLSearchParams({ portal })}`}><span className="google-g">G</span> Continue with Google</a><div className="auth-divider"><span>or use password</span></div></>}
            <form className="auth-form" onSubmit={submit}>
              <label>Email address<input name="email" type="email" value={form.email} onChange={update} autoComplete="username" placeholder="Admin email" required /></label>
              <label>Password<input name="password" type="password" value={form.password} onChange={update} autoComplete="current-password" placeholder="Enter your password" required /></label>
              <button className="button button-primary auth-submit" disabled={busy}>{busy ? "Please wait…" : "Sign in"} <ArrowRight size={16} /></button>
            </form>
          </> : <>
            {portal === "department" && <label>Department<select value={department} onChange={(event) => setDepartment(event.target.value)} required><option value="">Choose your department</option>{DEPARTMENTS.map((item) => <option key={item} value={item}>{item.charAt(0) + item.slice(1).toLowerCase()}</option>)}</select></label>}
            {(portal === "student" || portal === "department") && <small className="field-hint">Use a VIT Google account whose email domain starts with “vit” and ends in “.ac.in”.</small>}
            {googleEnabled && (portal !== "department" || department) && <a className="button button-google" href={`${API_BASE}/auth/google?${new URLSearchParams({ portal, ...(portal === "department" ? { department } : {}), ...(mode === "register" ? { mode } : {}) })}`}><span className="google-g">G</span> Continue with Google</a>}
          </>}
          {portal === "student" || portal === "department" ? <p className="auth-switch">{mode === "login" ? "New to CampusCare?" : "Already have an account?"} <button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); setMessage(""); }}>{mode === "login" ? "Create an account" : "Sign in"}</button></p> : <p className="auth-switch">Portal access is assigned by a CampusCare administrator.</p>}
          <p className="auth-note"><ShieldCheck size={14} /> Your details are only shared with the team handling your concern.</p>
          </>}
        </div>
      </section>
    </main>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState("overview");
  const [complaints, setComplaints] = useState([]);
  const [stats, setStats] = useState({ total: 0, by_status: {}, by_department: {} });
  const [selected, setSelected] = useState(null);
  const [history, setHistory] = useState([]);
  const [users, setUsers] = useState([]);
  const [categories, setCategories] = useState([]);
  const [events, setEvents] = useState([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const isAdmin = user?.role === "ADMIN";
  const isOfficer = user?.role === "OFFICER";

  const refresh = useCallback(async () => {
    if (!user) return;
    setError("");
    try {
      const requests = [api("/complaints"), api("/dashboard")];
      if (user.role === "ADMIN") requests.push(api("/admin/users"), api("/admin/audit"), api("/admin/categories"));
      const results = await Promise.all(requests);
      const [complaintResult, dashboard] = results;
      setComplaints(complaintResult.complaints);
      setStats(dashboard);
      if (user.role === "ADMIN") {
        setUsers(results[2].users);
        setEvents(results[3].events);
        setCategories(results[4].categories);
      }
    } catch (requestError) {
      setError(requestError.message);
    }
  }, [user]);

  const selectedId = selected?.id;
  const refreshSelected = useCallback(async () => {
    if (!selectedId || selectedRef.current?.id !== selectedId) return;
    try {
      const [detail, timeline] = await Promise.all([
        api(`/complaints/${selectedId}`),
        api(`/complaints/${selectedId}/history`),
      ]);
      if (selectedRef.current?.id !== selectedId) return;
      setSelected(detail.complaint);
      setHistory(timeline.history);
    } catch (requestError) {
      setError(requestError.message);
    }
  }, [selectedId]);

  const [bootError, setBootError] = useState("");
  useEffect(() => {
    api("/auth/me").then((result) => {
      setUser(result.user);
      setView(result.user.role === "OFFICER" ? "complaints" : "overview");
    }).catch((requestError) => {
      if (requestError.status !== 401) setBootError(requestError.message);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    refresh();
  }, [user, refresh]);

  useEffect(() => {
    if (!user) return undefined;
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") {
        refresh();
        refreshSelected();
      }
    };
    window.addEventListener("focus", refreshWhenVisible);
    const interval = window.setInterval(refreshWhenVisible, 30000);
    return () => {
      window.removeEventListener("focus", refreshWhenVisible);
      window.clearInterval(interval);
    };
  }, [user, refresh, refreshSelected]);

  useEffect(() => {
    if (!notice) return undefined;
    const timeout = setTimeout(() => setNotice(""), 3500);
    return () => clearTimeout(timeout);
  }, [notice]);

  const filteredComplaints = useMemo(() => complaints.filter((item) => {
    const matchesFilter = filter === "ALL" || item.status === filter;
    const query = search.trim().toLowerCase();
    return matchesFilter && (!query || [item.reference, item.title, item.department, item.status].join(" ").toLowerCase().includes(query));
  }), [complaints, filter, search]);

  const signOut = async () => {
    try { await api("/auth/logout", { method: "POST" }); }
    catch (requestError) { setError(`Sign-out could not clear the server session: ${requestError.message}`); return; }
    setUser(null);
    setComplaints([]);
    setSelected(null);
  };

  const openComplaint = async (complaint) => {
    setError("");
    try {
      const [detail, timeline] = await Promise.all([
        api(`/complaints/${complaint.id}`),
        api(`/complaints/${complaint.id}/history`),
      ]);
      setSelected(detail.complaint);
      setHistory(timeline.history);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const reassignDepartment = async (complaintId, department) => {
    setBusy(true);
    try {
      const result = await api(`/admin/complaints/${complaintId}/department`, {
        method: "PATCH",
        body: JSON.stringify({ department }),
      });
      setSelected(result.complaint);
      setNotice(`${result.complaint.reference} moved to ${department.toLowerCase()}.`);
      await refresh();
      await refreshSelected();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const deleteComplaint = async (complaint) => {
    if (!window.confirm(`Permanently delete ${complaint.reference}? Its complaint history, feedback, and embedding will also be deleted. This cannot be undone.`)) return;
    setBusy(true);
    try {
      await api(`/admin/complaints/${complaint.id}`, { method: "DELETE" });
      setSelected(null);
      setNotice(`${complaint.reference} was deleted.`);
      await refresh();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const saveStatus = async (complaintId, status, resolution = "", department = "") => {
    setBusy(true);
    try {
      await api(`/complaints/${complaintId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status, resolution, department }),
      });
      setNotice("Complaint updated and added to its history.");
      setSelected(null);
      await refresh();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const rollbackComplaint = async (complaint, historyItem) => {
    if (!window.confirm(`Undo the recorded ${historyItem.action.replaceAll("_", " ").toLowerCase()} change?`)) return;
    try {
      await api(`/admin/complaints/${complaint.id}/rollback`, {
        method: "POST",
        body: JSON.stringify({ history_id: historyItem.id }),
      });
      setNotice("The selected change was rolled back and recorded.");
      setSelected(null);
      await refresh();
    } catch (requestError) { setError(requestError.message); }
  };

  const updateRole = async (target, role, department) => {
    try {
      await api(`/admin/users/${target.id}/role`, { method: "PATCH", body: JSON.stringify({ role, department }) });
      await refresh();
      setNotice(`${target.full_name}'s access updated.`);
      return true;
    } catch (requestError) { setError(requestError.message); return false; }
  };

  const deleteUser = async (target) => {
    if (!window.confirm(`Delete ${target.full_name}'s account? Their sign-in details will be removed and the account anonymized. Linked complaint and audit history will be retained.`)) return;
    try {
      await api(`/admin/users/${target.id}`, { method: "DELETE" });
      await refresh();
      setNotice(`${target.full_name}'s account was deleted and anonymized.`);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const rollbackAudit = async (event) => {
    const change = event.action === "USER_ROLE_UPDATED" ? "role and department" : "account status";
    if (!window.confirm(`Roll back the latest ${change} change for ${event.actor}?`)) return;
    try {
      await api(`/admin/audit/${event.id}/rollback`, { method: "POST", body: JSON.stringify({}) });
      await refresh();
      setNotice(`The ${change} change was rolled back.`);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const addCategory = async (department, name) => {
    try {
      await api("/admin/categories", { method: "POST", body: JSON.stringify({ department, name }) });
      await refresh();
      setNotice("Category added to the routing catalog.");
    } catch (requestError) { setError(requestError.message); }
  };

  const sendFeedback = async (complaintId, rating, comment) => {
    try {
      await api(`/complaints/${complaintId}/feedback`, { method: "POST", body: JSON.stringify({ rating, comment }) });
      setNotice("Thanks — your feedback has been recorded.");
      setSelected(null);
    } catch (requestError) { setError(requestError.message); }
  };

  if (loading) return <div className="loading-screen"><span className="brand-mark"><Sparkles size={18} /></span><span>Opening your workspace…</span></div>;
  if (!user) return <AuthScreen onSignedIn={(signedInUser) => {
    setUser(signedInUser);
    setView(signedInUser.role === "OFFICER" ? "complaints" : "overview");
  }} initialError={bootError} />;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={(event) => { event.preventDefault(); setView("overview"); }}><span className="brand-mark"><Sparkles size={17} /></span><span>CampusCare<small>SMART COMPLAINT HUB</small></span></a>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav">
          <button className={view === "overview" ? "active" : ""} onClick={() => setView("overview")}><LayoutDashboard size={17} /> Overview</button>
          <button className={view === "complaints" ? "active" : ""} onClick={() => setView("complaints")}><MessageSquareText size={17} /> {isOfficer ? "Department queue" : "My complaints"}<span className="nav-count">{complaints.length}</span></button>
          {!isOfficer && <button className={view === "submit" ? "active" : ""} onClick={() => { setView("submit"); setSelected(null); }}><FilePlus2 size={17} /> Submit a concern</button>}
          {isAdmin && <><div className="workspace-label admin-label">ADMINISTRATION</div><button className={view === "users" ? "active" : ""} onClick={() => setView("users")}><Users size={17} /> People & access</button><button className={view === "categories" ? "active" : ""} onClick={() => setView("categories")}><Building2 size={17} /> Categories</button><button className={view === "system" ? "active" : ""} onClick={() => setView("system")}><Activity size={17} /> System activity</button></>}
        </nav>
        <div className="sidebar-bottom">
          <div className="help-card"><span className="help-icon"><CircleHelp size={16} /></span><b>Need a hand?</b><p>Reach out to campus support if you need help submitting a concern.</p><span className="help-link">View support guide <ArrowRight size={13} /></span></div>
          <div className="profile-row"><span className="avatar">{initials(user.full_name)}</span><span className="profile-meta"><b>{user.full_name}</b><small>{user.role === "USER" ? "User" : `${user.role.toLowerCase()}${user.department ? ` · ${user.department.toLowerCase()}` : ""}`}</small></span><button className="icon-button logout-button" title="Sign out" onClick={signOut}><LogOut size={16} /></button></div>
        </div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">CampusCare <span>/</span> <b>{view === "overview" ? "Overview" : view === "submit" ? "New concern" : view === "complaints" ? "Complaints" : view === "users" ? "People & access" : view === "categories" ? "Categories" : "System activity"}</b></div>
          <div className="topbar-actions"><span className="privacy-chip"><ShieldCheck size={14} /> Private workspace</span><button className="icon-button notification-button" title="Notifications"><Bell size={17} /><i /></button><button className="top-avatar" title="Sign out" aria-label="Sign out" onClick={signOut}>{initials(user.full_name)}</button></div>
        </header>
        <div className="page-wrap">
          {notice && <div className="toast"><Check size={16} /> {notice}<button onClick={() => setNotice("")}><X size={14} /></button></div>}
          {error && <div className="error-banner page-error">{error}<button onClick={() => setError("")}><X size={15} /></button></div>}
          {view === "overview" && <Overview user={user} complaints={complaints} stats={stats} onViewAll={() => setView("complaints")} onNew={() => setView("submit")} onOpen={openComplaint} />}
          {view === "submit" && <SubmitConcern onComplete={async (complaint) => { setNotice(`Concern submitted · ${complaint.reference}`); await refresh(); setView("complaints"); await openComplaint(complaint); }} />}
          {view === "complaints" && <section className="page-section">
            <div className="page-heading"><div><div className="eyebrow">YOUR CAMPUS, YOUR VOICE</div><h1>{isOfficer ? "Department queue" : "My complaints"}</h1><p>{isOfficer ? `Review and progress concerns routed to ${user.department || "your department"}.` : "Follow every concern from first report to resolution."}</p></div>{!isOfficer && <button className="button button-primary" onClick={() => setView("submit")}><Plus size={16} /> New concern</button>}</div>
            <ComplaintTable items={filteredComplaints} search={search} setSearch={setSearch} filter={filter} setFilter={setFilter} onOpen={openComplaint} />
          </section>}
          {view === "users" && isAdmin && <UsersPanel users={users} events={events} onUpdateRole={updateRole} onDeleteUser={deleteUser} onRollback={rollbackAudit} />}
          {view === "categories" && isAdmin && <CategoriesPanel categories={categories} onCreate={addCategory} />}
          {view === "system" && isAdmin && <SystemPanel events={events} onRollback={rollbackAudit} />}
        </div>
        <footer className="page-footer"><span>CampusCare <i /> AI-assisted, human-led</span><span>Need urgent help? Contact campus security directly.</span></footer>
      </main>
      {selected && <ComplaintDrawer key={selected.id} complaint={selected} history={history} user={user} busy={busy} onClose={() => setSelected(null)} onStatus={saveStatus} onDepartment={reassignDepartment} onDelete={deleteComplaint} onRollback={rollbackComplaint} onFeedback={sendFeedback} />}
    </div>
  );
}

function Overview({ user, complaints, stats, onViewAll, onNew, onOpen }) {
  const citizen = user.role === "USER";
  const openCount = (stats.by_status.SUBMITTED || 0) + (stats.by_status.ASSIGNED || 0) + (stats.by_status.IN_PROGRESS || 0);
  const resolvedCount = stats.by_status.RESOLVED || 0;
  const firstName = user.full_name.split(" ")[0];
  return <section className="page-section">
    <div className="welcome-row"><div><div className="eyebrow">{new Intl.DateTimeFormat("en", { weekday: "long", month: "long", day: "numeric" }).format(new Date()).toUpperCase()}</div><h1>{citizen ? `Good day, ${firstName}.` : `Welcome back, ${firstName}.`}</h1><p>{citizen ? "A campus concern is a chance to make things better. We're here to help." : `${user.role === "ADMIN" ? "Here is your campus-wide" : `Here is your ${user.department || "department"}-level`} service snapshot.`}</p></div>{citizen && <button className="button button-primary" onClick={onNew}><Plus size={16} /> Submit a concern</button>}</div>
    <div className="stat-grid">
      <StatCard label={citizen ? "TOTAL SUBMITTED" : "IN YOUR QUEUE"} value={stats.total} icon={<MessageSquareText size={17} />} tone="violet" note="All time" />
      <StatCard label="AWAITING ACTION" value={openCount} icon={<Clock3 size={17} />} tone="amber" note="Submitted or in progress" trendIcon={<ArrowUpRight size={13} />} />
      <StatCard label="RESOLVED" value={resolvedCount} icon={<Check size={17} />} tone="green" note={stats.total ? `${Math.round((resolvedCount / stats.total) * 100)}% of concerns` : "No resolutions yet"} trendIcon={<ArrowDownRight size={13} />} />
      <StatCard label="DEPARTMENTS" value={Object.keys(stats.by_department || {}).length || 5} icon={<Building2 size={17} />} tone="blue" note="Connected to your campus" />
    </div>
    <div className="content-grid">
      <div className="panel recent-panel">
        <div className="panel-heading"><div><h2>{citizen ? "Your recent concerns" : "Recent activity"}</h2><p>{citizen ? "Stay up to date with your reports." : "The latest complaints in your view."}</p></div><button className="text-button" onClick={onViewAll}>View all <ArrowRight size={14} /></button></div>
        {complaints.length === 0 ? <EmptyState onNew={onNew} citizen={citizen} /> : <div className="recent-list">{complaints.slice(0, 5).map((item) => <button className="recent-item" key={item.id} onClick={() => onOpen(item)}><span className={`department-icon ${(item.department || "").toLowerCase()}`}><Building2 size={16} /></span><span className="recent-main"><b>{item.title}</b><small>{item.reference} <i /> {item.department.toLowerCase()} <i /> {formatDate(item.created_at)}</small></span><StatusBadge status={item.status} /><ArrowRight className="recent-arrow" size={15} /></button>)}</div>}
      </div>
      <div className="right-column">
        <div className="ai-card"><div className="ai-card-label"><span><Sparkles size={14} /></span> SMART ROUTING</div><h3>Right issue.<br />Right people.</h3><p>You choose the department. AI suggests a category and priority, then finds useful past resolutions.</p><div className="ai-steps"><span><i>01</i> Describe what happened</span><span><i>02</i> Review AI suggestions</span><span><i>03</i> Track the response</span></div>{citizen && <button className="ai-card-link" onClick={onNew}>Start a concern <ArrowRight size={14} /></button>}</div>
        <div className="department-panel panel"><div className="panel-heading compact"><div><h2>Department pulse</h2><p>Where concerns are routed.</p></div><Building2 size={17} className="muted-icon" /></div><div className="dept-bars">{DEPARTMENTS.map((department) => { const amount = stats.by_department?.[department] || 0; const max = Math.max(1, ...Object.values(stats.by_department || {})); return <div className="dept-bar-row" key={department}><span>{department.toLowerCase()}</span><div className="bar-track"><i style={{ width: `${Math.max(amount ? 10 : 0, (amount / max) * 100)}%` }} /></div><b>{amount}</b></div>; })}</div></div>
      </div>
    </div>
  </section>;
}

function StatCard({ label, value, icon, tone, note, trendIcon }) {
  return <div className="stat-card"><div className="stat-card-top"><span>{label}</span><span className={`stat-icon ${tone}`}>{icon}</span></div><div className="stat-value">{value}</div><div className="stat-note">{trendIcon && <span>{trendIcon}</span>}{note}</div></div>;
}

function EmptyState({ onNew, citizen }) {
  return <div className="empty-state"><div className="empty-illustration"><MessageSquareText size={24} /></div><h3>{citizen ? "Nothing to follow just yet" : "Your queue is clear"}</h3><p>{citizen ? "When something needs attention, let us know. We'll help it find the right team." : "New concerns routed to your department will appear here."}</p>{citizen && <button className="button button-outline" onClick={onNew}>Submit your first concern <ArrowRight size={14} /></button>}</div>;
}

function ComplaintTable({ items, search, setSearch, filter, setFilter, onOpen }) {
  return <div className="panel table-panel"><div className="table-toolbar"><label className="search-box"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search concerns…" /></label><label className="filter-select"><Filter size={15} /><select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="ALL">All statuses</option>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><ChevronDown size={14} /></label><span className="results-count">{items.length} results</span></div>
    {items.length === 0 ? <div className="empty-table">No concerns match this view.</div> : <div className="table-scroll"><table><thead><tr><th>CONCERN</th><th>DEPARTMENT</th><th>PRIORITY</th><th>STATUS</th><th>SUBMITTED</th><th /></tr></thead><tbody>{items.map((item) => <tr key={item.id} onClick={() => onOpen(item)}><td><span className="complaint-title">{item.title}</span><small>{item.reference}</small></td><td><span className="dept-cell"><i className={`department-dot ${(item.department || "").toLowerCase()}`} />{item.department.toLowerCase()}</span></td><td><span className={`priority priority-${item.priority.toLowerCase()}`}><i />{item.priority.toLowerCase()}</span></td><td><StatusBadge status={item.status} /></td><td className="date-cell">{formatDate(item.created_at)}</td><td><ArrowRight size={15} className="table-arrow" /></td></tr>)}</tbody></table></div>}
  </div>;
}

function SubmitConcern({ onComplete }) {
  const [form, setForm] = useState({ title: "", description: "", location: "", department: "" });
  const [analysis, setAnalysis] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [step, setStep] = useState(1);
  const analyze = async (event) => {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      const result = await api("/ai/analyze", { method: "POST", body: JSON.stringify({ description: form.description, department: form.department }) });
      setAnalysis(result);
      setForm((current) => ({ ...current, department: result.department }));
      setStep(2);
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  };
  const submit = async () => {
    setBusy(true); setError("");
    try {
      const result = await api("/complaints", { method: "POST", body: JSON.stringify(form) });
      await onComplete(result.complaint);
    } catch (requestError) { setError(requestError.message); setBusy(false); }
  };
  return <section className="page-section submit-section">
    <div className="page-heading"><div><div className="eyebrow">WE'RE LISTENING</div><h1>Submit a concern</h1><p>Tell us what is happening. We'll help it reach the right team.</p></div><div className="step-indicator"><span className={step >= 1 ? "current" : ""}>01</span><i /><span className={step >= 2 ? "current" : ""}>02</span><small>{step === 1 ? "Your concern" : "Review & send"}</small></div></div>
    <div className="form-layout">
      <div className="panel form-panel">
        <div className="form-panel-title"><span className="form-title-icon"><FilePlus2 size={18} /></span><div><h2>{step === 1 ? "What needs attention?" : "Review your concern"}</h2><p>{step === 1 ? "A few details will help us understand and route it." : "Check the AI suggestions before it goes to your campus team."}</p></div></div>
        {error && <div className="error-banner">{error}</div>}
        {step === 1 ? <form onSubmit={analyze} className="concern-form">
          <label>Short title <span>REQUIRED</span><input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="e.g. Water leak near the east residence hall" minLength={4} maxLength={160} required /></label>
          <label>What happened? <span>REQUIRED</span><textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Share the details that will help the team understand the issue. Include what you noticed and when it started." minLength={15} maxLength={5000} rows={6} required /><small className="field-hint">Please avoid sharing passwords or sensitive personal information.</small></label>
          <label>Department <span>REQUIRED</span><select value={form.department} onChange={(event) => setForm({ ...form, department: event.target.value })} required><option value="">Choose a department</option>{DEPARTMENTS.map((department) => <option key={department} value={department}>{department.charAt(0) + department.slice(1).toLowerCase()}</option>)}</select><small className="field-hint">You choose the team. AI will suggest a category and priority for your review.</small></label>
          <label>Where is it happening? <span>OPTIONAL</span><input value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} placeholder="Building, room, or campus area" maxLength={160} /></label>
          <button className="button button-primary form-submit" disabled={busy}>{busy ? "Finding the right team…" : "Review AI suggestions"} <Sparkles size={15} /></button>
        </form> : <>
          <div className="analysis-result"><div className="analysis-heading"><span className="analysis-spark"><Sparkles size={16} /></span><span><b>AI suggestions are ready</b><small>Based on similar past concerns and campus guidance.</small></span><span className="match-pill">AI REVIEW</span></div><div className="suggestion-grid"><div><span className="suggestion-label">YOUR DEPARTMENT</span><b>{form.department}</b></div><div><span className="suggestion-label">CATEGORY</span><b>{analysis?.category}</b></div><div><span className="suggestion-label">AI PRIORITY</span><b className={`priority-text priority-${(analysis?.priority || "medium").toLowerCase()}`}>{analysis?.priority}</b></div></div>
            {analysis?.duplicate && <div className="duplicate-warning"><span>!</span><div><b>This may be similar to an existing concern.</b><small>We’ll still submit it so the team can review it alongside related reports.</small></div></div>}
            <div className="resolution-suggestion"><span className="suggestion-label">SUGGESTED NEXT STEP</span><p>{analysis?.suggested_resolution}</p></div>
            {analysis?.warning && <p className="model-warning">AI is running in local example-matching mode: {analysis.warning}</p>}
          </div>
          <div className="review-summary"><b>{form.title}</b><p>{form.description}</p>{form.location && <small><Building2 size={13} /> {form.location}</small>}</div>
          <div className="review-actions"><button className="button button-outline" onClick={() => setStep(1)} disabled={busy}>Back to edit</button><button className="button button-primary" onClick={submit} disabled={busy}>{busy ? "Submitting…" : "Submit concern"} <ArrowRight size={15} /></button></div>
        </>}
      </div>
      <aside className="form-aside"><div className="aside-card"><span className="aside-icon"><ShieldCheck size={18} /></span><h3>Your privacy matters</h3><p>Your concern is visible only to you and the staff authorized to respond.</p></div><div className="aside-card process-card"><span className="aside-icon purple"><Activity size={18} /></span><h3>What happens next?</h3><ol><li><i>1</i><span><b>Department selection</b><small>You choose the team that receives the concern.</small></span></li><li><i>2</i><span><b>Team review</b><small>A staff member takes a look.</small></span></li><li><i>3</i><span><b>Clear follow-up</b><small>Track progress right here.</small></span></li></ol></div><div className="aside-note"><CircleHelp size={15} /><span>For immediate danger, contact campus security directly.</span></div></aside>
    </div>
  </section>;
}

function ComplaintDrawer({ complaint, history, user, busy, onClose, onStatus, onDepartment, onDelete, onRollback, onFeedback }) {
  const [resolution, setResolution] = useState("");
  const [rating, setRating] = useState(5);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [department, setDepartment] = useState(complaint.department);
  const transitions = {
    SUBMITTED: ["ASSIGNED", "IN_PROGRESS", "REJECTED"],
    ASSIGNED: ["IN_PROGRESS", "REJECTED"],
    IN_PROGRESS: ["RESOLVED", "REJECTED"],
  };
  const nextStatuses = transitions[complaint.status] || [];
  const [status, setStatus] = useState(nextStatuses[0] || "IN_PROGRESS");
  const staff = user.role === "ADMIN" || user.role === "OFFICER";
  return <div className="drawer-backdrop" onClick={onClose}><aside className="complaint-drawer" onClick={(event) => event.stopPropagation()}>
    <header className="drawer-header"><span className="eyebrow">CONCERN DETAILS</span><button className="icon-button" onClick={onClose} aria-label="Close"><X size={19} /></button></header>
    <div className="drawer-content"><div className="drawer-reference">{complaint.reference} <StatusBadge status={complaint.status} /></div><h2>{complaint.title}</h2><div className="drawer-meta"><span><Building2 size={14} /> {complaint.department.toLowerCase()}</span><span><Clock3 size={14} /> {formatDate(complaint.created_at)}</span></div>
      <div className="drawer-section"><span className="drawer-label">DESCRIPTION</span><p>{complaint.description}</p>{complaint.location && <small className="location-pill"><Building2 size={13} />{complaint.location}</small>}</div>
      <div className="drawer-ai"><div><Sparkles size={15} /><b>AI routing</b></div><p>{complaint.category} <i /> {complaint.priority.toLowerCase()} priority</p>{complaint.suggested_resolution && <small>{complaint.suggested_resolution}</small>}</div>
      {complaint.resolution && <div className="drawer-section resolution-box"><span className="drawer-label">RESOLUTION</span><p>{complaint.resolution}</p></div>}
      <div className="drawer-section timeline-section"><span className="drawer-label">ACTIVITY TIMELINE</span><div className="timeline">{history.map((item) => <div className="timeline-item" key={item.id}><i /><span><b>{item.action.replaceAll("_", " ").toLowerCase()}</b><small>Activity #{item.id} · {item.actor} · {formatDate(item.created_at)}</small>{item.note && <small>{item.note}</small>}{user.role === "ADMIN" && item.before_state && history[history.length - 1]?.id === item.id && <button className="timeline-undo" onClick={() => onRollback(complaint, item)}><RotateCcw size={12} /> Undo latest change</button>}</span></div>)}</div></div>
      {user.role === "ADMIN" && <div className="drawer-actions"><label>Responsible department<select value={department} onChange={(event) => setDepartment(event.target.value)}>{DEPARTMENTS.map((name) => <option key={name} value={name}>{name}</option>)}</select></label><button className="button button-outline" onClick={() => onDepartment(complaint.id, department)} disabled={busy || department === complaint.department}>{busy ? "Saving…" : "Change department"} <Building2 size={15} /></button><button className="delete-user-button" onClick={() => onDelete(complaint)} disabled={busy}><Trash2 size={14} /> Delete complaint</button></div>}
      {staff && nextStatuses.length > 0 && <div className="drawer-actions"><label>Update status<select value={status} onChange={(event) => setStatus(event.target.value)}>{nextStatuses.map((nextStatus) => <option key={nextStatus} value={nextStatus}>{STATUS_LABELS[nextStatus]}</option>)}</select></label>{status === "RESOLVED" && <label>Resolution details<textarea value={resolution} onChange={(event) => setResolution(event.target.value)} minLength={10} rows={3} placeholder="What was done to resolve this?" required /></label>}<button className="button button-primary" onClick={() => onStatus(complaint.id, status, resolution, complaint.department)} disabled={busy || (status === "RESOLVED" && resolution.trim().length < 10)}>{busy ? "Saving…" : status === "RESOLVED" ? "Close complaint" : "Save update"} {status === "RESOLVED" ? <Check size={15} /> : <ArrowRight size={15} />}</button></div>}
      {user.role === "USER" && complaint.status === "RESOLVED" && (complaint.feedback_submitted ? <p className="feedback-thanks">Thank you — your feedback is recorded.</p> : <div className="feedback-box"><label>How was this resolved?<select value={rating} onChange={(event) => setRating(Number(event.target.value))}><option value={5}>5 — Excellent</option><option value={4}>4 — Good</option><option value={3}>3 — Okay</option><option value={2}>2 — Needs improvement</option><option value={1}>1 — Not resolved well</option></select></label><textarea value={feedbackComment} onChange={(event) => setFeedbackComment(event.target.value)} maxLength={1000} placeholder="Optional feedback" rows={2} /><button className="button button-outline" onClick={() => onFeedback(complaint.id, rating, feedbackComment)}>Send feedback</button></div>)}
    </div>
  </aside></div>;
}

function UsersPanel({ users, events, onUpdateRole, onDeleteUser, onRollback }) {
  const [pending, setPending] = useState({});
  const setRole = (item, role) => {
    if (role === "OFFICER") {
      setPending((current) => ({ ...current, [item.id]: { role, department: item.department || "" } }));
    } else {
      setPending((current) => { const next = { ...current }; delete next[item.id]; return next; });
      onUpdateRole(item, role, "");
    }
  };
  const applyOfficer = (item) => {
    const selection = pending[item.id];
    if (!selection?.department) return;
    onUpdateRole(item, "OFFICER", selection.department).then((updated) => {
      if (updated) setPending((current) => { const next = { ...current }; delete next[item.id]; return next; });
    });
  };
  return <section className="page-section"><div className="page-heading"><div><div className="eyebrow">ACCESS CONTROL</div><h1>People & access</h1><p>Assign least-privilege roles for complaint review and administration.</p></div><span className="admin-chip"><ShieldCheck size={14} /> ADMIN ONLY</span></div><div className="panel table-panel"><div className="panel-heading users-heading"><div><h2>Registered accounts</h2><p>{users.length} people in your workspace</p></div><span className="results-count">Roles are enforced by the API</span></div><div className="table-scroll"><table><thead><tr><th>PERSON / ACTIONS</th><th>PORTAL TYPE</th><th>ROLE</th><th>DEPARTMENT</th><th>ACCOUNT</th></tr></thead><tbody>{users.map((item) => {
    const selection = pending[item.id];
    const role = selection?.role || item.role;
    const department = selection?.department ?? item.department ?? "";
    const latestReversibleEvent = events.find((event) =>
      event.resource_type === "user"
      && event.resource_id === item.id
      && event.can_rollback
    );
    return <tr key={item.id} onClick={(event) => event.stopPropagation()}>
      <td><span className="user-cell"><i className="avatar small-avatar">{initials(item.full_name)}</i><span><b>{item.full_name}</b><small>{item.email}</small><span className="user-action-buttons">
        {latestReversibleEvent && <button className="rollback-access-button" onClick={() => onRollback(latestReversibleEvent)} title="Undo latest access change"><RotateCcw size={13} /> Undo access change</button>}
        <button className="delete-user-button" onClick={() => onDeleteUser(item)} title="Delete account"><Trash2 size={14} /> Delete account</button>
      </span></span></span></td>
      <td>{item.role === "ADMIN" ? "Admin" : item.role === "OFFICER" ? "Department" : item.user_type === "WORKING_STAFF" ? "Department pending" : "User"}</td>
      <td><select className="role-select" value={role} onChange={(event) => setRole(item, event.target.value)}><option value="USER">User</option><option value="OFFICER">Officer</option><option value="ADMIN">Admin</option></select></td>
      <td>{role === "OFFICER" ? <div className="department-assignment"><select className="role-select" value={department} onChange={(event) => {
        if (selection) setPending((current) => ({ ...current, [item.id]: { ...selection, department: event.target.value } }));
        else onUpdateRole(item, "OFFICER", event.target.value);
      }}><option value="">Choose department</option>{DEPARTMENTS.map((name) => <option key={name}>{name}</option>)}</select>{selection && <button className="apply-role" disabled={!department} onClick={() => applyOfficer(item)}>Apply</button>}</div> : item.user_type === "WORKING_STAFF" && item.department ? <span>{item.department.toLowerCase()} · pending{item.role === "USER" && <button className="apply-role" onClick={() => onUpdateRole(item, "OFFICER", item.department)}>Approve request</button>}</span> : <span className="muted">—</span>}</td>
      <td><span className={`account-status ${item.is_active ? "active" : ""}`}><i />{item.is_active ? "Active" : "Disabled"}</span></td>
    </tr>;
  })}</tbody></table></div></div><p className="permission-note"><ShieldCheck size={15} /> New registrations are Users. Department sign-up requests remain pending until an administrator approves them as Officers. Only Admins can change access.</p></section>;
}

function CategoriesPanel({ categories, onCreate }) {
  const [department, setDepartment] = useState(DEPARTMENTS[0]);
  const [name, setName] = useState("");
  const submit = (event) => {
    event.preventDefault();
    onCreate(department, name.trim());
    setName("");
  };
  return <section className="page-section"><div className="page-heading"><div><div className="eyebrow">ROUTING CATALOG</div><h1>Complaint categories</h1><p>Maintain the categories available to AI-assisted department routing.</p></div><span className="admin-chip"><ShieldCheck size={14} /> ADMIN ONLY</span></div><div className="categories-layout"><form className="panel category-form" onSubmit={submit}><h2>Add a category</h2><p>New categories become available to future AI routing suggestions.</p><label>Department<select value={department} onChange={(event) => setDepartment(event.target.value)}>{DEPARTMENTS.map((item) => <option key={item}>{item}</option>)}</select></label><label>Category name<input value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={80} placeholder="e.g. Water Leakage" required /></label><button className="button button-primary"><Plus size={15} /> Add category</button></form><div className="panel category-list"><div className="panel-heading"><div><h2>Routing categories</h2><p>{categories.length} categories across five departments</p></div></div><div className="category-groups">{DEPARTMENTS.map((item) => {
    const group = categories.filter((category) => category.department === item);
    return <div className="category-group" key={item}><span className={`department-dot ${item.toLowerCase()}`} /><b>{item.toLowerCase()}</b><div>{group.map((category) => <span className="category-chip" key={category.id}>{category.name}</span>)}</div></div>;
  })}</div></div></div></section>;
}

function SystemPanel({ events, onRollback }) {
  return <section className="page-section"><div className="page-heading"><div><div className="eyebrow">OVERSIGHT</div><h1>System activity</h1><p>Review account actions and complaint changes.</p></div><span className="admin-chip"><ShieldCheck size={14} /> ADMIN ONLY</span></div>
    <div className="panel table-panel"><div className="panel-heading users-heading"><div><h2>Audit trail</h2><p>Latest security-relevant actions. Reversible access changes can be undone.</p></div><Activity size={17} className="muted-icon" /></div><div className="audit-list">{events.length ? events.map((event) => <div className="audit-item" key={event.id}><span className="audit-dot" /><span><b>{event.action.replaceAll("_", " ").toLowerCase()}</b><small>Activity #{event.id} · {event.actor} · {event.resource_type}{event.resource_id ? ` · ${String(event.resource_id).slice(0, 8)}` : ""}</small></span><time>{formatDate(event.created_at)}</time>{event.can_rollback && <button className="rollback-access-button" onClick={() => onRollback(event)}><RotateCcw size={13} /> Roll back</button>}</div>) : <div className="empty-table">No audited activity yet.</div>}</div></div>
  </section>;
}

export default App;
