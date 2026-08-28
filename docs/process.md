# Section 1 — Chosen Process and Its Position on the Spectrum

### (a) The Model — Explicit Hybrid (Incremental Core with Prototyping Flavor)
We do not follow pure Waterfall or pure Spiral. Instead, we adopt an iterative, feature-sliced incremental strategy where each sprint produces a working, testable, and potentially deployable slice of the Mini-LMS. We explicitly embed rapid prototyping within first 24-48 hours of each sprint to clarify UI/UX requirements before coding begins.  
#### **How One Cycle (Sprint) Actually Runs — Order, Roles, and Outputs:**

| Phase | Timeline | Who Does What | Order & Activities | Output at End of Phase |
| :--- | :--- | :--- | :--- | :--- |
| **1. Sprint Planning** | Days 1-2 | **Entire Team** | We review the product backlog, prioritize the highest-value features for the upcoming sprint, and break down user stories into tasks. Roles are dynamically assigned per sprint based on task load (we rotate or flex, but generally: **Member A** = Backend/API; **Member B** = Frontend/UI; **Member C** = Database & Grading Logic; **Member D** = Testing & Statistics). | A signed-off Sprint Backlog with clear acceptance criteria. |
| **2. Rapid Prototyping (UI/UX)** | Days 2–3 | **Member B (Frontend/UI) + Team review** | Before touching production code, we sketch low-fidelity mockups of the new UI components. For example, before building the "difficulty analysis" dashboard, we draw a quick wireframe to get customer approval. | Approved UI wireframes. |
| **3. Development & Integration** | Days 3–13 | **Entire team (parallel work)** | We develop in parallel using feature branches. Member C finalizes the database migrations (if any). Member A builds the APIs. Member B implements the frontend components. Member D writes unit tests and integration tests for the grading engine. We integrate continuously (daily merges) to avoid "integration hell." | Fully coded and unit-tested features for the sprint. |
| **4. Sprint Review & Validation** | Day 14 | **Team presents to Instructor** | We deploy the working increment to a staging server. The instructor actively tests the new features (e.g., creates a quiz, takes it, views stats). We collect feedback on what works and what needs tweaking. | **Working, validated software increment** + documented instructor feedback. |
| **5. Retrospective & Backlog Refinement** | Day 14 | **Entire Team** | We discuss what went well, what went wrong, and adjust our process for the next sprint. We refine the product backlog for Sprint N+1 based on the instructor's feedback. | Updated backlog and improved team workflow. |

### (b) The Position — Explicit Spectrum Placement

**Position:** **80% Agile (Iterative/Adaptive) with 20% Plan-Driven (Frozen Milestones & Infrastructure).** 
We are **not** "fully agile" because we deliberately freeze certain high-risk, foundational components to prevent architectural collapse. We are **not** "fully plan-driven" because we actively welcome changes to features, UI, and analytics formulas every 2 weeks.

#### **Justification (What runs at which rhythm):**
| Rhythm | Aspect | Decision/Component | Status |
| :--- | :--- | :--- | :--- |
| **Frozen for the ENTIRE semester (Plan-Driven 20%)** | **Database Schema** | Tables for core data models. These are defined in Sprint 0 and never structurally altered (to avoid costly data migrations). | **Frozen** |
| | **Core Grading Engine Rules** | The fundamental logic for grading: MCQ = exact string matching; Short Answer = case-insensitive substring/keyword matching. This is finalized before coding starts to ensure backend stability. | **Frozen** |
| | **Tech Stack** | E.g. Python, PostgreSQL, Streamlit - chosen upfront to avoid mid-term switching costs. | **Frozen** |
| | **Major Milestones** | The 5 sprints act as fixed *plan-driven* gates for the instructor to evaluate progress (no skipping sprints). | **Frozen (Dates)** |
| **Re-opened EVERY 2-week Sprint (Agile 80%)** | **UI/UX Layout & Styling** | Colors, button placements, dashboard widget arrangements, and navigation flows are entirely flexible and changed based on instructor feedback each sprint. | **Flexible** |
| | **Anti-Cheating Strategy** | We start with simple question randomization in Sprint 4, but if feedback suggests we need copy-paste blocking or IP tracking, we can pivot and add it in Sprint 5. | **Flexible** |
| | **Additional Services** | Queries, email notifications, CSV export features — these can be re-prioritized, added, or removed from the backlog if deemed "truly vital" during sprint planning. | **Flexible** |
  
