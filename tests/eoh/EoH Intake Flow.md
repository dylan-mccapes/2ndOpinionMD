# **EoH CHATBOT INTAKE FLOW TREE (Option A)**

### ***Diagnosis-agnostic, signal-driven, and designed for adaptive probing.***

---

# **0\. WELCOME BLOCK**

**Bot:**  
 “Hi, I’m here to help understand what’s been going on with your health. I’ll ask simple questions one at a time. You can type short answers, long answers, or speak in your own words.”

Proceed → Node 1\.

---

# **1\. ORIGIN STORY — SYMPTOM ONSET**

**Bot:**  
 “When did you first start noticing any symptoms or changes in your health?”

### **Triggers & Follow-Ups**

* **Mentions timeline (“months ago”, “last week”):**  
   “Have things been mostly improving, worsening, or up-and-down since then?”

* **Mentions sudden event (injury, infection, stress):**  
   “Got it. Did anything seem to change right after that?”

* **Mentions long-standing issues:**  
   “Have these stayed the same over time or become more noticeable recently?”

Proceed → Node 2\.

---

# **2\. PRIMARY SYMPTOM AREAS**

**Bot:**  
 “What part of your body or daily life has been the most affected lately?”

*(Let the patient define the frame. No body system is suggested.)*

### **Trigger Detection**

If they mention:

* **Pain / stiffness / weakness / numbness:** → open “movement” deep-dive.

* **Breathing issues:** → open “respiratory” deep-dive.

* **Digestion issues:** → GI branch.

* **Low energy / fatigue:** → energy branch.

* **Sleep issues:** → sleep branch.

* **Mood or cognitive changes:** → psychosocial branch.

* **Skin issues:** → dermatologic branch.

* **Multiple systems:** → multi-system follow-up.

### **Universal Follow-Up**

“Does this feeling stay in one place, or does it move or spread?”

Proceed → appropriate branch (2A–2G), then → Node 3\.

---

## **2A. MOVEMENT / JOINT / MUSCLE BRANCH (Diagnosis-agnostic)**

**Bot:**  
 “Can you describe what the sensation feels like — discomfort, stiffness, tightness, weakness, or something else?”

**Triggers:**

* If they mention **timing** → ask:  
   “When is it usually at its best or worst during the day?”

* If they mention **symmetry** → tag but don’t probe diagnostically.

* If they mention **swelling** →  
   “Have you noticed swelling, warmth, or changes in how that area looks?”

* If they mention **difficulty using the area:**  
   “What tasks has this made more challenging?”

Return → Node 3\.

---

## **2B. ENERGY / FATIGUE BRANCH**

**Bot:**  
 “How has your energy level been recently?”

Follow-ups:

* “Is the tiredness constant or does it come and go?”

* “Is it worse at certain times of day?”

Return → Node 3\.

---

## **2C. RESPIRATORY BRANCH (safety-sensitive)**

**Bot:**  
 “Thanks for sharing that. Can you tell me more about the breathing issue you noticed?”

**Triggers:**  
 If **shortness of breath**, **chest tightness**, or **rapid breathing**:  
 → open **Red Flag Pathway** (Node 9).

Return → Node 3\.

---

## **2D. GI BRANCH**

“Have you noticed changes in digestion, appetite, or nausea?”

Return → Node 3\.

---

## **2E. SLEEP BRANCH**

“How has your sleep been lately?”

Return → Node 3\.

---

## **2F. MOOD / COGNITION BRANCH**

“How have your mood, focus, or stress levels been affected?”

If emotional heaviness, denial, catastrophic language →  
 Tag for **PSI cues** → Node 5 later.

Return → Node 3\.

---

## **2G. SKIN / SENSORY BRANCH**

“Any changes in your skin or sensations?”

Return → Node 3\.

---

# **3\. FUNCTIONAL IMPACT**

**Bot:**  
 “What everyday tasks have become harder recently, if any?”

### **Trigger Follow-Ups**

* Grip/task difficulty →  
   “Is this something new or has it been happening for a while?”

* Walking/stairs →  
   “What makes it easier or harder?”

* Concentration/mental fatigue →  
   “Does this fluctuate or stay steady?”

Proceed → Node 4\.

---

# **4\. SYMPTOM SEVERITY (0–10)**

**Bot:**  
 “On a 0–10 scale, how would you rate your discomfort or symptoms on an average day?”

Then:  
 “What about your energy or fatigue level on a 0–10 scale?”

### **Trigger**

If **≥7** → open escalation-lite:  
 “What tends to push it to the highest levels?”

Proceed → Node 5\.

---

# **5\. PATTERNS & CYCLING**

**Bot:**  
 “Do your symptoms follow any patterns — certain times of day, certain activities, or certain days/weeks?”

### **Trigger Handling**

If pattern detected:

* morning → tag

* activity-triggered → tag

* weather-triggered → tag

* food-triggered → tag

* cyclical → tag

Proceed → Node 6\.

---

# **6\. HEALTH HISTORY (Neutral, Non-Diagnostic)**

**Bot:**  
 “Have you been diagnosed with any ongoing health conditions in the past?”

If yes:  
 “Just list whatever you remember — even short notes are fine.”

No further probing.

Proceed → Node 7\.

---

# **7\. MEDICATIONS & CHANGES**

**Bot:**  
 “What medications or supplements are you currently taking?”

Follow-up triggers:

* “Any recent changes in dose or new medications?”

* “Have you noticed improvements or side effects?”

Proceed → Node 8\.

---

# **8\. RECENT TESTING**

**Bot:**  
 “Have you had any recent blood tests, imaging, or other medical tests done?”

If yes:  
 “Do you have access to the results or a patient portal?”

If they say yes → tag for portal access.

Proceed → Node 9\.

---

# **9\. RED FLAG PATHWAY (Adaptive Safety)**

This only activates if earlier signals triggered it.

**Bot (gentle tone):**  
 “Just to make sure we fully understand your situation, have you experienced any of the following?”

* Fevers or night sweats?

* Unintentional weight loss?

* New shortness of breath?

* Rapid swelling anywhere?

Follow-up thresholds:

* If **yes** to any →  
   “When did this start?”  
   “Has it been getting worse quickly?”  
   → Flag for clinician review.

* If severe →  
   “Thank you for sharing this. Based on what you’re describing, it might help to get timely medical attention. Would you like help summarizing this for your clinician?”

Return → Node 10\.

---

# **10\. STRESS & LIFE CONTEXT**

**Bot:**  
 “How has your stress, sleep, or overall life load been recently?”

Follow-up:  
 “Has anything in the past few months significantly affected your day-to-day health?”

Proceed → Node 11\.

---

# **11\. EHR / PORTAL ACCESS**

**Bot:**  
 “Do you use a patient portal like MyChart?  
 If you’re open to sharing temporary read-only access, we can automatically gather your labs and history. This is optional.”

Proceed → Node 12\.

---

# **12\. OPEN FIELD**

**Bot:**  
 “Is there anything else you want us to know about what you’ve been experiencing?”

Capture final narrative \+ PSI cues.

---

# **END OF INTAKE**

**Bot:**  
 “Thank you — this gives us enough to build your health timeline and pattern map. We’ll process everything and share next steps soon.”

