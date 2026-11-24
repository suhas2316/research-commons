# Frontend Module

## Module Overview
This folder contains the client-facing user interface for **Research Commons**.

- **Assigned Team Member:** Poorna
- **Primary Tech Stack:** React, Vite, Tailwind CSS, Recharts

---

## Planned Responsibilities & Features
1. **User Authentication & Profiles:**
   - Registration, login, and user profile views.
   - Department and research interest selection.
2. **Community & Discussions:**
   - Feed and posts display.
   - Commenting and following authors/topics.
3. **Research Library:**
   - Paper collections, bookmarking/saving papers, and private notes.
4. **Search UI:**
   - Unified search interface covering papers, library items, authors, and posts.
5. **Research Assistant UI:**
   - Interactive chat interface displaying grounded answers with citation sources.
6. **Analytics Dashboard:**
   - Admin metrics and charts (using Recharts) for trending topics, activity by department, and collaboration.

---

## Getting Started (Planned)
When starting development:
1. Initialize the project using Vite:
   ```bash
   npm create vite@latest . -- --template react
   ```
2. Install Tailwind CSS and component dependencies.
3. Keep reusable UI components (buttons, modals, navbar, cards) inside a `src/components/` folder.
4. Connect frontend pages to the FastAPI backend API endpoints.
