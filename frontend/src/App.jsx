import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  BookOpen,
  Bot,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  FileText,
  FolderOpen,
  Home,
  Library,
  LogOut,
  Menu,
  MessageCircle,
  MoreHorizontal,
  Plus,
  Search,
  Send,
  Sparkles,
  UserRound,
  Users,
  X,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { apiRequest } from './api'
import { createDemoPortal, demoUsers } from './demoData'
import './App.css'

const AnalyticsPage = lazy(() => import('./AnalyticsPage.jsx'))
const USER_STORAGE_KEY = 'research_commons_user'
const navigation = [
  { label: 'Overview', items: [{ id: 'home', label: 'Home', icon: Home }, { id: 'feed', label: 'Community feed', icon: MessageCircle }] },
  { label: 'Explore', items: [{ id: 'search', label: 'Discover research', icon: Search }, { id: 'library', label: 'My library', icon: Library }, { id: 'assistant', label: 'Research assistant', icon: Bot }] },
  { label: 'Workspace', items: [{ id: 'analytics', label: 'Analytics', icon: Activity }, { id: 'profile', label: 'My profile', icon: UserRound }] },
]
const pageTitles = {
  home: 'Home',
  feed: 'Community feed',
  search: 'Discover research',
  library: 'My library',
  assistant: 'Research assistant',
  analytics: 'Research insights',
  profile: 'My profile',
}

function readStoredSession() {
  try {
    const stored = JSON.parse(window.localStorage.getItem(USER_STORAGE_KEY) || 'null')
    if (!stored?.id || !stored.name || !stored.email) {
      if (stored) window.localStorage.removeItem(USER_STORAGE_KEY)
      return null
    }
    return {
      user: {
        id: stored.id,
        name: stored.name,
        email: stored.email,
        role: stored.role || 'student',
        department: stored.department || '',
        interests: stored.interests || [],
      },
      mode: stored.mode === 'demo' ? 'demo' : 'api',
    }
  } catch {
    window.localStorage.removeItem(USER_STORAGE_KEY)
    return null
  }
}

function persistSession(user, mode) {
  try {
    window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({
      id: user.id,
      name: user.name,
      email: user.email,
      role: user.role,
      department: user.department,
      interests: user.interests || [],
      mode,
    }))
    return true
  } catch {
    return false
  }
}

function initialsFor(name = '') {
  return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0] || '').join('').toUpperCase() || 'RC'
}

