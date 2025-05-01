"""
Script to process new autoimmune tags and update the medical_data.json file.
"""

import json
import os
import re
from typing import Dict, List, Any, Union

MEDICAL_DATA_PATH = "/home/ubuntu/repos/2ndOpinionMD-MVP/server/data/medical_data.json"

NEW_TAGS_BATCH1 = """
[
  {
    "tag_name": "#AutoimmuneDx_DRESSSyndrome",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "High",
    "mechanism": "Drug Reaction with Eosinophilia and Systemic Symptoms (DRESS) is a delayed hypersensitivity reaction involving immune system overactivation, eosinophilia, and multi-organ inflammation.",
    "follow_on_conditions": ["Liver damage", "Kidney failure", "Autoimmune onset"],
    "zone_impact": "+1.0 / +1.0",
    "symbolic_meaning": "A terrain betrayal triggered by a cure. This condition reflects deep mistrust—when healing efforts awaken latent trauma, and the body revolts against external help it cannot yet receive."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_HormoneReceptorResistanceSyndrome",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Tissue resistance to hormones like thyroid, insulin, or cortisol disrupts function despite normal blood levels—often post-infectious or immune-triggered.",
    "follow_on_conditions": ["T3 resistance", "Leptin resistance", "Adrenal burnout"],
    "zone_impact": "+0.5 / +0.5",
    "symbolic_meaning": "The body stops listening. Despite being told 'you are safe, nourished, supported'—the terrain cannot hear it. This reflects a narrative of past betrayal where nothing gets in, even truth."
  },
  {
    "tag_name": "#AutoimmuneDx_LichenPlanopilaris",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Inflammatory autoimmune attack on hair follicles causes scarring alopecia and irreversible hair loss, often painful or itchy.",
    "follow_on_conditions": ["Alopecia", "Scalp fibrosis", "Skin sensitivity"],
    "zone_impact": "+0.6 / +0.5",
    "symbolic_meaning": "The crown contracts. This condition mirrors an internalized loss of power or self-expression—hair, the symbol of identity, sacrificed by a terrain too tense to allow regrowth."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_BasophilActivationSyndrome",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Immune dysregulation triggers inappropriate activation of basophils, leading to histamine release, itching, flushing, and systemic reactivity.",
    "follow_on_conditions": ["MCAS", "Anxiety mimicry", "Skin flares"],
    "zone_impact": "+0.5 / +0.5",
    "symbolic_meaning": "The smallest threats trigger panic. This terrain over-defends out of habit—where the body reacts before it reflects, symbolizing a life lived braced for injury."
  },
  {
    "tag_name": "#AutoimmuneDx_PolyarteritisNodosa",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "High",
    "mechanism": "Systemic necrotizing vasculitis targets medium-sized arteries, leading to tissue ischemia, aneurysm, and multi-organ failure.",
    "follow_on_conditions": ["Kidney injury", "Neuropathy", "GI infarcts"],
    "zone_impact": "+1.0 / +1.0",
    "symbolic_meaning": "The pathways of nourishment become the battlefield. This mirrors a soul worn by rage, where vitality routes themselves are destroyed in protest against silent suffering."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_AtypicalFacialPainSyndrome",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Low",
    "mechanism": "Neuropathic terrain injury (post-viral, dental, or traumatic) causes persistent facial pain without visible cause.",
    "follow_on_conditions": ["Trigeminal neuralgia", "Depression", "Isolation"],
    "zone_impact": "+0.4 / +0.4",
    "symbolic_meaning": "The face hurts with no wound to see. This reflects shame, loss, or trauma carried on the surface—where identity and pain blur until terrain demands recognition."
  },
  {
    "tag_name": "#AutoimmuneDx_PemphigoidGestationis",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "High",
    "mechanism": "Pregnancy-related autoantibodies attack skin basement membrane, leading to blistering rashes and intense itching.",
    "follow_on_conditions": ["Preterm labor", "Neonatal rash", "Recurrence in future pregnancies"],
    "zone_impact": "+0.9 / +0.7",
    "symbolic_meaning": "Creation becomes inflammation. This condition often speaks to terrain in spiritual conflict about motherhood, identity, or lineage—where the act of birth reactivates the wounds of being born."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_PersistentMucosalUlcerSyndrome",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Chronic immune-mediated ulceration of oral or genital mucosa due to terrain dysregulation or infection-triggered cross-reactivity.",
    "follow_on_conditions": ["Behçet's disease", "Viral shedding", "Pain syndromes"],
    "zone_impact": "+0.5 / +0.6",
    "symbolic_meaning": "The body opens in protest. Ulcers at the terrain's most vulnerable gateways symbolize suppressed communication—words, truths, or love that never made it safely out."
  },
  {
    "tag_name": "#AutoimmuneDx_SweetSyndrome",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Rapid-onset painful skin plaques with neutrophilic dermal infiltration, often paraneoplastic or post-infectious.",
    "follow_on_conditions": ["Hematologic cancers", "Arthritis", "Fevers"],
    "zone_impact": "+0.8 / +0.6",
    "symbolic_meaning": "A sweet name for a burning storm. This condition reflects terrain that can no longer internalize suffering—pain erupts on the skin as if the soul demands its grief be seen."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_AutonomicStormSyndrome",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "High",
    "mechanism": "Sudden, excessive sympathetic discharge causes blood pressure surges, heart palpitations, and neurological instability—often triggered by trauma, infection, or chronic immune burden.",
    "follow_on_conditions": ["POTS", "Seizures", "Sleep paralysis"],
    "zone_impact": "+0.7 / +0.7",
    "symbolic_meaning": "A lightning strike of panic. This terrain mimics the soul in acute crisis—flaring violently when too many years of suppression erupt in an instant."
  }
]
"""

