# server/utils/diagnostic_rule_eval.py

def _resolve(spec, facts):
    # Resolve {"var": "name"} or plain value
    if isinstance(spec, dict) and "var" in spec:
        return facts.get(spec["var"])
    return spec

def _truthy(x):
    # Conservative truthiness for clinical flags
    return bool(x)

def _eval_node(node, facts, defs):
    # 1) Simple VAR checks
    if isinstance(node, dict) and "var" in node:
        # (a) bare {"var": "x"} -> truthiness
        if set(node.keys()) == {"var"}:
            return _truthy(facts.get(node["var"]))
        # (b) {"var": "x", "is": true/false} -> explicit boolean match
        if "is" in node:
            return _truthy(facts.get(node["var"])) == bool(node["is"])

    # 2) Comparators
    if "gte" in node:
        v = _resolve(node["gte"], facts)
        try:
            return (v or 0) >= node["value"]
        except TypeError:
            return False

    if "lte" in node:
        v = _resolve(node["lte"], facts)
        try:
            return (v or 0) <= node["value"]
        except TypeError:
            return False

    if "gte_count" in node:
        v = _resolve(node["gte_count"], facts)
        try:
            return (v or 0) >= node["value"]
        except TypeError:
            return False

    # 3) Boolean composition
    if "not" in node:
        return not _eval_node(node["not"], facts, defs)

    if "all" in node:
        return all(_eval_node(n, facts, defs) for n in node["all"])

    if "any" in node:
        return any(_eval_node(n, facts, defs) for n in node["any"])

    # 4) References to named subrules
    if "ref" in node:
        ref = node["ref"]
        if ref not in defs:
            raise ValueError(f"Unknown ref '{ref}' in rule")
        return _eval_node(defs[ref], facts, defs)

    raise ValueError(f"Unsupported node: {node}")

def evaluate(rule_json, facts):
    defs = rule_json.get("defs", {})
    ok = _eval_node(rule_json["logic"], facts, defs)
    label = rule_json.get("label_positive") if ok else rule_json.get("label_negative", "No")
    return {"ok": ok, "label": label}

