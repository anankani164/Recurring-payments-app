'use client'

import { FormEvent, Fragment, useEffect, useMemo, useState } from 'react'

type Client = { id: number; name: string; email: string }
type Project = { id: number; name: string; client_id: number; amount_usd: number; recurrence: string; rate_type: string; next_invoice_date: string }
type FxRate = { id: number; rate_date: string; code: string; cash_buying: number; cash_selling: number; tts_buying: number; tts_selling: number; source_url: string }
type Invoice = { id: number; project_id: number; invoice_date: string; amount_usd: number; fx_rate: number; amount_ghs: number; rate_type: string; source_rate_date: string }
type JobLog = { id: number; job_name: string; status: string; message: string; created_at: string }
type User = { id: number; username: string; email: string; role: string; is_active: boolean }
type Tab = 'overview' | 'clients' | 'projects' | 'rates' | 'invoices' | 'jobs' | 'users'

const PAGE_SIZE = 8
const RATE_TYPES = ['cash_buying', 'cash_selling', 'tts_buying', 'tts_selling']
const USER_ROLES = ['admin', 'user']

const NAV: { id: Tab; label: string; icon: string; mobileLabel: string }[] = [
  { id: 'overview',  label: 'Overview',  icon: '◈', mobileLabel: 'Home'     },
  { id: 'clients',   label: 'Clients',   icon: '⊙', mobileLabel: 'Clients'  },
  { id: 'projects',  label: 'Projects',  icon: '▦', mobileLabel: 'Projects' },
  { id: 'rates',     label: 'FX Rates',  icon: '⇄', mobileLabel: 'Rates'    },
  { id: 'invoices',  label: 'Invoices',  icon: '◻', mobileLabel: 'Invoices' },
  { id: 'jobs',      label: 'Job Logs',  icon: '◉', mobileLabel: 'Jobs'     },
  { id: 'users',     label: 'Users',     icon: '◐', mobileLabel: 'Users'    },
]

function Pagination({ page, pages, onPrev, onNext }: { page: number; pages: number; onPrev: () => void; onNext: () => void }) {
  return (
    <div className="pagination">
      <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={onPrev}>← Prev</button>
      <span>Page {page} of {pages}</span>
      <button className="btn btn-ghost btn-sm" disabled={page >= pages} onClick={onNext}>Next →</button>
    </div>
  )
}

