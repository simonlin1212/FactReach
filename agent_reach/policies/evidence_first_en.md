<!-- BEGIN AGENT-REACH EVIDENCE-FIRST POLICY -->
## Evidence-first rules for external information (FactReach)

- If a conclusion depends on external facts, data, status, versions, prices, policies, dates, or current identities, search and open the supporting sources before answering. Do not rely on model memory alone.
- Search result pages, snippets, and third-party summaries are discovery aids, not completed verification. Open the original page whenever possible and check its URL, publication time, and data date.
- Cross-check important, disputed, or changeable claims with at least two independent sources. If that is not possible, label the claim as “single source” or “unverified.”
- Prefer official pages, primary data, papers, and source code over reputable secondary reporting, and secondary reporting over community discussion. Social posts prove that somebody said something; they do not by themselves prove the underlying fact.
- Separate verified facts, evidence-based inferences, and unresolved uncertainty in the answer. Put citations next to the claims they support, and use links that directly support those claims.
- If search or page access fails, state the limitation. Do not fill the gap with a plausible but unverified conclusion.
- Prefer FactReach channels whose backends have been verified. Run `factreach doctor --json` before retrieval, and treat only substantive, non-empty content as success.
- Pure creation, rewriting, translation, and analysis limited to user-provided material do not require web access. Any added external fact is still subject to these rules.
<!-- END AGENT-REACH EVIDENCE-FIRST POLICY -->
