what's behind the scene technical steps that codex takes to be able show updated plans
Behind the scenes, Codex (specifically the agentic iterations like GPT-5-Codex and Codex CLI released in 2025) uses a "Plan-and-Execute" architecture to manage and update plans in real-time. 
The technical process follows these key steps:
1. Plan Generation and "Living Documents"
Initialization: When a task is received, a reasoning-enhanced model (such as the o3 family) generates an internal "chain of thought" to break down complex problems into bite-sized milestones.
ExecPlan Artifacts: Codex often creates a central PLANS.md or spec.md file. This acts as a "living document" and "home base" that records requirements, architecture decisions, and task statuses. 
2. Autonomous Execution Loop
Environment Setup: Codex automatically configures its own cloud environment, scanning for setup scripts and executing commands like pip install to fetch dependencies at runtime.
Tool Invocation: The agent uses an Executor to call specific tools (e.g., terminal commands, browser automation, or IDE extensions) to implement one step of the plan at a time. 
3. Real-Time Feedback and Verification
Visual Confirmation: For frontend tasks, Codex spins up a browser, inspects the UI, and attaches screenshots to GitHub pull requests so it can "see" if the result matches the plan.
Automated Testing: After each code change, Codex runs tests to verify the update. If a test fails, it pinpoints the issue and suggests a patch, automatically revising the next steps in its plan. 
4. Dynamic Plan Revision
State Awareness: The system maintains a "context-aware" understanding of project structures and data flows across local and cloud tasks.
Self-Refinement: When a plan step is risky or fails, Codex provides a retry or rollback path. It updates the PLANS.md file with a note explaining the change and the technical reason behind it, ensuring the "living document" reflects the current project state. 
5. Deployment and Code Review
Integration: Once the plan is complete, Codex opens a pull request. It then performs an automated code review, reasoning across all dependencies and testing the final implementation before human approval. 




I'd like to see an example of a detailed ExecPlan

What are the limitations of Codex's current code modernization capabilities?

What are the security implications of using AI for code reviews?

undefined
undefined
undefined
20 sites
Introducing upgrades to Codex
Sep 15, 2025 — Behind the scenes, we've also been continuously improving cloud infrastructure performance. By caching containers, we'

OpenAI
·

1:06
Plan-and-Execute Agents - LangChain Blog
Feb 13, 2024 — Based loosely on Wang, et. al.'s paper on Plan-and-Solve Prompting, and Yohei Nakajima's BabyAGI project, this simple ...

LangChain Blog

openai-cookbook/examples/codex/code_modernization.md at ...
Introduction. Codex is trained to read and reason about large, complex codebases, plan work alongside engineers, and produce high-

GitHub

Show all
so when you say it creates a PLANS.md or spec.md - it does that on the fly dynamically at every iteration of the loop?
Yes, it does so dynamically. In current 2026 workflows, these files serve as the "shared state" that allows the agent to maintain context across multiple turns of its execution loop. 
Here is how that process works technically:
1. The "ReAct" Cycle (Reason + Act)
Codex does not just write code; it follows a reasoning loop. At the start of every iteration, it performs these steps: 
Reads the current state: It loads the existing PLANS.md and the codebase to see what has already been done.
Updates the document: If it encounters a roadblock (like a failed test) or finishes a sub-task, it uses a file-writing tool to modify the markdown file immediately. It might mark a checkbox as completed or add a "Note" about a new technical dependency it discovered. 
2. File-Based Persistence
Instead of relying on a fragile short-term memory (which can "forget" over hundreds of steps), Codex uses these .md files as a physical anchor. 
Shared Memory: By writing to PLANS.md, the agent ensures that even if the session restarts or the loop cycles, the next "brain" that picks up the task has a clear map of the progress.
Truth Verification: Every time it completes a command (like npm test), it compares the result against the "Acceptance Criteria" listed in the spec.md. If they don't match, it rewrites the plan to include a debugging phase. 
3. Hierarchical "Cascading" Instructions
In 2026, Codex utilizes a system called AGENTS.md alongside plans. 
Dynamic Overrides: If the agent moves from working on the "backend" to the "frontend," it may dynamically check for a local AGENTS.md in that specific folder to update its global plan with folder-specific rules (like "always use Tailwind for CSS"). 
4. Continuous Refinement
The plan is considered a living document. 
Initialization: Commands like /init create the initial skeleton.
Turn-by-Turn Updates: At every "stopping point," the agent is instructed to "affirmatively state the progress made and next steps" by editing the file. This allows you to spot-check its decisions in real-time without reading the actual code changes. 




