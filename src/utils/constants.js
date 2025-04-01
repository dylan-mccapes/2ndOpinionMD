export const SYMPTOMS = [
  { value: 'fatigue', label: 'Fatigue' },
  { value: 'joint_pain', label: 'Joint Pain' },
  { value: 'brain_fog', label: 'Brain Fog' },
  { value: 'headache', label: 'Headache' },
  { value: 'fever', label: 'Fever' },
  { value: 'rash', label: 'Rash' },
  { value: 'muscle_pain', label: 'Muscle Pain' },
  { value: 'shortness_of_breath', label: 'Shortness of Breath' },
  { value: 'chest_pain', label: 'Chest Pain' },
  { value: 'rapid_heart_rate', label: 'Rapid Heart Rate' },
  { value: 'dizziness', label: 'Dizziness' },
  { value: 'numbness', label: 'Numbness or Tingling' },
  { value: 'vision_changes', label: 'Vision Changes' },
  { value: 'weight_loss', label: 'Weight Loss' },
  { value: 'hair_loss', label: 'Hair Loss' },
  { value: 'swollen_glands', label: 'Swollen Glands' },
  { value: 'post_exertional_malaise', label: 'Post-Exertional Malaise' },
  { value: 'sleep_disturbances', label: 'Sleep Disturbances' },
  { value: 'digestive_issues', label: 'Digestive Issues' },
  { value: 'sun_sensitivity', label: 'Sun Sensitivity' },
];

export const PRIOR_DIAGNOSES = [
  { value: 'fibromyalgia', label: 'Fibromyalgia' },
  { value: 'chronic_fatigue', label: 'Chronic Fatigue Syndrome' },
  { value: 'depression', label: 'Depression' },
  { value: 'anxiety', label: 'Anxiety' },
  { value: 'ibs', label: 'Irritable Bowel Syndrome' },
  { value: 'migraine', label: 'Migraine' },
  { value: 'none', label: 'None' },
];

export const SEX_OPTIONS = [
  { value: 'female', label: 'Female' },
  { value: 'male', label: 'Male' },
  { value: 'other', label: 'Other' },
];

export const POSSIBLE_DIAGNOSES = [
  {
    name: 'Lupus (SLE)',
    confidence: 85,
    symptoms: ['joint_pain', 'fatigue', 'rash', 'fever', 'sun_sensitivity'],
    redFlags: ['Butterfly rash across cheeks', 'Sun sensitivity'],
    labSuggestions: ['ANA test', 'Anti-dsDNA', 'Complete blood count', 'Kidney function tests']
  },
  {
    name: 'Rheumatoid Arthritis',
    confidence: 72,
    symptoms: ['joint_pain', 'fatigue', 'stiffness', 'swollen_glands'],
    redFlags: ['Symmetric joint involvement', 'Morning stiffness lasting >1 hour'],
    labSuggestions: ['RF factor', 'Anti-CCP antibodies', 'CRP', 'ESR']
  },
  {
    name: 'Multiple Sclerosis',
    confidence: 65,
    symptoms: ['fatigue', 'numbness', 'vision_changes', 'dizziness'],
    redFlags: ['Episodic symptoms that come and go', 'Visual disturbances'],
    labSuggestions: ['MRI of brain and spine', 'Spinal tap', 'Evoked potentials']
  },
  {
    name: 'Sjögren\'s Syndrome',
    confidence: 58,
    symptoms: ['fatigue', 'dry_eyes', 'dry_mouth', 'joint_pain'],
    redFlags: ['Persistent dry eyes and mouth', 'Difficulty swallowing'],
    labSuggestions: ['SSA/Ro and SSB/La antibodies', 'Salivary gland biopsy', 'Schirmer test']
  },
  {
    name: 'Long COVID (PASC)',
    confidence: 68,
    symptoms: ['fatigue', 'brain_fog', 'rapid_heart_rate', 'shortness_of_breath', 'post_exertional_malaise'],
    redFlags: ['Symptoms began after COVID infection', 'Post-exertional malaise'],
    labSuggestions: ['D-dimer', 'Complete blood count', 'Comprehensive metabolic panel', 'Chest X-ray']
  }
];