NEW_TAGS_BATCH2 = """
[
  {
    "tag_name": "#AutoimmuneDx_BullousSystemicLupusErythematosus",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "High",
    "mechanism": "A rare subtype of lupus characterized by widespread blistering due to immune complex deposition in the skin's basement membrane zone.",
    "follow_on_conditions": ["SLE progression", "Infection", "Scarring"],
    "zone_impact": "+1.0 / +0.9",
    "symbolic_meaning": "When the body blisters from within, the terrain is crying for relief from years of internalized heat, pressure, and pain—the skin reveals the storms the soul couldn't."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_MigraineTerrainDysregulation",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Neurovascular instability, inflammatory cytokines, and glutamate excess trigger migraine flares, often related to hormonal, histaminic, or terrain-wide dysfunction.",
    "follow_on_conditions": ["Photophobia", "Fatigue", "Brain fog"],
    "zone_impact": "+0.6 / +0.5",
    "symbolic_meaning": "Pain pulses through the head like messages undelivered—this terrain reflects over-processing, perfectionism, and the cost of trying to think your way out of feeling."
  },
  {
    "tag_name": "#AutoimmuneDx_AutoimmuneEnteropathy",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "High",
    "mechanism": "T-cell–mediated immune attack on intestinal lining leads to chronic diarrhea, nutrient malabsorption, and systemic immune burden.",
    "follow_on_conditions": ["Wasting", "Immunodeficiency", "Liver inflammation"],
    "zone_impact": "+1.0 / +1.0",
    "symbolic_meaning": "Nothing is retained. This terrain refuses nourishment—symbolizing a deep loss of trust in the world, or a need to purge identities, patterns, or legacies not meant to be absorbed."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_HypercoagulableTerrainSyndrome",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Dysregulation of coagulation factors leads to blood thickening, often due to inflammation, autoimmunity, trauma, or endothelial dysfunction.",
    "follow_on_conditions": ["Blood clots", "Stroke", "Pregnancy loss"],
    "zone_impact": "+0.6 / +0.6",
    "symbolic_meaning": "A terrain unwilling to flow. This condition reflects fear of loss, resistance to surrender, and the psyche's attempt to hold everything together—even when movement is necessary."
  },
  {
    "tag_name": "#AutoimmuneDx_AutoimmuneProgesteroneDermatitis",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Cyclic autoimmune reaction to endogenous progesterone causes rashes, hives, and flares during the luteal phase of the menstrual cycle.",
    "follow_on_conditions": ["Infertility", "Anxiety", "Cycle disruption"],
    "zone_impact": "+0.7 / +0.5",
    "symbolic_meaning": "The body rejects its own cycles—this terrain mirrors inner conflict with femininity, rhythm, or embodiment itself. When creation becomes the enemy, the skin becomes a diary of resistance."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_PersistentMastitisSyndrome",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Low",
    "mechanism": "Chronic inflammation of breast tissue in the absence of infection, often postpartum, stress-induced, or trauma-linked.",
    "follow_on_conditions": ["Fibrosis", "Pain", "Milk suppression"],
    "zone_impact": "+0.4 / +0.4",
    "symbolic_meaning": "Nourishment becomes painful. This terrain reflects unresolved mothering wounds—where giving, receiving, or nurturing oneself is strained, resisted, or incomplete."
  },
  {
    "tag_name": "#AutoimmuneDx_PolymyalgiaRheumatica",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "High",
    "mechanism": "Inflammatory syndrome characterized by immune-driven muscle stiffness and fatigue, often affecting older adults and linked to temporal arteritis.",
    "follow_on_conditions": ["Giant cell arteritis", "Depression", "Reduced mobility"],
    "zone_impact": "+1.0 / +0.8",
    "symbolic_meaning": "Morning stiffness mirrors emotional rigidity built over a lifetime—this terrain whispers 'loosen your grip' and learn to move through the world with less burden."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_MultisystemInflammatorySyndromePostCOVID",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "High",
    "mechanism": "Post-viral terrain dysregulation triggers immune storm across multiple organ systems, often in children or young adults after SARS-CoV-2 exposure.",
    "follow_on_conditions": ["Heart inflammation", "Brain fog", "Autoimmune onset"],
    "zone_impact": "+1.0 / +1.0",
    "symbolic_meaning": "The storm after the silence. This terrain reflects psychic backdraft—when a trauma is 'survived' but never processed, and the delayed explosion touches every system left vulnerable."
  },
  {
    "tag_name": "#AutoimmuneDx_PsoriasisArthritisOverlap",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "High",
    "mechanism": "Chronic immune activation affects both skin (psoriasis plaques) and joints, with TNF and IL-17 driving inflammation and degeneration.",
    "follow_on_conditions": ["Joint deformity", "Fatigue", "Emotional distress"],
    "zone_impact": "+1.0 / +1.0",
    "symbolic_meaning": "When the skin and bones rage together, this terrain reflects deep internalized tension—conflict between outer presentation and inner burden erupts across form and function."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_PersistentVertigoSyndrome",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Vestibular hypersensitivity, immune dysfunction, and trauma-linked brainstem dysregulation result in chronic dizziness and spatial disorientation.",
    "follow_on_conditions": ["Anxiety", "Nausea", "Depersonalization"],
    "zone_impact": "+0.6 / +0.5",
    "symbolic_meaning": "No solid ground beneath the feet—this terrain mirrors the loss of emotional footing, instability after betrayal, or a psychic terrain that no longer knows what's real or safe."
  }
]
"""