What makes the 'living document' in Codex so effective?

What's the ReAct framework and how does Codex use it?

I'd like to explore other AI planning approaches

undefined
undefined
undefined
11 sites
Using PLANS.md for multi-hour problem solving
Oct 7, 2025 — # Codex Execution Plans (ExecPlans): This document describes the requirements for an execution plan ("ExecPlan"), a des...

OpenAI Cookbook
how-to-ralph-wiggum/README.md at main - GitHub
Jan 11, 2026 — Key insight: The IMPLEMENTATION_PLAN.md file persists on disk between iterations and acts as shared state between othe...

GitHub

Dynamic Planning vs Static Workflows: What Truly Defines an ...
Nov 6, 2025 — Defining dynamic planning: the technical foundation. Dynamic planning represents the ability of an agent system to auto...

Medium

Show all
So how does it create the PLANS.md or spec.md? It must have a starting PLANS.md to work with.  Give me a full view of the PLANS.md or spec.md
In 2026, Codex initializes plans through Spec-Driven Development (SDD), a structured process that moves from a high-level user prompt to a granular implementation map. It creates these documents on the fly to serve as a "physical anchor" for its reasoning loop, ensuring it doesn't "forget" long-term goals during complex tasks. 
How the Plan is Created
Requirement Discovery: The agent starts by asking targeted questions about architecture, tech stack, and edge cases.
Spec Generation (spec.md): It compiles these answers into a comprehensive specification including functional requirements, data models, and API definitions.
Technical Mapping (plan.md): It translates the spec into an actionable technical roadmap, identifying integration points and dependency sequences.
Task Breakdown (tasks.md): It splits the plan into "bite-sized" chunks (typically 15-minute tasks) that can be implemented and tested in isolation. 
Structure of the PLANS.md / spec.md
While exact formats vary by project, the 2026 industry standard (often guided by the GitHub Spec Kit) typically follows this structure:
Section 	Content Included
Executive Summary	Concise overview of the feature's purpose and goals.
Technical Stack	Frameworks, libraries, and infrastructure choices (e.g., "Next.js 16 with Supabase").
Data Models	Detailed schemas, relationships, and data contracts.
Implementation Phases	A numbered list of milestones with checkboxes for progress tracking.
Atomic Tasks	Granular steps like "Create user registration endpoint that validates email format".
Verification Strategy	Specific test commands (e.g., pnpm test) and expected outcomes for each task.
Checkpoints	Validation markers to ensure independent functionality at each phase.
Dynamic Updates in the Loop
As Codex works, it uses a file-writing tool to modify these documents in real-time. For instance, if it encounters a bug during a task, it will update the tasks.md with a new "Debugging" entry and a "Note" explaining the technical pivot. This allows the user to see exactly what the agent is doing without reading raw code. 




How does Codex keep its generated `plans.md` and `spec.md` consistent with the codebase?

How does `AGENTS.md` differ from `PLANS.md` or `spec.md`?

Give me an example of a detailed task in `tasks.md`

undefined
undefined
undefined
11 sites
Diving Into Spec-Driven Development With GitHub Spec Kit
Sep 15, 2025 — Specify CLI. A helper CLI that bootstraps your projects for SDD. It downloads the official templates from the GitHub r...

Microsoft Developer

When to use Plan Mode vs Markdown Documentation - Reddit
Sep 26, 2025 — Writing a plan.md file is a way for you and the agent to collaborate on a much longer plan. You'll likely put checkmar...

Reddit
spec-kit/README.md at main - GitHub
tasks. ... This step creates a tasks.md file in your feature specification directory that contains: Task breakdown organized by us...