function Empty({ label }: { label: string }) {
  return (
    <div className="empty">
      <div className="empty-icon">○</div>
      No {label} yet
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const cls = status === 'success' ? 'badge-green' : status === 'failed' ? 'badge-red' : status === 'started' ? 'badge-yellow' : 'badge-grey'
  return <span className={`badge ${cls}`}>{status}</span>
}

function RoleBadge({ role }: { role: string }) {
  const cls = role === 'superadmin' ? 'badge-red' : role === 'admin' ? 'badge-yellow' : 'badge-grey'
  return <span className={`badge ${cls}`}>{role}</span>
}

export default function Dashboard() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || ''

  const [health, setHealth]   = useState('checking…')
  const [token, setToken]     = useState('')
  const [tab, setTab]         = useState<Tab>('overview')
  const [msg, setMsg]         = useState('')
  const [msgOk, setMsgOk]     = useState(true)

  const [username, setUsername] = useState('superadmin')
  const [password, setPassword] = useState('')

  const [clients,  setClients]  = useState<Client[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [rates,    setRates]    = useState<FxRate[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [jobs,     setJobs]     = useState<JobLog[]>([])
  const [users,    setUsers]    = useState<User[]>([])

  const [clientName,  setClientName]  = useState('')
  const [clientEmail, setClientEmail] = useState('')

  const [projectName,     setProjectName]     = useState('')
  const [projectClientId, setProjectClientId] = useState('')
  const [amountUsd,       setAmountUsd]       = useState('')
  const [nextDate,        setNextDate]        = useState('')
  const [rateType,        setRateType]        = useState('tts_selling')

  const [pdfUrl,    setPdfUrl]    = useState('')
  const [pdfFile,   setPdfFile]   = useState<File | null>(null)
  const [pdfCode,   setPdfCode]   = useState('USD')

  // manual FX rate entry
  const [manualRateDate,    setManualRateDate]    = useState('')
  const [manualRateCode,    setManualRateCode]    = useState('USD')
  const [manualCashBuying,  setManualCashBuying]  = useState('')
  const [manualCashSelling, setManualCashSelling] = useState('')
  const [manualTtsBuying,   setManualTtsBuying]   = useState('')
  const [manualTtsSelling,  setManualTtsSelling]  = useState('')

  // manual invoice generation
  const [invoiceProjectId, setInvoiceProjectId] = useState('')
  const [invoiceDate,      setInvoiceDate]      = useState('')

  const [newUsername, setNewUsername] = useState('')
  const [newUserEmail, setNewUserEmail] = useState('')
  const [newUserPassword, setNewUserPassword] = useState('')
  const [newUserRole, setNewUserRole] = useState('user')
  const [editingUser, setEditingUser] = useState<number | null>(null)

  const [clientPage,  setClientPage]  = useState(1)
  const [projectPage, setProjectPage] = useState(1)
  const [userPage,    setUserPage]    = useState(1)
  const [invoicePage, setInvoicePage] = useState(1)
  const [ratePage,    setRatePage]    = useState(1)
  const [jobPage,     setJobPage]     = useState(1)

  const headers = useMemo(
    () => ({ 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }),
    [token],
  )

  const ok  = (m: string) => { setMsgOk(true);  setMsg(m) }
  const err = (m: string) => { setMsgOk(false); setMsg(m) }

  const loadData = async () => {
    if (!token) return
    try {
      const [cR, pR, rR, iR, jR, uR] = await Promise.all([
        fetch(`${apiBase}/clients`,  { headers }),
        fetch(`${apiBase}/projects`, { headers }),
        fetch(`${apiBase}/rates`,    { headers }),
        fetch(`${apiBase}/invoices`, { headers }),
        fetch(`${apiBase}/jobs`,     { headers }),
        fetch(`${apiBase}/users`,    { headers }),
      ])
      if (cR.ok) setClients(await cR.json())
      if (pR.ok) setProjects(await pR.json())
      if (rR.ok) setRates(await rR.json())
      if (iR.ok) setInvoices(await iR.json())
      if (jR.ok) setJobs(await jR.json())
      if (uR.ok) setUsers(await uR.json())
    } catch { err('Failed to load data from API') }
  }

  useEffect(() => {
    fetch(`${apiBase}/health`).then(r => r.json()).then(d => setHealth(d.status)).catch(() => setHealth('unreachable'))
  }, [apiBase])

  useEffect(() => { loadData() }, [token])

  const login = async (e: FormEvent) => {
    e.preventDefault(); setMsg('')
    const res = await fetch(`${apiBase}/auth/login`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!res.ok) return err('Login failed — check username / password')
    const data = await res.json()
    setToken(data.access_token); setPassword('')
    ok('Signed in successfully')
  }

  const createUser = async (e: FormEvent) => {
    e.preventDefault(); setMsg('')
    if (newUserPassword.length < 8) return err('Password must be at least 8 characters')
    const res = await fetch(`${apiBase}/users`, {
      method: 'POST', headers,
      body: JSON.stringify({ username: newUsername, email: newUserEmail, password: newUserPassword, role: newUserRole }),
    })
    if (!res.ok) return err('Could not create user')
    setNewUsername(''); setNewUserEmail(''); setNewUserPassword(''); setNewUserRole('user')
    ok('User created'); await loadData()
  }

  const updateUser = async (userId: number, payload: object) => {
    const res = await fetch(`${apiBase}/users/${userId}`, { method: 'PATCH', headers, body: JSON.stringify(payload) })
    if (!res.ok) return err('Failed to update user')
    ok('User updated'); await loadData()
  }

  const addClient = async (e: FormEvent) => {
    e.preventDefault(); setMsg('')
    if (!clientName.trim()) return err('Client name is required')
    const res = await fetch(`${apiBase}/clients`, { method: 'POST', headers, body: JSON.stringify({ name: clientName, email: clientEmail }) })
    if (!res.ok) return err('Could not create client')
    setClientName(''); setClientEmail('')
    ok('Client created'); await loadData()
  }

  const deleteClient = async (id: number) => {
    const res = await fetch(`${apiBase}/clients/${id}`, { method: 'DELETE', headers })
    if (!res.ok) return err('Could not delete client')
    ok('Client deleted'); await loadData()
  }

  const addProject = async (e: FormEvent) => {
    e.preventDefault(); setMsg('')
    if (!projectClientId) return err('Please select a client')
    if (!amountUsd || Number(amountUsd) <= 0) return err('Amount must be greater than 0')
    if (!nextDate) return err('Next invoice date is required')
    const res = await fetch(`${apiBase}/projects`, {
      method: 'POST', headers,
      body: JSON.stringify({ name: projectName, client_id: Number(projectClientId), amount_usd: Number(amountUsd), recurrence: 'monthly', rate_type: rateType, next_invoice_date: nextDate }),
    })
    if (!res.ok) return err('Could not create project')
    setProjectName(''); setProjectClientId(''); setAmountUsd(''); setNextDate(''); setRateType('tts_selling')
    ok('Project created'); await loadData()
  }

  const deleteProject = async (id: number) => {
    const res = await fetch(`${apiBase}/projects/${id}`, { method: 'DELETE', headers })
    if (!res.ok) return err('Could not delete project')
    ok('Project deleted'); await loadData()
  }

  const addManualRate = async (e: FormEvent) => {
    e.preventDefault(); setMsg('')
    if (!manualRateDate) return err('Rate date is required')
    const body = {
      rate_date: manualRateDate,
      code: manualRateCode,
      cash_buying:  Number(manualCashBuying),
      cash_selling: Number(manualCashSelling),
      tts_buying:   Number(manualTtsBuying),
      tts_selling:  Number(manualTtsSelling),
    }
    const res = await fetch(`${apiBase}/rates`, { method: 'POST', headers, body: JSON.stringify(body) })
    if (!res.ok) {
      const detail = await res.json().catch(() => null)
      return err(detail?.detail ?? 'Could not save rate')
    }
    setManualRateDate(''); setManualCashBuying(''); setManualCashSelling(''); setManualTtsBuying(''); setManualTtsSelling('')
    ok('Rate saved'); await loadData()
  }

  const generateInvoice = async (e: FormEvent) => {
    e.preventDefault(); setMsg('')
    if (!invoiceProjectId) return err('Please select a project')
    if (!invoiceDate) return err('Invoice date is required')
    const res = await fetch(`${apiBase}/projects/${invoiceProjectId}/invoice?invoice_date=${invoiceDate}`, { method: 'POST', headers })
    if (!res.ok) {
      const detail = await res.json().catch(() => null)
      return err(detail?.detail ?? 'Could not generate invoice')
    }
    setInvoiceProjectId(''); setInvoiceDate('')
    ok('Invoice generated'); await loadData()
  }

  const uploadPdf = async (e: FormEvent) => {
    e.preventDefault(); setMsg('')
    if (!pdfFile) return err('Please select a PDF file')
    const formData = new FormData()
    formData.append('file', pdfFile)
    formData.append('target_code', pdfCode)
    const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}
    const res = await fetch(`${apiBase}/rates/upload-pdf`, { method: 'POST', headers: authHeaders, body: formData })
    if (!res.ok) {
      const detail = await res.json().catch(() => null)
      const msg = detail?.detail ?? 'Could not process uploaded PDF'
      return err(`${msg}. If the PDF format is not recognised, use "Add Rate Manually" instead.`)
    }
    setPdfFile(null); ok('Rate extracted from PDF'); await loadData()
  }

  const ingestPdf = async (e: FormEvent) => {
    e.preventDefault(); setMsg('')
    if (!pdfUrl.startsWith('http://') && !pdfUrl.startsWith('https://')) return err('URL must start with http:// or https://')
    const res = await fetch(`${apiBase}/rates/ingest-pdf`, { method: 'POST', headers, body: JSON.stringify({ source_url: pdfUrl, target_code: pdfCode }) })
    if (!res.ok) return err('Could not ingest PDF rate')
    setPdfUrl(''); ok('Rate ingested from URL'); await loadData()
  }

  const runJobsNow = async () => {
    setMsg('')
    const res = await fetch(`${apiBase}/run-jobs-now`, { method: 'POST', headers })
    if (!res.ok) return err('Failed to run jobs')
    ok('Jobs completed'); await loadData()
  }

  // Paged slices
  const pagedClients  = clients.slice( (clientPage  - 1) * PAGE_SIZE, clientPage  * PAGE_SIZE)
  const pagedProjects = projects.slice((projectPage - 1) * PAGE_SIZE, projectPage * PAGE_SIZE)
  const pagedUsers    = users.slice(   (userPage    - 1) * PAGE_SIZE, userPage    * PAGE_SIZE)
  const pagedInvoices = invoices.slice((invoicePage - 1) * PAGE_SIZE, invoicePage * PAGE_SIZE)
  const pagedRates    = rates.slice(   (ratePage    - 1) * PAGE_SIZE, ratePage    * PAGE_SIZE)
  const pagedJobs     = jobs.slice(    (jobPage     - 1) * PAGE_SIZE, jobPage     * PAGE_SIZE)

  const clientPages  = Math.max(1, Math.ceil(clients.length  / PAGE_SIZE))
  const projectPages = Math.max(1, Math.ceil(projects.length / PAGE_SIZE))
  const userPages    = Math.max(1, Math.ceil(users.length    / PAGE_SIZE))
  const invoicePages = Math.max(1, Math.ceil(invoices.length / PAGE_SIZE))
  const ratePages    = Math.max(1, Math.ceil(rates.length    / PAGE_SIZE))
  const jobPages     = Math.max(1, Math.ceil(jobs.length     / PAGE_SIZE))

  // ── Login Screen ─────────────────────────────────────────────────────────
  if (!token) {
    return (
      <div className="login-screen">
        <div className="login-card">
          <div className="login-brand">
            <div className="login-brand-icon">R</div>
            <div>
              <div className="login-brand-name">Recurring Payments</div>
              <div className="login-brand-sub">Admin Dashboard</div>
            </div>
          </div>
          {msg && <div className={`alert ${msgOk ? 'alert-ok' : 'alert-err'}`}>{msg}</div>}
          <h1 className="login-heading">Welcome back</h1>
          <p className="login-sub">Sign in to your account to continue</p>
          <form onSubmit={login} className="form-grid">
            <div className="form-group">
              <label className="form-label">Username</label>
              <input className="input" value={username} onChange={e => setUsername(e.target.value)} required autoComplete="username" />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} required autoComplete="current-password" />
            </div>
            <button className="btn btn-primary" type="submit" style={{ marginTop: 4 }}>Sign In</button>
          </form>
          <div className="login-footer">
            API status: <span className={health === 'ok' ? 'ok' : 'bad'}>{health}</span>
          </div>
        </div>
      </div>
    )
  }

  // ── Main App ──────────────────────────────────────────────────────────────
  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-logo">
          <div className="logo-badge">R</div>
          <span className="logo-text">Recurring Payments</span>
        </div>
        <div className="header-right">
          <div className="api-status">
            <span className={`status-dot ${health !== 'ok' ? 'bad' : ''}`} />
            API {health}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => { setToken(''); setMsg('') }}>Sign out</button>
        </div>
      </header>

      <div className="main-layout">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-group-label">Navigation</div>
          {NAV.map(item => (
            <button key={item.id} className={`nav-btn ${tab === item.id ? 'active' : ''}`} onClick={() => { setTab(item.id); setMsg('') }}>
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </aside>

        {/* Content */}
        <main className="content">
          {msg && <div className={`alert ${msgOk ? 'alert-ok' : 'alert-err'}`}>{msg}</div>}

          {/* ── Overview ─────────────────────────────────────── */}
          {tab === 'overview' && (
            <>
              <div className="page-header">
                <h1 className="page-title">Overview</h1>
                <p className="page-subtitle">Your recurring payments at a glance</p>
              </div>
              <div className="stats-grid">
                <div className="stat-card"><div className="stat-label">Clients</div><div className="stat-value accent">{clients.length}</div></div>
                <div className="stat-card"><div className="stat-label">Projects</div><div className="stat-value accent">{projects.length}</div></div>
                <div className="stat-card"><div className="stat-label">FX Rates</div><div className="stat-value">{rates.length}</div></div>
                <div className="stat-card"><div className="stat-label">Invoices</div><div className="stat-value">{invoices.length}</div></div>
                <div className="stat-card"><div className="stat-label">Job Runs</div><div className="stat-value">{jobs.length}</div></div>
              </div>
              <div className="card">
                <div className="card-header"><span className="card-title">Quick Actions</span></div>
                <button className="btn btn-primary" onClick={runJobsNow}>▶ Run Jobs Now</button>
              </div>
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Recent Invoices</span>
                  <span className="card-count">{invoices.length} total</span>
                </div>
                {invoices.length === 0 ? <Empty label="invoices" /> : (
                  <div className="table-wrap">
                    <table>
                      <thead><tr><th>Date</th><th>Project</th><th>USD</th><th>FX Rate</th><th>GHS</th><th>Type</th></tr></thead>
                      <tbody>
                        {invoices.slice(0, 10).map(inv => (
                          <tr key={inv.id}>
                            <td className="td-mono">{inv.invoice_date}</td>
                            <td>{projects.find(p => p.id === inv.project_id)?.name ?? `#${inv.project_id}`}</td>
                            <td className="td-mono">${inv.amount_usd.toFixed(2)}</td>
                            <td className="td-mono">{inv.fx_rate}</td>
                            <td className="td-mono">GHS {inv.amount_ghs.toFixed(2)}</td>
                            <td><span className="badge badge-grey">{inv.rate_type}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}

          {/* ── Clients ──────────────────────────────────────── */}
          {tab === 'clients' && (
            <>
              <div className="page-header">
                <h1 className="page-title">Clients</h1>
                <p className="page-subtitle">Manage your billing clients</p>
              </div>
              <div className="card">
                <div className="card-header"><span className="card-title">Add Client</span></div>
                <form onSubmit={addClient} className="form-grid">
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Name</label>
                      <input className="input" placeholder="Acme Corp" value={clientName} onChange={e => setClientName(e.target.value)} required />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Email</label>
                      <input className="input" type="email" placeholder="billing@acme.com" value={clientEmail} onChange={e => setClientEmail(e.target.value)} required />
                    </div>
                  </div>
                  <div className="form-actions">
                    <button className="btn btn-primary" type="submit">Add Client</button>
                  </div>
                </form>
              </div>
              <div className="card">
                <div className="card-header">
                  <span className="card-title">All Clients</span>
                  <span className="card-count">{clients.length}</span>
                </div>
                {clients.length === 0 ? <Empty label="clients" /> : (
                  <>
                    <div className="table-wrap">
                      <table>
                        <thead><tr><th>#</th><th>Name</th><th>Email</th><th></th></tr></thead>
                        <tbody>
                          {pagedClients.map(c => (
                            <tr key={c.id}>
                              <td className="td-id">{c.id}</td>
                              <td><strong>{c.name}</strong></td>
                              <td style={{ color: 'var(--text-muted)' }}>{c.email}</td>
                              <td style={{ textAlign: 'right' }}>
                                <button className="btn btn-danger-soft btn-sm" onClick={() => deleteClient(c.id)}>Delete</button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <Pagination page={clientPage} pages={clientPages} onPrev={() => setClientPage(p => p - 1)} onNext={() => setClientPage(p => p + 1)} />
                  </>
                )}
              </div>
            </>
          )}

          {/* ── Projects ─────────────────────────────────────── */}
          {tab === 'projects' && (
            <>
              <div className="page-header">
                <h1 className="page-title">Projects</h1>
                <p className="page-subtitle">Recurring billing projects</p>
              </div>
              <div className="card">
                <div className="card-header"><span className="card-title">Add Project</span></div>
                <form onSubmit={addProject} className="form-grid">
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Project Name</label>
                      <input className="input" placeholder="Monthly retainer" value={projectName} onChange={e => setProjectName(e.target.value)} required />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Client</label>
                      <select className="select" value={projectClientId} onChange={e => setProjectClientId(e.target.value)} required>
                        <option value="">Select client…</option>
                        {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                      </select>
                    </div>
                  </div>
                  <div className="form-row-3">
                    <div className="form-group">
                      <label className="form-label">Amount (USD)</label>
                      <input className="input" type="number" step="0.01" min="0.01" placeholder="500.00" value={amountUsd} onChange={e => setAmountUsd(e.target.value)} required />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Next Invoice Date</label>
                      <input className="input" type="date" value={nextDate} onChange={e => setNextDate(e.target.value)} required />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Rate Type</label>
                      <select className="select" value={rateType} onChange={e => setRateType(e.target.value)}>
                        {RATE_TYPES.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </div>
                  </div>
                  <div className="form-actions">
                    <button className="btn btn-primary" type="submit">Add Project</button>
                  </div>
                </form>
              </div>
              <div className="card">
                <div className="card-header">
                  <span className="card-title">All Projects</span>
                  <span className="card-count">{projects.length}</span>
                </div>
                {projects.length === 0 ? <Empty label="projects" /> : (
                  <>
                    <div className="table-wrap">
                      <table>
                        <thead><tr><th>#</th><th>Name</th><th>Client</th><th>USD / mo</th><th>Rate Type</th><th>Next Invoice</th><th></th></tr></thead>
                        <tbody>
                          {pagedProjects.map(p => (
                            <tr key={p.id}>
                              <td className="td-id">{p.id}</td>
                              <td><strong>{p.name}</strong></td>
                              <td style={{ color: 'var(--text-muted)' }}>{clients.find(c => c.id === p.client_id)?.name ?? `#${p.client_id}`}</td>
                              <td className="td-mono">${p.amount_usd.toFixed(2)}</td>
                              <td><span className="badge badge-grey">{p.rate_type}</span></td>
                              <td className="td-mono" style={{ color: new Date(p.next_invoice_date) <= new Date() ? 'var(--danger)' : 'var(--text)' }}>{p.next_invoice_date}</td>
                              <td style={{ textAlign: 'right' }}>
                                <button className="btn btn-danger-soft btn-sm" onClick={() => deleteProject(p.id)}>Delete</button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <Pagination page={projectPage} pages={projectPages} onPrev={() => setProjectPage(p => p - 1)} onNext={() => setProjectPage(p => p + 1)} />
                  </>
                )}
              </div>
            </>
          )}

          {/* ── FX Rates ──────────────────────────────────────── */}
          {tab === 'rates' && (
            <>
              <div className="page-header">
                <h1 className="page-title">FX Rates</h1>
                <p className="page-subtitle">Exchange rates for invoice conversion</p>
              </div>
              <div className="card">
                <div className="card-header"><span className="card-title">Add Rate Manually</span></div>
                <form onSubmit={addManualRate} className="form-grid">
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Rate Date</label>
                      <input className="input" type="date" value={manualRateDate} onChange={e => setManualRateDate(e.target.value)} required />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Currency Code</label>
                      <input className="input" placeholder="USD" value={manualRateCode} onChange={e => setManualRateCode(e.target.value.toUpperCase())} maxLength={5} required />
                    </div>
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Cash Buying</label>
                      <input className="input" type="number" step="0.0001" placeholder="0.0000" value={manualCashBuying} onChange={e => setManualCashBuying(e.target.value)} required />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Cash Selling</label>
                      <input className="input" type="number" step="0.0001" placeholder="0.0000" value={manualCashSelling} onChange={e => setManualCashSelling(e.target.value)} required />
                    </div>
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">TTS Buying</label>
                      <input className="input" type="number" step="0.0001" placeholder="0.0000" value={manualTtsBuying} onChange={e => setManualTtsBuying(e.target.value)} required />
                    </div>
                    <div className="form-group">
                      <label className="form-label">TTS Selling</label>
                      <input className="input" type="number" step="0.0001" placeholder="0.0000" value={manualTtsSelling} onChange={e => setManualTtsSelling(e.target.value)} required />
                    </div>
                  </div>
                  <div className="form-actions">
                    <button className="btn btn-primary" type="submit">Save Rate</button>
                  </div>
                </form>
              </div>
              <div className="card">
                <div className="card-header"><span className="card-title">Upload PDF from Device</span></div>
                <form onSubmit={uploadPdf} className="form-grid">
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">PDF File</label>
                      <input
                        className="input"
                        type="file"
                        accept=".pdf,application/pdf"
                        onChange={e => setPdfFile(e.target.files?.[0] ?? null)}
                        required
                        style={{ cursor: 'pointer' }}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Currency Code</label>
                      <input className="input" placeholder="USD" value={pdfCode} onChange={e => setPdfCode(e.target.value.toUpperCase())} maxLength={5} required />
                    </div>
                  </div>
                  {pdfFile && (
                    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      Selected: <strong style={{ color: 'var(--text)' }}>{pdfFile.name}</strong> ({(pdfFile.size / 1024).toFixed(1)} KB)
                    </p>
                  )}
                  <div className="form-actions">
                    <button className="btn btn-primary" type="submit">Upload &amp; Parse</button>
                  </div>
                </form>
              </div>
              <div className="card">
                <div className="card-header"><span className="card-title">Ingest from URL</span></div>
                <form onSubmit={ingestPdf} className="form-grid">
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">PDF URL</label>
                      <input className="input" placeholder="https://bank.example/forex.pdf" value={pdfUrl} onChange={e => setPdfUrl(e.target.value)} required />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Currency Code</label>
                      <input className="input" placeholder="USD" value={pdfCode} onChange={e => setPdfCode(e.target.value.toUpperCase())} maxLength={5} required />
                    </div>
                  </div>
                  <div className="form-actions">
                    <button className="btn btn-secondary" type="submit">Ingest from URL</button>
                  </div>
                </form>
              </div>
              <div className="card">
                <div className="card-header">
                  <span className="card-title">All Rates</span>
                  <span className="card-count">{rates.length}</span>
                </div>
                {rates.length === 0 ? <Empty label="rates" /> : (
                  <>
                    <div className="table-wrap">
                      <table>
                        <thead><tr><th>Date</th><th>Code</th><th>Cash Buy</th><th>Cash Sell</th><th>TTS Buy</th><th>TTS Sell</th></tr></thead>
                        <tbody>
                          {pagedRates.map(r => (
                            <tr key={r.id}>
                              <td className="td-mono">{r.rate_date}</td>
                              <td><span className="badge badge-blue">{r.code}</span></td>
                              <td className="td-mono">{r.cash_buying}</td>
                              <td className="td-mono">{r.cash_selling}</td>
                              <td className="td-mono">{r.tts_buying}</td>
                              <td className="td-mono">{r.tts_selling}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <Pagination page={ratePage} pages={ratePages} onPrev={() => setRatePage(p => p - 1)} onNext={() => setRatePage(p => p + 1)} />
                  </>
                )}
              </div>
            </>
          )}

          {/* ── Invoices ──────────────────────────────────────── */}
          {tab === 'invoices' && (
            <>
              <div className="page-header">
                <h1 className="page-title">Invoices</h1>
                <p className="page-subtitle">Generate and view invoices</p>
              </div>
              <div className="card">
                <div className="card-header"><span className="card-title">Generate Invoice</span></div>
                <form onSubmit={generateInvoice} className="form-grid">
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Project</label>
                      <select className="select" value={invoiceProjectId} onChange={e => setInvoiceProjectId(e.target.value)} required>
                        <option value="">Select project…</option>
                        {projects.map(p => (
                          <option key={p.id} value={p.id}>
                            {p.name} ({clients.find(c => c.id === p.client_id)?.name ?? `client #${p.client_id}`})
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="form-group">
                      <label className="form-label">Invoice Date</label>
                      <input className="input" type="date" value={invoiceDate} onChange={e => setInvoiceDate(e.target.value)} required />
                    </div>
                  </div>
                  <div className="form-actions">
                    <button className="btn btn-primary" type="submit">Generate Invoice</button>
                  </div>
                </form>
              </div>
              <div className="card">
                <div className="card-header">
                  <span className="card-title">All Invoices</span>
                  <span className="card-count">{invoices.length}</span>
                </div>
                {invoices.length === 0 ? <Empty label="invoices" /> : (
                  <>
                    <div className="table-wrap">
                      <table>
                        <thead><tr><th>#</th><th>Date</th><th>Project</th><th>USD</th><th>FX Rate</th><th>GHS</th><th>Type</th></tr></thead>
                        <tbody>
                          {pagedInvoices.map(inv => (
                            <tr key={inv.id}>
                              <td className="td-id">{inv.id}</td>
                              <td className="td-mono">{inv.invoice_date}</td>
                              <td>{projects.find(p => p.id === inv.project_id)?.name ?? `#${inv.project_id}`}</td>
                              <td className="td-mono">${inv.amount_usd.toFixed(2)}</td>
                              <td className="td-mono">{inv.fx_rate}</td>
                              <td className="td-mono">GHS {inv.amount_ghs.toFixed(2)}</td>
                              <td><span className="badge badge-grey">{inv.rate_type}</span></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <Pagination page={invoicePage} pages={invoicePages} onPrev={() => setInvoicePage(p => p - 1)} onNext={() => setInvoicePage(p => p + 1)} />
                  </>
                )}
              </div>
            </>
          )}

          {/* ── Job Logs ──────────────────────────────────────── */}
          {tab === 'jobs' && (
            <>
              <div className="page-header">
                <h1 className="page-title">Job Logs</h1>
                <p className="page-subtitle">Scheduler and worker activity</p>
              </div>
              <div className="card" style={{ marginBottom: 18 }}>
                <button className="btn btn-primary" onClick={runJobsNow}>▶ Run Jobs Now</button>
              </div>
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Recent Logs</span>
                  <span className="card-count">{jobs.length}</span>
                </div>
                {jobs.length === 0 ? <Empty label="job logs" /> : (
                  <>
                    <div className="table-wrap">
                      <table>
                        <thead><tr><th>Time</th><th>Job</th><th>Status</th><th>Message</th></tr></thead>
                        <tbody>
                          {pagedJobs.map(j => (
                            <tr key={j.id}>
                              <td className="td-mono" style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{new Date(j.created_at).toLocaleString()}</td>
                              <td><span className="badge badge-grey">{j.job_name}</span></td>
                              <td><StatusBadge status={j.status} /></td>
                              <td style={{ color: 'var(--text-muted)', maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{j.message}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <Pagination page={jobPage} pages={jobPages} onPrev={() => setJobPage(p => p - 1)} onNext={() => setJobPage(p => p + 1)} />
                  </>
                )}
              </div>
            </>
          )}

          {/* ── Users ────────────────────────────────────────── */}
          {tab === 'users' && (
            <>
              <div className="page-header">
                <h1 className="page-title">Users</h1>
                <p className="page-subtitle">Account management (superadmin only)</p>
              </div>
              <div className="card">
                <div className="card-header"><span className="card-title">Create User</span></div>
                <form onSubmit={createUser} className="form-grid">
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Username</label>
                      <input className="input" placeholder="john_doe" value={newUsername} onChange={e => setNewUsername(e.target.value)} required />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Email</label>
                      <input className="input" type="email" placeholder="john@example.com" value={newUserEmail} onChange={e => setNewUserEmail(e.target.value)} required />
                    </div>
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label className="form-label">Password</label>
                      <input className="input" type="password" placeholder="Min 8 characters" value={newUserPassword} onChange={e => setNewUserPassword(e.target.value)} required />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Role</label>
                      <select className="select" value={newUserRole} onChange={e => setNewUserRole(e.target.value)}>
                        {USER_ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </div>
                  </div>
                  <div className="form-actions">
                    <button className="btn btn-primary" type="submit">Create User</button>
                  </div>
                </form>
              </div>
              <div className="card">
                <div className="card-header">
                  <span className="card-title">All Users</span>
                  <span className="card-count">{users.length}</span>
                </div>
                {users.length === 0 ? <Empty label="users" /> : (
                  <>
                    <div className="table-wrap">
                      <table>
                        <thead><tr><th>#</th><th>Username</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead>
                        <tbody>
                          {pagedUsers.map(u => (
                            <Fragment key={u.id}>
                              <tr>
                                <td className="td-id">{u.id}</td>
                                <td><strong>{u.username}</strong></td>
                                <td style={{ color: 'var(--text-muted)' }}>{u.email}</td>
                                <td><RoleBadge role={u.role} /></td>
                                <td>
                                  <span className={`badge ${u.is_active ? 'badge-green' : 'badge-grey'}`}>{u.is_active ? 'Active' : 'Inactive'}</span>
                                </td>
                                <td>
                                  <div style={{ display: 'flex', gap: 6 }}>
                                    <button className="btn btn-secondary btn-sm" onClick={() => setEditingUser(editingUser === u.id ? null : u.id)}>
                                      {editingUser === u.id ? 'Cancel' : 'Edit'}
                                    </button>
                                    {u.username !== 'superadmin' && (
                                      <button className="btn btn-ghost btn-sm" onClick={() => updateUser(u.id, { is_active: !u.is_active })}>
                                        {u.is_active ? 'Deactivate' : 'Activate'}
                                      </button>
                                    )}
                                  </div>
                                </td>
                              </tr>
                              {editingUser === u.id && (
                                <tr>
                                  <td colSpan={6} style={{ padding: '8px 14px', background: 'var(--surface-2)' }}>
                                    <div className="edit-row">
                                      <span style={{ fontSize: 12, color: 'var(--text-muted)', marginRight: 4 }}>Change role:</span>
                                      <select
                                        className="select"
                                        defaultValue={u.role}
                                        onChange={e => { updateUser(u.id, { role: e.target.value }); setEditingUser(null) }}
                                        style={{ width: 'auto' }}
                                      >
                                        <option value="user">user</option>
                                        <option value="admin">admin</option>
                                        <option value="superadmin">superadmin</option>
                                      </select>
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </Fragment>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <Pagination page={userPage} pages={userPages} onPrev={() => setUserPage(p => p - 1)} onNext={() => setUserPage(p => p + 1)} />
                  </>
                )}
              </div>
            </>
          )}
        </main>
      </div>

      {/* Mobile bottom navigation */}
      <nav className="bottom-nav">
        <div className="bottom-nav-items">
          {NAV.map(item => (
            <button
              key={item.id}
              className={`bottom-nav-btn ${tab === item.id ? 'active' : ''}`}
              onClick={() => { setTab(item.id); setMsg('') }}
            >
              <span className="bnav-icon">{item.icon}</span>
              <span className="bnav-label">{item.mobileLabel}</span>
            </button>
          ))}
        </div>
      </nav>
    </div>
  )
}