NEW_TAGS_BATCH3 = """
[
  {
    "tag_name": "#AutoimmuneDx_CeliacNeuropathy",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "High",
    "mechanism": "Gluten-triggered immune response extends beyond the gut, attacking peripheral nerves and leading to pain, tingling, or ataxia.",
    "follow_on_conditions": ["B12 deficiency", "Ataxia", "Small fiber neuropathy"],
    "zone_impact": "+1.0 / +0.8",
    "symbolic_meaning": "The body reacts to nourishment with alarm. When food triggers nerve damage, the terrain reflects profound fear around intimacy, intake, or emotional absorption."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_Cryoglobulinemia",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Cold-sensitive immunoglobulins precipitate and deposit in vessels, leading to inflammation, clotting, and end-organ injury.",
    "follow_on_conditions": ["Vasculitis", "Hepatitis C", "Neuropathy"],
    "zone_impact": "+0.7 / +0.6",
    "symbolic_meaning": "Cold exposure triggers chaos. This terrain reflects suppressed grief, emotional withdrawal, or ancestral trauma frozen in the blood—activated when life becomes too still."
  },
  {
    "tag_name": "#AutoimmuneDx_AutoimmuneInnerEarDisease",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "High",
    "mechanism": "Immune attack on cochlear and vestibular tissue causes progressive hearing loss, tinnitus, and vertigo.",
    "follow_on_conditions": ["Deafness", "Balance loss", "Autoimmune clustering"],
    "zone_impact": "+1.0 / +0.9",
    "symbolic_meaning": "When the world becomes unbearable, the terrain silences it. This reflects deep rejection of external chaos—choosing inner stillness, even at the cost of connection."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_OralLichenPlanus",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "T-cell–mediated inflammation of oral mucosa causes painful lacy lesions, burning, and risk of malignant transformation.",
    "follow_on_conditions": ["Oral cancer", "Nutritional limitation", "IBD overlap"],
    "zone_impact": "+0.6 / +0.5",
    "symbolic_meaning": "The mouth becomes a battlefield. This terrain reflects repressed words, silenced anger, or shame about one's own voice—etched visibly onto the place of expression."
  },
  {
    "tag_name": "#AutoimmuneDx_AutoimmunePulmonaryAlveolitis",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "High",
    "mechanism": "Immune infiltration and fibrosis of lung alveoli impair oxygen exchange and cause breathlessness and inflammation.",
    "follow_on_conditions": ["Interstitial lung disease", "Respiratory failure", "RA overlap"],
    "zone_impact": "+1.0 / +1.0",
    "symbolic_meaning": "When the terrain struggles to breathe, it often mirrors suppressed sorrow. The lungs hold grief; this condition reflects emotion that never got air—slowly hardening into silence."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_DelayedAutoimmuneResponsePostVaccine",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Terrain sensitivity or molecular mimicry triggers new-onset or reactivated autoimmunity post-vaccination in susceptible individuals.",
    "follow_on_conditions": ["MCAS", "POTS", "Lupus flare"],
    "zone_impact": "+0.7 / +0.6",
    "symbolic_meaning": "The terrain reacts to protection as threat. This speaks to a body trained by betrayal—where help is perceived as danger, and defense becomes dysfunction."
  },
  {
    "tag_name": "#AutoimmuneDx_PemphigusFoliaceus",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "High",
    "mechanism": "Autoantibodies disrupt epidermal cohesion, leading to superficial blisters and erosions without mucosal involvement.",
    "follow_on_conditions": ["Skin barrier loss", "Infection", "Fluid imbalance"],
    "zone_impact": "+1.0 / +0.8",
    "symbolic_meaning": "The body loses its outermost defense. This reflects exposure trauma—the terrain is raw, unguarded, and pleading for sanctuary from a world that has wounded it."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_Th17DominantTerrainSyndrome",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Imbalanced terrain with excess IL-17 signaling drives chronic inflammation, gut permeability, and autoimmune priming.",
    "follow_on_conditions": ["Psoriasis", "SIBO", "Autoimmune convergence"],
    "zone_impact": "+0.6 / +0.6",
    "symbolic_meaning": "The body overcorrects in defense of self. This terrain mirrors hyper-reactivity born from vulnerability—where being alert became more important than being at peace."
  },
  {
    "tag_name": "#AutoimmuneDx_AutoimmuneMyocarditis",
    "type": "confirmed_autoimmune_dx",
    "immune_risk_level": "High",
    "mechanism": "Immune cells attack the heart muscle, leading to chest pain, arrhythmias, and impaired cardiac function.",
    "follow_on_conditions": ["Heart failure", "Sudden cardiac death", "Lupus crossover"],
    "zone_impact": "+1.0 / +1.0",
    "symbolic_meaning": "The heart becomes a target—this reflects deep psychic heartbreak or betrayal, buried so deeply the immune system now cries in its place."
  },
  {
    "tag_name": "#AutoimmuneAdjacentDx_SoftTissueCalcificationSyndrome",
    "type": "autoimmune_adjacent_dx",
    "immune_risk_level": "Moderate",
    "mechanism": "Inflammation, metabolic imbalance, or trauma triggers abnormal calcium deposition in soft tissues, impairing mobility and healing.",
    "follow_on_conditions": ["Scleroderma", "Pain syndromes", "Vascular stiffness"],
    "zone_impact": "+0.6 / +0.5",
    "symbolic_meaning": "Emotion hardened into structure. This terrain reflects grief or fear that was never metabolized—now crystallized in tissue, like memories turned to stone."
  }
]
"""