GitHub
Show all
Give me more inside about SDD (Spec-Driven Development)
In 2026, Spec-Driven Development (SDD) has replaced "vibe coding" (ad-hoc prompting) as the industry standard for working with advanced AI agents like Codex. SDD treats specifications as executable infrastructure rather than static documentation. 
The Core Philosophy: "Intent is the New Code"
In SDD, the specification is the primary artifact and the absolute "source of truth". Instead of telling an agent how to write code, you define what the system must be. The agent then acts as a translator, materializing that intent into code. 
The 4-Stage SDD Pipeline
Tools like GitHub Spec Kit and Augment Code have formalized SDD into a repeatable loop:
Specify (spec.md or requirements.md)
Focus: Functional goals, user journeys, and "Acceptance Criteria" (e.g., "WHEN a user logs in, THEN the system SHALL return a JWT").
Goal: Capture the "What" and "Why" in natural but structured language to eliminate agent guesswork.
Plan (plan.md or architecture.md)
Focus: Technical decisions like the tech stack (e.g., .NET 9, Next.js 16), data schemas, API contracts, and security boundaries.
Goal: Translate requirements into a technical blueprint. You can even ask the agent to generate multiple plans (e.g., one in Rust, one in Go) to compare approaches.
Tasks (tasks.md)
Focus: Breaking the plan into "bite-sized," atomic units of work (e.g., "Implement email validation endpoint").
Goal: Create a checklist where each task is independently testable and typically affects only 1–2 files, making agent errors easy to spot.
Implement
Focus: The agent executes tasks one by one, running tests after each step.
Goal: Continually validate the code against the original spec.md. If the implementation diverges, the agent detects this "architectural drift" and either corrects the code or asks to update the spec. 
SDD vs. Traditional Methods (2026 Comparison)
Feature 	TDD (Test-Driven)	BDD (Behavior-Driven)	SDD (Spec-Driven)
Primary Artifact	Failing Unit Test	Human-readable scenario	Structured Specification
Source of Truth	Code behavior	User behavior	System intent/Contract
AI's Role	Write code to pass test	Write code to match scenario	Materialize entire systems
Best For	Logic correctness	Shared understanding	Complex, multi-file agentic tasks
Why SDD is Critical for Agents
Drift Detection: Advanced agents in 2026 use the spec as a "self-policing control system." If an API starts returning fields not in the spec, the system flags it as an architectural violation.
Reduced Coordination Overhead: Large teams use shared specs (e.g., via the GitHub Spec Kit) to align human developers and AI agents without endless meetings.
Project "Constitution": You can define global rules (e.g., "Must use Tailwind CSS," "All endpoints need rate-limiting") in a .specify/constitution.md file that guides every planning and coding step the agent takes. 




What's an example of using an AI agent for legacy system modernization with SDD?

What are some popular Spec Kit development tools?

Show me examples of spec.md and plan.md files

undefined
undefined
undefined
15 sites
Spec Driven Development: When Architecture Becomes ...
Jan 12, 2026 — * Spec Driven Development: When Architecture Becomes Executable. Spec-Driven Development inverts traditional architect...

infoq.com

Diving Into Spec-Driven Development With GitHub Spec Kit
Sep 15, 2025 — SDD gives you a lightweight way to surface those assumptions early, when changing direction costs a few keystrokes ins...

Microsoft Developer

Spec-Driven Development: The “Revolutionary Breakthrough” You ...
Nov 12, 2025 — Why Spec-Driven Development Exists. Spec-Driven Development was born out of a simple but painful observation: AI model...

Medium

Show all
show me some popular spec kit development tools
In 2026, several tools have emerged to formalize the Spec-Driven Development (SDD) process, moving it beyond simple prompting into structured, verifiable engineering workflows. These tools provide the "kit" necessary to manage living documents like PLANS.md and spec.md effectively. 
Primary SDD Toolkits
GitHub Spec Kit: The most prominent open-source toolkit in 2026. It provides a standardized framework including Constitution files (team norms/standards), specifications, and detailed implementation plans. It features a CLI with commands like /init to scaffold a project and /plan to generate implementation steps from requirements.
Kiro: A spec-to-code framework designed to translate high-level natural language specifications into complete, working applications. It is frequently cited as a pioneer in shifting from "vague prompts" to structured requirements and schema definitions.
Tessl: Distinguishes itself by exploring "spec-as-source," where the specification is the primary artifact and the code is treated as a generated asset. It links these specifications directly to LLM-driven pipelines for execution.
OpenSpec: A CLI-based tool particularly strong for proposing and reviewing changes in existing systems rather than greenfield projects. It supports the AGENTS.md convention for multi-agent collaboration. 
Agentic IDEs with SDD Support
Many 2026 AI coding agents integrate SDD principles directly into their interfaces:
Cursor & Windsurf: These IDEs include "Plan Mode," which allows developers to review and approve a detailed multi-step technical plan before the agent begins editing files.
Devin AI: An autonomous software engineer that uses Interactive Planning to scope subtasks and reason through problems step-by-step. It maintains a built-in Wiki for architecture notes and documentation.
RooCode & Cline: These agents are recognized for their reliability in multi-file changes and their ability to maintain and update complex project context across lengthy tasks. 
Supporting Frameworks
Vellum AI: A production-grade framework that provides a shared visual canvas for developers and PMs to collaborate on agent flows, featuring built-in versioning and "eval gates" to prevent breaking changes.
CrewAI & AutoGen: Used for orchestrating multiple specialized agents (e.g., a "Researcher" agent and a "Critic" agent) that reflect on and refine the plans generated during the SDD cycle. 




