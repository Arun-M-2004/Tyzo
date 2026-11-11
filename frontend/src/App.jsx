
import { useEffect, useMemo, useState } from "react";
import axios from "axios";

import {
  Activity,
  AlertCircle,
  BarChart3,
  Bell,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Clock3,
  Database,
  FileSearch,
  Layers3,
  LayoutDashboard,
  LoaderCircle,
  Search,
  Settings,
  ShieldCheck,
  Ticket,
  X,
  RefreshCw,
} from "lucide-react";

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from "recharts";

import "./App.css";

const API = "http://127.0.0.1:5000/api";
const LIMIT = 20;

const COLORS = [
  "#818cf8",
  "#38bdf8",
  "#34d399",
  "#fbbf24",
  "#fb7185",
  "#a78bfa",
  "#2dd4bf",
  "#94a3b8",
];

const EMPTY_FILTERS = {
  category: "",
  priority: "",
  status: "",
  confidence: "",
};

function App() {
  // --------------------------------------------------
  // APPLICATION STATE
  // --------------------------------------------------

  const [activePage, setActivePage] = useState("overview");

  const [datasets, setDatasets] = useState([]);
  const [datasetId, setDatasetId] = useState("");

  const [summary, setSummary] = useState(null);

  const [tickets, setTickets] = useState([]);
  const [totalTickets, setTotalTickets] = useState(0);

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  const [selectedTicket, setSelectedTicket] = useState(null);

  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const [error, setError] = useState("");

  // --------------------------------------------------
  // LOAD DATASETS
  // --------------------------------------------------

  useEffect(() => {
    let cancelled = false;

    async function loadDatasets() {
      try {
        const response = await axios.get(`${API}/datasets`);

        if (cancelled) return;

        const items = response.data.datasets || [];

        setDatasets(items);

        if (items.length > 0) {
          setDatasetId(String(items[0].id));
        } else {
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setError(
            "Cannot connect to Tyzo backend. Check that Flask is running."
          );
          setLoading(false);
        }
      }
    }

    loadDatasets();

    return () => {
      cancelled = true;
    };
  }, []);

  // --------------------------------------------------
  // LOAD TICKETS WITH SEARCH AND FILTERS
  // --------------------------------------------------

  useEffect(() => {
    if (!datasetId) return;

    let cancelled = false;

    async function loadTickets() {
      setLoading(true);
      setError("");

      try {
        const response = await axios.get(`${API}/tickets`, {
          params: {
            dataset_id: datasetId,
            page,
            limit: LIMIT,
            search: search.trim() || undefined,
            category: filters.category || undefined,
            priority: filters.priority || undefined,
            status: filters.status || undefined,
            confidence: filters.confidence || undefined,
          },
        });

        if (cancelled) return;

        if (!response.data.success) {
          throw new Error("Ticket API returned an unsuccessful response.");
        }

        setTickets(response.data.tickets || []);

        setTotalTickets(
          response.data.pagination?.total_tickets || 0
        );
      } catch (err) {
        if (!cancelled) {
          setTickets([]);
          setTotalTickets(0);
          setError(
            "Unable to load tickets. Please check the backend."
          );
          console.error("Ticket loading failed:", err);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadTickets();

    return () => {
      cancelled = true;
    };
  }, [
    datasetId,
    page,
    search,
    filters.category,
    filters.priority,
    filters.status,
    filters.confidence,
  ]);

  // --------------------------------------------------
  // LOAD FULL DATASET ANALYTICS
  // --------------------------------------------------

  useEffect(() => {
    if (!datasetId) return;

    let cancelled = false;

    async function loadSummary() {
      setSummaryLoading(true);

      try {
        const response = await axios.get(
          `${API}/datasets/${datasetId}/summary`
        );

        if (cancelled) return;

        setSummary(response.data.summary || null);
      } catch (err) {
        if (!cancelled) {
          setSummary(null);
          console.error("Summary loading failed:", err);
        }
      } finally {
        if (!cancelled) {
          setSummaryLoading(false);
        }
      }
    }

    loadSummary();

    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  // --------------------------------------------------
  // CATEGORY DISTRIBUTION
  // --------------------------------------------------

  const categoryData = useMemo(() => {
    return (summary?.category_distribution || []).map((item) => ({
      name: item.problem_category,
      value: item.ticket_count,
    }));
  }, [summary]);

  // --------------------------------------------------
  // AGING STATISTICS
  // --------------------------------------------------

  const olderTickets = useMemo(() => {
    return (summary?.aging_distribution || [])
      .filter((item) =>
        ["30-59 days", "60+ days"].includes(item.aging_band)
      )
      .reduce(
        (total, item) => total + item.ticket_count,
        0
      );
  }, [summary]);

  // --------------------------------------------------
  // HIGH PRIORITY STATISTICS
  // --------------------------------------------------

  const highPriority = useMemo(() => {
    return (summary?.priority_distribution || [])
      .filter((item) => {
        const value = String(item.priority || "").toLowerCase();

        return value.includes("1 -") || value.includes("2 -");
      })
      .reduce(
        (total, item) => total + item.ticket_count,
        0
      );
  }, [summary]);

  // --------------------------------------------------
  // FILTER OPTIONS FROM DATASET SUMMARY
  // --------------------------------------------------

  const categories = summary?.category_distribution?.map(
    (item) => item.problem_category
  ) || [];

  const priorities = summary?.priority_distribution?.map(
    (item) => item.priority
  ) || [];

  const statuses = summary?.status_distribution?.map(
    (item) => item.status
  ) || [];

  const totalPages = Math.max(
    1,
    Math.ceil(totalTickets / LIMIT)
  );

  // --------------------------------------------------
  // OPEN INDIVIDUAL TICKET
  // --------------------------------------------------

  async function openTicket(ticket) {
    setSelectedTicket(ticket);
    setDetailLoading(true);

    try {
      const response = await axios.get(
        `${API}/tickets/${ticket.id}`
      );

      if (response.data.success) {
        setSelectedTicket(response.data.ticket);
      }
    } catch (err) {
      console.error("Ticket detail loading failed:", err);
      setError("Unable to load ticket details.");
    } finally {
      setDetailLoading(false);
    }
  }

  // --------------------------------------------------
  // CHANGE DATASET
  // --------------------------------------------------

  function changeDataset(value) {
    setDatasetId(value);
    setPage(1);
    setSearch("");
    setFilters(EMPTY_FILTERS);
    setSummary(null);
    setSelectedTicket(null);
  }

  // --------------------------------------------------
  // UPDATE FILTER
  // --------------------------------------------------

  function updateFilter(name, value) {
    setFilters((previous) => ({
      ...previous,
      [name]: value,
    }));

    setPage(1);
  }

  // --------------------------------------------------
  // CLEAR FILTERS
  // --------------------------------------------------

  function clearFilters() {
    setSearch("");
    setFilters(EMPTY_FILTERS);
    setPage(1);
  }

  // --------------------------------------------------
  // NAVIGATION
  // --------------------------------------------------

  function navigateTo(pageName) {
    setActivePage(pageName);
    setSelectedTicket(null);
    setError("");
  }

  // --------------------------------------------------
  // DASHBOARD
  // --------------------------------------------------

  return (
    <div className="app-shell">

      {/* SIDEBAR */}

      <aside className="sidebar">

        <div className="brand">
          <div className="brand-mark">T</div>

          <div>
            <h1>tyzo<span>.</span></h1>
            <p>INTELLIGENCE PLATFORM</p>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>

        <nav className="navigation">

          <button
            className={`nav-item ${
              activePage === "overview" ? "active" : ""
            }`}
            onClick={() => navigateTo("overview")}
          >
            <LayoutDashboard size={18} />
            <span>Overview</span>
          </button>

          <button
            className={`nav-item ${
              activePage === "tickets" ? "active" : ""
            }`}
            onClick={() => navigateTo("tickets")}
          >
            <Ticket size={18} />
            <span>Ticket Intelligence</span>
          </button>

          <button
            className={`nav-item ${
              activePage === "collective" ? "active" : ""
            }`}
            onClick={() => navigateTo("collective")}
          >
            <BarChart3 size={18} />
            <span>Collective Intelligence</span>
          </button>

          <button
            className="nav-item"
            onClick={() => setError("Issue Clusters page is coming next.")}
          >
            <Layers3 size={18} />
            <span>Issue Clusters</span>
            <span className="nav-soon">Soon</span>
          </button>

          <button
            className="nav-item"
            onClick={() => setError("Aging Analysis page is coming next.")}
          >
            <Clock3 size={18} />
            <span>Aging Analysis</span>
            <span className="nav-soon">Soon</span>
          </button>

        </nav>

        <div className="nav-label second-label">SYSTEM</div>

        <nav className="navigation">

          <button
            className="nav-item"
            onClick={() => setError("Dataset management is coming next.")}
          >
            <Database size={18} />
            <span>Datasets</span>
          </button>

          <button
            className="nav-item"
            onClick={() => setError("Settings are coming next.")}
          >
            <Settings size={18} />
            <span>Settings</span>
          </button>

          <button
            className="nav-item"
            onClick={() => setError("Help and support is coming next.")}
          >
            <CircleHelp size={18} />
            <span>Help & Support</span>
          </button>

        </nav>

        <div className="sidebar-bottom">

          <div className="system-status">
            <span className="status-dot"></span>

            <div>
              <strong>System operational</strong>
              <p>Connected to local API</p>
            </div>
          </div>

          <div className="profile">
            <div className="avatar">A</div>

            <div>
              <strong>Tyzo Workspace</strong>
              <p>Administrator</p>
            </div>
          </div>

        </div>
      </aside>

      {/* MAIN CONTENT */}

      <main className="main-content">

        {/* TOP BAR */}

        <header className="topbar">

          <div className="breadcrumb">
            Workspace
            <span>/</span>
            <strong>
              {activePage === "overview"
                ? "Overview"
                : activePage === "tickets"
                  ? "Ticket Intelligence"
                  : "Collective Intelligence"}
            </strong>
          </div>

          <div className="topbar-right">

            <div className="api-indicator">
              <span className="status-dot"></span>
              API Connected
            </div>

            <button className="icon-button" aria-label="Notifications">
              <Bell size={19} />
            </button>

            <div className="top-avatar">A</div>

          </div>
        </header>

        <div className="page-content">

          {/* DATASET SELECTOR */}

          <section className="welcome-row">

            <div>
              <div className="eyebrow">
                <Activity size={14} />
                TICKET INTELLIGENCE
              </div>

              <h2>
                {activePage === "overview"
                  ? "Overview"
                  : activePage === "tickets"
                    ? "Ticket Intelligence"
                    : "Collective Intelligence"}
              </h2>

              <p className="page-description">
                {activePage === "overview"
                  ? "Your IT operations, analyzed and organized in one place."
                  : activePage === "tickets"
                    ? "Search, investigate and understand individual IT tickets."
                    : "Discover patterns and trends across your IT tickets."}
              </p>
            </div>

            <div className="dataset-control">

              <label htmlFor="dataset-select">
                ACTIVE DATASET
              </label>

              <div className="select-wrap">

                <Database size={16} />

                <select
                  id="dataset-select"
                  value={datasetId}
                  onChange={(e) => changeDataset(e.target.value)}
                >
                  {datasets.map((dataset) => (
                    <option
                      key={dataset.id}
                      value={dataset.id}
                    >
                      {dataset.original_filename || dataset.dataset_name}
                    </option>
                  ))}
                </select>

                <ChevronDown size={15} />

              </div>
            </div>

          </section>

          {/* ERROR MESSAGE */}

          {error && (
            <div className="error-banner">
              <AlertCircle size={17} />
              {error}

              <button onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}

          {/* =========================================
              OVERVIEW PAGE
          ========================================= */}

          {activePage === "overview" && (

            <>

              {loading && tickets.length === 0 ? (

                <div className="loading-state">
                  <LoaderCircle className="spin" size={30} />
                  <p>Loading your ticket intelligence...</p>
                </div>

              ) : (

                <>

                  {/* STATISTICS */}

                  <section className="stats-grid">

                    <StatCard
                      label="TOTAL TICKETS"
                      value={summary?.total_tickets ?? totalTickets}
                      icon={<Ticket size={19} />}
                      color="purple"
                      note="Tickets in selected dataset"
                    />

                    <StatCard
                      label="DATASETS"
                      value={datasets.length}
                      icon={<Database size={19} />}
                      color="blue"
                      note="Uploaded datasets"
                    />

                    <StatCard
                      label="30+ DAY TICKETS"
                      value={olderTickets}
                      icon={<Clock3 size={19} />}
                      color="orange"
                      note="Across the full dataset"
                    />

                    <StatCard
                      label="HIGH PRIORITY"
                      value={highPriority}
                      icon={<ShieldCheck size={19} />}
                      color="green"
                      note="Across the full dataset"
                    />

                  </section>

                  {/* ANALYTICS */}

                  <section className="insight-grid">

                    <div className="panel category-panel">

                      <div className="panel-heading">

                        <div>
                          <h3>Problem categories</h3>
                          <p>Distribution across all dataset tickets</p>
                        </div>

                        <span className="panel-icon">
                          <BarChart3 size={18} />
                        </span>

                      </div>

                      {summaryLoading ? (

                        <div className="empty-message">
                          Loading dataset analytics...
                        </div>

                      ) : categoryData.length > 0 ? (

                        <div className="chart-content">

                          <div className="donut-chart">

                            <ResponsiveContainer width="100%" height={210}>

                              <PieChart>

                                <Pie
                                  data={categoryData}
                                  dataKey="value"
                                  nameKey="name"
                                  innerRadius={62}
                                  outerRadius={88}
                                  paddingAngle={3}
                                  stroke="none"
                                >

                                  {categoryData.map((entry, index) => (
                                    <Cell
                                      key={entry.name}
                                      fill={COLORS[index % COLORS.length]}
                                    />
                                  ))}

                                </Pie>

                                <Tooltip
                                  contentStyle={{
                                    background: "#171c2b",
                                    border: "1px solid #30384d",
                                    borderRadius: 8,
                                    color: "#fff",
                                  }}
                                />

                              </PieChart>

                            </ResponsiveContainer>

                          </div>

                          <div className="category-legend">

                            {categoryData.map((item, index) => (

                              <div
                                className="legend-item"
                                key={item.name}
                              >

                                <span
                                  className="legend-dot"
                                  style={{
                                    background: COLORS[index % COLORS.length],
                                  }}
                                />

                                <span className="legend-name">
                                  {item.name}
                                </span>

                                <strong>{item.value}</strong>

                              </div>

                            ))}

                          </div>

                        </div>

                      ) : (

                        <div className="empty-message">
                          No category data available.
                        </div>

                      )}

                    </div>

                    {/* INTELLIGENCE SNAPSHOT */}

                    <div className="panel intelligence-panel">

                      <div className="panel-heading">

                        <div>
                          <h3>Intelligence snapshot</h3>
                          <p>Current dataset activity</p>
                        </div>

                        <span className="panel-icon">
                          <FileSearch size={18} />
                        </span>

                      </div>

                      <div className="snapshot-item">

                        <div className="snapshot-icon purple-bg">
                          <Ticket size={17} />
                        </div>

                        <div>
                          <strong>
                            {(summary?.total_tickets ?? totalTickets).toLocaleString()} tickets
                          </strong>
                          <p>Available in this dataset</p>
                        </div>

                      </div>

                      <div className="snapshot-item">

                        <div className="snapshot-icon blue-bg">
                          <Database size={17} />
                        </div>

                        <div>
                          <strong>{datasets.length} datasets</strong>
                          <p>Stored in Tyzo database</p>
                        </div>

                      </div>

                      <div className="snapshot-item">

                        <div className="snapshot-icon green-bg">
                          <Activity size={17} />
                        </div>

                        <div>
                          <strong>{tickets.length} tickets loaded</strong>
                          <p>Current page of ticket results</p>
                        </div>

                      </div>

                      <div className="snapshot-note">
                        <ShieldCheck size={16} />
                        Analysis is stored in your local Tyzo database.
                      </div>

                    </div>

                  </section>

                  {/* RECENT TICKETS */}

                  <section className="panel tickets-panel">

                    <div className="panel-heading tickets-heading">

                      <div>
                        <h3>Recent tickets</h3>
                        <p>Latest records from the selected dataset.</p>
                      </div>

                      <button
                        className="clear-filters"
                        onClick={() => navigateTo("tickets")}
                      >
                        View all tickets
                        <ChevronRight size={15} />
                      </button>

                    </div>

                    <TicketTable
                      tickets={tickets.slice(0, 5)}
                      loading={loading}
                      onSelect={openTicket}
                    />

                  </section>

                </>

              )}

            </>

          )}

          {/* =========================================
              TICKET INTELLIGENCE PAGE
          ========================================= */}

          {activePage === "tickets" && (

            <>

              {/* TICKET STATISTICS */}

              <section className="stats-grid">

                <StatCard
                  label="MATCHING TICKETS"
                  value={totalTickets}
                  icon={<Ticket size={19} />}
                  color="purple"
                  note="Based on current filters"
                />

                <StatCard
                  label="HIGH CONFIDENCE"
                  value={tickets.filter(
                    (ticket) => ticket.confidence === "High"
                  ).length}
                  icon={<ShieldCheck size={19} />}
                  color="green"
                  note="On current page"
                />

                <StatCard
                  label="LOW CONFIDENCE"
                  value={tickets.filter(
                    (ticket) => ticket.confidence === "Low"
                  ).length}
                  icon={<AlertCircle size={19} />}
                  color="orange"
                  note="On current page"
                />

                <StatCard
                  label="CURRENT PAGE"
                  value={`${page}/${totalPages}`}
                  icon={<Layers3 size={19} />}
                  color="blue"
                  note="Ticket results"
                />

              </section>

              {/* FILTER PANEL */}

              <div className="panel filter-panel">

                <div className="panel-heading">

                  <div>
                    <h3>Find tickets</h3>
                    <p>
                      Search and combine filters to narrow your results.
                    </p>
                  </div>

                  <Search size={19} />

                </div>

                <div className="filter-controls">

                  <div className="filter-search">

                    <label>SEARCH</label>

                    <div className="ticket-search">

                      <Search size={16} />

                      <input
                        value={search}
                        placeholder="Ticket ID or description..."
                        onChange={(e) => {
                          setSearch(e.target.value);
                          setPage(1);
                        }}
                      />

                      {search && (
                        <button
                          onClick={() => {
                            setSearch("");
                            setPage(1);
                          }}
                          aria-label="Clear search"
                        >
                          <X size={15} />
                        </button>
                      )}

                    </div>

                  </div>

                  <FilterSelect
                    label="CATEGORY"
                    value={filters.category}
                    options={categories}
                    onChange={(value) =>
                      updateFilter("category", value)
                    }
                  />

                  <FilterSelect
                    label="PRIORITY"
                    value={filters.priority}
                    options={priorities}
                    onChange={(value) =>
                      updateFilter("priority", value)
                    }
                  />

                  <FilterSelect
                    label="STATUS"
                    value={filters.status}
                    options={statuses}
                    onChange={(value) =>
                      updateFilter("status", value)
                    }
                  />

                  <FilterSelect
                    label="CONFIDENCE"
                    value={filters.confidence}
                    options={["High", "Medium", "Low"]}
                    onChange={(value) =>
                      updateFilter("confidence", value)
                    }
                  />

                </div>

                <div className="filter-footer">

                  <button
                    className="clear-filters"
                    onClick={clearFilters}
                  >
                    <X size={14} />
                    Clear all filters
                  </button>

                  <span>
                    {totalTickets.toLocaleString()} matching tickets
                  </span>

                </div>

              </div>

              {/* TICKET RECORDS */}

              <section className="panel tickets-panel">

                <div className="panel-heading tickets-heading">

                  <div>
                    <h3>Ticket records</h3>
                    <p>
                      Select a ticket to inspect its complete analysis.
                    </p>
                  </div>

                  <button
                    className="icon-button"
                    onClick={() => {
                      setPage(1);
                      setSearch("");
                      setFilters(EMPTY_FILTERS);
                    }}
                    title="Reset filters"
                  >
                    <RefreshCw size={17} />
                  </button>

                </div>

                <TicketTable
                  tickets={tickets}
                  loading={loading}
                  onSelect={openTicket}
                />

                <Pagination
                  page={page}
                  totalPages={totalPages}
                  totalTickets={totalTickets}
                  limit={LIMIT}
                  loading={loading}
                  onPageChange={setPage}
                />

              </section>

            </>

          )}

          {/* =========================================
              COLLECTIVE INTELLIGENCE PLACEHOLDER
          ========================================= */}

          {activePage === "collective" && (

            <div className="panel">

              <div className="panel-heading">
                <div>
                  <h3>Collective Intelligence</h3>
                  <p>
                    Cross-ticket analysis and recurring issue discovery.
                  </p>
                </div>
                <Layers3 size={20} />
              </div>

              <div className="empty-message">
                Collective Intelligence page is the next development phase.
              </div>

            </div>

          )}

        </div>

        {/* FOOTER */}

        <footer className="footer">
          <span>TYZO INTELLIGENCE PLATFORM</span>
          <span>Local environment · Version 1.0</span>
        </footer>

      </main>

      {/* =========================================
          INDIVIDUAL TICKET DETAIL PANEL
      ========================================= */}

      {selectedTicket && (

        <div
          className="modal-backdrop"
          onClick={() => {
            if (!detailLoading) setSelectedTicket(null);
          }}
        >

          <div
            className="ticket-modal"
            onClick={(e) => e.stopPropagation()}
          >

            <div className="modal-header">

              <div>
                <span className="eyebrow">TICKET DETAILS</span>
                <h2>{selectedTicket.ticket_id}</h2>
              </div>

              <button
                className="icon-button"
                onClick={() => setSelectedTicket(null)}
                disabled={detailLoading}
              >
                <X size={20} />
              </button>

            </div>

            {detailLoading ? (

              <div className="loading-state">
                <LoaderCircle className="spin" size={28} />
                Loading analysis...
              </div>

            ) : (

              <TicketDetails ticket={selectedTicket} />

            )}

          </div>

        </div>

      )}

    </div>
  );
}


// ==================================================
// STATISTICS CARD
// ==================================================

function StatCard({ label, value, icon, color, note }) {
  return (
    <div className="stat-card">

      <div className="stat-top">
        <span>{label}</span>

        <span className={`stat-icon ${color}`}>
          {icon}
        </span>
      </div>

      <strong className="stat-value">
        {Number(value).toLocaleString()}
      </strong>

      <p>{note}</p>

    </div>
  );
}


// ==================================================
// FILTER SELECT
// ==================================================

function FilterSelect({ label, value, options, onChange }) {
  return (
    <div className="filter-field">

      <label>{label}</label>

      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >

        <option value="">All</option>

        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}

      </select>

    </div>
  );
}


// ==================================================
// TICKET TABLE
// ==================================================

function TicketTable({ tickets, loading, onSelect }) {
  return (
    <div className="table-wrap">

      <table>

        <thead>
          <tr>
            <th>TICKET ID</th>
            <th>SUMMARY</th>
            <th>CATEGORY</th>
            <th>PRIORITY</th>
            <th>AGE</th>
            <th>CONFIDENCE</th>
            <th></th>
          </tr>
        </thead>

        <tbody>

          {tickets.map((ticket) => (

            <tr
              key={ticket.id}
              onClick={() => onSelect(ticket)}
            >

              <td className="ticket-id">
                {ticket.ticket_id}
              </td>

              <td className="summary-cell">
                {ticket.ticket_summary || "No summary available"}
              </td>

              <td>
                <span className="category-tag">
                  {ticket.problem_category || "Unclassified"}
                </span>
              </td>

              <td>{ticket.priority || "Unknown"}</td>

              <td>
                {ticket.age_days ?? "—"} days
              </td>

              <td>
                <span
                  className={`confidence ${String(
                    ticket.confidence || ""
                  ).toLowerCase()}`}
                >
                  {ticket.confidence || "Unknown"}
                </span>
              </td>

              <td>
                <ChevronRight size={17} className="row-arrow" />
              </td>

            </tr>

          ))}

        </tbody>

      </table>

      {loading && (
        <div className="table-loading">
          <LoaderCircle className="spin" size={19} />
          Loading tickets...
        </div>
      )}

      {!loading && tickets.length === 0 && (
        <div className="empty-message">
          No matching tickets found.
        </div>
      )}

    </div>
  );
}


// ==================================================
// PAGINATION
// ==================================================

function Pagination({
  page,
  totalPages,
  totalTickets,
  limit,
  loading,
  onPageChange,
}) {
  const start = totalTickets === 0 ? 0 : (page - 1) * limit + 1;
  const end = Math.min(page * limit, totalTickets);

  return (
    <div className="pagination">

      <span>
        Showing {start}–{end} of {totalTickets}
      </span>

      <div className="pagination-actions">

        <button
          disabled={page <= 1 || loading}
          onClick={() => onPageChange(page - 1)}
        >
          <ChevronLeft size={17} />
          Previous
        </button>

        <span>
          Page {page} of {totalPages}
        </span>

        <button
          disabled={page >= totalPages || loading}
          onClick={() => onPageChange(page + 1)}
        >
          Next
          <ChevronRight size={17} />
        </button>

      </div>

    </div>
  );
}


// ==================================================
// INDIVIDUAL TICKET DETAILS
// ==================================================

function TicketDetails({ ticket }) {
  return (
    <div className="modal-body">

      <h4>Ticket summary</h4>

      <p>
        {ticket.ticket_summary || "No summary available."}
      </p>

      <div className="detail-grid">

        <Detail
          label="Category"
          value={ticket.problem_category}
        />

        <Detail
          label="Status"
          value={ticket.status}
        />

        <Detail
          label="Priority"
          value={ticket.priority}
        />

        <Detail
          label="Age"
          value={
            ticket.age_days != null
              ? `${ticket.age_days} days`
              : null
          }
        />

        <Detail
          label="Confidence"
          value={ticket.confidence}
        />

      </div>

      <div className="detail-section">
        <h4>Documented issue</h4>
        <p>
          {ticket.documented_issue ||
            "Not documented in source data."}
        </p>
      </div>

      <div className="detail-section">
        <h4>Action already taken</h4>
        <p>
          {ticket.documented_action_taken ||
            "No documented action available."}
        </p>
      </div>

      <div className="detail-section">
        <h4>Recommended action</h4>
        <p>
          {ticket.recommended_action || "Not available."}
        </p>
      </div>

      <div className="detail-section">
        <h4>Possible solution</h4>
        <p>
          {ticket.possible_solution || "Not available."}
        </p>
      </div>

      <div className="detail-section">
        <h4>Actual resolution</h4>
        <p>
          {ticket.actual_resolution ||
            "No confirmed resolution documented."}
        </p>
      </div>

      <div className="detail-section">
        <h4>Evidence</h4>
        <p>
          {Array.isArray(ticket.evidence)
            ? ticket.evidence.join(", ")
            : ticket.evidence || "No evidence available."}
        </p>
      </div>

    </div>
  );
}


// ==================================================
// DETAIL FIELD
// ==================================================

function Detail({ label, value }) {
  return (
    <div className="detail-box">

      <span>{label}</span>

      <strong>{value || "Not available"}</strong>

    </div>
  );
}

export default App;
