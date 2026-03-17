# Novel Development Cycle Pipeline Template

## Overview
This pipeline governs the transformation of a raw concept into a structured narrative, ensuring world-state consistency and thematic alignment across all chapters.

**Initial Stage**: world_foundation

### Stage: world_foundation
- **Description**: Define the physical laws, cultural lore, and "system constraints" of the setting.
- **Allowed Agents**: ["WorldBuilderAgent"]
- **Exit Condition**: ctx.lore_is_consistent() and ctx.has_physics_rules()
**Next Stages**:
- character_synthesis — if ctx.setting_finalized()
- world_foundation — if ctx.contradictions_found()

### Stage: character_synthesis
- **Description**: Generate character profiles, motivations, and internal arcs.
- **Allowed Agents**: ["CharacterArchitectAgent"]
- **Exit Condition**: len(artifact["cast_list"]) >= 1 and ctx.all_chars_have_arcs()
**Next Stages**:
- plot_stratification — if ctx.cast_ready()
- world_foundation — if ctx.character_origin_conflicts_with_lore()

### Stage: plot_stratification
- **Description**: Map the Three-Act structure into discrete scene beats and milestones.
- **Allowed Agents**: ["PlotStrategistAgent"]
- **Exit Condition**: ctx.climax_defined() and ctx.pacing_score_is_optimal()
**Next Stages**:
- consistency_audit — if ctx.plot_complete()
- character_synthesis — if ctx.protagonist_motivation_is_weak()

### Stage: consistency_audit
- **Description**: Cross-reference the plot beats against the World Foundation and Character Arcs to find plot holes.
- **Allowed Agents**: ["ConsistencyAuditAgent"]
- **Exit Condition**: ctx.no_plot_holes_detected()
**Next Stages**:
- prose_refinement — if ctx.audit_passed()
- plot_stratification — if ctx.logic_gap_found()
- block — if ctx.unresolvable_paradox_detected()

### Stage: prose_refinement
- **Description**: Convert structured scene beats into high-fidelity narrative prose.
- **Allowed Agents**: ["ProseRefinerAgent"]
- **Exit Condition**: ctx.word_count_met() and ctx.tone_check("gritty_melancholic")
**Next Stages**:
- hitl_review

### Stage: hitl_review
- **Description**: Human-in-the-loop pause for creative sign-off on prose style and emotional resonance.
- **Allowed Agents**: ["PlotlineAssistant"] 
- **Exit Condition**: ctx.human_approved()
**Next Stages**:
- publish_ready — if ctx.approved()
- prose_refinement — if ctx.human_requests_rewrite()
- block — if ctx.creative_direction_mismatch()

### Stage: block
- **Description**: Pipeline halted due to core logic failure, lore collapse, or creative stall.
- **Allowed Agents**: ["ConsistencyAuditAgent", "PlotStrategistAgent"]
**Next Stages**:
- terminal — if ctx.project_abandoned()
- world_foundation — if ctx.world_reboot_required()

### Stage: terminal
- **Description**: Narrative artifact finalized, exported to `artifacts/narrative/`, and state locked.
- **Terminal**: true
