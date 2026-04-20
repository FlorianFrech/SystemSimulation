# Chapter 5 Guideline

This document defines the scope, structure, and boundary rules for the  Chapter 5 (Feature Implementation andVerification). It must be read together with:

- `research/guideline.md` (global thesis guideline)
- `research/theory/glossary.md` (terminology)
- `research/theory/notation.md` (notation)

---

## Structure of the Implementation Sections

### Motivation
- 1-3 sentences. Always present. Reference SRs, mention parent UR in parentheses.
- Connect to the dependency chain: what previously introduced features does this build on?

### Theory / Background
- 0.5-1 page, optional. Include only if the implementation requires concepts not covered in Chapter 2. Examples: IJCSA iteration scheme, bisection-based event localization, zero-crossing functions.
- Skip entirely for features where the implementation IS the explanation (e.g., port system, history recording).
- Reference Chapter 2 for shared foundations rather than repeating.

### Implementation
- Core, several pages.
- Use the most appropriate medium:
  - Class diagram: when the contribution is structural (e.g., CoSimComponent hierarchy, Algorithm strategy pattern)
  - Code listing: when a specific algorithm or mechanism matters (e.g., IJCSA loop, event bisection, state transfer)
  - Prose with inline code: for simpler features where a diagram or listing would be overkill
- Keep listings short (15-25 lines). Simplify or excerpt rather than showing full source code.

### Verification
- 0.5-1 page. Show ONE well-chosen minimal example that demonstrates correctness of this specific feature in isolation. Present: setup, expected behavior, observed result, brief discussion. Use a figure (plot) or table for quantitative results. Note known limitations if any. Do NOT show comprehensive test coverage — that's not the purpose. The case study (Ch.6) validates at system level.

## Boundary Rules
- Each section must be self-contained and focused on a single feature. Avoid mixing multiple features in one section.
- Do not repeat theory from Chapter 2 unless absolutely necessary. Reference it instead.
- Do not include implementation details that are not directly relevant to the feature being explained. Keep it concise and focused.
- Do not include verification cases that test multiple features at once. Each case should isolate the feature being verified.
- Do not include comprehensive test results or coverage metrics. Focus on a single illustrative example for verification. The case study in Chapter 6 will cover system-level validation.
