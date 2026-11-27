const papers = [
  {
    id: 'demo-paper-1',
    title: 'Human-centered artificial intelligence for public good',
    authors: 'A. Nair, R. Menon, and S. Iyer',
    year: 2025,
    journal: 'Journal of Responsible Technology',
    abstract: 'A multidisciplinary framework for evaluating how AI systems can support inclusive and accountable public services.',
    tags: ['Artificial intelligence', 'Public policy'],
    citations: 42,
  },
  {
    id: 'demo-paper-2',
    title: 'Climate resilience and community-led water governance',
    authors: 'M. Rao and L. Fernandez',
    year: 2024,
    journal: 'Sustainability Science',
    abstract: 'This study examines local knowledge, institutional coordination, and community participation in water resilience planning.',
    tags: ['Sustainability', 'Governance'],
    citations: 31,
  },
  {
    id: 'demo-paper-3',
    title: 'Language technologies for preserving oral histories',
    authors: 'P. Kulkarni, N. Das, and J. Thomas',
    year: 2025,
    journal: 'Digital Scholarship in the Humanities',
    abstract: 'Ethical workflows for documenting, transcribing, and preserving multilingual oral history collections.',
    tags: ['Digital humanities', 'Language'],
    citations: 18,
  },
  {
    id: 'demo-paper-4',
    title: 'Open research networks across emerging economies',
    authors: 'S. Banerjee and K. Joseph',
    year: 2023,
    journal: 'Research Policy',
    abstract: 'A network analysis of cross-institutional research partnerships and open knowledge exchange.',
    tags: ['Research policy', 'Networks'],
    citations: 67,
  },
]

const people = [
  { id: 'demo-person-1', name: 'Dr. Ananya Nair', role: 'faculty', department: 'School of Engineering', email: 'ananya.demo@example.edu', interests: ['Responsible AI', 'Public policy'] },
  { id: 'demo-person-2', name: 'Rohan Menon', role: 'researcher', department: 'School of Management Sciences', email: 'rohan.demo@example.edu', interests: ['Sustainability', 'Governance'] },
  { id: 'demo-person-3', name: 'Dr. Kavya Rao', role: 'faculty', department: 'School of Arts, Humanities and Social Sciences', email: 'kavya.demo@example.edu', interests: ['Digital humanities', 'Language'] },
]

const posts = [
  {
    id: 'demo-post-1',
    author: 'Dr. Ananya Nair',
    department: 'School of Engineering',
    initials: 'AN',
    time: '2 hours ago',
    title: 'What does responsible AI look like in a university setting?',
    body: 'We have been mapping practical ways to bring transparency and human oversight into research workflows. What frameworks are other teams using?',
    tags: ['Responsible AI', 'Research methods'],
    comments: [{ id: 'demo-comment-1', author_name: 'Rohan Menon', content: 'We are comparing a few governance approaches this semester.' }],
    commentCount: 1,
  },
  {
    id: 'demo-post-2',
    author: 'Rohan Menon',
    department: 'School of Management Sciences',
    initials: 'RM',
    time: 'Yesterday',
    title: 'Reading list: community-led climate resilience',
    body: 'Our group is collecting case studies on local water governance. Happy to compare notes with anyone working in this area.',
    tags: ['Sustainability', 'Fieldwork'],
    comments: [],
    commentCount: 0,
  },
]

const library = [
  { ...papers[1], paper_id: papers[1].id, collectionName: 'Sustainability', collection_name: 'Sustainability', notes: 'Compare the community participation section with our field notes.' },
  { ...papers[0], paper_id: papers[0].id, collectionName: 'Responsible AI', collection_name: 'Responsible AI', notes: 'Review the evaluation framework before seminar.' },
]

const trends = [
  { name: 'Responsible AI', growth: '+24%', tone: 'rose', papers: 25 },
  { name: 'Water governance', growth: '+18%', tone: 'blue', papers: 19 },
  { name: 'Digital humanities', growth: '+12%', tone: 'green', papers: 13 },
]

const analytics = {
  monthlyActivity: [
    { month: 'Jun', papers: 24, searches: 12 },
    { month: 'Jul', papers: 31, searches: 18 },
    { month: 'Aug', papers: 28, searches: 21 },
    { month: 'Sep', papers: 43, searches: 26 },
    { month: 'Oct', papers: 38, searches: 31 },
    { month: 'Nov', papers: 52, searches: 37 },
  ],
  departmentActivity: [
    { name: 'Engineering', activity: 123, share: 34 },
    { name: 'Arts & Humanities', activity: 94, share: 26 },
    { name: 'Management', activity: 79, share: 22 },
    { name: 'Biosciences', activity: 65, share: 18 },
  ],
  collaborations: [
    { name: 'Engineering + Humanities', value: 38 },
    { name: 'Management + Biosciences', value: 27 },
    { name: 'Engineering + Management', value: 22 },
    { name: 'Other partnerships', value: 13 },
  ],
}

export function createDemoPortal(user) {
  return {
    papers: structuredClone(papers),
    posts: structuredClone(posts),
    library: structuredClone(library),
    paperComments: {},
    people: structuredClone(people),
    peopleTotal: 1284,
    postsTotal: posts.length,
    profile: { ...user, bio: 'Research interests, questions, and collaborations.' },
    trends: structuredClone(trends),
    analytics: structuredClone(analytics),
  }
}

export const demoUsers = [
  { id: 'demo-student', name: 'Poorna Chandra', email: 'poorna.demo@chanakyauniversity.edu.in', role: 'student', department: 'School of Engineering' },
  { id: 'demo-faculty', name: 'Dr. Ananya Nair', email: 'ananya.demo@chanakyauniversity.edu.in', role: 'faculty', department: 'School of Engineering' },
  { id: 'demo-researcher', name: 'Rohan Menon', email: 'rohan.demo@chanakyauniversity.edu.in', role: 'researcher', department: 'School of Management Sciences' },
  { id: 'demo-admin', name: 'Research Administrator', email: 'admin.demo@chanakyauniversity.edu.in', role: 'admin', department: 'University Administration' },
]
