"""Minimal public adapter: retain private information, send no messages.

Prepare with forwarding_policy_identity=private_only.identity and run with
forwarding_policy=private_only. This is an adapter example, not a new algorithm.
"""


def private_only(header, reports, ownership, limits):
    # Consume public content however your policy needs; no evaluator labels exist.
    for _ in reports:
        pass
    views = [[] for _ in range(header["agent_count"])]
    for report_id, owners in ownership:
        for agent in owners:
            views[agent].append(report_id)
    return {"evidence": views, "messages": []}


private_only.identity = "example-private-only-1"
