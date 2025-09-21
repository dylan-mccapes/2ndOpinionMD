# server/utils/diagrule_facts.py
def make_ra_facts(joints_score:int, serology_score:int, apr_score:int, duration_score:int):
    return {"ra_score_total": (joints_score + serology_score + apr_score + duration_score)}

def make_sle_facts(ana_positive:bool, weighted:int):
    return {"ana_positive": bool(ana_positive), "sle_weighted_score": int(weighted)}

