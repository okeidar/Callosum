# Handle Contradictions

## Directive

If the user's request **or your implementation plan** contradicts an established rule or a product rule in `CLAUDE.md` or `template/wiki-contract.md`, handle it gracefully by highlighting the contradiction and asking for clarification.

## Guidelines

1. **Identify Contradiction:** Before proceeding with a request, cross-reference it with the project's shipped rules and wiki contract.

2. **Halt and Inquire:** If a contradiction is found, do not proceed with the request.

3. **Cite the Rule:** Clearly state which rule or document is being contradicted. Quote the relevant section if possible.

4. **Ask for Clarification:** Ask the user how they would like to proceed. Options might include:
   - Making a one-time exception
   - Updating the rule or document
   - Withdrawing the request
   - Finding an alternative approach that satisfies both

5. **Example Response:** "Your request to add error handling for this feature seems to conflict with our 'Happy Flow Focus' principle in coding-standards.md, which states: 'Implementations should only handle the basic success path. Do not implement error handling or edge cases unless explicitly requested.' Should I proceed with your request as a one-time exception, or should we update the rule to allow error handling for this type of feature?"

## When to Apply

- User request conflicts with established coding standards
- User request contradicts architecture decisions in product guidance
- User request goes against YAGNI/DRY/SRP principles
- User request would break established patterns
- **Your implementation plan deviates from shipped product rules (different files, skipped architecture, etc.)**
- **You're applying engineering principles that override documented architecture**

## Critical: Your Own Plans Can Contradict Docs

**Contradictions aren't just from user requests.** Your implementation decisions can also contradict product guidance:

- Design doc specifies files A, B, C → Your plan creates only A, C — **Contradiction**
- Design doc mandates generic layer → You decide to skip it per YAGNI — **Contradiction**
- Design doc shows specific architecture → You implement "simpler" version — **Contradiction**

**Before implementing, check: Does my file/architecture plan match the product contract exactly?**

## Common Contradiction Patterns to Watch For

**1. Input vs Computation Contradiction:**
- Doc says: "Component is deterministic" or "Data A is already known" or "All X ARE Y by construction"
- Your plan: Logic to compute, generate, or derive that data
- **This is a contradiction** - if it's already provided/known, don't recompute it

**2. Identity Relationship Contradiction:**
- Doc says: "A IS B" or "A contains B" or "B comes from A"
- Your plan: Treats A and B as separate entities or applies transformation between them
- **This is a contradiction** - if A IS B, they're identical; if A contains B, B is part of A's structure

**3. Scope Mismatch Contradiction:**
- Doc says: "Component handles X and Y" or "Process produces 2 outputs"
- Your design: Has X, Y, Z, W (4 elements)
- **This is a contradiction** - why are there more elements? Where do Z and W come from?

**4. Example vs Principle Contradiction:**
- Doc example shows: Specific transformation or processing step
- Doc principle states: Different behavior or approach
- **This is a contradiction** - example and principle conflict
- **Action**: Ask user which is correct - example or principle?

**5. Data Source Contradiction:**
- Doc says: "Data comes from source X"
- Your plan: Obtains or computes that data from different source Y
- **This is a contradiction** - if data source is specified, follow it

**When you detect ANY of these patterns:**
1. STOP immediately
2. Quote the contradictory statements from product guidance
3. Explain why they contradict
4. Ask user for clarification: "Which interpretation is correct?"
5. DO NOT proceed with assumptions

Always handle contradictions with respect and clarity, presenting options rather than refusing outright.
