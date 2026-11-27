import { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowRight, BookOpen, MousePointerClick, Users } from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { apiRequest } from './api'

const colors = ['#7b2438', '#b58a48', '#6f8471', '#a8b7c1', '#9c6a83', '#7897a4']
const emptyAnalytics = { monthlyActivity: [], departmentActivity: [], collaborations: [] }

function monthLabel(value) {
  if (!value || value.length < 7) return value || 'Unknown'
  const date = new Date(`${value}-01T00:00:00`)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
}

function chartPayload(event) {
  return event?.activePayload?.[0]?.payload || event?.payload || null
}

export default function AnalyticsPage({ dataMode, analytics }) {
  const [liveAnalytics, setLiveAnalytics] = useState(null)
  const [topicItems, setTopicItems] = useState([])
  const [topPapers, setTopPapers] = useState([])
  const [systemCounts, setSystemCounts] = useState(null)
  const [loadingLive, setLoadingLive] = useState(() => dataMode === 'live')
  const [loadWarning, setLoadWarning] = useState('')
  const [selectedInsight, setSelectedInsight] = useState(null)

  useEffect(() => {
    if (dataMode !== 'live') return undefined

    let active = true
    Promise.allSettled([
      apiRequest('/api/analytics/trends'),
      apiRequest('/api/analytics/topics'),
      apiRequest('/api/analytics/collaboration'),
      apiRequest('/api/analytics/topic-clusters'),
      apiRequest('/api/analytics/top-papers?top_n=8'),
      apiRequest('/'),
    ]).then(([trendsResult, departmentsResult, collaborationResult, topicsResult, papersResult, healthResult]) => {
      if (!active) return
      const failures = []
      const valueOrEmpty = (result, label) => {
        if (result.status === 'fulfilled') return result.value
        failures.push(`${label}: ${result.reason.message}`)
        return []
      }

      const rawTrends = valueOrEmpty(trendsResult, 'Engagement timeline')
      const rawDepartments = valueOrEmpty(departmentsResult, 'Department activity')
      const rawCollaborations = valueOrEmpty(collaborationResult, 'Collaboration network')
      const rawTopics = valueOrEmpty(topicsResult, 'Research topics')
      const rawPapers = valueOrEmpty(papersResult, 'Top papers')
      if (healthResult.status === 'fulfilled') setSystemCounts(healthResult.value.counts || {})
      else failures.push(`Service totals: ${healthResult.reason.message}`)

      const monthMap = new Map()
      if (Array.isArray(rawTrends)) rawTrends.forEach((item) => {
        const key = item.year_month || 'Unknown'
        if (!monthMap.has(key)) monthMap.set(key, { month: key, papers: 0, searches: 0 })
        const count = Number(item.total_events || 0)
        if (item.event_type === 'view' || item.event_type === 'save') monthMap.get(key).papers += count
        if (item.event_type === 'search') monthMap.get(key).searches += count
      })
      const monthlyActivity = [...monthMap.values()].sort((a, b) => a.month.localeCompare(b.month))
      const departmentTotal = Array.isArray(rawDepartments)
        ? rawDepartments.reduce((sum, item) => sum + Number(item.interaction_count || 0), 0)
        : 0
      const departmentActivity = Array.isArray(rawDepartments) ? rawDepartments.map((item) => ({
        name: item.department || 'Unassigned',
        activity: Number(item.interaction_count || 0),
        share: departmentTotal ? Math.round((Number(item.interaction_count || 0) / departmentTotal) * 100) : 0,
      })) : []
      const collaborationTotal = Array.isArray(rawCollaborations)
        ? rawCollaborations.reduce((sum, item) => sum + Number(item.engagement_volume || 0), 0)
        : 0
      const collaborations = Array.isArray(rawCollaborations) ? rawCollaborations.map((item) => ({
        name: item.researcher_department
          ? `${item.researcher_department}${item.topic_area ? ` · ${item.topic_area}` : ''}`
          : item.topic_area || 'Research network',
        value: Number(item.engagement_volume || 0),
        share: collaborationTotal ? Math.round((Number(item.engagement_volume || 0) / collaborationTotal) * 100) : 0,
      })) : []

      setLiveAnalytics({ monthlyActivity, departmentActivity, collaborations })
      setTopicItems(Array.isArray(rawTopics?.clusters) ? rawTopics.clusters : Array.isArray(rawTopics) ? rawTopics : [])
      setTopPapers(Array.isArray(rawPapers) ? rawPapers : [])
      setLoadWarning(failures.join(' · '))
    }).finally(() => {
      if (active) setLoadingLive(false)
    })

    return () => { active = false }
  }, [dataMode])

  const activeAnalytics = useMemo(() => {
    const source = dataMode === 'live' ? liveAnalytics || emptyAnalytics : analytics
    const collaborationVolume = source.collaborations.reduce((sum, item) => sum + Number(item.value || 0), 0)
    return {
      ...source,
      departmentActivity: source.departmentActivity.map((item) => ({
        ...item,
        share: item.share ?? item.activity,
      })),
      collaborations: source.collaborations.map((item) => ({
        ...item,
        share: item.share ?? (collaborationVolume ? Math.round((Number(item.value || 0) / collaborationVolume) * 100) : 0),
      })),
    }
  }, [dataMode, liveAnalytics, analytics])
  const displayedTopics = dataMode === 'live' ? topicItems : [
    { cluster_id: 1, name: 'AI & Data Mining Systems', paper_volume: 340, topics: ['Computer Science', 'Artificial Intelligence', 'Data Mining', 'Machine Learning'] },
    { cluster_id: 2, name: 'Distributed & Cloud Networks', paper_volume: 180, topics: ['Cloud Computing', 'World Wide Web', 'Software'] },
    { cluster_id: 3, name: 'Bioinformatics & Life Sciences', paper_volume: 165, topics: ['Bioinformatics', 'Computational Biology', 'Biology'] },
    { cluster_id: 4, name: 'Applied Mathematics & Modeling', paper_volume: 95, topics: ['Mathematics', 'Engineering'] },
  ]
  const totalEvents = useMemo(() => activeAnalytics.monthlyActivity.reduce(
    (sum, month) => sum + Number(month.papers || 0) + Number(month.searches ?? month.discussions ?? 0),
    0,
  ), [activeAnalytics])
  const selected = selectedInsight?.payload
  const paperTotal = systemCounts?.papers

  return (
    <div className="page-content analytics-page">
      <div className="page-heading-row">
        <div><span className="eyebrow">CAMPUS RESEARCH INTELLIGENCE</span><h1>Research insights</h1><p>Explore activity, topics, and collaboration across the research community.</p></div>
        <span className={`local-model-badge ${dataMode === 'live' ? 'analytics-live-badge' : ''}`}><span className="live-dot" />{dataMode === 'live' ? 'Live service data' : 'Illustrative demo data'}</span>
      </div>
      {loadWarning && <p className="analytics-warning" role="status">{loadWarning}</p>}
      {loadingLive && <p className="analytics-loading" role="status">Loading institutional analytics...</p>}

      <div className="analytics-kpis">
        <article className="metric-card"><span className="metric-icon rose"><Activity size={17} /></span><span className="metric-label">Tracked interactions</span><strong>{dataMode === 'live' && !loadingLive && totalEvents === 0 ? '0' : totalEvents.toLocaleString()}</strong><span className="metric-change">Across the available six-month window</span></article>
        <article className="metric-card"><span className="metric-icon gold"><BookOpen size={17} /></span><span className="metric-label">Research departments</span><strong>{activeAnalytics.departmentActivity.length}</strong><span className="metric-change">With recorded activity</span></article>
        <article className="metric-card"><span className="metric-icon green"><Users size={17} /></span><span className="metric-label">Cross-department ties</span><strong>{activeAnalytics.collaborations.length}</strong><span className="metric-change">Distinct research connections</span></article>
        <article className="metric-card"><span className="metric-icon blue"><BookOpen size={17} /></span><span className="metric-label">Papers in collection</span><strong>{dataMode === 'live' && paperTotal != null ? Number(paperTotal).toLocaleString() : '—'}</strong><span className="metric-change">{dataMode === 'live' ? 'Current backend corpus' : 'Open the admin console for totals'}</span></article>
      </div>

      <div className="analytics-grid">
        <section className="chart-card activity-chart">
          <div className="chart-card-heading"><div><span className="eyebrow">SIX-MONTH TIMELINE</span><h2>Research engagement over time</h2><p>Click a month to inspect its event totals.</p></div><MousePointerClick size={16} className="chart-hint-icon" /></div>
          <div className="chart-legend"><span><i className="legend-dot burgundy" /> Views & saves</span><span><i className="legend-dot gold" /> Searches</span></div>
          {activeAnalytics.monthlyActivity.length ? <div className="line-chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activeAnalytics.monthlyActivity} margin={{ top: 10, right: 12, left: -20, bottom: 0 }} onClick={(event) => { const payload = chartPayload(event); if (payload) setSelectedInsight({ type: 'month', payload }) }}>
                <defs><linearGradient id="paperFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7b2438" stopOpacity={0.14} /><stop offset="95%" stopColor="#7b2438" stopOpacity={0} /></linearGradient><linearGradient id="searchFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#b58a48" stopOpacity={0.13} /><stop offset="95%" stopColor="#b58a48" stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid stroke="#eee9e2" vertical={false} />
                <XAxis dataKey="month" tickFormatter={monthLabel} axisLine={false} tickLine={false} tick={{ fill: '#8b867e', fontSize: 10 }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#8b867e', fontSize: 10 }} />
                <Tooltip labelFormatter={monthLabel} />
                <Area type="monotone" dataKey="papers" name="Views & saves" stroke="#7b2438" strokeWidth={2.2} fill="url(#paperFill)" activeDot={{ r: 5, cursor: 'pointer' }} />
                <Area type="monotone" dataKey="searches" name="Searches" stroke="#b58a48" strokeWidth={2.2} fill="url(#searchFill)" activeDot={{ r: 5, cursor: 'pointer' }} />
              </AreaChart>
            </ResponsiveContainer>
          </div> : <div className="analytics-empty">No timeline events are available for this data source.</div>}
        </section>

        <section className="chart-card">
          <div className="chart-card-heading"><div><span className="eyebrow">DEPARTMENT ENGAGEMENT</span><h2>Activity by department</h2><p>Click a bar or department to see recorded interactions.</p></div><MousePointerClick size={16} className="chart-hint-icon" /></div>
          {activeAnalytics.departmentActivity.length ? <>
            <div className="line-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={activeAnalytics.departmentActivity} layout="vertical" margin={{ top: 8, right: 15, left: 10, bottom: 0 }} onClick={(event) => { const payload = chartPayload(event); if (payload) setSelectedInsight({ type: 'department', payload }) }}>
                  <CartesianGrid stroke="#eee9e2" horizontal={false} />
                  <XAxis type="number" axisLine={false} tickLine={false} tick={{ fill: '#8b867e', fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" width={104} axisLine={false} tickLine={false} tick={{ fill: '#746c64', fontSize: 9 }} />
                  <Tooltip />
                  <Bar dataKey="activity" name="Interactions" fill="#7b2438" radius={[0, 4, 4, 0]} cursor="pointer" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="department-legend">{activeAnalytics.departmentActivity.map((item, index) => <button className="analytics-drill-row" key={item.name} onClick={() => setSelectedInsight({ type: 'department', payload: item })}><i style={{ background: colors[index % colors.length] }} /><span>{item.name}</span><strong>{Number(item.activity).toLocaleString()} events</strong></button>)}</div>
          </> : <div className="analytics-empty">No department activity has been recorded yet.</div>}
        </section>
      </div>

      {selected && <section className="analytics-detail-panel" aria-live="polite">
        <div><span className="eyebrow">CHART DRILL-DOWN</span><h2>{selectedInsight.type === 'month' ? monthLabel(selected.month) : selected.name || 'Selected insight'}</h2>
          {selectedInsight.type === 'month' && <p>{Number(selected.papers || 0).toLocaleString()} research views and saves · {Number(selected.searches ?? selected.discussions ?? 0).toLocaleString()} searches</p>}
          {selectedInsight.type === 'department' && <p>{Number(selected.activity || 0).toLocaleString()} recorded interactions · {Number(selected.share || 0)}% of department activity</p>}
          {selectedInsight.type === 'collaboration' && <p>{Number(selected.value || 0).toLocaleString()} network connections · {Number(selected.share || 0)}% of the displayed collaboration volume</p>}
          {selectedInsight.type === 'topic' && <p>{Number(selected.paper_volume || 0).toLocaleString()} papers mention this research concept.</p>}
          {selectedInsight.type === 'paper' && <p>{Number(selected.save_count || 0).toLocaleString()} saves · {Number(selected.discussion_count || 0) + Number(selected.comment_count || 0)} linked discussions and paper comments</p>}
        </div><button className="analytics-detail-close" onClick={() => setSelectedInsight(null)}>Clear selection</button>
      </section>}

      <section className="chart-card analytics-topics-card">
        <div className="chart-card-heading"><div><span className="eyebrow">RESEARCH LANDSCAPE</span><h2>Most represented topics</h2><p>Concept frequency in the corpus{dataMode === 'live' ? ' · click a topic for its paper count' : ' · illustrative sample'}</p></div></div>
        {displayedTopics.length ? <div className="analytics-topic-grid">{displayedTopics.map((topic, index) => <button className="analytics-topic-card" key={topic.cluster_id || topic.name || index} onClick={() => setSelectedInsight({ type: 'topic', payload: topic })}><span className="topic-card-index" style={{ background: colors[index % colors.length] }}>0{index + 1}</span><span className="topic-paper-volume">{Number(topic.paper_volume || topic.interaction_count || 0).toLocaleString()} papers</span><strong>{topic.name || topic.topic || topic.department}</strong><span className="topic-card-tags">{(topic.topics || []).slice(0, 4).map((tag) => <i key={tag}>{tag}</i>)}</span></button>)}</div> : <div className="analytics-empty">No topic concepts are available for this data source.</div>}
      </section>

      <div className="analytics-bottom">
        <section className="chart-card">
          <div className="chart-card-heading"><div><span className="eyebrow">CROSS-SCHOOL WORK</span><h2>Collaboration network</h2><p>Select a network segment or label to inspect its share.</p></div><MousePointerClick size={16} className="chart-hint-icon" /></div>
          {activeAnalytics.collaborations.length ? <div className="collaboration-layout">
            <div className="collaboration-chart"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={activeAnalytics.collaborations} dataKey="value" nameKey="name" innerRadius={45} outerRadius={72} paddingAngle={4} stroke="none" onClick={(entry) => setSelectedInsight({ type: 'collaboration', payload: entry })}>{activeAnalytics.collaborations.map((item, index) => <Cell key={item.name} fill={colors[index % colors.length]} cursor="pointer" />)}</Pie><Tooltip formatter={(value) => [`${Number(value).toLocaleString()} ties`, 'Connections']} /></PieChart></ResponsiveContainer></div>
            <div className="department-legend">{activeAnalytics.collaborations.map((item, index) => <button className="analytics-drill-row" key={item.name} onClick={() => setSelectedInsight({ type: 'collaboration', payload: item })}><i style={{ background: colors[index % colors.length] }} /><span>{item.name}</span><strong>{Number(item.value).toLocaleString()} · {item.share || 0}%</strong></button>)}</div>
          </div> : <div className="analytics-empty">No cross-department connections are available.</div>}
        </section>
        <section className="chart-card analytics-top-papers"><div className="chart-card-heading"><div><span className="eyebrow">COMMUNITY SIGNALS</span><h2>Most saved research</h2><p>Saved papers with linked discussion activity.</p></div></div>
          {dataMode === 'live' ? topPapers.length ? <div className="top-paper-list">{topPapers.slice(0, 6).map((paper, index) => <button className="top-paper-row" key={paper.id} onClick={() => setSelectedInsight({ type: 'paper', payload: paper })}><span>{String(index + 1).padStart(2, '0')}</span><strong>{paper.title}</strong><small>{Number(paper.save_count || 0)} saves</small></button>)}</div> : <div className="analytics-empty compact">No library saves are available yet.</div> : <div className="demo-analytics-note"><BookOpen size={18} /><p>Connect the backend to view real save and discussion rankings.</p></div>}
        </section>
      </div>
      <p className="analytics-footnote"><ArrowRight size={13} /> Charts reflect connected API data when available; demo figures are illustrative and never presented as live measurements.</p>
    </div>
  )
}
