import { useEffect, useState } from 'react'
import { Activity, BookOpen, Users } from 'lucide-react'
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

const colors = ['#7b2438', '#b58a48', '#6f8471', '#a8b7c1']

export default function AnalyticsPage({ dataMode, analytics }) {
  const [liveAnalytics, setLiveAnalytics] = useState(null)
  const [loadingLive, setLoadingLive] = useState(false)

  useEffect(() => {
    if (dataMode === 'live') {
      setLoadingLive(true)
      Promise.allSettled([
        apiRequest('/api/analytics/trends'),
        apiRequest('/api/analytics/topics'),
        apiRequest('/api/analytics/collaboration'),
      ])
        .then(([trendsRes, topicsRes, collabRes]) => {
          const trendsData = trendsRes.status === 'fulfilled' && Array.isArray(trendsRes.value) ? trendsRes.value : []
          const topicsData = topicsRes.status === 'fulfilled' && Array.isArray(topicsRes.value) ? topicsRes.value : []
          const collabData = collabRes.status === 'fulfilled' && Array.isArray(collabRes.value) ? collabRes.value : []

          if (trendsData.length > 0 || topicsData.length > 0) {
            // Group trends by month
            const monthMap = {}
            trendsData.forEach((item) => {
              const m = item.year_month || '2026-06'
              if (!monthMap[m]) monthMap[m] = { month: m, papers: 0, discussions: 0 }
              if (item.event_type === 'save' || item.event_type === 'view') {
                monthMap[m].papers += Number(item.total_events || 0)
              } else {
                monthMap[m].discussions += Number(item.total_events || 0)
              }
            })
            const monthlyActivity = Object.values(monthMap).sort((a, b) => a.month.localeCompare(b.month))

            // Department activity share
            const deptMap = {}
            let totalDeptEvents = 0
            topicsData.forEach((item) => {
              const d = item.department || 'General'
              const count = Number(item.interaction_count || 0)
              deptMap[d] = (deptMap[d] || 0) + count
              totalDeptEvents += count
            })
            const departmentActivity = Object.entries(deptMap).map(([name, count]) => ({
              name,
              activity: totalDeptEvents > 0 ? Math.round((count / totalDeptEvents) * 100) : 0,
            }))

            // Collaborations
            const collaborations = collabData.slice(0, 5).map((item) => ({
              name: `${item.researcher_department || 'Dept'} & ${item.topic_area || 'Area'}`,
              value: Number(item.engagement_volume || 1),
            }))

            setLiveAnalytics({
              monthlyActivity: monthlyActivity.length > 0 ? monthlyActivity : analytics.monthlyActivity,
              departmentActivity: departmentActivity.length > 0 ? departmentActivity : analytics.departmentActivity,
              collaborations: collaborations.length > 0 ? collaborations : analytics.collaborations,
            })
          }
        })
        .catch(() => {})
        .finally(() => setLoadingLive(false))
    }
  }, [dataMode, analytics])

  const activeAnalytics = liveAnalytics || analytics

  return (
    <div className="page-content">
      <div className="page-heading-row">
        <div>
          <span className="eyebrow">ADMINISTRATOR WORKSPACE</span>
          <h1>Research insights</h1>
          <p>Institutional analytics powered by DuckDB OLAP engine.</p>
        </div>
        <span className="local-model-badge">
          <span className="live-dot" /> {liveAnalytics ? 'Live DuckDB Engine' : 'Sample preview mode'}
        </span>
      </div>

      <div className="analytics-kpis">
        <article className="metric-card">
          <span className="metric-icon rose"><Activity size={17} /></span>
          <span className="metric-label">Total activity volume</span>
          <strong>{activeAnalytics.monthlyActivity.reduce((sum, month) => sum + (month.papers || 0) + (month.discussions || 0), 0)}</strong>
          <span className="metric-change">Events tracked across 6 months</span>
        </article>
        <article className="metric-card">
          <span className="metric-icon gold"><BookOpen size={17} /></span>
          <span className="metric-label">Research departments</span>
          <strong>{activeAnalytics.departmentActivity.length}</strong>
          <span className="metric-change">Academic departments</span>
        </article>
        <article className="metric-card">
          <span className="metric-icon green"><Users size={17} /></span>
          <span className="metric-label">Collaboration partnerships</span>
          <strong>{activeAnalytics.collaborations.length}</strong>
          <span className="metric-change">Inter-school initiatives</span>
        </article>
        <article className="metric-card">
          <span className="metric-icon blue"><Activity size={17} /></span>
          <span className="metric-label">Reporting window</span>
          <strong>6 mo</strong>
          <span className="metric-change">June - November 2026</span>
        </article>
      </div>

      <div className="analytics-grid">
        <section className="chart-card activity-chart">
          <div className="chart-card-heading">
            <div>
              <span className="eyebrow">SIX-MONTH TIMELINE</span>
              <h2>Research engagement over time</h2>
              <p>Interaction events (views, bookmarks, searches) by month</p>
            </div>
          </div>
          <div className="chart-legend">
            <span><i className="legend-dot burgundy" /> Papers & Bookmarks</span>
            <span><i className="legend-dot gold" /> Discussions & Searches</span>
          </div>
          <div className="line-chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activeAnalytics.monthlyActivity} margin={{ top: 10, right: 12, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="paperFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#7b2438" stopOpacity={0.14} />
                    <stop offset="95%" stopColor="#7b2438" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="discussionFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#b58a48" stopOpacity={0.13} />
                    <stop offset="95%" stopColor="#b58a48" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#eee9e2" vertical={false} />
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#8b867e', fontSize: 11 }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#8b867e', fontSize: 11 }} />
                <Tooltip />
                <Area type="monotone" dataKey="papers" name="Papers" stroke="#7b2438" strokeWidth={2.2} fill="url(#paperFill)" />
                <Area type="monotone" dataKey="discussions" name="Discussions" stroke="#b58a48" strokeWidth={2.2} fill="url(#discussionFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="chart-card">
          <div className="chart-card-heading">
            <div>
              <span className="eyebrow">DEPARTMENT ENGAGEMENT</span>
              <h2>Research by school</h2>
              <p>Activity share across academic departments</p>
            </div>
          </div>
          <div className="line-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={activeAnalytics.departmentActivity} layout="vertical" margin={{ top: 8, right: 15, left: 10, bottom: 0 }}>
                <CartesianGrid stroke="#eee9e2" horizontal={false} />
                <XAxis type="number" axisLine={false} tickLine={false} tick={{ fill: '#8b867e', fontSize: 10 }} />
                <YAxis type="category" dataKey="name" width={95} axisLine={false} tickLine={false} tick={{ fill: '#746c64', fontSize: 9 }} />
                <Tooltip />
                <Bar dataKey="activity" name="Activity %" fill="#7b2438" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="department-legend">
            {activeAnalytics.departmentActivity.map((item, index) => (
              <div key={item.name}>
                <i style={{ background: colors[index % colors.length] }} />
                <span>{item.name}</span>
                <strong>{item.activity}%</strong>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="analytics-bottom">
        <section className="chart-card">
          <div className="chart-card-heading">
            <div>
              <span className="eyebrow">CROSS-SCHOOL WORK</span>
              <h2>Inter-department collaboration network</h2>
              <p>Top inter-school topic and research partnerships</p>
            </div>
          </div>
          <div className="collaboration-layout">
            <div className="collaboration-chart">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={activeAnalytics.collaborations} dataKey="value" nameKey="name" innerRadius={45} outerRadius={72} paddingAngle={4} stroke="none">
                    {activeAnalytics.collaborations.map((item, index) => (
                      <Cell key={item.name} fill={colors[index % colors.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${value}%`, 'Volume']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="department-legend">
              {activeAnalytics.collaborations.map((item, index) => (
                <div key={item.name}>
                  <i style={{ background: colors[index % colors.length] }} />
                  <span>{item.name}</span>
                  <strong>{item.value}%</strong>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="insight-callout">
          <span className="insight-icon"><Activity size={18} /></span>
          <span className="eyebrow">ANALYTICS ENGINE</span>
          <h3>DuckDB Columnar Processing</h3>
          <p>
            Aggregations are computed directly from columnar Parquet/Star-schema structures. Sub-second analytics allow administrators to drill down by department, topic, and researcher.
          </p>
        </section>
      </div>
    </div>
  )
}