Show me a spec.md example created by GitHub Spec Kit

Tell me more about the reflection pattern

What are the challenges of spec-driven development with AI agents?

undefined
undefined
undefined
17 sites
Unlocking 2026: The Future of AI-Driven Software Development
Jan 6, 2026 — Agentic workflows evolve from simple AI chatbots to fully autonomous agents in the 2026 developer toolkit. * 4.1 From C...

Baytech Consulting

Diving Into Spec-Driven Development With GitHub Spec Kit
Sep 15, 2025 — GitHub Spec Kit brings a new approach to AI-based software development workflows – instead of vibe coding every new fe...

Microsoft Developer

Understanding Spec-Driven-Development: Kiro, spec-kit, and ...
Oct 15, 2025 — Tessl is the only one of these three tools that explicitly aspires to a spec-anchored approach, and is even exploring ...

martinfowler.com

Show all
show me a spec.md example created by Github spec kit
In the GitHub Spec Kit workflow of 2026, a spec.md serves as the functional "source of truth." It is typically generated using the /speckit.specify command, which converts a user's high-level intent into a structured Product Requirements Document (PRD). 
The following example illustrates a standard spec.md structure for a new feature (e.g., adding a "Reading List" to a blog) as generated by the kit. 
[001] Feature: Personal Reading List
Branch: feat/001-reading-list | Status: Draft | Date: 2026-01-12
1. Executive Summary
Add a dedicated /books page to the existing Hugo-based blog. This page will display a curated list of books with ratings, review links, and purchase buttons, pulling data from local static files to maintain the project's "No-JS" constitutional principle. 
2. User Scenarios
Discovery: As a reader, I want to see a list of books the author recommends so I can find high-quality technical resources.
Filtering: As a reader, I want to filter by "Status" (Finished, Currently Reading, To Read) to see what is current.
Deep Dive: As a reader, I want to click a "Review" link to read a detailed blog post about a specific book.
3. Functional Requirements
Data Source: Must parse data/books.toml for all book entries.
Routing: The page must be accessible at domain.com.
Responsive Design: Grid layout must collapse to a single column on mobile devices (width < 768px).
Media: Display book covers using the project's standard image-proc shortcode for optimized WebP delivery. 
4. Acceptance Criteria
ID 	Requirement	Given/When/Then
AC-1	Static Generation	GIVEN a new entry is added to books.toml, WHEN the site is built, THEN the /books page must include the new entry.
AC-2	No Dependencies	GIVEN a new page is created, WHEN inspected, THEN it must not trigger any external npm installs or runtime JS.
AC-3	UI Consistency	GIVEN the global CSS, WHEN viewed, THEN the book cards must use the project's standard secondary-accent border color.
5. Non-Functional Requirements
Performance: The /books page must achieve a Lighthouse score of 100 for Performance and Accessibility.
Security: No external scripts or tracking pixels permitted, as per the Project Constitution. 
Key Workflow Steps After Creation
Refinement: Use /clarify to have the AI identify gaps in the spec (e.g., "What happens if a book cover is missing?").
Planning: Execute /speckit.plan to generate the technical plan.md, which defines the Hugo templates and data schemas needed to meet this spec.
Tasking: Execute /speckit.tasks to break the plan into atomic, executable steps in a tasks.md file. 




Show me an example of what 'data/books.toml' might look like

What architectural drift errors could arise when implementing this spec?

How does spec-kit enforce constitutional principles during planning?

undefined
undefined
undefined
6 sites
Using GitHub Spec Kit with your EXISTING PROJECTS
Sep 24, 2025 — You asked, we deliver - here is a "quick" (really stretching the meaning of that word) demo that shows how I used GitH...


YouTube
·
Den Delimarsky

