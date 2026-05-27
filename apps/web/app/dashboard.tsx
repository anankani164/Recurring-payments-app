'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'

type Client = { id: number; name: string; email: string }
type Project = {
  id: number
  name: string
  client_id: number
  amount_usd: number
  recurrence: string
  rate_type: string
  next_invoice_date: string
}
type FxRate = {
  id: number
  rate_date: string
  code: string
  cash_buying: number
  cash_selling: number
  tts_buying: number
  tts_selling: number
  source_url: string
}
type Invoice = {
  id: number
  project_id: number
  invoice_date: string
  amount_usd: number
  fx_rate: number
  amount_ghs: number
  rate_type: string
  source_rate_date: string
}
type JobLog = { id: number; job_name: string; status: string; message: string; created_at: string }
type Health = { status: string }
type User = { id: number; username: string; email: string; role: string; is_active: boolean }

const rateTypes = ['cash_buying', 'cash_selling', 'tts_buying', 'tts_selling']
const userRoles = ['admin', 'user']

export default function Dashboard() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || ''

  const [health, setHealth] = useState('checking...')
  const [token, setToken] = useState('')
  const [username, setUsername] = useState('superadmin')
  const [password, setPassword] = useState('')

  const headers = useMemo(
    () => ({ 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }),
    [token],
  )

  const [clients, setClients] = useState<Client[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [rates, setRates] = useState<FxRate[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [jobs, setJobs] = useState<JobLog[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [editingUser, setEditingUser] = useState<number | null>(null)

  const [clientName, setClientName] = useState('')
  const [clientEmail, setClientEmail] = useState('')
  const [projectName, setProjectName] = useState('')
  const [projectClientId, setProjectClientId] = useState('')
  const [amountUsd, setAmountUsd] = useState('')
  const [nextDate, setNextDate] = useState('')
  const [rateType, setRateType] = useState('tts_selling')
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState<'ok' | 'err'>('ok')
  const [pdfUrl, setPdfUrl] = useState('')

  const [newUsername, setNewUsername] = useState('')
  const [newUserEmail, setNewUserEmail] = useState('')
  const [newUserPassword, setNewUserPassword] = useState('')
  const [newUserRole, setNewUserRole] = useState('user')
  const [clientPage, setClientPage] = useState(1)
  const [projectPage, setProjectPage] = useState(1)
  const [userPage, setUserPage] = useState(1)
  const pageSize = 5

  const loadData = async () => {
    if (!token) return
    try {
      const [cRes, pRes, rRes, iRes, jRes, uRes] = await Promise.all([
        fetch(`${apiBase}/clients`, { headers }),
        fetch(`${apiBase}/projects`, { headers }),
        fetch(`${apiBase}/rates`, { headers }),
        fetch(`${apiBase}/invoices`, { headers }),
        fetch(`${apiBase}/jobs`, { headers }),
        fetch(`${apiBase}/users`, { headers }),
      ])
      if (cRes.ok) setClients(await cRes.json())
      if (pRes.ok) setProjects(await pRes.json())
      if (rRes.ok) setRates(await rRes.json())
      if (iRes.ok) setInvoices(await iRes.json())
      if (jRes.ok) setJobs(await jRes.json())
      if (uRes.ok) setUsers(await uRes.json())
    } catch {
      setMessageType('err')
      setMessage('Failed to load data from API')
    }
  }

  useEffect(() => {
    fetch(`${apiBase}/health`)
      .then((r) => r.json() as Promise<Health>)
      .then((d) => setHealth(d.status))
      .catch(() => setHealth('unreachable'))
  }, [apiBase])

  useEffect(() => { loadData() }, [token])

  const login = async (e: FormEvent) => {
    e.preventDefault()
    setMessage('')
    const res = await fetch(`${apiBase}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!res.ok) { setMessageType('err'); return setMessage('Login failed. Check username/password.') }
    const data = await res.json()
    setToken(data.access_token)
    setPassword('')
    setMessageType('ok')
    setMessage('Logged in successfully')
  }

  const createUser = async (e: FormEvent) => {
    e.preventDefault()
    setMessage('')
    if (newUserPassword.length < 8) { setMessageType('err'); return setMessage('Password must be at least 8 characters') }
    const res = await fetch(`${apiBase}/users`, {
      method: 'POST', headers,
      body: JSON.stringify({ username: newUsername, email: newUserEmail, password: newUserPassword, role: newUserRole }),
    })
    if (!res.ok) { setMessageType('err'); return setMessage('Could not create user (superadmin only)') }
    setNewUsername(''); setNewUserEmail(''); setNewUserPassword(''); setNewUserRole('user')
    setMessageType('ok'); setMessage('User created')
    await loadData()
  }

  const addClient = async (e: FormEvent) => {
    e.preventDefault(); setMessage('')
    if (!clientName.trim()) { setMessageType('err'); return setMessage('Client name is required') }
    const res = await fetch(`${apiBase}/clients`, { method: 'POST', headers, body: JSON.stringify({ name: clientName, email: clientEmail }) })
    if (!res.ok) { setMessageType('err'); return setMessage('Could not create client') }
    setClientName(''); setClientEmail('')
    await loadData()
  }

  const addProject = async (e: FormEvent) => {
    e.preventDefault(); setMessage('')
    if (!projectClientId) { setMessageType('err'); return setMessage('Please select a client for the project') }
    if (!amountUsd || Number(amountUsd) <= 0) { setMessageType('err'); return setMessage('Amount USD must be greater than 0') }
    if (!nextDate) { setMessageType('err'); return setMessage('Next invoice date is required') }
    const res = await fetch(`${apiBase}/projects`, {
      method: 'POST', headers,
      body: JSON.stringify({ name: projectName, client_id: Number(projectClientId), amount_usd: Number(amountUsd), recurrence: 'monthly', rate_type: rateType, next_invoice_date: nextDate }),
    })
    if (!res.ok) { setMessageType('err'); return setMessage('Could not create project') }
    setProjectName(''); setProjectClientId(''); setAmountUsd(''); setNextDate(''); setRateType('tts_selling')
    await loadData()
  }

  const ingestPdfRate = async (e: FormEvent) => {
    e.preventDefault(); setMessage('')
    if (!pdfUrl.startsWith('http://') && !pdfUrl.startsWith('https://')) { setMessageType('err'); return setMessage('PDF URL must start with http:// or https://') }
    const res = await fetch(`${apiBase}/rates/ingest-pdf`, { method: 'POST', headers, body: JSON.stringify({ source_url: pdfUrl, target_code: 'USD' }) })
    if (!res.ok) { setMessageType('err'); return setMessage('Could not ingest PDF rate') }
    setPdfUrl('')
    await loadData()
  }

  const runJobsNow = async () => {
    setMessage('')
    const res = await fetch(`${apiBase}/run-jobs-now`, { method: 'POST', headers })
    if (!res.ok) { setMessageType('err'); return setMessage('Failed to run jobs') }
    await loadData()
  }

  const updateUser = async (userId: number, payload: { role?: string; is_active?: boolean }) => {
    const res = await fetch(`${apiBase}/users/${userId}`, { method: 'PATCH', headers, body: JSON.stringify(payload) })
    if (!res.ok) { setMessageType('err'); setMessage('Failed to update user'); return }
    setMessageType('ok'); setMessage('User updated')
    await loadData()
  }

  const pagedClients = clients.slice((clientPage - 1) * pageSize, clientPage * pageSize)
  const pagedProjects = projects.slice((projectPage - 1) * pageSize, projectPage * pageSize)
  const pagedUsers = users.slice((userPage - 1) * pageSize, userPage * pageSize)
  const clientPages = Math.max(1, Math.ceil(clients.length / pageSize))
  const projectPages = Math.max(1, Math.ceil(projects.length / pageSize))
  const userPages = Math.max(1, Math.ceil(users.length / pageSize))

  return (
    <main style={{ fontFamily: 'sans-serif', padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      <h1>Recurring Payments Dashboard</h1>
      <p>API Health: {health}</p>
      {message && <p style={{ color: messageType === 'err' ? 'crimson' : 'green' }}>{message}</p>}

      <section style={{ marginTop: 24 }}>
        <h2>Login</h2>
        <form onSubmit={login} style={{ display: 'grid', gap: 8 }}>
          <input placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          <input placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <button type="submit">Login</button>
        </form>
      </section>

      {token && (
        <>
          <section style={{ marginTop: 24 }}>
            <h2>Superadmin: Create User</h2>
            <form onSubmit={createUser} style={{ display: 'grid', gap: 8 }}>
              <input placeholder="Username" value={newUsername} onChange={(e) => setNewUsername(e.target.value)} required />
              <input placeholder="Email" type="email" value={newUserEmail} onChange={(e) => setNewUserEmail(e.target.value)} required />
              <input placeholder="Password" type="password" value={newUserPassword} onChange={(e) => setNewUserPassword(e.target.value)} required />
              <select value={newUserRole} onChange={(e) => setNewUserRole(e.target.value)}>
                {userRoles.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              <button type="submit">Create User</button>
            </form>
          </section>

          <section style={{ marginTop: 24 }}>
            <h2>Users</h2>
            <ul>
              {pagedUsers.map((u) => (
                <li key={u.id} style={{ marginBottom: 8 }}>
                  <b>{u.username}</b> ({u.email}) — role: {u.role} — {u.is_active ? 'active' : 'inactive'}{' '}
                  <button onClick={() => setEditingUser(editingUser === u.id ? null : u.id)}>Edit</button>
                  {u.username !== 'superadmin' && (
                    <button onClick={() => updateUser(u.id, { is_active: !u.is_active })}>
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  )}
                  {editingUser === u.id && (
                    <span style={{ marginLeft: 8 }}>
                      <select defaultValue={u.role} onChange={(e) => updateUser(u.id, { role: e.target.value })}>
                        <option value="user">user</option>
                        <option value="admin">admin</option>
                        <option value="superadmin">superadmin</option>
                      </select>
                    </span>
                  )}
                </li>
              ))}
            </ul>
            <p>
              Page {userPage} of {userPages}{' '}
              <button disabled={userPage <= 1} onClick={() => setUserPage((p) => Math.max(1, p - 1))}>Prev</button>{' '}
              <button disabled={userPage >= userPages} onClick={() => setUserPage((p) => Math.min(userPages, p + 1))}>Next</button>
            </p>
          </section>

          <section style={{ marginTop: 24 }}>
            <h2>Actions</h2>
            <button onClick={runJobsNow}>Run jobs now</button>
          </section>

          <section style={{ marginTop: 24 }}>
            <h2>Add Client</h2>
            <form onSubmit={addClient} style={{ display: 'grid', gap: 8 }}>
              <input placeholder="Client Name" value={clientName} onChange={(e) => setClientName(e.target.value)} required />
              <input placeholder="Client Email" type="email" value={clientEmail} onChange={(e) => setClientEmail(e.target.value)} required />
              <button type="submit">Save Client</button>
            </form>
          </section>

          <section style={{ marginTop: 24 }}>
            <h2>Add Project</h2>
            <form onSubmit={addProject} style={{ display: 'grid', gap: 8 }}>
              <input placeholder="Project Name" value={projectName} onChange={(e) => setProjectName(e.target.value)} required />
              <select value={projectClientId} onChange={(e) => setProjectClientId(e.target.value)} required>
                <option value="">Select Client</option>
                {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <input placeholder="Amount USD" type="number" step="0.01" value={amountUsd} onChange={(e) => setAmountUsd(e.target.value)} required />
              <input type="date" value={nextDate} onChange={(e) => setNextDate(e.target.value)} required />
              <select value={rateType} onChange={(e) => setRateType(e.target.value)}>
                {rateTypes.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              <button type="submit">Save Project</button>
            </form>
          </section>

          <section style={{ marginTop: 24 }}>
            <h2>Ingest Bank PDF Rate</h2>
            <form onSubmit={ingestPdfRate} style={{ display: 'grid', gap: 8 }}>
              <input placeholder="https://bank.example/forex.pdf" value={pdfUrl} onChange={(e) => setPdfUrl(e.target.value)} required />
              <button type="submit">Ingest PDF</button>
            </form>
          </section>

          <section style={{ marginTop: 24 }}>
            <h2>Recent Data</h2>
            <p>Clients: {clients.length} | Projects: {projects.length} | Rates: {rates.length} | Invoices: {invoices.length} | Jobs: {jobs.length}</p>
            <h3>Clients</h3>
            <ul>{pagedClients.map((c) => <li key={c.id}>{c.name} ({c.email})</li>)}</ul>
            <p>
              Page {clientPage} of {clientPages}{' '}
              <button disabled={clientPage <= 1} onClick={() => setClientPage((p) => Math.max(1, p - 1))}>Prev</button>{' '}
              <button disabled={clientPage >= clientPages} onClick={() => setClientPage((p) => Math.min(clientPages, p + 1))}>Next</button>
            </p>
            <h3>Projects</h3>
            <ul>{pagedProjects.map((p) => <li key={p.id}>{p.name} - USD {p.amount_usd} - {p.next_invoice_date}</li>)}</ul>
            <p>
              Page {projectPage} of {projectPages}{' '}
              <button disabled={projectPage <= 1} onClick={() => setProjectPage((p) => Math.max(1, p - 1))}>Prev</button>{' '}
              <button disabled={projectPage >= projectPages} onClick={() => setProjectPage((p) => Math.min(projectPages, p + 1))}>Next</button>
            </p>
          </section>
        </>
      )}
    </main>
  )
}
