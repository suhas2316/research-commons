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

const colors = ['#7b2438', '#b58a48', '#6f8471', '#a8b7c1']

export default function AnalyticsPage({ dataMode, analytics }) {
  if (dataMode === 'live') {
    return (
      <div className="page-content">
        <div className="page-heading-row"><div><span className="eyebrow">ADMINISTRATOR WORKSPACE</span><h1>Research insights</h1><p>Service availability</p></div></div>
        <section className="service-unavailable"><span className="service-unavailable-icon"><Activity size={20} /></span><h2>Analytics data is not connected</h2><p>The search and analytics team has not published a dashboard endpoint in the shared FastAPI contract.</p></section>
      </div>
    )
  }

  return (
    <div className="page-content">
      <div className="page-heading-row"><div><span className="eyebrow">ADMINISTRATOR WORKSPACE</span><h1>Research insights</h1><p>Activity and collaboration overview.</p></div><span className="local-model-badge"><span className="live-dot" /> Offline sample mode</span></div>
      <div className="analytics-kpis"><article className="metric-card"><span className="metric-icon rose"><Activity size={17} /></span><span className="metric-label">Sample activity</span><strong>{analytics.monthlyActivity.reduce((sum, month) => sum + month.papers + month.discussions, 0)}</strong><span className="metric-change">Across 6 months</span></article><article className="metric-card"><span className="metric-icon gold"><BookOpen size={17} /></span><span className="metric-label">Research areas</span><strong>{analytics.departmentActivity.length}</strong><span className="metric-change">Departments represented</span></article><article className="metric-card"><span className="metric-icon green"><Users size={17} /></span><span className="metric-label">Collaboration links</span><strong>{analytics.collaborations.length}</strong><span className="metric-change">Sample partnerships</span></article><article className="metric-card"><span className="metric-icon blue"><Activity size={17} /></span><span className="metric-label">Reporting period</span><strong>6 mo</strong><span className="metric-change">June - November</span></article></div>
      <div className="analytics-grid">
        <section className="chart-card activity-chart"><div className="chart-card-heading"><div><span className="eyebrow">SIX-MONTH TREND</span><h2>Research activity over time</h2><p>Papers and discussions per month</p></div></div><div className="chart-legend"><span><i className="legend-dot burgundy" /> Papers</span><span><i className="legend-dot gold" /> Discussions</span></div><div className="line-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={analytics.monthlyActivity} margin={{ top: 10, right: 12, left: -20, bottom: 0 }}><defs><linearGradient id="paperFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7b2438" stopOpacity={0.14} /><stop offset="95%" stopColor="#7b2438" stopOpacity={0} /></linearGradient><linearGradient id="discussionFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#b58a48" stopOpacity={0.13} /><stop offset="95%" stopColor="#b58a48" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#eee9e2" vertical={false} /><XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#8b867e', fontSize: 11 }} dy={10} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#8b867e', fontSize: 11 }} /><Tooltip /><Area type="monotone" dataKey="papers" name="Papers" stroke="#7b2438" strokeWidth={2.2} fill="url(#paperFill)" /><Area type="monotone" dataKey="discussions" name="Discussions" stroke="#b58a48" strokeWidth={2.2} fill="url(#discussionFill)" /></AreaChart></ResponsiveContainer></div></section>
        <section className="chart-card"><div className="chart-card-heading"><div><span className="eyebrow">DEPARTMENT ACTIVITY</span><h2>Research by school</h2><p>Share of sample activity</p></div></div><div className="line-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={analytics.departmentActivity} layout="vertical" margin={{ top: 8, right: 15, left: 10, bottom: 0 }}><CartesianGrid stroke="#eee9e2" horizontal={false} /><XAxis type="number" axisLine={false} tickLine={false} tick={{ fill: '#8b867e', fontSize: 10 }} /><YAxis type="category" dataKey="name" width={95} axisLine={false} tickLine={false} tick={{ fill: '#746c64', fontSize: 9 }} /><Tooltip /><Bar dataKey="activity" name="Activity" fill="#7b2438" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer></div><div className="department-legend">{analytics.departmentActivity.map((item, index) => <div key={item.name}><i style={{ background: colors[index % colors.length] }} /><span>{item.name}</span><strong>{item.activity}%</strong></div>)}</div></section>
      </div>
      <div className="analytics-bottom"><section className="chart-card"><div className="chart-card-heading"><div><span className="eyebrow">CROSS-SCHOOL WORK</span><h2>Collaboration network</h2><p>Example partnership distribution</p></div></div><div className="collaboration-layout"><div className="collaboration-chart"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={analytics.collaborations} dataKey="value" nameKey="name" innerRadius={45} outerRadius={72} paddingAngle={4} stroke="none">{analytics.collaborations.map((item, index) => <Cell key={item.name} fill={colors[index % colors.length]} />)}</Pie><Tooltip formatter={(value) => [`${value}%`, 'Partnerships']} /></PieChart></ResponsiveContainer></div><div className="department-legend">{analytics.collaborations.map((item, index) => <div key={item.name}><i style={{ background: colors[index % colors.length] }} /><span>{item.name}</span><strong>{item.value}%</strong></div>)}</div></div></section><section className="insight-callout"><span className="insight-icon"><Activity size={18} /></span><span className="eyebrow">SAMPLE DASHBOARD</span><h3>Preview only</h3><p>These illustrative charts are not connected to the university database. Live analytics will replace them when the analytics API is available.</p></section></div>
      <p className="demo-disclaimer">Offline preview · Sample figures only. Do not report as project results.</p>
    </div>
  )
}
