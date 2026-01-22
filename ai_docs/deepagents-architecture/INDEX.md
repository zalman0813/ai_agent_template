# DeepAgents CLI vs SDK Architecture - Index

> Comprehensive technical documentation comparing DeepAgents CLI and SDK approaches. This documentation is split into 8 parts for easier navigation and reading.

**Version:** 1.0
**Last Updated:** 2026-01-21
**Total Pages:** 8 parts (~700 lines each)

---

## Quick Navigation

### 🎯 New to DeepAgents?
Start here → [Part 1: Overview](part1-overview.md) → [Part 4: Skills & Decision Framework](part4-skills-decision.md) → [Part 5: Implementation Patterns](part5-implementation.md)

### 🏗️ Building a Production Agent?
[Part 2: Core Concepts](part2-core-concepts.md) → [Part 5: Implementation Patterns](part5-implementation.md) → [Part 7: Migration & Troubleshooting](part7-migration-troubleshooting.md)

### 🔍 Looking for Specific Information?
Use the [Quick Reference Guide](#quick-reference-guide) below or search within specific parts.

### 🐛 Troubleshooting?
Jump to → [Part 7: Troubleshooting Section](part7-migration-troubleshooting.md#troubleshooting)

---

## Document Structure

### [Part 1: Overview](part1-overview.md) (~700 lines)
**Sections 1-3**: Executive Summary, CLI vs SDK Overview, Architecture Comparison

**What You'll Learn:**
- Decision tree for choosing CLI vs SDK
- Key differences at a glance
- Philosophical differences (trust model, flexibility, tool management)
- Execution flow diagrams
- When each approach makes sense

**Read This If:**
- You're new to DeepAgents
- You need to decide between CLI and SDK
- You want a high-level understanding

**Key Topics:**
- CLI execution model (bash → host)
- SDK execution model (agent → middleware → backend → sandbox)
- Architecture diagrams and data flows
- Component comparison

---

### [Part 2: Core Concepts](part2-core-concepts.md) (~1,100 lines)
**Sections 4-5**: Core Concepts, Backend Implementations Deep Dive

**What You'll Learn:**
- All 5 backend types in detail
- Backend protocols and capabilities
- Configuration options and best practices
- Custom backend implementation

**Read This If:**
- You're implementing a custom agent
- You need to understand backend architecture
- You want to build a custom backend

**Key Topics:**
- StateBackend (agent state management)
- FilesystemBackend (fast file operations)
- DockerBackend (sandboxed execution)
- RemoteBackend (distributed computing)
- CompositeBackend (path routing)
- Custom backend implementation guide

---

### [Part 3: Middleware & Execution](part3-middleware-execution.md) (~800 lines)
**Sections 6-7**: Middleware Comparison, Execution Mechanisms

**What You'll Learn:**
- How middleware works in DeepAgents
- All middleware types explained
- Execution differences (bash vs execute)
- Working directory concepts
- Path resolution in CompositeBackend

**Read This If:**
- You're building custom middleware
- You need to understand tool generation
- You want to optimize execution performance

**Key Topics:**
- FilesystemMiddleware (tool generation)
- SkillsMiddleware (skill discovery)
- SubAgentMiddleware (task delegation)
- CLI bash tool vs SDK execute tool
- Working directory handling
- Shell features comparison

---

### [Part 4: Skills & Decision Framework](part4-skills-decision.md) (~850 lines)
**Sections 8-9**: Skills System, Decision Framework

**What You'll Learn:**
- Complete skills system architecture
- Progressive disclosure pattern
- SKILL.md specification
- When to use CLI vs SDK (decision framework)
- Use case recommendations

**Read This If:**
- You're building agents with skills
- You need to decide on architecture approach
- You want to implement custom skills

**Key Topics:**
- SKILL.md format and frontmatter
- Skills discovery flow (Level 1/2/3)
- Skills backend configuration
- Skill execution patterns
- Decision tree and use case matrix
- Feature requirements checklist

---

### [Part 5: Implementation Patterns](part5-implementation.md) (~850 lines)
**Section 10**: Implementation Patterns

**What You'll Learn:**
- 7 complete implementation patterns with code
- Progressive complexity (minimal → full-featured)
- Real-world examples
- Production-ready configurations

**Read This If:**
- You're ready to implement your agent
- You want copy-paste ready code examples
- You need production configuration templates

**Key Patterns:**
1. Minimal SDK (State Only) - ~50 lines
2. Filesystem Access - ~100 lines
3. Docker Execution (Sandboxed) - ~150 lines
4. Docker + Skills - ~200 lines
5. Full-Featured (Docker + Skills + SubAgents) - ~250 lines
6. Remote Execution - ~150 lines
7. Custom Backend - ~200 lines

---

### [Part 6: Comparison & Patterns](part6-comparison-patterns.md) (~750 lines)
**Sections 11-12**: Comparison Tables, Common Patterns and Anti-Patterns

**What You'll Learn:**
- Feature matrix comparisons
- Performance characteristics
- Security considerations
- Best practices (patterns)
- Common mistakes (anti-patterns)

**Read This If:**
- You need quick reference comparisons
- You want to avoid common mistakes
- You're optimizing performance or security

**Key Topics:**
- Feature matrix (CLI vs SDK variants)
- Performance comparison table
- Security comparison
- Backend capabilities matrix
- 6 best practice patterns
- 9 common anti-patterns with solutions

---

### [Part 7: Migration & Troubleshooting](part7-migration-troubleshooting.md) (~850 lines)
**Sections 13-14**: Migration Guide, Troubleshooting

**What You'll Learn:**
- Step-by-step migration (CLI → SDK)
- Hybrid approach strategies
- Common issues and solutions
- Debugging techniques

**Read This If:**
- You're migrating from CLI to SDK
- You're encountering errors
- You need debugging help

**Key Topics:**
- CLI to SDK migration (7-step process)
- bash() to execute() conversion
- Backend configuration issues
- Middleware troubleshooting
- Skills problems
- Path resolution issues
- Docker troubleshooting

---

### [Part 8: Reference](part8-reference.md) (~850 lines)
**Sections 15-17**: FAQ, Glossary, Additional Resources

**What You'll Learn:**
- 30+ frequently asked questions
- Complete terminology reference
- Links to official documentation
- Community resources

**Read This If:**
- You have specific questions
- You need terminology clarification
- You want to learn more

**Key Sections:**
- FAQ (general, backend, middleware, skills, execution, debugging)
- Glossary (A-Z term definitions)
- Additional resources (official docs, code examples, community)

---

## Quick Reference Guide

### By Topic

| Topic | Part | Section |
|-------|------|---------|
| **Architecture Comparison** | [Part 1](part1-overview.md) | Section 3 |
| **Backend Types** | [Part 2](part2-core-concepts.md) | Sections 4-5 |
| **Middleware** | [Part 3](part3-middleware-execution.md) | Section 6 |
| **Skills** | [Part 4](part4-skills-decision.md) | Section 8 |
| **Decision Framework** | [Part 4](part4-skills-decision.md) | Section 9 |
| **Code Examples** | [Part 5](part5-implementation.md) | Section 10 |
| **Performance** | [Part 6](part6-comparison-patterns.md) | Section 11 |
| **Best Practices** | [Part 6](part6-comparison-patterns.md) | Section 12 |
| **Migration** | [Part 7](part7-migration-troubleshooting.md) | Section 13 |
| **Troubleshooting** | [Part 7](part7-migration-troubleshooting.md) | Section 14 |
| **FAQ** | [Part 8](part8-reference.md) | Section 15 |

### By Use Case

| Use Case | Recommended Reading Order |
|----------|--------------------------|
| **Learning DeepAgents** | Part 1 → Part 4 → Part 5 (Pattern 1-2) |
| **Building First Agent** | Part 1 → Part 2 → Part 5 (Pattern 3) |
| **Production Deployment** | Part 4 (Section 9) → Part 5 (Pattern 5) → Part 6 |
| **Adding Skills** | Part 4 (Section 8) → Part 5 (Pattern 4) |
| **Troubleshooting** | Part 7 (Section 14) → Part 8 (FAQ) |
| **Migration CLI→SDK** | Part 7 (Section 13) |
| **Custom Backend** | Part 2 (Section 5.6) → Part 5 (Pattern 7) |
| **Performance Optimization** | Part 6 (Section 11) → Part 6 (Section 12) |

### By Question

| Question | Answer Location |
|----------|----------------|
| CLI vs SDK? | [Part 1, Section 2](part1-overview.md#2-overview-cli-vs-sdk) |
| What backend to use? | [Part 4, Section 9](part4-skills-decision.md#9-decision-framework) |
| How to implement skills? | [Part 4, Section 8](part4-skills-decision.md#8-skills-system) |
| Code examples? | [Part 5, Section 10](part5-implementation.md#10-implementation-patterns) |
| Common mistakes? | [Part 6, Section 12](part6-comparison-patterns.md#12-common-patterns-and-anti-patterns) |
| How to migrate? | [Part 7, Section 13](part7-migration-troubleshooting.md#13-migration-guide) |
| Error: Container not found? | [Part 7, Section 14.1](part7-migration-troubleshooting.md#141-backend-issues) |
| Error: Skills not discovered? | [Part 7, Section 14.2](part7-migration-troubleshooting.md#142-middleware-issues) |

---

## Document Statistics

- **Total Lines**: ~5,685 lines
- **Sections**: 17 main sections
- **Code Examples**: 25+ detailed examples
- **Diagrams**: 8+ ASCII diagrams
- **Tables**: 6 comprehensive comparison tables
- **FAQ Entries**: 30+ questions
- **Glossary Terms**: 40+ definitions

---

## Reading Recommendations

### For Beginners (2-3 hours)
1. [Part 1: Overview](part1-overview.md) - Understand the landscape (30 min)
2. [Part 4: Decision Framework](part4-skills-decision.md#9-decision-framework) - Choose your approach (20 min)
3. [Part 5: Pattern 1-3](part5-implementation.md) - Start simple (40 min)
4. [Part 8: FAQ](part8-reference.md) - Common questions (30 min)

### For Developers (4-5 hours)
1. Read Part 1, 2, 3 - Comprehensive foundation (2 hours)
2. [Part 5: All Patterns](part5-implementation.md) - Implementation guide (1 hour)
3. [Part 6: Patterns](part6-comparison-patterns.md) - Best practices (1 hour)
4. [Part 7: Troubleshooting](part7-migration-troubleshooting.md) - Reference material (1 hour)

### For Architects (6-8 hours)
Read all parts in sequence for complete understanding.

### Quick Reference (5-10 minutes)
- [Decision Framework](part4-skills-decision.md#9-decision-framework)
- [Comparison Tables](part6-comparison-patterns.md#11-comparison-tables)
- [FAQ](part8-reference.md#15-faq)

---

## Original Single-File Version

The complete documentation is also available as a single file:
- **File**: `deepagents-cli-vs-sdk-architecture.md` (5,685 lines)
- **Use When**: You need to search across all sections or prefer single-file reference

---

## Contributing

Found an error? Have suggestions? Please:
1. Open an issue in the repository
2. Submit a pull request with improvements
3. Share your implementation patterns

---

## Version History

- **v1.0** (2026-01-21) - Initial release
  - Split into 8 parts for easier navigation
  - 17 sections covering all aspects of CLI vs SDK
  - 25+ code examples, 6 comparison tables
  - 30+ FAQ entries, complete glossary

---

## Related Documentation

### In This Repository
- `langchain_middleware.md` - LangChain middleware design
- `agent-skills.md` - Agent Skills specification
- `langchain-v1.0.md` - LangChain v1.0 reference
- `examples/skill-agent/` - Complete implementation example

### Official Sources
- [DeepAgents SDK](https://github.com/deepagents/deepagents)
- [Agent Skills](https://agentskills.io/)
- [LangChain v1.0](https://python.langchain.com/)
- [Claude API](https://docs.anthropic.com/)

---

**Happy Building! 🚀**

*For questions or feedback, please see the project repository.*
