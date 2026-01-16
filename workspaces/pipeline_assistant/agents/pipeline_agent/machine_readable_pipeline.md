#  machine_readable_pipeline.md  
*Specification-Driven Development – Dynamic Pipeline*

---

## Stage: Spec_Check

**Description**  
Ensure `spec.md` exists, is readable, and internally consistent.  
No mutations allowed at this stage.

**Allowed Agents**
- SpecInspectorAgent

**Exit Condition**
- `artifact_is_valid(artifact)`

**Next Stages**
- **Clarification**  
  Condition: `artifact_has_spec_gaps(artifact)`
- **Ideation**  
  Condition: `artifact_is_valid(artifact)`

---

## Stage: Clarification

**Description**  
Resolve ambiguities, contradictions, or missing requirements.  
May request HITL input.

**Allowed Agents**
- ClarifierAgent

**Exit Condition**
- `clarifications_resolved(artifact)`

**Next Stages**
- **Ideation**  
  Condition: `clarifications_resolved(artifact)`
- **Block**  
  Condition: `clarification_failed(artifact)`

---

## Stage: Ideation

**Description**  
Generate candidate plans or proposals aligned with `spec.md`.  
Writes proposals to `artifact.md` only.

**Allowed Agents**
- IdeationAgent  
- OptimisticAgent

**Exit Condition**
- `len(artifact['proposals']) > 0`

**Next Stages**
- **Judgment**  
  Condition: *(implicit – proceed when exit condition met)*

---

## Stage: Judgment

**Description**  
Evaluate proposals for conflicts, feasibility, and specification alignment.

**Allowed Agents**
- CriticAgent  
- SynthesizerAgent

**Exit Condition**
- `all_proposals_reviewed(artifact)`

**Next Stages**
- **Validation**  
  Condition: `accepted_proposals_exist(artifact)`
- **Clarification**  
  Condition: `critical_issues_detected(artifact)`
- **Ideation**  
  Condition: `artifact_requires_new_ideas(artifact)`
- **Block**  
  Condition: `all_proposals_invalid(artifact)`

---

## Stage: Validation

**Description**  
Validate accepted proposals against constraints, tech stack,  
and execution feasibility.

**Allowed Agents**
- ValidatorAgent

**Exit Condition**
- `artifact_is_valid(artifact)`

**Next Stages**
- **Approval**  
  Condition: `artifact_is_valid(artifact)`
- **Spec_Revision**  
  Condition: `proposal_conflicts_with_spec(artifact)`

---

## Stage: Spec_Revision

**Description**  
Propose changes to `spec.md`.  
Requires explicit HITL approval before applying.

**Allowed Agents**
- SpecRevisionAgent

**Exit Condition**
- `hitl_approved == True`

**Next Stages**
- **Ideation**  
  Condition: *(always after approval)*

---

## Stage: Approval

**Description**  
Final human or system approval before execution.

**Allowed Agents**
- ApprovalAgent

**Exit Condition**
- `hitl_approved == True`

**Next Stages**
- **Terminal**

---

## Stage: Block

**Description**  
Pipeline cannot proceed safely.  
Requires human intervention.

**Allowed Agents**
- SafetyAgent

**Exit Condition**
- `False`

**Terminal Stage**
- Yes

---

## Stage: Terminal

**Description**  
Pipeline completed successfully.

**Terminal Stage**
- Yes

---

##  LLM Extraction Contract (Required)

<!--
LLM Extraction Prompt:

Extract each stage into a dict with the following keys:

{
  "name": str,
  "description": str,
  "allowed_agents": List[str],
  "exit_condition": str | null,
  "next_stages": List[
    {
      "name": str,
      "condition": str | null
    }
  ],
  "terminal": bool (optional)
}

Rules:
- Preserve stage order
- Preserve condition strings verbatim
- Do NOT evaluate conditions
- Missing conditions should be set to null
- Output must be machine-consumable by PipelineAdapter
-->