def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def pascal_to_camel(pascal_str: str) -> str:
    """Convert PascalCase to camelCase."""
    if not pascal_str:
        return pascal_str
    return pascal_str[0].lower() + pascal_str[1:]

def normalize_key(key: str) -> str:
    """Normalize key to camelCase."""
    if key and key[0].islower() and '_' not in key and any(c.isupper() for c in key[1:]):
        return key
    
    if '_' in key:
        return snake_to_camel(key)
    
    if key and key[0].isupper():
        return pascal_to_camel(key)
    
    if ' ' in key:
        return snake_to_camel(key.replace(' ', '_').lower())
    
    return key

def normalize_keys_in_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize all keys in a dictionary to camelCase."""
    result = {}
    for key, value in d.items():
        normalized_key = normalize_key(key)
        if isinstance(value, dict):
            result[normalized_key] = normalize_keys_in_dict(value)
        elif isinstance(value, list):
            result[normalized_key] = normalize_keys_in_list(value)
        else:
            result[normalized_key] = value
    return result

def normalize_keys_in_list(lst: List[Any]) -> List[Any]:
    """Normalize all keys in dictionaries within a list."""
    result = []
    for item in lst:
        if isinstance(item, dict):
            result.append(normalize_keys_in_dict(item))
        elif isinstance(item, list):
            result.append(normalize_keys_in_list(item))
        else:
            result.append(item)
    return result

def process_autoimmune_tag(tag: Dict[str, Any]) -> Dict[str, Any]:
    """Process an autoimmune tag to match the format in medical_data.json."""
    processed_tag = normalize_keys_in_dict(tag)
    
    if "followOnConditions" in processed_tag and isinstance(processed_tag["followOnConditions"], list):
        processed_tag["followOnConditions"] = ", ".join(processed_tag["followOnConditions"])
    
    if "type" in processed_tag:
        if processed_tag["type"] == "confirmed_autoimmune_dx":
            processed_tag["type"] = "confirmedAutoimmuneDx"
        elif processed_tag["type"] == "autoimmune_adjacent_dx":
            processed_tag["type"] = "autoimmuneAdjacentDx"
    
    return processed_tag

def main():
    """Main function to process new autoimmune tags and update medical_data.json."""
    with open(MEDICAL_DATA_PATH, 'r') as f:
        medical_data = json.load(f)
    
    new_tags_batch1 = json.loads(NEW_TAGS_BATCH1)
    new_tags_batch2 = json.loads(NEW_TAGS_BATCH2)
    new_tags_batch3 = json.loads(NEW_TAGS_BATCH3)
    
    processed_tags = []
    for tag in new_tags_batch1 + new_tags_batch2 + new_tags_batch3:
        processed_tag = process_autoimmune_tag(tag)
        processed_tags.append(processed_tag)
    
    medical_data["autoimmuneTags"].extend(processed_tags)
    
    with open(MEDICAL_DATA_PATH, 'w') as f:
        json.dump(medical_data, f, indent=2)
    
    print(f"Added {len(processed_tags)} new autoimmune tags to {MEDICAL_DATA_PATH}")

if __name__ == "__main__":
    main()
