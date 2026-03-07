/**
 * 2OPMD Mobile — Onboarding Store (Zustand)
 *
 * Collects all data from onboarding screens O1-O17.
 * Persisted in memory during onboarding flow; submitted on O15 (Save Progress).
 */

import { create } from 'zustand';

export type SeverityLevel = 'mild' | 'moderate' | 'severe' | 'flare';

export interface DayEntry {
  day: number;
  severity: SeverityLevel | null;
}

export type UserPath = 'diagnosed' | 'searching' | null;

export type GenderIdentity = 'female' | 'male' | 'another' | 'prefer_not_to_say' | null;

interface OnboardingState {
  // O5 — Name
  name: string;
  setName: (name: string) => void;

  // O6 — Age
  ageRange: string | null;
  setAgeRange: (range: string) => void;

  // O7 — Gender Identity
  genderIdentity: GenderIdentity;
  genderIdentityCustom: string;
  setGenderIdentity: (identity: GenderIdentity) => void;
  setGenderIdentityCustom: (text: string) => void;

  // O8 — Diagnosed vs Searching
  userPath: UserPath;
  setUserPath: (path: UserPath) => void;

  // O9A — Diagnosed Path
  diagnoses: string[];
  setDiagnoses: (diagnoses: string[]) => void;
  toggleDiagnosis: (diagnosis: string) => void;

  // O9B — Searching Path
  searchingExplanation: string;
  setSearchingExplanation: (text: string) => void;

  // O10 — 30-Day Bad-Day Map
  dayMap: DayEntry[];
  setDaySeverity: (day: number, severity: SeverityLevel | null) => void;

  // O11 — Emotional Context
  selectedEmotions: string[];
  toggleEmotion: (emotion: string) => void;

  // O12 — Top Symptoms
  selectedSymptoms: string[];
  toggleSymptom: (symptom: string) => void;

  // O16 — Optional Records
  hasUploadedRecords: boolean;
  setHasUploadedRecords: (value: boolean) => void;

  // Progress tracking
  currentStep: number;
  totalSteps: number;
  setCurrentStep: (step: number) => void;

  // Reset
  resetOnboarding: () => void;
}

const initialDayMap: DayEntry[] = Array.from({ length: 30 }, (_, i) => ({
  day: i + 1,
  severity: null,
}));

const initialState = {
  name: '',
  ageRange: null as string | null,
  genderIdentity: null as GenderIdentity,
  genderIdentityCustom: '',
  userPath: null as UserPath,
  diagnoses: [] as string[],
  searchingExplanation: '',
  dayMap: initialDayMap,
  selectedEmotions: [] as string[],
  selectedSymptoms: [] as string[],
  hasUploadedRecords: false,
  currentStep: 1,
  totalSteps: 17,
};

export const useOnboardingStore = create<OnboardingState>((set) => ({
  ...initialState,

  setName: (name) => set({ name }),
  setAgeRange: (ageRange) => set({ ageRange }),
  setGenderIdentity: (genderIdentity) => set({ genderIdentity }),
  setGenderIdentityCustom: (genderIdentityCustom) => set({ genderIdentityCustom }),
  setUserPath: (userPath) => set({ userPath }),
  setDiagnoses: (diagnoses) => set({ diagnoses }),
  toggleDiagnosis: (diagnosis) =>
    set((state) => ({
      diagnoses: state.diagnoses.includes(diagnosis)
        ? state.diagnoses.filter((d) => d !== diagnosis)
        : [...state.diagnoses, diagnosis],
    })),
  setSearchingExplanation: (searchingExplanation) => set({ searchingExplanation }),
  setDaySeverity: (day, severity) =>
    set((state) => ({
      dayMap: state.dayMap.map((entry) =>
        entry.day === day ? { ...entry, severity } : entry,
      ),
    })),
  toggleEmotion: (emotion) =>
    set((state) => {
      if (state.selectedEmotions.includes(emotion)) {
        return { selectedEmotions: state.selectedEmotions.filter((e) => e !== emotion) };
      }
      if (state.selectedEmotions.length >= 5) return state;
      return { selectedEmotions: [...state.selectedEmotions, emotion] };
    }),
  toggleSymptom: (symptom) =>
    set((state) => ({
      selectedSymptoms: state.selectedSymptoms.includes(symptom)
        ? state.selectedSymptoms.filter((s) => s !== symptom)
        : [...state.selectedSymptoms, symptom],
    })),
  setHasUploadedRecords: (hasUploadedRecords) => set({ hasUploadedRecords }),
  setCurrentStep: (currentStep) => set({ currentStep }),
  resetOnboarding: () => set(initialState),
}));