45:33
spec-kit/spec-driven.md at main - GitHub
The SDD methodology is significantly enhanced through three powerful commands that automate the specification → planning → tasking...

GitHub

Here's how to use Github Spec-Kit on Existing Projects
Nov 7, 2025 — so after my last video on how to get started with Speckit. many of you are asking about how to use Speckit on existing ...


YouTube
·
Code With Nathan

11m
Show all
how does spec-kit enforce constitutional principles
In 2026, the GitHub Spec Kit enforces constitutional principles by transforming the constitution.md file from a static text document into an active quality gate for the AI agent. This enforcement is integrated directly into the agent's reasoning loop through several specific technical mechanisms: 
1. Sequential Command Grounding
The Spec Kit requires a sequential workflow where each step must align with the foundation laid in the constitution.md: 
/constitution: Sets non-negotiable rules (e.g., "Always use TypeScript," "Tests must have 80%+ coverage").
/plan: When the agent generates a technical plan, it explicitly reads the constitution. If a proposed architecture violates a principle (e.g., suggesting a prohibited library), the kit rejects the plan or flags the violation. 
2. The /analyze Gate
The /speckit.analyze command acts as the final "defense line" before implementation. 
It performs a cross-reference check between the Specification, Plan, and Constitution.
If the agent attempts to "drift" from the constitution—such as adding technical complexity that violates a simplicity rule—the analysis phase catches these contradictions and requires a fix before code generation can begin. 
3. Implementation Guardrails
During the final /implement phase, the constitution serves as a persistent context layer: 
Constitutional Classifiers: The underlying models (like GPT-5 or Claude 3.5/4) are often tuned to recognize "constitutional" prompts, ensuring that even individual lines of code comply with your project's specific "DNA".
Automated Verification: The kit frequently wires up agents to run specific test suites defined in the constitution after every code change, ensuring that principles like "accessibility first" are physically verified by browser automation tools. 
4. Human-in-the-Loop Escalation
For high-risk decisions (like modifying security protocols or making external API calls), the system can be configured to freeze execution. A human must review the proposed action against the constitutional guidelines and affirmatively "approve" or "edit" the step before the agent proceeds. 