The database, grading engine, and tech stack are "frozen" for the whole semester (Plan-Driven). All feature implementations, UI designs, analytics algorithms, and security tactics are "re-opened" and reprioritized every single sprint (Agile).

# Section 2 — The Five Diagnostic Questions

### **1. Are your requirements stable or volatile? What evidence do we have?**

Our requirements are a mix, but deliberately managed: the core data structure and grading mechanics are stable, while the *user-facing features and analytics* are volatile. We have concrete evidence: we intentionally froze the database schema and the fundamental grading rules before Sprint 1 to prevent costly re-architecture. However, our sprint backlog shows we re-prioritize UI layouts, anti-cheating tactics and other services such as notifications or data exporter. every two weeks based on instructor feedback. Since we have no prior experience building an LMS, we fully expect the instructor to request substantial UI and reporting changes after each demo—confirming that the surface-level requirements are volatile, even if the backend foundation is not.

### **2. Does the project carry safety or legal impact that would demand formal documentation and change control?**

Our Mini-LMS carries negligible safety or legally binding financial impact. Unlike healthcare record systems, aviation software, or core banking platforms, a miscalculated quiz grade in our academic project does not endanger lives, violate patient privacy, or incur regulatory fines. Consequently, we do not mandate formal, auditable change-control boards, signed-off requirement documents, or heavyweight traceability matrices. However, we still maintain lightweight, version-controlled documentation (this `process.md` file, API endpoint specs, and a database entity-relationship diagram) purely for team coordination and to help the instructor understand our architecture—not to satisfy external legal audits or safety certifications.

### **3. Is your team large and distributed, or small and co-located? How does that affect communication cost?**

Our team consists of exactly four members, all co-located on the same university campus with overlapping class schedules and physical access to shared lab spaces. This small, tightly coupled structure keeps our communication costs exceptionally low—we can hold impromptu 15-minute stand-up meetings in person, resolve integration conflicts via quick whiteboard sketching, and clarify ambiguous user stories face-to-face without waiting for asynchronous Slack threads. This low communication overhead is precisely what enables our rapid 2-week incremental cycles; we do not waste time writing exhaustive formal specifications for each other, because we can simply talk and demonstrate working code.

### **4. Can your customer (the instructor, plus any real users you consult) engage continuously, or only at fixed checkpoints?**

Our primary customer—the course instructor—engages with us on a predictable, continuous bi-weekly cadence by attending our sprint review meetings at the end of every 2-week cycle to test the working increment and provide direct, actionable feedback on new features (e.g. "add a timer to the quiz interface"). Additionally, the instructor is available via email and in-person office hours between sprints for urgent clarifications on quiz format or grading expectations. We do not rely on external end-users beyond the instructor, so this bi-weekly feedback loop is sufficiently continuous to steer our decisions on UI, anti-cheating, and analytics each sprint.

### **5. What do organizational culture and contract constraints allow? For this course: the four fixed milestones and the final demo date.**

The course imposes a clear plan-driven contractual constraint: four fixed submission milestones plus a mandatory final demo date, which act as hard, non-negotiable gates for formal evaluation. To satisfy this, we align our 5 sprints within these organizational boundaries and ensure that our repository is publicly accessible (or explicitly shared with the instructor as a collaborator) prior to every submission, as required by the course policy. This hybrid arrangement forces us to maintain a stable, demonstrably working product at each fixed milestone, yet still allows us to iteratively refine and reprioritize features between these gates. In short, the culture of this course allows agile iteration but contractually demands plan-driven progress visibility—so we embrace both.

