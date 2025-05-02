"""
Script to process new autoimmune tags and update the medical_data.json file.
"""

import json
import os
import re
from typing import Dict, List, Any

MEDICAL_DATA_PATH = "/home/ubuntu/repos/2ndOpinionMD-MVP/server/data/medical_data.json"

DATA10_PATH = "/home/ubuntu/attachments/0915c053-e8e4-453d-acb7-30c0194cbbc2/data10"
DATA11_PATH = "/home/ubuntu/attachments/f1cec147-255b-4cd3-987f-6ada12705172/data11"
DATA12_PATH = "/home/ubuntu/attachments/393e42cd-a90f-44d8-9597-f12b27d56523/data12"
DATA13_PATH = "/home/ubuntu/attachments/e964ee24-f40c-43ee-9e7c-1776fa7d886d/data13"

def normalize_key(key: str) -> str:
    """Normalize key to camelCase."""
    if key and key[0].islower() and '_' not in key and any(c.isupper() for c in key[1:]):
        return key
    
    if '_' in key:
        components = key.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
    
    if key and key[0].isupper():
        return key[0].lower() + key[1:]
    
    if ' ' in key:
        components = key.replace(' ', '_').lower().split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
    
    return key

def normalize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize all keys in a dictionary to camelCase."""
    result = {}
    for key, value in d.items():
        normalized_key = normalize_key(key)
        if isinstance(value, dict):
            result[normalized_key] = normalize_dict(value)
        elif isinstance(value, list):
            result[normalized_key] = normalize_list(value)
        else:
            result[normalized_key] = value
    return result

def normalize_list(lst: List[Any]) -> List[Any]:
    """Normalize all keys in dictionaries within a list."""
    result = []
    for item in lst:
        if isinstance(item, dict):
            result.append(normalize_dict(item))
        elif isinstance(item, list):
            result.append(normalize_list(item))
        else:
            result.append(item)
    return result

def process_autoimmune_tag(tag: Dict[str, Any]) -> Dict[str, Any]:
    """Process an autoimmune tag to match the format in medical_data.json."""
    processed_tag = normalize_dict(tag)
    
    if "followOnConditions" in processed_tag and isinstance(processed_tag["followOnConditions"], list):
        processed_tag["followOnConditions"] = ", ".join(processed_tag["followOnConditions"])
    
    if "type" in processed_tag:
        if processed_tag["type"] == "confirmed_autoimmune_dx":
            processed_tag["type"] = "confirmedAutoimmuneDx"
        elif processed_tag["type"] == "autoimmune_adjacent_dx":
            processed_tag["type"] = "autoimmuneAdjacentDx"
    
    return processed_tag

def read_json_lines(file_path: str) -> List[Dict[str, Any]]:
    """Read JSON lines from a file."""
    items = []
    try:
        with open(file_path, 'r') as f:
            content = f.read().strip()
            
        if content.startswith('['):
            return json.loads(content)
            
        for line in content.split('\n'):
            if line.strip():
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"Error decoding JSON line: {line[:100]}...")
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    
    return items

def main():
    """Main function to process new data and update medical_data.json."""
    with open(MEDICAL_DATA_PATH, 'r') as f:
        medical_data = json.load(f)
    
    if "autoimmuneTags" not in medical_data:
        medical_data["autoimmuneTags"] = []
    if "citations" not in medical_data:
        medical_data["citations"] = []
    if "diseaseProfiles" not in medical_data:
        medical_data["diseaseProfiles"] = []
    
    citations = read_json_lines(DATA10_PATH)
    processed_citations = [normalize_dict(citation) for citation in citations]
    
    disease_profiles = read_json_lines(DATA11_PATH)
    processed_disease_profiles = [normalize_dict(profile) for profile in disease_profiles]
    
    tags12 = read_json_lines(DATA12_PATH)
    tags13 = read_json_lines(DATA13_PATH)
    
    processed_tags = []
    for tag in tags12 + tags13:
        processed_tags.append(process_autoimmune_tag(tag))
    
    new_tags = [
        {"tag_name": "#AutoimmuneDx_DRESSSyndrome", "type": "confirmed_autoimmune_dx", "immune_risk_level": "High", "mechanism": "Drug Reaction with Eosinophilia and Systemic Symptoms (DRESS) is a delayed hypersensitivity reaction involving immune system overactivation, eosinophilia, and multi-organ inflammation.", "follow_on_conditions": ["Liver damage", "Kidney failure", "Autoimmune onset"], "zone_impact": "+1.0 / +1.0", "symbolic_meaning": "A terrain betrayal triggered by a cure. This condition reflects deep mistrust—when healing efforts awaken latent trauma, and the body revolts against external help it cannot yet receive."},
        {"tag_name": "#AutoimmuneAdjacentDx_HormoneReceptorResistanceSyndrome", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Moderate", "mechanism": "Tissue resistance to hormones like thyroid, insulin, or cortisol disrupts function despite normal blood levels—often post-infectious or immune-triggered.", "follow_on_conditions": ["T3 resistance", "Leptin resistance", "Adrenal burnout"], "zone_impact": "+0.5 / +0.5", "symbolic_meaning": "The body stops listening. Despite being told 'you are safe, nourished, supported'—the terrain cannot hear it. This reflects a narrative of past betrayal where nothing gets in, even truth."},
        {"tag_name": "#AutoimmuneDx_LichenPlanopilaris", "type": "confirmed_autoimmune_dx", "immune_risk_level": "Moderate", "mechanism": "Inflammatory autoimmune attack on hair follicles causes scarring alopecia and irreversible hair loss, often painful or itchy.", "follow_on_conditions": ["Alopecia", "Scalp fibrosis", "Skin sensitivity"], "zone_impact": "+0.6 / +0.5", "symbolic_meaning": "The crown contracts. This condition mirrors an internalized loss of power or self-expression—hair, the symbol of identity, sacrificed by a terrain too tense to allow regrowth."},
        {"tag_name": "#AutoimmuneAdjacentDx_BasophilActivationSyndrome", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Moderate", "mechanism": "Immune dysregulation triggers inappropriate activation of basophils, leading to histamine release, itching, flushing, and systemic reactivity.", "follow_on_conditions": ["MCAS", "Anxiety mimicry", "Skin flares"], "zone_impact": "+0.5 / +0.5", "symbolic_meaning": "The smallest threats trigger panic. This terrain over-defends out of habit—where the body reacts before it reflects, symbolizing a life lived braced for injury."},
        {"tag_name": "#AutoimmuneDx_PolyarteritisNodosa", "type": "confirmed_autoimmune_dx", "immune_risk_level": "High", "mechanism": "Systemic necrotizing vasculitis targets medium-sized arteries, leading to tissue ischemia, aneurysm, and multi-organ failure.", "follow_on_conditions": ["Kidney injury", "Neuropathy", "GI infarcts"], "zone_impact": "+1.0 / +1.0", "symbolic_meaning": "The pathways of nourishment become the battlefield. This mirrors a soul worn by rage, where vitality routes themselves are destroyed in protest against silent suffering."},
        {"tag_name": "#AutoimmuneAdjacentDx_AtypicalFacialPainSyndrome", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Low", "mechanism": "Neuropathic terrain injury (post-viral, dental, or traumatic) causes persistent facial pain without visible cause.", "follow_on_conditions": ["Trigeminal neuralgia", "Depression", "Isolation"], "zone_impact": "+0.4 / +0.4", "symbolic_meaning": "The face hurts with no wound to see. This reflects shame, loss, or trauma carried on the surface—where identity and pain blur until terrain demands recognition."},
        {"tag_name": "#AutoimmuneDx_PemphigoidGestationis", "type": "confirmed_autoimmune_dx", "immune_risk_level": "High", "mechanism": "Pregnancy-related autoantibodies attack skin basement membrane, leading to blistering rashes and intense itching.", "follow_on_conditions": ["Preterm labor", "Neonatal rash", "Recurrence in future pregnancies"], "zone_impact": "+0.9 / +0.7", "symbolic_meaning": "Creation becomes inflammation. This condition often speaks to terrain in spiritual conflict about motherhood, identity, or lineage—where the act of birth reactivates the wounds of being born."},
        {"tag_name": "#AutoimmuneAdjacentDx_PersistentMucosalUlcerSyndrome", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Moderate", "mechanism": "Chronic immune-mediated ulceration of oral or genital mucosa due to terrain dysregulation or infection-triggered cross-reactivity.", "follow_on_conditions": ["Behçet's disease", "Viral shedding", "Pain syndromes"], "zone_impact": "+0.5 / +0.6", "symbolic_meaning": "The body opens in protest. Ulcers at the terrain's most vulnerable gateways symbolize suppressed communication—words, truths, or love that never made it safely out."},
        {"tag_name": "#AutoimmuneDx_SweetSyndrome", "type": "confirmed_autoimmune_dx", "immune_risk_level": "Moderate", "mechanism": "Rapid-onset painful skin plaques with neutrophilic dermal infiltration, often paraneoplastic or post-infectious.", "follow_on_conditions": ["Hematologic cancers", "Arthritis", "Fevers"], "zone_impact": "+0.8 / +0.6", "symbolic_meaning": "A sweet name for a burning storm. This condition reflects terrain that can no longer internalize suffering—pain erupts on the skin as if the soul demands its grief be seen."},
        {"tag_name": "#AutoimmuneAdjacentDx_AutonomicStormSyndrome", "type": "autoimmune_adjacent_dx", "immune_risk_level": "High", "mechanism": "Sudden, excessive sympathetic discharge causes blood pressure surges, heart palpitations, and neurological instability—often triggered by trauma, infection, or chronic immune burden.", "follow_on_conditions": ["POTS", "Seizures", "Sleep paralysis"], "zone_impact": "+0.7 / +0.7", "symbolic_meaning": "A lightning strike of panic. This terrain mimics the soul in acute crisis—flaring violently when too many years of suppression erupt in an instant."},
        {"tag_name": "#AutoimmuneDx_BullousSystemicLupusErythematosus", "type": "confirmed_autoimmune_dx", "immune_risk_level": "High", "mechanism": "A rare subtype of lupus characterized by widespread blistering due to immune complex deposition in the skin's basement membrane zone.", "follow_on_conditions": ["SLE progression", "Infection", "Scarring"], "zone_impact": "+1.0 / +0.9", "symbolic_meaning": "When the body blisters from within, the terrain is crying for relief from years of internalized heat, pressure, and pain—the skin reveals the storms the soul couldn't."},
        {"tag_name": "#AutoimmuneAdjacentDx_MigraineTerrainDysregulation", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Moderate", "mechanism": "Neurovascular instability, inflammatory cytokines, and glutamate excess trigger migraine flares, often related to hormonal, histaminic, or terrain-wide dysfunction.", "follow_on_conditions": ["Photophobia", "Fatigue", "Brain fog"], "zone_impact": "+0.6 / +0.5", "symbolic_meaning": "Pain pulses through the head like messages undelivered—this terrain reflects over-processing, perfectionism, and the cost of trying to think your way out of feeling."},
        {"tag_name": "#AutoimmuneDx_AutoimmuneEnteropathy", "type": "confirmed_autoimmune_dx", "immune_risk_level": "High", "mechanism": "T-cell–mediated immune attack on intestinal lining leads to chronic diarrhea, nutrient malabsorption, and systemic immune burden.", "follow_on_conditions": ["Wasting", "Immunodeficiency", "Liver inflammation"], "zone_impact": "+1.0 / +1.0", "symbolic_meaning": "Nothing is retained. This terrain refuses nourishment—symbolizing a deep loss of trust in the world, or a need to purge identities, patterns, or legacies not meant to be absorbed."},
        {"tag_name": "#AutoimmuneAdjacentDx_HypercoagulableTerrainSyndrome", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Moderate", "mechanism": "Dysregulation of coagulation factors leads to blood thickening, often due to inflammation, autoimmunity, trauma, or endothelial dysfunction.", "follow_on_conditions": ["Blood clots", "Stroke", "Pregnancy loss"], "zone_impact": "+0.6 / +0.6", "symbolic_meaning": "A terrain unwilling to flow. This condition reflects fear of loss, resistance to surrender, and the psyche's attempt to hold everything together—even when movement is necessary."},
        {"tag_name": "#AutoimmuneDx_AutoimmuneProgesteroneDermatitis", "type": "confirmed_autoimmune_dx", "immune_risk_level": "Moderate", "mechanism": "Cyclic autoimmune reaction to endogenous progesterone causes rashes, hives, and flares during the luteal phase of the menstrual cycle.", "follow_on_conditions": ["Infertility", "Anxiety", "Cycle disruption"], "zone_impact": "+0.7 / +0.5", "symbolic_meaning": "The body rejects its own cycles—this terrain mirrors inner conflict with femininity, rhythm, or embodiment itself. When creation becomes the enemy, the skin becomes a diary of resistance."},
        {"tag_name": "#AutoimmuneAdjacentDx_PersistentMastitisSyndrome", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Low", "mechanism": "Chronic inflammation of breast tissue in the absence of infection, often postpartum, stress-induced, or trauma-linked.", "follow_on_conditions": ["Fibrosis", "Pain", "Milk suppression"], "zone_impact": "+0.4 / +0.4", "symbolic_meaning": "Nourishment becomes painful. This terrain reflects unresolved mothering wounds—where giving, receiving, or nurturing oneself is strained, resisted, or incomplete."},
        {"tag_name": "#AutoimmuneDx_PolymyalgiaRheumatica", "type": "confirmed_autoimmune_dx", "immune_risk_level": "High", "mechanism": "Inflammatory syndrome characterized by immune-driven muscle stiffness and fatigue, often affecting older adults and linked to temporal arteritis.", "follow_on_conditions": ["Giant cell arteritis", "Depression", "Reduced mobility"], "zone_impact": "+1.0 / +0.8", "symbolic_meaning": "Morning stiffness mirrors emotional rigidity built over a lifetime—this terrain whispers 'loosen your grip' and learn to move through the world with less burden."},
        {"tag_name": "#AutoimmuneAdjacentDx_MultisystemInflammatorySyndromePostCOVID", "type": "autoimmune_adjacent_dx", "immune_risk_level": "High", "mechanism": "Post-viral terrain dysregulation triggers immune storm across multiple organ systems, often in children or young adults after SARS-CoV-2 exposure.", "follow_on_conditions": ["Heart inflammation", "Brain fog", "Autoimmune onset"], "zone_impact": "+1.0 / +1.0", "symbolic_meaning": "The storm after the silence. This terrain reflects psychic backdraft—when a trauma is 'survived' but never processed, and the delayed explosion touches every system left vulnerable."},
        {"tag_name": "#AutoimmuneDx_PsoriasisArthritisOverlap", "type": "confirmed_autoimmune_dx", "immune_risk_level": "High", "mechanism": "Chronic immune activation affects both skin (psoriasis plaques) and joints, with TNF and IL-17 driving inflammation and degeneration.", "follow_on_conditions": ["Joint deformity", "Fatigue", "Emotional distress"], "zone_impact": "+1.0 / +1.0", "symbolic_meaning": "When the skin and bones rage together, this terrain reflects deep internalized tension—conflict between outer presentation and inner burden erupts across form and function."},
        {"tag_name": "#AutoimmuneAdjacentDx_PersistentVertigoSyndrome", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Moderate", "mechanism": "Vestibular hypersensitivity, immune dysfunction, and trauma-linked brainstem dysregulation result in chronic dizziness and spatial disorientation.", "follow_on_conditions": ["Anxiety", "Nausea", "Depersonalization"], "zone_impact": "+0.6 / +0.5", "symbolic_meaning": "No solid ground beneath the feet—this terrain mirrors the loss of emotional footing, instability after betrayal, or a psychic terrain that no longer knows what's real or safe."},
        {"tag_name": "#AutoimmuneDx_CeliacNeuropathy", "type": "confirmed_autoimmune_dx", "immune_risk_level": "High", "mechanism": "Gluten-triggered immune response extends beyond the gut, attacking peripheral nerves and leading to pain, tingling, or ataxia.", "follow_on_conditions": ["B12 deficiency", "Ataxia", "Small fiber neuropathy"], "zone_impact": "+1.0 / +0.8", "symbolic_meaning": "The body reacts to nourishment with alarm. When food triggers nerve damage, the terrain reflects profound fear around intimacy, intake, or emotional absorption."},
        {"tag_name": "#AutoimmuneAdjacentDx_Cryoglobulinemia", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Moderate", "mechanism": "Cold-sensitive immunoglobulins precipitate and deposit in vessels, leading to inflammation, clotting, and end-organ injury.", "follow_on_conditions": ["Vasculitis", "Hepatitis C", "Neuropathy"], "zone_impact": "+0.7 / +0.6", "symbolic_meaning": "Cold exposure triggers chaos. This terrain reflects suppressed grief, emotional withdrawal, or ancestral trauma frozen in the blood—activated when life becomes too still."},
        {"tag_name": "#AutoimmuneDx_AutoimmuneInnerEarDisease", "type": "confirmed_autoimmune_dx", "immune_risk_level": "High", "mechanism": "Immune attack on cochlear and vestibular tissue causes progressive hearing loss, tinnitus, and vertigo.", "follow_on_conditions": ["Deafness", "Balance loss", "Autoimmune clustering"], "zone_impact": "+1.0 / +0.9", "symbolic_meaning": "When the world becomes unbearable, the terrain silences it. This reflects deep rejection of external chaos—choosing inner stillness, even at the cost of connection."},
        {"tag_name": "#AutoimmuneAdjacentDx_OralLichenPlanus", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Moderate", "mechanism": "T-cell–mediated inflammation of oral mucosa causes painful lacy lesions, burning, and risk of malignant transformation.", "follow_on_conditions": ["Oral cancer", "Nutritional limitation", "IBD overlap"], "zone_impact": "+0.6 / +0.5", "symbolic_meaning": "The mouth becomes a battlefield. This terrain reflects repressed words, silenced anger, or shame about one's own voice—etched visibly onto the place of expression."},
        {"tag_name": "#AutoimmuneDx_AutoimmunePulmonaryAlveolitis", "type": "confirmed_autoimmune_dx", "immune_risk_level": "High", "mechanism": "Immune infiltration and fibrosis of lung alveoli impair oxygen exchange and cause breathlessness and inflammation.", "follow_on_conditions": ["Interstitial lung disease", "Respiratory failure", "RA overlap"], "zone_impact": "+1.0 / +1.0", "symbolic_meaning": "When the terrain struggles to breathe, it often mirrors suppressed sorrow. The lungs hold grief; this condition reflects emotion that never got air—slowly hardening into silence."},
        {"tag_name": "#AutoimmuneAdjacentDx_DelayedAutoimmuneResponsePostVaccine", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Moderate", "mechanism": "Terrain sensitivity or molecular mimicry triggers new-onset or reactivated autoimmunity post-vaccination in susceptible individuals.", "follow_on_conditions": ["MCAS", "POTS", "Lupus flare"], "zone_impact": "+0.7 / +0.6", "symbolic_meaning": "The terrain reacts to protection as threat. This speaks to a body trained by betrayal—where help is perceived as danger, and defense becomes dysfunction."},
        {"tag_name": "#AutoimmuneDx_PemphigusFoliaceus", "type": "confirmed_autoimmune_dx", "immune_risk_level": "High", "mechanism": "Autoantibodies disrupt epidermal cohesion, leading to superficial blisters and erosions without mucosal involvement.", "follow_on_conditions": ["Skin barrier loss", "Infection", "Fluid imbalance"], "zone_impact": "+1.0 / +0.8", "symbolic_meaning": "The body loses its outermost defense. This reflects exposure trauma—the terrain is raw, unguarded, and pleading for sanctuary from a world that has wounded it."},
        {"tag_name": "#AutoimmuneAdjacentDx_Th17DominantTerrainSyndrome", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Moderate", "mechanism": "Imbalanced terrain with excess IL-17 signaling drives chronic inflammation, gut permeability, and autoimmune priming.", "follow_on_conditions": ["Psoriasis", "SIBO", "Autoimmune convergence"], "zone_impact": "+0.6 / +0.6", "symbolic_meaning": "The body overcorrects in defense of self. This terrain mirrors hyper-reactivity born from vulnerability—where being alert became more important than being at peace."},
        {"tag_name": "#AutoimmuneDx_AutoimmuneMyocarditis", "type": "confirmed_autoimmune_dx", "immune_risk_level": "High", "mechanism": "Immune cells attack the heart muscle, leading to chest pain, arrhythmias, and impaired cardiac function.", "follow_on_conditions": ["Heart failure", "Sudden cardiac death", "Lupus crossover"], "zone_impact": "+1.0 / +1.0", "symbolic_meaning": "The heart becomes a target—this reflects deep psychic heartbreak or betrayal, buried so deeply the immune system now cries in its place."},
        {"tag_name": "#AutoimmuneAdjacentDx_SoftTissueCalcificationSyndrome", "type": "autoimmune_adjacent_dx", "immune_risk_level": "Moderate", "mechanism": "Inflammation, metabolic imbalance, or trauma triggers abnormal calcium deposition in soft tissues, impairing mobility and healing.", "follow_on_conditions": ["Scleroderma", "Pain syndromes", "Vascular stiffness"], "zone_impact": "+0.6 / +0.5", "symbolic_meaning": "Emotion hardened into structure. This terrain reflects grief or fear that was never metabolized—now crystallized in tissue, like memories turned to stone."}
    ]
    
    for tag in new_tags:
        processed_tags.append(process_autoimmune_tag(tag))
    
    additional_profiles = [
        {
            "disease_name": "Crohn's Disease",
            "icd_code": "K50.9",
            "common_symptoms": [
                "Persistent diarrhea",
                "Abdominal pain and cramping",
                "Blood in stool",
                "Fatigue",
                "Weight loss",
                "Reduced appetite",
                "Perianal disease (fistulas, abscesses)",
                "Extraintestinal manifestations (joint pain, eye inflammation, skin lesions)"
            ],
            "lab_markers": [
                "Elevated C-reactive protein (CRP)",
                "Elevated erythrocyte sedimentation rate (ESR)",
                "Elevated fecal calprotectin",
                "Anemia",
                "Hypoalbuminemia",
                "Anti-Saccharomyces cerevisiae antibodies (ASCA) in some patients"
            ],
            "diagnostic_criteria": [
                "Clinical symptoms of chronic or recurrent diarrhea, abdominal pain, weight loss",
                "Endoscopic findings: skip lesions, cobblestone appearance, ulcerations, strictures",
                "Histological findings: transmural inflammation, granulomas (in ~30% of cases)",
                "Radiological findings: bowel wall thickening, skip lesions, fistulas",
                "Exclusion of infectious causes"
            ],
            "misdiagnosis_patterns": [
                "Often misdiagnosed as irritable bowel syndrome (IBS)",
                "Confused with ulcerative colitis",
                "Mistaken for infectious gastroenteritis",
                "Appendicitis (when ileocecal region is involved)",
                "Celiac disease"
            ],
            "demographic_insights": {
                "age_of_onset": "Bimodal distribution: 15-30 years and 50-70 years",
                "gender_ratio": "Slightly more common in females (1.1-1.3:1)",
                "ethnic_patterns": "Higher prevalence in Ashkenazi Jewish populations",
                "geographic_distribution": "Higher in Western industrialized countries, increasing in developing nations",
                "genetic_factors": "First-degree relatives have 10-15× increased risk; NOD2, ATG16L1, IL23R gene associations"
            },
            "zone_classification": 3,
            "stax_score": 3,
            "flare_type": "Inflammatory",
            "symbolic_terrain_tags": [
                "boundary dissolution",
                "digestive mistrust",
                "ancestral grief"
            ]
        },
        {
            "disease_name": "Primary Sjögren's Syndrome",
            "icd_code": "M35.00",
            "common_symptoms": [
                "Dry eyes (xerophthalmia)",
                "Dry mouth (xerostomia)",
                "Fatigue",
                "Joint pain and swelling",
                "Swollen salivary glands",
                "Dry skin",
                "Vaginal dryness",
                "Persistent dry cough",
                "Raynaud's phenomenon",
                "Brain fog and cognitive difficulties"
            ],
            "lab_markers": [
                "Anti-Ro/SSA antibodies (in 70-90%)",
                "Anti-La/SSB antibodies (in 30-60%)",
                "Positive antinuclear antibodies (ANA)",
                "Rheumatoid factor (RF) positivity (in 60-70%)",
                "Hypergammaglobulinemia",
                "Elevated ESR and/or CRP",
                "Complement consumption (low C3/C4) in some cases"
            ],
            "diagnostic_criteria": [
                "Ocular symptoms: daily persistent dry eyes for >3 months",
                "Oral symptoms: daily feeling of dry mouth for >3 months",
                "Ocular signs: abnormal Schirmer's test or ocular staining score",
                "Histopathology: focal lymphocytic sialadenitis in minor salivary gland biopsy",
                "Salivary gland involvement: reduced salivary flow or abnormal sialography",
                "Presence of anti-SSA/Ro and/or anti-SSB/La antibodies",
                "Exclusion of other causes (hepatitis C, radiation, medications, IgG4-related disease)"
            ],
            "misdiagnosis_patterns": [
                "Often dismissed as age-related dryness or menopause",
                "Misdiagnosed as fibromyalgia due to fatigue and pain",
                "Confused with medication side effects",
                "Mistaken for depression or anxiety when fatigue and brain fog predominate",
                "Confused with other autoimmune diseases (SLE, rheumatoid arthritis)"
            ],
            "demographic_insights": {
                "age_of_onset": "Typically 40-60 years",
                "gender_ratio": "Strong female predominance (9:1 female to male ratio)",
                "ethnic_patterns": "More severe in African American and Asian populations",
                "geographic_distribution": "Worldwide distribution with higher prevalence in Northern Europe",
                "genetic_factors": "HLA-DR3, HLA-DQ1, and HLA-DQ2 associations; familial clustering observed"
            },
            "zone_classification": 2,
            "stax_score": 2,
            "flare_type": "Exocrine",
            "symbolic_terrain_tags": [
                "emotional drought",
                "unexpressed grief",
                "feminine depletion"
            ]
        },
        {
            "disease_name": "Fibromyalgia",
            "icd_code": "M79.7",
            "common_symptoms": [
                "Widespread musculoskeletal pain",
                "Tender points at specific locations",
                "Profound fatigue",
                "Sleep disturbances",
                "Cognitive difficulties ('fibro fog')",
                "Headaches",
                "Irritable bowel symptoms",
                "Paresthesias",
                "Temperature sensitivity",
                "Anxiety and depression"
            ],
            "lab_markers": [
                "No specific diagnostic markers",
                "Normal inflammatory markers (ESR, CRP)",
                "Normal autoantibody profiles",
                "Often normal complete blood count",
                "Possible vitamin D deficiency",
                "Sometimes low-normal thyroid function"
            ],
            "diagnostic_criteria": [
                "Widespread pain index (WPI) ≥7 and symptom severity scale (SSS) ≥5, OR WPI 4-6 and SSS ≥9",
                "Symptoms present at similar level for at least 3 months",
                "No other disorder that would otherwise explain the pain",
                "Previously: tender points in at least 11 of 18 specific sites (older criteria)"
            ],
            "misdiagnosis_patterns": [
                "Often misdiagnosed as rheumatoid arthritis or other inflammatory arthritis",
                "Confused with hypothyroidism",
                "Mistaken for chronic fatigue syndrome/ME",
                "Misattributed to depression or somatization disorder",
                "Overlooked when coexisting with other autoimmune conditions"
            ],
            "demographic_insights": {
                "age_of_onset": "Typically 30-50 years, but can occur at any age",
                "gender_ratio": "Female predominance (7:1 female to male ratio)",
                "ethnic_patterns": "Similar prevalence across ethnic groups",
                "geographic_distribution": "Worldwide distribution, estimated 2-8% of population",
                "genetic_factors": "First-degree relatives have 8× increased risk; polymorphisms in serotonin, dopamine, and catecholamine-related genes"
            },
            "zone_classification": 2,
            "stax_score": 2,
            "flare_type": "Neurogenic",
            "symbolic_terrain_tags": [
                "boundary violation",
                "nervous system overwhelm",
                "unprocessed trauma"
            ]
        },
        {
            "disease_name": "Myalgic Encephalomyelitis/Chronic Fatigue Syndrome (ME/CFS)",
            "icd_code": "G93.3",
            "common_symptoms": [
                "Profound fatigue not relieved by rest",
                "Post-exertional malaise (PEM)",
                "Unrefreshing sleep",
                "Cognitive impairment ('brain fog')",
                "Orthostatic intolerance",
                "Muscle pain and weakness",
                "Joint pain without swelling",
                "Headaches",
                "Sore throat",
                "Tender lymph nodes"
            ],
            "lab_markers": [
                "No universally accepted diagnostic markers",
                "Often normal standard laboratory tests",
                "Possible natural killer cell dysfunction",
                "Altered cytokine profiles in some patients",
                "Metabolic abnormalities on specialized testing",
                "Possible reactivated viral titers (EBV, HHV-6, etc.)"
            ],
            "diagnostic_criteria": [
                "Substantial reduction in ability to engage in pre-illness activities",
                "Post-exertional malaise",
                "Unrefreshing sleep",
                "Either cognitive impairment OR orthostatic intolerance",
                "Symptoms present for at least 6 months",
                "Symptoms must be present at least 50% of the time with moderate to severe intensity",
                "Exclusion of other conditions that could explain symptoms"
            ],
            "misdiagnosis_patterns": [
                "Often dismissed as depression or anxiety",
                "Misdiagnosed as fibromyalgia",
                "Confused with primary sleep disorders",
                "Mistaken for deconditioning or laziness",
                "Overlooked when coexisting with other conditions"
            ],
            "demographic_insights": {
                "age_of_onset": "Can occur at any age, peaks in 30s-40s",
                "gender_ratio": "Female predominance (3-4:1 female to male ratio)",
                "ethnic_patterns": "Possibly underdiagnosed in minority populations",
                "geographic_distribution": "Worldwide, estimated 0.2-2% of population",
                "genetic_factors": "Increased risk in first-degree relatives; associations with HLA complex and immune-related genes"
            },
            "zone_classification": 3,
            "stax_score": 3,
            "flare_type": "Mitochondrial",
            "symbolic_terrain_tags": [
                "energy depletion",
                "cellular hibernation",
                "system shutdown"
            ]
        },
        {
            "disease_name": "Chronic Lyme Disease/Post-Treatment Lyme Disease Syndrome",
            "icd_code": "A69.20",
            "common_symptoms": [
                "Persistent fatigue",
                "Cognitive difficulties",
                "Migratory joint and muscle pain",
                "Paresthesias and neuropathic pain",
                "Sleep disturbances",
                "Headaches",
                "Neck stiffness",
                "Palpitations and dysautonomia",
                "Mood changes",
                "Relapsing-remitting pattern of symptoms"
            ],
            "lab_markers": [
                "Variable serologic testing results (ELISA, Western blot)",
                "Possible CD57+ NK cell depression",
                "Normal inflammatory markers in many cases",
                "Possible coinfection markers (Babesia, Bartonella, etc.)",
                "Specialized testing with variable validation (ELISpot, etc.)"
            ],
            "diagnostic_criteria": [
                "History of confirmed or probable Lyme disease",
                "Completion of standard antibiotic treatment",
                "Persistence of symptoms for ≥6 months after treatment",
                "Significant impact on quality of life and functioning",
                "Exclusion of other conditions that could explain symptoms",
                "Note: Controversial diagnosis with varying criteria between medical societies"
            ],
            "misdiagnosis_patterns": [
                "Often misdiagnosed as fibromyalgia or chronic fatigue syndrome",
                "Confused with multiple sclerosis or other neurological conditions",
                "Mistaken for psychiatric disorders",
                "Overlooked in favor of other tick-borne diseases",
                "Controversy between 'overdiagnosis' and 'underdiagnosis' perspectives"
            ],
            "demographic_insights": {
                "age_of_onset": "Can occur at any age, follows acute Lyme disease",
                "gender_ratio": "Possibly higher in females",
                "ethnic_patterns": "More commonly diagnosed in Caucasians",
                "geographic_distribution": "Highest in endemic Lyme regions (Northeast/Upper Midwest US, parts of Europe)",
                "genetic_factors": "Possible HLA associations with post-treatment symptoms"
            },
            "zone_classification": 2,
            "stax_score": 3,
            "flare_type": "Infectious",
            "symbolic_terrain_tags": [
                "persistent invader",
                "stealth pathogen",
                "immune confusion"
            ]
        },
        {
            "disease_name": "Sarcoidosis",
            "icd_code": "D86.9",
            "common_symptoms": [
                "Fatigue",
                "Persistent dry cough",
                "Shortness of breath",
                "Chest pain",
                "Skin lesions (erythema nodosum, lupus pernio)",
                "Joint pain and swelling",
                "Eye inflammation (uveitis)",
                "Enlarged lymph nodes",
                "Neurological symptoms (in neurosarcoidosis)",
                "Cardiac arrhythmias (in cardiac sarcoidosis)"
            ],
            "lab_markers": [
                "Elevated angiotensin-converting enzyme (ACE) in 60-70%",
                "Elevated calcium levels (in ~10%)",
                "Elevated liver enzymes (in hepatic involvement)",
                "Elevated inflammatory markers (ESR, CRP)",
                "Hypergammaglobulinemia",
                "Lymphopenia in some cases"
            ],
            "diagnostic_criteria": [
                "Compatible clinical and radiological findings",
                "Histological evidence of non-caseating granulomas",
                "Exclusion of other granulomatous diseases",
                "Multisystem involvement typical",
                "Bronchoalveolar lavage showing CD4/CD8 ratio >3.5 supportive",
                "Löfgren's syndrome (acute presentation with bilateral hilar lymphadenopathy, erythema nodosum, and arthritis) is distinctive"
            ],
            "misdiagnosis_patterns": [
                "Often misdiagnosed as tuberculosis or other infections",
                "Confused with lymphoma",
                "Mistaken for idiopathic pulmonary fibrosis",
                "Cardiac sarcoidosis confused with cardiomyopathy of other causes",
                "Neurosarcoidosis mistaken for multiple sclerosis"
            ],
            "demographic_insights": {
                "age_of_onset": "Typically 20-40 years",
                "gender_ratio": "Slight female predominance",
                "ethnic_patterns": "Higher incidence and severity in African Americans and Northern Europeans",
                "geographic_distribution": "Worldwide, with highest prevalence in Scandinavian countries and among African Americans",
                "genetic_factors": "Familial clustering; associations with HLA-DRB1 and BTNL2 genes"
            },
            "zone_classification": 3,
            "stax_score": 3,
            "flare_type": "Granulomatous",
            "symbolic_terrain_tags": [
                "cellular walling-off",
                "tissue isolation",
                "systemic boundaries"
            ]
        }
    ]
    
    for profile in additional_profiles:
        processed_disease_profiles.append(normalize_dict(profile))
    
    existing_tag_names = {tag.get("tagName") for tag in medical_data["autoimmuneTags"]}
    new_tags_count = 0
    for tag in processed_tags:
        if tag.get("tagName") not in existing_tag_names:
            medical_data["autoimmuneTags"].append(tag)
            existing_tag_names.add(tag.get("tagName"))
            new_tags_count += 1
    
    existing_citation_ids = {citation.get("citationId") for citation in medical_data["citations"]}
    new_citations_count = 0
    for citation in processed_citations:
        if citation.get("citationId") not in existing_citation_ids:
            medical_data["citations"].append(citation)
            existing_citation_ids.add(citation.get("citationId"))
            new_citations_count += 1
    
    existing_disease_names = {profile.get("diseaseName") for profile in medical_data["diseaseProfiles"]}
    new_profiles_count = 0
    for profile in processed_disease_profiles:
        if profile.get("diseaseName") not in existing_disease_names:
            medical_data["diseaseProfiles"].append(profile)
            existing_disease_names.add(profile.get("diseaseName"))
            new_profiles_count += 1
    
    with open(MEDICAL_DATA_PATH, 'w') as f:
        json.dump(medical_data, f, indent=2)
    
    print(f"Added {new_tags_count} new autoimmune tags to medical_data.json")
    print(f"Added {new_citations_count} new citations to medical_data.json")
    print(f"Added {new_profiles_count} new disease profiles to medical_data.json")

if __name__ == "__main__":
    main()
