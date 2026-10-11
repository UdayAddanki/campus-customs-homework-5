import { useCallback, useEffect, useMemo, useState } from 'react'

const API = 'http://localhost:8000'
type Ticket = { id: number; type: string; requester: string; subject: string; sku: string | null; size: string | null; qty: number | null; status: string; notes: string; created_at: string }
type Event = { timestamp?: string; agent?: string; action?: string; ticket_id?: number; tool?: string; result?: string | Record<string, unknown> | null }

function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [balance, setBalance] = useState<number | null>(null)
  const [selected, setSelected] = useState<number>(() => {
    const requested = Number(new URLSearchParams(window.location.search).get('ticket'))
    return [101, 102, 103].includes(requested) ? requested : 101
  })
  const [running, setRunning] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    const [ticketResponse, eventResponse, cashResponse] = await Promise.all([fetch(`${API}/tickets`), fetch(`${API}/events?limit=500`), fetch(`${API}/cash`)] )
    if (!ticketResponse.ok || !eventResponse.ok || !cashResponse.ok) throw new Error('The operations API could not be reached.')
    setTickets(await ticketResponse.json()); setEvents(await eventResponse.json()); setBalance((await cashResponse.json()).balance)
  }, [])

  useEffect(() => { refresh().catch(e => setError(e.message)) }, [refresh])
  const ticket = tickets.find(item => item.id === selected)
  const ticketEvents = useMemo(() => events.filter(item => item.ticket_id === selected), [events, selected])
  const startRun = async () => {
    setRunning(true); setError(''); setMessage('');
    try { const response = await fetch(`${API}/tickets/${selected}/run`, { method: 'POST' }); const body = await response.json(); if (!response.ok) throw new Error(body.detail || 'Agent run failed.'); setMessage('Agent run completed successfully.'); await refresh() }
    catch (e) { setError(e instanceof Error ? e.message : 'Agent run failed.') }
    finally { setRunning(false) }
  }

  return <div className="app-shell">
    <header className="topbar"><div><div className="eyebrow">CAMPUS CUSTOMS</div><h1>Operations desk</h1></div><div className="balance"><span>Checking balance</span><strong>{balance === null ? '—' : `$${balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}</strong><button className="icon-button" onClick={() => refresh().catch(e => setError(e.message))} aria-label="Refresh dashboard">↻</button></div></header>
    <main className="layout">
      <aside className="ticket-panel"><div className="section-heading"><div><span className="eyebrow">INBOX</span><h2>Open tickets</h2></div><span className="count">{tickets.length}</span></div><div className="ticket-list">{tickets.map(item => <button className={`ticket-row ${item.id === selected ? 'selected' : ''}`} key={item.id} onClick={() => setSelected(item.id)}><div className="row-top"><span className="ticket-id">#{item.id}</span><span className={`status ${item.status}`}>{item.status}</span></div><strong>{item.subject}</strong><span className="muted">{item.requester}</span><span className="muted">{item.sku ? `${item.sku} · size ${item.size}` : 'Facilities'}</span></button>)}</div></aside>
      <section className="workspace">{ticket ? <><div className="workspace-header"><div><span className="eyebrow">TICKET #{ticket.id}</span><h2>{ticket.subject}</h2><p className="muted">{ticket.requester} · {ticket.notes}</p></div><div className={`status large ${ticket.status}`}>{ticket.status}</div></div><div className="action-bar"><button className="primary" onClick={startRun} disabled={running}>{running ? 'Agents working…' : 'Start agent team'}</button><span className="muted">Review findings before taking an approved action.</span></div>{message && <div className="notice success">{message}</div>}{error && <div className="notice error">{error}</div>}<div className="feed-card"><div className="section-heading"><div><span className="eyebrow">LIVE TRACE</span><h3>Agent activity</h3></div><button className="text-button" onClick={() => refresh().catch(e => setError(e.message))}>Refresh</button></div>{ticketEvents.length ? <div className="activity-feed">{ticketEvents.map((event, index) => <div className="activity" key={`${event.timestamp}-${index}`}><div className="dot"/><div><div className="activity-meta"><strong>{event.agent || 'System'}</strong><span>{event.action}</span>{event.tool && <code>{event.tool}</code>}</div>{event.result && <p>{typeof event.result === 'string' ? event.result : JSON.stringify(event.result)}</p>}<small>{event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ''}</small></div></div>)}</div> : <div className="empty"><div className="empty-icon">✦</div><strong>No activity yet</strong><span>Start the agent team to see the ticket move through the shop.</span></div>}</div></> : <div className="empty"><strong>Loading tickets…</strong></div>}</section>
    </main>
  </div>
}

export default App