# Section 3 — Critical Thinking: Risks of the Opposite Choice

The opposite choice (fully plan-driven) would be catastrophic for our Mini-LMS. The single biggest risk is "late-stage requirements discovery failure" — the known waterfall problem where customers only realize what they truly need after seeing working software, but the plan has already frozen everything.

### **Mechanism of damage:** 
In a fully plan-driven approach, we would be forced to commit to a complete, detailed specification of the entire Mini-LMS in Week 1 — including exact UI layouts, all analytics formulas, and the full anti-cheating feature set — before writing any code. Our instructor (customer) would approve this specification, but without ever having seen an interactive prototype. We would then spend 8–10 weeks building the entire system against that frozen specification, delaying integration testing until the very end. Because the instructor only forms accurate opinions after interacting with real software, the first time they actually use the complete system (likely at our first major milestone or mid-semester demo), they would inevitably say: *"The statistics dashboard is confusing — I wanted a bar chart per question, not a line graph,"* or *"I didn't realize I needed a 'time limit' option until now — please add it,"* or *"The short-answer grading is too strict — allow synonyms for common variations."* 

In a fully plan-driven process, these are requirements changes, not adjustments. Each change would trigger a formal change-control procedure, requiring us to revise the specification, re-estimate, and re-code large portions of the backend, frontend, and grading engine — all of which were tightly coupled to the original frozen spec. Since we have already built the entire system around the initial assumptions, fixing these late-discovered mismatches would require expensive re-architecture, extensive regression testing, and likely delay the final deliverable beyond the semester's fixed demo date.

### **Concrete symptom we would observe first:**
The first symptom would appear at the first milestone demo when the instructor tests the full or near-full system for the first time. Instead of offering minor tweaks (e.g. "change this button color"), the instructor would provide structurally contradictory feedback that invalidates core UI workflows or data presentation choices — for example, saying, *"This score distribution view is completely unusable; I need it grouped by question type, not by student."* At that moment, we would realize that we built the *wrong* dashboard, and because our plan had frozen all UI and service logic upfront, fixing it would require tearing down and rewriting thousands of lines of code — a cost we could have avoided entirely with our actual bi-weekly incremental demos.


# Section 4 — Process Rules Our Team Commits to
### **Rule 1 — Pull Request & Code Review Mandate**  
Every commit merged into the `main` branch must be submitted via a Pull Request (PR) and approved by at least one team member other than the author. The approving reviewer must explicitly comment that the PR passes all existing automated tests and does not break the frozen database schema or grading API endpoints. This is verifiable through GitHub's PR approval history and comment threads.

### **Rule 2 — Fixed Sprint Cadence and Backlog Refinement**  
Our sprint length is fixed at two calendar weeks, starting every Monday at 9:30 AM and ending on the following Friday at 6:30 PM. The product backlog is re-prioritized and frozen for that sprint during a mandatory planning meeting held on the first Monday of each sprint (before any new coding begins). The finalized Sprint Backlog (with assigned user stories and task owners) must be committed to the repository by the end of that Monday. This is checkable via file timestamps and meeting notes.

### **Rule 3 — Frozen Component Change Protocol (Unanimous Vote)**  
Any proposed change to the frozen components — specifically, the database schema (tables, columns, relationships) or the core automated grading logic (score calculation for MCQ/short-answer) — requires a 4/4 unanimous team vote. The proposal, the rationale, and the vote outcome must be documented before any related code is pushed to `main`. This prevents unilateral architectural drift and is verifiable via the justification file and commit order.

### **Rule 4 — Definition of Done for Every Sprint Story**  
A user story is considered "done" and ready for the sprint review only when all three of the following are met:  
(a) It passes all newly added and existing regression tests (verified by GitHub Actions CI log).
(b) The instructor has manually tested and accepted the feature during the formal sprint review meeting.  
(c) All relevant API endpoints have inline docstrings or OpenAPI annotations updated in the codebase. This is checkable by reviewing the CI status, meeting notes, and code documentation diff for that story.