function formatDate(value) {
  if (!value) return 'Date unavailable'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function normalizePaper(record) {
  const paper = record.paper || record
  const authors = Array.isArray(paper.authors)
    ? paper.authors.map((author) => typeof author === 'string' ? author : author.name || author.display_name || '').filter(Boolean).join(', ')
    : paper.authors || ''
  const concepts = Array.isArray(paper.concepts) ? paper.concepts : []
  return {
    id: String(paper.id || record.paper_id || ''),
    title: paper.title || 'Untitled paper',
    authors,
    year: paper.publication_year || paper.year || 'Year unavailable',
    journal: paper.source || 'Research Commons',
    abstract: paper.abstract || '',
    tags: concepts.map((concept) => typeof concept === 'string' ? concept : concept.display_name || concept.name || '').filter(Boolean).slice(0, 3),
    citations: Number(paper.citation_count || paper.citations || 0),
    collectionName: record.collection_name || 'General',
    notes: record.notes || '',
  }
}

function normalizePost(record) {
  const author = record.author_name || record.author || 'Research Commons member'
  return {
    id: String(record.id),
    author,
    department: record.author_department || record.department || '',
    initials: initialsFor(author),
    time: formatDate(record.created_at),
    title: record.title || 'Untitled discussion',
    body: record.content || '',
    tags: Array.isArray(record.tags) ? record.tags : [],
    comments: Array.isArray(record.comments) ? record.comments : [],
    commentCount: Number(record.comment_count ?? record.comments?.length ?? 0),
  }
}

function Avatar({ initials, className = '' }) {
  return <span className={`avatar ${className}`}>{initials}</span>
}

function Sidebar({ activePage, onNavigate, onSignOut, mobileOpen, setMobileOpen, user }) {
  return (
    <>
      {mobileOpen && <button className="sidebar-backdrop" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><span>R</span></div>
          <div><strong>Research</strong><span>COMMONS</span></div>
          <button className="icon-button mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={18} /></button>
        </div>
        <div className="campus-switcher">
          <span className="campus-emblem">CU</span>
          <span><strong>Chanakya University</strong><small>Research network</small></span>
        </div>
        <nav className="side-nav" aria-label="Main navigation">
          {navigation.map((group) => (
            <section className="nav-group" key={group.label}>
              <p className="nav-label">{group.label}</p>
              {group.items.filter((item) => item.id !== 'analytics' || user.role === 'admin').map(({ id, label, icon: Icon }) => (
                <button type="button" className={`nav-link ${activePage === id ? 'active' : ''}`} key={id} onClick={() => { onNavigate(id); setMobileOpen(false) }}>
                  <Icon size={18} strokeWidth={1.8} /><span>{label}</span>
                </button>
              ))}
            </section>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-prompt">
          <div className="prompt-icon"><Sparkles size={16} /></div>
          <strong>Ideas grow together.</strong>
          <p>Share what you're working on with the research community.</p>
          <button onClick={() => onNavigate('feed')}>Start a discussion <ArrowRight size={14} /></button>
        </div>
        <a className="sidebar-help" href="https://chanakyauniversity.edu.in/" target="_blank" rel="noreferrer"><CircleHelp size={17} /> University website <ArrowUpRight size={14} /></a>
        <button className="sidebar-user" onClick={() => onNavigate('profile')}>
          <Avatar initials={initialsFor(user.name)} />
          <span><strong>{user.name}</strong><small>{user.role}</small></span>
          <MoreHorizontal size={19} />
        </button>
        <button className="sign-out-link" onClick={onSignOut}><LogOut size={15} /> Sign out</button>
      </aside>
    </>
  )
}

function Topbar({ title, onNavigate, onOpenMenu, user }) {
  return (
    <header className="topbar">
      <button className="icon-button menu-button" onClick={onOpenMenu} aria-label="Open navigation"><Menu size={20} /></button>
      <div className="breadcrumb"><span>Research Commons</span><ChevronRight size={14} /><strong>{title}</strong></div>
      <div className="topbar-actions">
        <button className="top-search" onClick={() => onNavigate('search')}><Search size={16} /><span>Search papers, people...</span><kbd>⌘ K</kbd></button>
        <button className="top-avatar" onClick={() => onNavigate('profile')} aria-label="Open your profile"><Avatar initials={initialsFor(user.name)} /></button>
      </div>
    </header>
  )
}

function SectionTitle({ eyebrow, title, action, onAction }) {
  return (
    <div className="section-title">
      <div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h2>{title}</h2></div>
      {action && <button className="text-button" onClick={onAction}>{action}<ArrowRight size={15} /></button>}
    </div>
  )
}

function PaperCard({ paper, saved, onSave }) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saveOpen, setSaveOpen] = useState(false)
  const [collectionName, setCollectionName] = useState(paper.collectionName || 'General')
  const [notes, setNotes] = useState(paper.notes || '')

  async function savePaper() {
    if (!onSave || saved) return
    setSaving(true)
    setError('')
    try {
      await onSave(paper.id, { collectionName, notes })
      setSaveOpen(false)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <article className="paper-card">
      <div className="paper-cover"><BookOpen size={22} strokeWidth={1.5} /><span>{paper.year}</span></div>
      <div className="paper-content">
        <div className="paper-meta"><span className="paper-type">RESEARCH PAPER</span><span>{paper.journal}</span></div>
        <h3>{paper.title}</h3>
        <p className="paper-authors">{paper.authors || 'Author details unavailable'} <span>·</span> {paper.year}</p>
        {paper.abstract && <p className="paper-abstract">{paper.abstract}</p>}
        {paper.tags.length > 0 && <div className="tag-row">{paper.tags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div>}
        {paper.notes && <p className="paper-note"><strong>Private note:</strong> {paper.notes}</p>}
        <div className="paper-footer">
          <span><FileText size={14} /> {paper.citations} citations</span>
          {onSave && <button className={`save-button ${saved ? 'saved' : ''}`} disabled={saved || saving} onClick={() => setSaveOpen(true)}>{saved ? <Bookmark size={15} /> : <Plus size={15} />}{saved ? 'In your library' : 'Save paper'}</button>}
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
      </div>
      {saveOpen && <Modal title="Save paper to your library" onClose={() => setSaveOpen(false)}><form className="composer-form" onSubmit={(event) => { event.preventDefault(); savePaper() }}><label htmlFor={`collection-${paper.id}`}>Collection</label><input id={`collection-${paper.id}`} value={collectionName} onChange={(event) => setCollectionName(event.target.value)} maxLength="120" required /><label htmlFor={`note-${paper.id}`}>Private note</label><textarea id={`note-${paper.id}`} value={notes} onChange={(event) => setNotes(event.target.value)} rows="3" placeholder="Add a note only you can see..." />{error && <p className="form-error" role="alert">{error}</p>}<div className="modal-actions"><button type="button" className="button button-quiet" onClick={() => setSaveOpen(false)}>Cancel</button><button type="submit" className="button button-primary" disabled={saving}>{saving ? 'Saving...' : 'Save paper'}</button></div></form></Modal>}
    </article>
  )
}

function HomePage({ user, papers, posts, library, peopleTotal, trends, dataMode, onNavigate, onSave, onAddComment }) {
  const savedIds = new Set(library.map((item) => String(item.paper_id || item.id)))
  return (
    <div className="page-content">
      <section className="welcome-banner">
        <div className="welcome-copy">
          <span className="welcome-kicker"><span className="live-dot" /> YOUR RESEARCH COMMUNITY</span>
          <h1>Welcome, {user.name.split(' ')[0]}<span>.</span></h1>
          <p>A place for learning, discovery, innovation, expression, and discourse.</p>
          <button className="button button-light" onClick={() => onNavigate('search')}>Explore the library <ArrowRight size={16} /></button>
        </div>
        <div className="welcome-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit-core"><BookOpen size={28} /></div><span className="orbit-star star-one">✦</span><span className="orbit-star star-two">✧</span></div>
        <div className="banner-caption">ROOTED IN IDEALS <span>·</span> ASCENDING WITH IDEAS</div>
      </section>
      <div className="quick-stats">
        <div className="stat-card"><span className="stat-icon burgundy"><BookOpen size={17} /></span><div><span className="stat-label">Papers in your library</span><strong>{library.length}</strong><small>From your saved research</small></div></div>
        <div className="stat-card"><span className="stat-icon ochre"><Users size={17} /></span><div><span className="stat-label">Research community</span><strong>{peopleTotal}</strong><small>Registered members</small></div></div>
        <div className="stat-card"><span className="stat-icon sage"><MessageCircle size={17} /></span><div><span className="stat-label">Recent discussions</span><strong>{posts.length}</strong><small>Loaded from the community feed</small></div></div>
      </div>
      <div className="home-columns">
        <section className="home-main-column">
          <SectionTitle eyebrow="RESEARCH COLLECTION" title="Recently added papers" action="Discover all" onAction={() => onNavigate('search')} />
          <div className="recommended-stack">{papers.slice(0, 2).map((paper) => <PaperCard key={paper.id} paper={paper} saved={savedIds.has(paper.id)} onSave={onSave} />)}{papers.length === 0 && <EmptyState title="No papers are available" text="The research collection has no records yet." />}</div>
          <SectionTitle eyebrow="FROM YOUR COMMUNITY" title="Recent discussions" action="Open feed" onAction={() => onNavigate('feed')} />
          <div className="discussion-list">{posts.slice(0, 2).map((post) => <DiscussionCard key={post.id} post={post} onAddComment={onAddComment} />)}{posts.length === 0 && <EmptyState title="No discussions yet" text="When researchers post to the feed, they will appear here." />}</div>
        </section>
        <aside className="home-aside">
          <div className="aside-panel service-panel"><span className="eyebrow">TOPIC MOMENTUM</span>{dataMode === 'live' ? <><h2>Trends will appear here</h2><p>The recommendations service has not published a trends endpoint yet.</p></> : trends.map((topic, index) => <button className="trend-row" key={topic.name} onClick={() => onNavigate('search')}><span className={`trend-number ${topic.tone}`}>0{index + 1}</span><span><strong>{topic.name}</strong><small>{topic.papers} papers this week</small></span><b>{topic.growth}</b></button>)}</div>
          <div className="assistant-promo"><span className="assistant-spark"><Sparkles size={17} /></span><span className="eyebrow">RESEARCH ASSISTANT</span><h3>Questions lead to discovery.</h3><p>{dataMode === 'live' ? 'Analyze research questions with the local AI assistant.' : 'Ask the AI assistant to analyze sample papers.'}</p><button className="button button-outline" onClick={() => onNavigate('assistant')}>Open assistant <ArrowRight size={15} /></button></div>
          <div className="quote-card"><span>“</span><p>A place for learning, discovery, innovation, expression, and discourse.</p><small>CHANAKYA UNIVERSITY · RESEARCH INITIATIVES</small></div>
        </aside>
      </div>
    </div>
  )
}

function DiscussionCard({ post, onAddComment }) {
  const [commentOpen, setCommentOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function submitComment(event) {
    event.preventDefault()
    if (!draft.trim()) return
    setSubmitting(true)
    setError('')
    try {
      await onAddComment(post.id, draft.trim())
      setDraft('')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <article className="discussion-card">
      <div className="discussion-header"><Avatar initials={post.initials} /><div className="discussion-author"><strong>{post.author}</strong><span>{post.department || 'Research Commons member'}</span></div><span className="discussion-time">{post.time}</span></div>
      <h3>{post.title}</h3><p className="discussion-body">{post.body}</p>
      {post.tags.length > 0 && <div className="tag-row">{post.tags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}</div>}
      <div className="discussion-actions"><button onClick={() => setCommentOpen(!commentOpen)}><MessageCircle size={16} />{post.commentCount} comments</button></div>
      {commentOpen && <div className="comment-thread">
        {post.comments.map((comment) => <div className="comment-entry" key={comment.id}><Avatar initials={initialsFor(comment.author_name)} /><div><strong>{comment.author_name || 'Researcher'}</strong><p>{comment.content}</p></div></div>)}
        <form className="comment-inline" onSubmit={submitComment}><Avatar initials="ME" /><input value={draft} onChange={(event) => setDraft(event.target.value)} aria-label="Write a comment" placeholder="Add a comment..." /><button disabled={!draft.trim() || submitting} aria-label="Send comment"><Send size={15} /></button></form>
        {error && <p className="form-error" role="alert">{error}</p>}
      </div>}
    </article>
  )
}

function FeedPage({ posts, onCreatePost, onAddComment }) {
  const [composerOpen, setComposerOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [tags, setTags] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function publishPost(event) {
    event.preventDefault()
    if (!title.trim() || !body.trim()) return
    setSubmitting(true)
    setError('')
    try {
      await onCreatePost(title.trim(), body.trim(), tags.split(',').map((tag) => tag.trim()).filter(Boolean))
      setTitle('')
      setBody('')
      setTags('')
      setComposerOpen(false)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-content">
      <div className="page-heading-row"><div><span className="eyebrow">IDEAS IN CONVERSATION</span><h1>Community feed</h1><p>Share discoveries, ask questions, and learn from your peers.</p></div><button className="button button-primary" onClick={() => setComposerOpen(true)}><Plus size={17} /> Start a discussion</button></div>
      <div className="feed-layout"><section className="feed-list"><div className="feed-tabs"><span className="selected">Recent discussions</span><span>{posts.length} loaded</span></div><div className="discussion-list">{posts.map((post) => <DiscussionCard key={post.id} post={post} onAddComment={onAddComment} />)}{posts.length === 0 && <EmptyState title="No discussions yet" text="Start a conversation with your research community." />}</div></section><aside className="feed-aside"><div className="aside-panel"><SectionTitle eyebrow="COMMUNITY GUIDELINES" title="Share with care" /><p className="service-copy">Credit your sources, keep discussion constructive, and make room for different perspectives.</p></div></aside></div>
      {composerOpen && <Modal title="Start a discussion" onClose={() => setComposerOpen(false)}><form className="composer-form" onSubmit={publishPost}><label htmlFor="post-title">Discussion title</label><input id="post-title" required value={title} onChange={(event) => setTitle(event.target.value)} placeholder="What would you like to discuss?" /><label htmlFor="post-body">Your post</label><textarea id="post-body" required value={body} onChange={(event) => setBody(event.target.value)} placeholder="Share a question, a discovery, or an idea..." rows="5" /><label htmlFor="post-tags">Tags</label><input id="post-tags" value={tags} onChange={(event) => setTags(event.target.value)} placeholder="Separate tags with commas" />{error && <p className="form-error" role="alert">{error}</p>}<div className="modal-actions"><button type="button" className="button button-quiet" onClick={() => setComposerOpen(false)}>Cancel</button><button className="button button-primary" type="submit" disabled={submitting}><Send size={15} />{submitting ? 'Publishing...' : 'Publish discussion'}</button></div></form></Modal>}
    </div>
  )
}

function SearchPage({ papers, library, people, posts, dataMode, onSave, onAddComment }) {
  const [query, setQuery] = useState('')
  const [activeTab, setActiveTab] = useState('Papers')
  const needle = query.trim().toLowerCase()
  const matches = (text) => !needle || text.toLowerCase().includes(needle)
  const filteredPapers = papers.filter((paper) => matches(`${paper.title} ${paper.authors} ${paper.abstract} ${paper.tags.join(' ')}`))
  const filteredLibrary = library.filter((paper) => matches(`${paper.title} ${paper.authors} ${paper.abstract} ${paper.tags.join(' ')} ${paper.collectionName}`))
  const filteredPeople = people.filter((person) => matches(`${person.name} ${person.department} ${person.email} ${(person.interests || []).join(' ')}`))
  const filteredPosts = posts.filter((post) => matches(`${post.title} ${post.body} ${post.tags.join(' ')}`))
  const resultSets = { Papers: filteredPapers, Library: filteredLibrary, People: filteredPeople, Posts: filteredPosts }
  const count = resultSets[activeTab].length

  return (
    <div className="page-content">
      <div className="page-heading-row"><div><span className="eyebrow">ONE SEARCH, MANY PERSPECTIVES</span><h1>Discover research</h1><p>Search papers, saved library items, researchers, and discussions.</p></div></div>
      <div className="search-hero"><form className="unified-search" onSubmit={(event) => event.preventDefault()}><Search size={20} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search papers, library items, members, and discussions..." autoFocus /><button className="button button-primary" type="submit">Search</button></form></div>
      <div className="search-results-head"><div className="result-tabs">{Object.keys(resultSets).map((tab) => <button key={tab} onClick={() => setActiveTab(tab)} className={activeTab === tab ? 'selected' : ''}>{tab}<span>{resultSets[tab].length}</span></button>)}</div></div>
      <p className="results-caption">{query ? `${count} ${activeTab.toLowerCase()} results for "${query}"` : `${count} ${activeTab.toLowerCase()} ${dataMode === 'live' ? 'available from the backend' : 'included in sample data'}`}</p>
      {activeTab === 'Papers' && <div className="search-paper-list">{filteredPapers.map((paper) => <PaperCard key={paper.id} paper={paper} saved={library.some((item) => item.id === paper.id)} onSave={onSave} />)}{!count && <EmptyState title="No matching papers" text="Try another search term or check back when more papers are available." />}</div>}
      {activeTab === 'Library' && <div className="search-paper-list">{filteredLibrary.map((paper) => <PaperCard key={`${paper.id}-${paper.collectionName}`} paper={paper} saved onSave={onSave} />)}{!count && <EmptyState title="No matching saved papers" text="Save a paper to your library to see it in this tab." />}</div>}
      {activeTab === 'People' && <div className="people-grid">{filteredPeople.map((person) => <article className="person-card" key={person.id}><Avatar initials={initialsFor(person.name)} /><h3>{person.name}</h3><p>{person.department || person.role}</p><div className="tag-row">{(person.interests || []).map((interest) => <span className="tag" key={interest}>{interest}</span>)}</div></article>)}{!count && <EmptyState title="No matching researchers" text="Try searching by name, department, or research interest." />}</div>}
      {activeTab === 'Posts' && <div className="discussion-list">{filteredPosts.map((post) => <DiscussionCard key={post.id} post={post} onAddComment={onAddComment} />)}{!count && <EmptyState title="No matching discussions" text="Try a different search term." />}</div>}
    </div>
  )
}

function LibraryPage({ library, onNavigate, onSave }) {
  const [activeCollection, setActiveCollection] = useState('All papers')
  const [selectedPaper, setSelectedPaper] = useState(null)
  const [notes, setNotes] = useState('')
  const [collectionName, setCollectionName] = useState('')
  const [savingNote, setSavingNote] = useState(false)
  const [noteError, setNoteError] = useState('')
  const collections = useMemo(() => {
    const groups = new Map()
    library.forEach((paper) => groups.set(paper.collectionName, (groups.get(paper.collectionName) || 0) + 1))
    return [...groups.entries()].map(([name, count]) => ({ name, count }))
  }, [library])
  const visiblePapers = activeCollection === 'All papers' ? library : library.filter((paper) => paper.collectionName === activeCollection)

  async function saveNote(event) {
    event.preventDefault()
    if (!selectedPaper) return
    setSavingNote(true)
    setNoteError('')
    try {
      await onSave(selectedPaper.id, { notes, collectionName })
      setSelectedPaper(null)
    } catch (requestError) {
      setNoteError(requestError.message)
    } finally {
      setSavingNote(false)
    }
  }

  return (
    <div className="page-content">
      <div className="page-heading-row"><div><span className="eyebrow">YOUR PERSONAL RESEARCH SPACE</span><h1>My library</h1><p>Saved papers and collections from your account.</p></div><button className="button button-primary" onClick={() => onNavigate('search')}><Plus size={17} /> Find papers</button></div>
      <div className="library-summary"><div className="library-summary-icon"><Library size={19} /></div><div><strong>{library.length} saved papers</strong><span>Loaded from your account.</span></div><button className="text-button" onClick={() => onNavigate('search')}>Browse research <ArrowRight size={15} /></button></div>
      <div className="collection-heading"><SectionTitle eyebrow="ORGANISE YOUR READING" title="Collections" /></div>
      {collections.length > 0 ? <div className="collection-grid"><button className="collection-card rose" onClick={() => setActiveCollection('All papers')}><span className="collection-icon"><FolderOpen size={19} /></span><span className="collection-count">{library.length} papers</span><strong>All papers</strong><small>Every saved item in your library</small><span className="collection-arrow"><ArrowUpRight size={15} /></span></button>{collections.map((collection, index) => <button className={`collection-card ${['rose', 'green', 'gold'][index % 3]}`} key={collection.name} onClick={() => setActiveCollection(collection.name)}><span className="collection-icon"><FolderOpen size={19} /></span><span className="collection-count">{collection.count} papers</span><strong>{collection.name}</strong><small>Saved in this collection</small><span className="collection-arrow"><ArrowUpRight size={15} /></span></button>)}</div> : <EmptyState title="No collections yet" text="Save a paper from Discover research. Collections from the backend will appear here." action="Discover papers" onAction={() => onNavigate('search')} />}
      {library.length > 0 && <><div className="library-papers-head"><SectionTitle eyebrow="YOUR READING LIST" title={activeCollection} /><button className="filter-button" onClick={() => setActiveCollection('All papers')}>{activeCollection}</button></div><div className="search-paper-list">{visiblePapers.map((paper) => <div className="library-entry" key={`${paper.id}-${paper.collectionName}`}><PaperCard paper={paper} saved /><button className="text-button note-edit-button" onClick={() => { setSelectedPaper(paper); setNotes(paper.notes || ''); setCollectionName(paper.collectionName); setNoteError('') }}>Edit private note <ArrowRight size={14} /></button></div>)}</div></>}
      {selectedPaper && <Modal title="Edit private note" onClose={() => setSelectedPaper(null)}><form className="composer-form" onSubmit={saveNote}><label htmlFor="library-collection">Collection</label><input id="library-collection" value={collectionName} onChange={(event) => setCollectionName(event.target.value)} maxLength="120" required /><label htmlFor="library-note">Private note</label><textarea id="library-note" value={notes} onChange={(event) => setNotes(event.target.value)} rows="4" placeholder="Add a note only you can see..." />{noteError && <p className="form-error" role="alert">{noteError}</p>}<div className="modal-actions"><button type="button" className="button button-quiet" onClick={() => setSelectedPaper(null)}>Cancel</button><button type="submit" className="button button-primary" disabled={savingNote}>{savingNote ? 'Saving...' : 'Save note'}</button></div></form></Modal>}
    </div>
  )
}

function AssistantPage({ papers }) {
  const [messages, setMessages] = useState([{ role: 'assistant', content: 'I can help analyze research questions, compare ideas, explain methods, and identify limitations. Ask a question to begin.', sources: [] }])
  const [draft, setDraft] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState('')
  const suggestions = ['What are the themes in responsible AI?', 'How do communities build climate resilience?', 'How can oral histories be preserved?']

  async function sendMessage(text = draft) {
    const prompt = text.trim()
    if (!prompt || isSending) return
    const history = messages.slice(-10).map(({ role, content }) => ({ role, content }))
    const userMessage = { role: 'user', content: prompt, sources: [] }
    setMessages((current) => [...current, userMessage])
    setDraft('')
    setError('')
    setIsSending(true)
    try {
      const response = await apiRequest('/api/assistant/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: prompt,
          history,
          papers: papers.slice(0, 50).map((paper) => ({
            id: String(paper.id),
            title: paper.title,
            authors: paper.authors || '',
            year: paper.year || '',
            abstract: (paper.abstract || '').slice(0, 4000),
            tags: Array.isArray(paper.tags) ? paper.tags.slice(0, 20) : [],
          })),
        }),
      })
      setMessages((current) => [...current, {
        role: 'assistant',
        content: response.answer,
        sources: Array.isArray(response.sources) ? response.sources : [],
      }])
    } catch (requestError) {
      setMessages((current) => current.slice(0, -1))
      setDraft(prompt)
      setError(requestError.message)
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div className="page-content assistant-page">
      <div className="page-heading-row"><div><span className="eyebrow">GROUNDED IN RESEARCH</span><h1>Research assistant</h1><p>Ask questions, analyze ideas, and explore evidence from the research collection.</p></div><span className="local-model-badge"><span className="live-dot" /> Ollama · local AI</span></div>
      <div className="chat-shell">
        <div className="chat-header"><span className="chat-bot-icon"><Bot size={19} /></span><div><strong>Research Commons AI</strong><small>Local model · responses grounded in relevant papers when available</small></div></div>
        <div className="chat-transcript">{messages.map((message, index) => <div className={`chat-message ${message.role}`} key={`${message.role}-${index}`}><div className="message-avatar">{message.role === 'assistant' ? <Sparkles size={15} /> : 'ME'}</div><div className="message-body"><span className="message-label">{message.role === 'assistant' ? 'RESEARCH COMMONS AI' : 'YOU'}</span>{message.role === 'assistant' ? <div className="assistant-markdown"><ReactMarkdown>{message.content}</ReactMarkdown></div> : <p>{message.content}</p>}{message.sources.length > 0 && <div className="citation-drawer"><div><FileText size={14} /><strong>Retrieved research</strong></div>{message.sources.map((paper, sourceIndex) => <details className="citation-details" key={paper.id}><summary><span>[{sourceIndex + 1}]</span><strong>{paper.title}</strong><ChevronDown size={14} /></summary><small>{paper.authors}{paper.year ? ` · ${paper.year}` : ''}</small><p>{paper.abstract}</p></details>)}</div>}</div></div>)}{isSending && <div className="chat-thinking" role="status"><Sparkles size={15} /> Analyzing your question with the local model...</div>}{messages.length === 1 && <div className="suggestion-block"><span>TRY A RESEARCH QUESTION</span>{suggestions.map((suggestion) => <button key={suggestion} onClick={() => sendMessage(suggestion)} disabled={isSending}>{suggestion}<ArrowUpRight size={14} /></button>)}</div>}</div>
        {error && <p className="form-error chat-error" role="alert">{error}</p>}
        <form className="chat-composer" onSubmit={(event) => { event.preventDefault(); sendMessage() }}><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMessage() } }} placeholder="Ask a research question..." rows="1" aria-label="Ask the research assistant" disabled={isSending} /><button type="submit" disabled={!draft.trim() || isSending} aria-label="Send question"><Send size={17} /></button><small>Questions run on your local Ollama model. Paper abstracts may be sent as context; no external AI service is used.</small></form>
      </div>
    </div>
  )
}

function ProfilePage({ profile, libraryCount, postCount }) {
  const interests = Array.isArray(profile.interests) ? profile.interests : []
  return (
    <div className="page-content">
      <div className="page-heading-row"><div><span className="eyebrow">YOUR PLACE IN THE COMMUNITY</span><h1>My profile</h1><p>Profile details returned by your Research Commons account.</p></div></div>
      <section className="profile-card"><div className="profile-cover"><span>CHANAKYA UNIVERSITY · RESEARCH COMMONS</span></div><div className="profile-main"><Avatar initials={initialsFor(profile.name)} className="profile-avatar" /><div className="profile-identity"><h2>{profile.name}</h2><span>{profile.role} · {profile.email}</span></div></div><div className="profile-details"><div><span className="eyebrow">DEPARTMENT</span><strong>{profile.department || 'Not set'}</strong></div><div><span className="eyebrow">RESEARCH INTERESTS</span><div className="tag-row">{interests.length ? interests.map((interest) => <span className="tag" key={interest}>{interest}</span>) : <span className="service-copy">No interests provided.</span>}</div></div></div></section>
      <div className="profile-lower"><div className="chart-card profile-about"><span className="eyebrow">ABOUT YOUR RESEARCH</span><h2>{profile.bio || 'Your research profile'}</h2><p>Profile editing is not available in the current backend API.</p></div><div className="chart-card profile-stats"><span className="eyebrow">YOUR CONTRIBUTIONS</span><div><strong>{libraryCount}</strong><span>Papers saved</span></div><div><strong>{postCount}</strong><span>Discussions started</span></div><div><strong>{Number(profile.followers_count || 0)}</strong><span>Researchers following you</span></div></div></div>
    </div>
  )
}

function EmptyState({ title, text, action, onAction }) {
  return <div className="empty-state"><span><BookOpen size={20} /></span><h3>{title}</h3><p>{text}</p>{action && <button className="button button-primary" onClick={onAction}>{action}<ArrowRight size={15} /></button>}</div>
}

function Modal({ title, onClose, children }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="modal-heading"><h2 id="modal-title">{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close"><X size={19} /></button></div>{children}</section></div>
}

function AuthPage({ onAuthenticated, onDemoLogin }) {
  const [isRegister, setIsRegister] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('student')
  const [department, setDepartment] = useState('')
  const [interests, setInterests] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking')

  useEffect(() => {
    let active = true
    apiRequest('/').then(() => {
      if (active) setBackendStatus('online')
    }).catch(() => {
      if (active) setBackendStatus('offline')
    })
    return () => { active = false }
  }, [])

  async function submit(event) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const path = isRegister ? '/api/users/register' : '/api/users/login'
      const payload = isRegister
        ? { name, email, password, role, department, interests: interests.split(',').map((item) => item.trim()).filter(Boolean) }
        : { email, password }
      const response = await apiRequest(path, { method: 'POST', body: JSON.stringify(payload) })
      if (!response?.user?.id) throw new Error('The authentication service returned an invalid user response.')
      onAuthenticated(response.user)
    } catch (requestError) {
      setError(requestError instanceof TypeError
        ? 'The backend is not reachable on port 8000. Start FastAPI or choose a demo login.'
        : requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  function switchMode() {
    setIsRegister(!isRegister)
    setError('')
  }

  return (
    <main className="auth-page">
      <div className="auth-brand"><div className="brand-mark"><span>R</span></div><div><strong>Research</strong><span>COMMONS</span></div></div>
      <section className="auth-card">
        <span className="eyebrow">CHANAKYA UNIVERSITY RESEARCH NETWORK</span>
        <h1>{isRegister ? 'Join the community.' : 'Welcome back.'}</h1>
        <p>{isRegister ? 'Create a Research Commons account.' : 'Sign in with your Research Commons account.'}</p>
        <form onSubmit={submit}>
          {isRegister && <label>Full name<input type="text" autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} required /></label>}
          <label>Email address<input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@chanakyauniversity.edu.in" required /></label>
          <label>Password<input type="password" autoComplete={isRegister ? 'new-password' : 'current-password'} value={password} onChange={(event) => setPassword(event.target.value)} minLength={isRegister ? 4 : 1} required /></label>
          {isRegister && <>
            <label>Role<select value={role} onChange={(event) => setRole(event.target.value)}><option value="student">Student</option><option value="faculty">Faculty</option><option value="researcher">Researcher</option><option value="admin">Admin</option></select></label>
            <label>Department<input value={department} onChange={(event) => setDepartment(event.target.value)} required /></label>
            <label>Research interests<input value={interests} onChange={(event) => setInterests(event.target.value)} placeholder="Separate interests with commas" /></label>
          </>}
          {error && <p className="form-error auth-error" role="alert">{error}</p>}
          <button className="button button-primary auth-submit" type="submit" disabled={submitting}>{submitting ? 'Connecting...' : isRegister ? 'Create account' : 'Sign in'}<ArrowRight size={16} /></button>
        </form>
        <div className="auth-switch">{isRegister ? 'Already have an account?' : 'Need an account?'} <button type="button" onClick={switchMode}>{isRegister ? 'Sign in' : 'Register'}</button></div>
        <div className="demo-login-section"><span>Quick demo access</span><div className="demo-login-grid">{demoUsers.map((demoUser) => <button key={demoUser.id} onClick={() => onDemoLogin(demoUser)}>Demo {demoUser.role}</button>)}</div></div>
        <span className={`auth-backend-status ${backendStatus}`}><i />{backendStatus === 'checking' ? 'Checking backend...' : backendStatus === 'online' ? 'Backend connected' : 'Backend server is starting on port 8000...'}</span>
        <span className="auth-api-note">Backend accounts require FastAPI. Demo access uses local sample data only.</span>
      </section>
      <div className="auth-foot">ROOTED IN IDEALS <span>·</span> ASCENDING WITH IDEAS</div>
    </main>
  )
}

function App() {
  const [session, setSession] = useState(readStoredSession)
  const user = session?.user || null
  const [activePage, setActivePage] = useState('home')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [portalData, setPortalData] = useState(() => session?.mode === 'demo' ? createDemoPortal(session.user) : null)
  const [dataMode, setDataMode] = useState(() => session?.mode === 'demo' ? 'demo' : 'live')
  const [loading, setLoading] = useState(() => Boolean(session && session.mode !== 'demo'))
  const [loadError, setLoadError] = useState('')
  const [offlineNotice, setOfflineNotice] = useState(() => session?.mode === 'demo' ? 'Demo preview is using sample data. Changes are stored only in this browser session.' : '')
  const [sessionWarning, setSessionWarning] = useState('')
  const [refreshVersion, setRefreshVersion] = useState(0)

  useEffect(() => {
    if (!session?.user?.id || session.mode === 'demo') return undefined
    let cancelled = false
    Promise.all([
      apiRequest('/api/papers?limit=100'),
      apiRequest('/api/posts?limit=100'),
      apiRequest(`/api/library/${encodeURIComponent(session.user.id)}`),
      apiRequest('/api/users?limit=100'),
      apiRequest(`/api/users/${encodeURIComponent(session.user.id)}`),
    ]).then(([paperResponse, postResponse, libraryResponse, peopleResponse, profile]) => {
      if (cancelled) return
      setPortalData({
        papers: (paperResponse.papers || []).map(normalizePaper),
        posts: (postResponse.posts || []).map(normalizePost),
        library: (libraryResponse.items || []).map(normalizePaper),
        people: peopleResponse.users || [],
        peopleTotal: Number(peopleResponse.total || 0),
        profile,
        postsTotal: Number(postResponse.total || 0),
        trends: [],
        analytics: null,
      })
      setDataMode('live')
      setOfflineNotice('')
      setLoadError('')
    }).catch((requestError) => {
      if (!cancelled) {
        const isOffline = requestError instanceof TypeError || requestError.message.includes('Backend URL is not configured')
        if (isOffline) {
          setPortalData(createDemoPortal(session.user))
          setDataMode('offline')
          setOfflineNotice(`Backend server is starting on port 8000 (${requestError.message}). Showing sample data; changes are not saved to the backend.`)
          setLoadError('')
        } else {
          setPortalData(null)
          setLoadError(requestError.message)
        }
      }
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [session, refreshVersion])

  function signOut() {
    window.localStorage.removeItem(USER_STORAGE_KEY)
    setSession(null)
    setPortalData(null)
    setLoading(false)
    setActivePage('home')
    setLoadError('')
    setOfflineNotice('')
    setSessionWarning('')
    setDataMode('live')
  }

  function refreshPortal() {
    if (dataMode !== 'live') {
      setPortalData(createDemoPortal(user))
      return
    }
    setLoading(true)
    setLoadError('')
    setRefreshVersion((version) => version + 1)
  }

  function onAuthenticated(authenticatedUser, mode = 'api') {
    const activeSession = {
      user: {
        id: authenticatedUser.id,
        name: authenticatedUser.name,
        email: authenticatedUser.email,
        role: authenticatedUser.role || 'student',
        department: authenticatedUser.department || '',
        interests: authenticatedUser.interests || [],
      },
      mode,
    }
    if (!persistSession(activeSession.user, mode)) {
      setSessionWarning('This browser could not save your session. You may need to sign in again after reloading.')
    } else {
      setSessionWarning('')
    }
    setSession(activeSession)
    setLoadError('')
    setDataMode(mode === 'demo' ? 'demo' : 'live')
    setOfflineNotice(mode === 'demo' ? 'Demo preview is using sample data. Changes are stored only in this browser session.' : '')
    setPortalData(mode === 'demo' ? createDemoPortal(activeSession.user) : null)
    setLoading(mode !== 'demo')
    setActivePage('home')
  }

  function onDemoLogin(demoUser) {
    onAuthenticated(demoUser, 'demo')
  }

  async function savePaper(paperId, { notes = '', collectionName = 'General' } = {}) {
    if (dataMode === 'live') {
      await apiRequest('/api/library/save', {
        method: 'POST',
        body: JSON.stringify({ user_id: user.id, paper_id: paperId, notes, collection_name: collectionName }),
      })
      refreshPortal()
      return
    }
    setPortalData((current) => {
      const paper = current.papers.find((item) => item.id === paperId)
      if (!paper) return current
      const entry = { ...paper, paper_id: paperId, collectionName, collection_name: collectionName, notes }
      const remaining = current.library.filter((item) => !(item.id === paperId && item.collectionName === collectionName))
      return { ...current, library: [entry, ...remaining] }
    })
  }

  async function createPost(title, content, tags) {
    if (dataMode === 'live') {
      await apiRequest('/api/posts', {
        method: 'POST',
        body: JSON.stringify({ user_id: user.id, title, content, tags }),
      })
      refreshPortal()
      return
    }
    const newPost = {
      id: `demo-post-${Date.now()}`,
      author: user.name,
      department: user.department,
      initials: initialsFor(user.name),
      time: 'Just now',
      title,
      body: content,
      tags,
      comments: [],
      commentCount: 0,
    }
    setPortalData((current) => ({ ...current, posts: [newPost, ...current.posts], postsTotal: current.postsTotal + 1 }))
  }

  async function addComment(postId, content) {
    if (dataMode === 'live') {
      await apiRequest(`/api/posts/${encodeURIComponent(postId)}/comment`, {
        method: 'POST',
        body: JSON.stringify({ user_id: user.id, content }),
      })
      refreshPortal()
      return
    }
    setPortalData((current) => ({
      ...current,
      posts: current.posts.map((post) => post.id !== postId ? post : {
        ...post,
        comments: [...post.comments, { id: `demo-comment-${Date.now()}`, author_name: user.name, content }],
        commentCount: post.commentCount + 1,
      }),
    }))
  }

  function renderPage() {
    if (!portalData) return null
    if (activePage === 'feed') return <FeedPage posts={portalData.posts} onCreatePost={createPost} onAddComment={addComment} />
    if (activePage === 'search') return <SearchPage papers={portalData.papers} library={portalData.library} people={portalData.people} posts={portalData.posts} dataMode={dataMode} onSave={savePaper} onAddComment={addComment} />
    if (activePage === 'library') return <LibraryPage library={portalData.library} onNavigate={setActivePage} onSave={savePaper} />
    if (activePage === 'assistant') return <AssistantPage papers={portalData.papers} />
    if (activePage === 'analytics') return <AnalyticsPage dataMode={dataMode} analytics={portalData.analytics || createDemoPortal(user).analytics} />
    if (activePage === 'profile') return <ProfilePage profile={portalData.profile} libraryCount={portalData.library.length} postCount={portalData.postsTotal} />
    return <HomePage user={user} papers={portalData.papers} posts={portalData.posts} library={portalData.library} peopleTotal={portalData.peopleTotal} trends={portalData.trends || []} dataMode={dataMode} onNavigate={setActivePage} onSave={savePaper} onAddComment={addComment} />
  }

  if (!user) return <AuthPage onAuthenticated={(authenticatedUser) => onAuthenticated(authenticatedUser, 'api')} onDemoLogin={onDemoLogin} />

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} onNavigate={setActivePage} onSignOut={signOut} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} user={user} />
      <main className="main-panel">
        <Topbar title={pageTitles[activePage]} onNavigate={setActivePage} onOpenMenu={() => setMobileOpen(true)} user={user} />
        <div className="page-wrap">
          {offlineNotice && <div className="offline-banner" role="status"><span className="service-unavailable-icon"><Activity size={17} /></span><div><strong>{dataMode === 'demo' ? 'Demo login' : 'Backend server is starting on port 8000...'}</strong><p>{offlineNotice}</p></div></div>}
          {sessionWarning && <p className="form-error session-warning" role="status">{sessionWarning}</p>}
          {loading && <div className="page-loading" role="status">Loading your account data from Research Commons...</div>}
          {!loading && loadError && <div className="connection-error" role="alert"><h2>Could not load your account data</h2><p>{loadError}</p><button className="button button-primary" onClick={refreshPortal}>Retry</button><button className="button button-outline" onClick={signOut}>Sign out</button></div>}
          {!loading && !loadError && <Suspense fallback={<div className="page-loading">Loading page...</div>}>{renderPage()}</Suspense>}
        </div>
        <footer className="app-footer"><span>Research Commons <span className="footer-dot">·</span> Chanakya University</span><span>Rooted in ideals. Ascending with ideas.</span></footer>
      </main>
    </div>
  )
}

export default App