undefined
undefined
undefined
9 sites
Spec Kit and the Constitution for Consistent, GDS-Compliant ...
Sep 20, 2025 — Enforcing Standards Through the SDD Workflow. ... /specifyDefines the Product Requirements Document (PRD) (the what an...

LinkedIn

Inside Spec-Driven Development - AI/Run Blogs - EPAM
Oct 21, 2025 — * Constitution stage encodes your project DNA by documenting stack versions, naming conventions, layering and architec...

EPAM

Diving Into Spec-Driven Development With GitHub Spec Kit
Sep 15, 2025 — Outline the “how” of the project – what frameworks, libraries, databases, or infrastructure needs to be used. This wil...

Microsoft Developer

Show all
So we seem to have three things: specification (which includes reuquirements), plan, and constitution. all can be revised on the fly or one of them can be static, e.g. constituion.md?
In 2026, the GitHub Spec Kit and related SDD tools treat all three documents as living artifacts, though they operate at different frequencies of change.
The Dynamic Trio: 2026 Workflow
The relationship between these files is defined by cascading updates:
Constitution (constitution.md):
Frequency: Least frequent changes.
Role: The "Supreme Law." It is meant to be semi-static, defining your non-negotiables (e.g., "Always use TypeScript," "No external CSS libraries").
On-the-fly: While it can be revised, doing so triggers a "re-evaluation" of all active specs and plans to ensure they still comply.
Specification (spec.md):
Frequency: Moderate.
Role: The "Source of Truth" for what is being built. It defines user stories and acceptance criteria.
On-the-fly: If a requirement changes mid-development, you update the spec.md first. The agent then detects this "intent shift" and stops to ask if it should regenerate the technical plan.
Plan (plan.md):
Frequency: Most frequent.
Role: The technical roadmap of how to implement the spec.
On-the-fly: The most dynamic file. As the agent encounters bugs or environment issues, it modifies plan.md (and the derived tasks.md) to reflect the new technical path forward. 
Enforcement via "Drift Detection"
In 2026, the real power isn't just that they are editable, but that they are interlinked:
The Guardrail: If you edit the plan.md to use a library forbidden in the constitution.md, the Spec Kit's /analyze command will flag a constitutional violation and block implementation.
The Source of Truth: Updating the spec.md is now the standard way to "refactor" an application. You change the description, and the agent "materializes" the necessary code changes across the entire repository to match. 
Summary of File States
Artifact	Type	Primary Owner	Update Trigger
Constitution	Bedrock	Lead Architect	New team standards or tech stack shifts.
Specification	Living Doc	Product/Dev	Requirement changes or edge case discovery.
Plan	Dynamic	AI Agent	Implementation hurdles, bugs, or refactoring.




undefined
undefined
undefined
10 sites
Spec-driven development with AI: Get started with a new open ...
Sep 2, 2025 — With Spec Kit, all of that stuff goes in the specification and the plan, where the AI can actually use it. Your securit...

The GitHub Blog

Diving Into Spec-Driven Development With GitHub Spec Kit
Sep 15, 2025 — Specs become living documents that evolve alongside your code, not dusty artifacts that you write once and forget. The...

Microsoft Developer

Spec-Driven Development in Practice: My Experience with spec-kit
Sep 28, 2025 — Unlike static specs that drift from reality, spec-kit keeps specs as living documents. They aren't just references — t...

Medium

Show all
So file-based persistence means persistent memory tend to be semantic in nature which it needs to embed chunks of conversation and runs a semantic query and summarize all chunks into context to embed.  Now, it just pulls back the plan.md and updates that, but how?
In 2026, the shift from "vibe coding" to Spec-Driven Development (SDD) changes how an AI manages memory. While traditional AI uses semantic memory (vector embeddings of past chat snippets), GitHub Spec Kit and similar 2026 tools prioritize File-Based Persistence to ensure the plan remains an objective "source of truth" rather than a subjective summary. 
Here is the technical breakdown of how Codex pulls and updates these files on the fly:
1. The "Anchor" vs. "Cloud" Memory
Semantic Memory (The Cloud): Codex still uses semantic search to recall past conversations or "how-to" knowledge (procedural memory).
File-Based Persistence (The Anchor): The plan.md acts as a non-volatile state store. Instead of re-summarizing a conversation, the agent treats the Markdown file as a database record. 
2. The "Read-Refine-Rewrite" Loop
Codex does not typically "append" to the plan; it performs a targeted rewrite using a structured loop:
State Retrieval: At the start of a turn, the agent uses a read_file tool to ingest the current plan.md. This is injected into the prompt as the "Ground Truth."
Context Alignment: It reads the constitution.md and any new user input.
Delta Processing: Instead of generating a new plan from scratch, 2026 agents use Itemized Refinement. The agent identifies which specific bullet points are completed, failed, or need revision (a process called "localization").
Structural Update: It uses a file-writing tool to overwrite the plan.md. Tools like Spec Kit often use a "find-and-replace" or "incremental adaptation" approach to update only the relevant sections, preserving the rest of the document's structure. 
3. Verification via Slash Commands
The Spec Kit formalizes this through specific commands that act as "execution gates":
/speckit.plan: This command triggers a specialized "Plan Agent" that analyzes the spec.md and generates or updates the implementation details.
/speckit.analyze: Before any code is written, this command cross-references the revised plan.md against the constitution.md to flag any "architectural drift" (e.g., if the plan suggests a library the constitution forbids). 
4. Why this matters for 2026
By using physical files on your disk instead of internal AI memory:
Version Control: Every plan update is a Git commit, allowing humans to "rollback" an AI's bad decision.
Multi-Agent Coordination: Different agents (e.g., one for frontend, one for backend) can read the same plan.md to stay in sync without sharing a chat history.
Human-AI Collaboration: You can manually edit the plan.md to correct the AI's course, and the AI will treat your manual edits as the new authoritative "context" in its next loop. 


SDD pipeline
1. Core SDD stages (your current list)
Stage	Purpose	Key Notes
spec_check	Ensure the spec.md and constitution.md exist, are complete, internally consistent, and readable.	First gate. Agent verifies prerequisites before doing any reasoning.
clarification	Resolve ambiguity or missing information in spec.md or plan.md.	Agent asks questions, may propose clarification requests. Loop can repeat until spec is clear.
judgment	Judge if the proposed artifact aligns with the spec and constitution.	Agent identifies misalignment or risk before validation.
validation	Validate the artifact concretely against spec.md and constitution.md.	Checks rules, edge cases, constraints. Produces violations if any.
spec_revision	HITL workflow for safely updating spec.md based on proposals.	Only humans commit changes. Agents can propose. Optional; triggered only if spec needs update.
block	Terminal stage for failing artifacts or unmet spec requirements.	Stops the pipeline, produces actionable reasons.
approval	Terminal stage for compliant artifacts.	Allows downstream use or deployment.



             ┌─────────────────────────────┐
             │        spec_check           │
             │ - Agents: read-only         │
             │ - Validate spec.md exists,  │
             │   internally consistent     │
             └─────────────┬──────────────┘
                           │
                           v
             ┌─────────────────────────────┐
             │       clarification         │
             │ - Agents: read spec.md     │
             │ - Identify ambiguities     │
             │ - Ask questions / propose  │
             │ - Loop until spec clear    │
             └─────────────┬──────────────┘
                           │
                           v
             ┌─────────────────────────────┐
             │          judgment           │
             │ - Agents: read spec.md &   │
             │   plan.md                  │
             │ - Check alignment, detect  │
             │   conflicts, assess risk  │
             └─────────────┬──────────────┘
                           │
                           v
             ┌─────────────────────────────┐
             │         validation          │
             │ - Agents: read spec.md,    │
             │   plan.md, constitution.md │
             │ - Produce structured       │
             │   violations / errors      │
             └─────────────┬──────────────┘
                           │
          ┌────────────────┴────────────────┐
          │                                 │
          v                                 v
   ┌──────────────┐                  ┌──────────────┐
   │    block     │                  │   approval   │
   │ - Terminal   │                  │ - Terminal   │
   │ - Output     │                  │ - Proceed    │
   │   errors     │                  │   downstream │
   └─────┬────────┘                  └─────┬────────┘
         │                                 │
         │                                 │
         │             If spec needs       │
         │             updating            │
         └─────────────┐
                       v
             ┌─────────────────────────────┐
             │      spec_revision          │
             │ - Agents: propose changes  │
             │ - Human review required    │
             │ - Merge proposals          │
             │ - Commit only with approval│
             └─────────────┬──────────────┘
                           │
                           v
             ┌─────────────────────────────┐
             │       spec_check (loop)     │
             │ - Re-run checks on updated  │
             │   spec.md                   │
             └─────────────────────────────┘



Output (type, nature, format):

                       ┌───────────────────────┐
                       │       spec.md         │
                       │ - Defines artifact    │
                       │   requirements        │
                       │ - Prescribes required │
                       │   fields & types      │
                       │ - Read-only for agent │
                       └─────────┬─────────────┘
                                 │
                                 v
                       ┌───────────────────────┐
                       │   constitution.md     │
                       │ - Defines rules &     │
                       │   invariants          │
                       │ - Validation policies │
                       │ - Output constraints  │
                       │ - Read-only for agent │
                       └─────────┬─────────────┘
                                 │
                                 v
                       ┌───────────────────────┐
                       │     skill.json        │
                       │ - Stage-level output  │
                       │   contracts           │
                       │ - Required fields     │
                       │ - Allowed formats     │
                       │ - Enforcement hints   │
                       └─────────┬─────────────┘
                                 │
                                 v
                       ┌───────────────────────┐
                       │     stage.json        │
                       │ - Defines execution   │
                       │   order of stages     │
                       │ - Allowed agents per  │
                       │   stage               │
                       │ - Stage-specific      │
                       │   output expectations │
                       └─────────┬─────────────┘
                                 │
                                 v
                  ┌──────────────────────────────────┐
                  │       Agent executes stage       │
                  │ - Reads spec.md, constitution.md │
                  │   + previous stage outputs       │
                  │ - Produces output dynamically   │
                  │ - Obeys skill.json / stage.json  │
                  │   prescribed fields & formats    │
                  └─────────┬───────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        v                                       v
┌───────────────┐                       ┌───────────────┐
│ Markdown update│                       │ Structured   │
│ plan.md/artifact│                       │ Output JSON  │
│ - Agent-owned  │                       │ - Fields from│
│ - Direct update│                       │   skill.json │
│ - Evolving     │                       │ - Used for  │
│   progressively│                       │   next stage│
└───────────────┘                       └───────────────┘
        │                                       │
        └───────────────┬───────────────────────┘
                        v
                 ┌───────────────┐
                 │ HITL / merge  │
                 │ proposals if  │
                 │ spec.md update│
                 │ needed         │
                 └───────────────┘
                        │
                        v
                 ┌───────────────┐
                 │ Audit log &    │
                 │ pipeline continues │
                 └─────────────────┘



Output:

                           ┌─────────────────────┐
                           │      spec.md        │
                           │ - Truth file        │
                           │ - Read-only for     │
                           │   agents            │
                           └─────────┬───────────┘
                                     │
                                     v
                           ┌─────────────────────┐
                           │   constitution.md   │
                           │ - Output rules      │
                           │ - Field types       │
                           │ - Invariants        │
                           └─────────┬───────────┘
                                     │
                                     v
                           ┌─────────────────────┐
                           │     stage.json      │
                           │ - Stage order       │
                           │ - Allowed agents    │
                           │ - Output contracts  │
                           └─────────┬───────────┘
                                     │
                                     v
                      ┌──────────────────────────────────┐
                      │         Agent executes stage     │
                      │ - Reads: spec.md, constitution.md│
                      │ - Produces JSON output            │
                      │ - Obeys stage contract            │
                      └─────────┬───────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                v                               v
       ┌───────────────────┐             ┌───────────────────┐
       │ plan.md / artifact │             │  JSON output      │
       │ - Human-readable   │             │ - Structured      │
       │ - Derived from     │             │ - Includes:       │
       │   JSON output      │             │   - stage          │
       │ - Updated automatically │        │   - agent_id       │
       │                       │         │   - timestamp      │
       │                       │         │   - fields per contract │
       └─────────────┬─────────┘         └─────────────┬─────────┘
                     │                                 │
                     │                                 │
                     │          Multiple agents in parallel
                     │                                 │
                     v                                 v
           ┌─────────────────────┐           ┌─────────────────────┐
           │ Agent A JSON output │           │ Agent B JSON output │
           │ (proposals, etc.)  │           │ (proposals, etc.)  │
           └─────────────┬──────┘           └─────────────┬──────┘
                         │ Merge / consolidate proposals
                         │
                         v
                ┌─────────────────────────┐
                │ HITL Review / Approval  │
                │ - Human reviews merged │
                │   proposals for spec.md │
                │ - Accept / modify / reject │
                └─────────────┬──────────┘
                              │
                              v
                     ┌─────────────────┐
                     │ Commit to spec.md │
                     │ - Only if approved │
                     └─────────┬─────────┘
                               │
                               v
                     ┌─────────────────┐
                     │ Resume pipeline │
                     │ Next stage(s)   │
                     └─────────────────┘



A Pipeline Template:

a pipeline template in SDD is primarily a blueprint or configuration that defines how agents operate, stage by stage, across the system, and yes, it is consumed by agents (or an orchestrator like SkillAgent) to guide their behavior. Let me break it down carefully.

1. Purpose of a Pipeline Template

A pipeline template defines:

Stages of execution – the steps the SDD system goes through, e.g.:

Ideation → Spec_Check → Clarification → Judgment → Validation → Approval → Block

Allowed agents per stage – which agent types can act in a stage.

Rules for outputs – how proposals, plans, or artifacts are formatted and merged.

Flow control – conditions for moving to the next stage or iteration.

Traceability & logging – how metadata is stored for audit purposes.

So it’s like a map or protocol for the agents to know:

Where they are in the pipeline

What they are allowed to do

How their outputs are recorded

When human intervention is required

2. How an Agent Consumes It

SkillAgent / SDDAgent reads the pipeline template (usually stage.json + constitution.md rules).

At each stage:

Checks which agents are allowed to run.

Passes the current artifact.md / plan.md to the agents.

Enforces behavior rules from constitution.md.

Collects JSON outputs from agents.

Merges and evolves outputs into artifact.md / plan.md.

Determines stage exit conditions (e.g., all required agents completed, proposals validated).

Moves to next stage or triggers HITL review if needed.


Key points

Stage.json = “Who can act”

PipelineAdapter = “Where to go next”

The same stage can repeat multiple times if artifact state requires it.

Dynamic routing enables:

Loops (e.g., spec revisions → ideation → judgment)

Branching (e.g., conflicts → clarification)

HITL intervention points


======

pipeline_template.md
        ↓
PipelineTemplateExtractor
        ↓
PipelineLinter  ← static safety
        ↓
PipelineDiff    ← change awareness
        ↓
PipelineAdapter ← runtime routing
