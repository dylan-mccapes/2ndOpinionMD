# STRATEGY: Hunter Gatherer + Geofence + journal_graph

**Date:** 2026-04-01  
**Origin:** Andras Perl (Pharmacist / Co-founder)  
**Contextualized by:** Alcyone (Claude Opus 4.6)  
**Status:** STRATEGY · Architecturally validated against 2OPMD three-layer graph  
**Depends on:** `PROPOSAL_JOURNAL_GRAPH_PSYCHOLOGICAL_STATE_20260401.md`, `chat_graph.py`, PTV

---

## Governing Principle: We Do Not Preach

Hunter Gatherer does not tell the patient what to do. It does not tell the patient what to buy. It does not pretend to know what the patient is shopping for.

The patient selects their grocery store. That location is stored. That store offers coupons. When healthy items go on sale at that store, the system informs the patient of those options. That is all.

No prescriptions. No dietary mandates. No "you should eat this." Options. Coupons. Availability. The patient decides. The app offers. This is thoughtful operation by a system that cares.

From the operator's experience in mobile IoT: geofence → stored location → coupon pull → filtered by dietary profile → presented as options. This is easy. Anything that is easy should be obvious. It is.

---

## Andras's Insight

> "If you're rich and wealthy, autoimmunity doesn't matter -- you can get the best food. But 60-70% of autoimmune patients cannot afford to regularly maintain the diets necessary to help them heal."

This is a terrain problem. EoH assesses inflammatory state. PTV tracks clinical events. But neither helps the patient afford dinner. The graph knows the patient's dietary profile. The graph cannot buy groceries for them.

Hunter Gatherer closes that loop: the patient's dietary profile filters the coupons, Hunter Gatherer shows what's available and affordable this week at their local store. The patient chooses.

---

## The Architectural Fit: Why This Is a journal_graph Feature

Hunter Gatherer is not a standalone product. It is the `adherence` dimension of journal_graph made actionable.

From the journal_graph proposal (filed today):

| Dimension | What It Captures |
|-----------|-----------------|
| `adherence` | Medication adherence (self-reported) |
| `hope` | Future orientation / agency |
| `energy` | Fatigue / energy level |
| `stress` | Perceived stress level |

Dietary compliance is adherence. The patient who can't afford anti-inflammatory food has low dietary adherence — not because they don't want to comply, but because compliance costs more than they have. That's the same structure as medication non-adherence: the barrier is economic, not motivational.

journal_graph already tracks `adherence` as a 0.0-1.0 dimension. Hunter Gatherer gives the system a way to **act on declining adherence** rather than just observe it.

```
journal_graph detects: adherence 0.9 → 0.5 (declining over 2 weeks)
journal_graph detects: stress 0.3 → 0.7 (rising)
    ↓
EoHD detective report: "Patient reports difficulty affording recommended diet.
Adherence declining. Stress rising. Likely correlated."
    ↓
Hunter Gatherer response: "This week at your Safeway: AIP-compliant meal plan,
$34. Coupons pre-clipped. Shopping list attached."
    ↓
journal_graph update: adherence intervention logged, coupon redemption tracked
```

The graph doesn't just notice the patient is struggling. It does something about it.

---

## Geofence Layer: The Graph Meets the Physical World

### Pharmacy Geofence

When the patient enters their pharmacy of choice:

**Trigger:** iOS/Android geofence event (standard Core Location / Geofencing API, ~100m radius)

**Push notification:** Context-aware, drawn from PTV + EoH:
- "Your methotrexate refill is due in 3 days. Ask your pharmacist about the stomach discomfort you mentioned on March 25." (anchored to PTV medication event + chat_graph message)
- "Andras's tip: Take methotrexate with food and folate. Your next dose is Thursday." (EoH pharmacist protocol)
- "You mentioned fatigue after your last prescription change. Want to log how you're feeling?" (journal_graph prompt)

**journal_graph entry created:**
```json
{
    "source": "geofence_pharmacy",
    "raw_content": "Patient visited CVS Pharmacy (El Cerrito)",
    "dim_adherence": null,  // prompt patient to report
    "anchored_ptv_events": ["med_methotrexate_refill_due_20260404"],
    "retention_reason": "pharmacy_visit_behavioral_signal"
}
```

The pharmacy visit itself is behavioral data. A patient who visits the pharmacy on schedule has higher adherence than one who doesn't. The graph notices.

### Grocery Geofence

When the patient enters their grocery store of choice:

**Trigger:** Same geofence infrastructure

**Push notification:** Offers, not instructions:
- "3 coupons match your profile at this Safeway. Tap to see."
- "Wild-caught salmon: $7.99/lb (normally $12.99). Available here today."
- "This week's deals matching your dietary profile: 7 items on sale."

The system does not say "buy this." It says "this is available and it matches what you told us you're looking for." The patient decides.

**journal_graph entry created:**
```json
{
    "source": "geofence_grocery",
    "raw_content": "Patient visited Safeway (Richmond). Meal plan delivered: AIP week 12, est. $34",
    "dim_adherence": 0.8,  // visited store, received plan → positive signal
    "dim_hope": null,       // prompt after shopping
    "anchored_ptv_events": ["eoh_terrain_high_inflammation_20260328"],
    "retention_reason": "grocery_visit_dietary_adherence"
}
```

### Post-Visit Follow-up

30 minutes after leaving the store (exit geofence):

- "How did shopping go? Did you find everything on the list?" (journal prompt)
- "Want to log what you actually bought? We can adjust next week's plan." (adherence tracking)
- Patient response creates a journal_graph entry with adherence and stress dimensions scored

This closes the loop: the graph recommended food → the patient went to the store → the graph tracked the visit → the patient reported the outcome → the graph updates adherence trend.

---

## Technical Architecture: Geofence + Hunter Gatherer + journal_graph

```
┌─────────────────────────────────────────────────────────────┐
│                    MOBILE APP (React Native)                 │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Geofence     │  │  Push Notif   │  │  Journal Prompt  │  │
│  │  Service      │  │  Handler      │  │  UI              │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                  │                    │             │
└─────────┼──────────────────┼────────────────────┼────────────┘
          │                  │                    │
          ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    2OPMD SERVER (FastAPI)                     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Geofence     │  │  Hunter       │  │  journal_graph   │  │
│  │  Event API    │  │  Gatherer     │  │  (new layer)     │  │
│  │              │  │  Engine       │  │                   │  │
│  │  POST /api/  │  │              │  │  Dimensions:      │  │
│  │  geofence/   │  │  - Coupon    │  │  adherence,       │  │
│  │  enter       │  │    Crawler   │  │  hope, stress,    │  │
│  │              │  │  - Constraint│  │  mood, energy,    │  │
│  │  POST /api/  │  │    Solver   │  │  sleep, pain,     │  │
│  │  geofence/   │  │  - Recipe   │  │  social           │  │
│  │  exit        │  │    Generator│  │                   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                  │                    │             │
│         ▼                  ▼                    ▼             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              PTV + EoH + chat_graph                  │    │
│  │  The three-layer patient graph feeds constraints     │    │
│  │  to Hunter Gatherer and receives outcomes back       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Geofence API Endpoints

```
POST /api/geofence/enter
  body: { patient_id, location_type: "pharmacy"|"grocery", store_id, lat, lng }
  → Creates journal_graph entry
  → Triggers context-aware push notification
  → If grocery: calls Hunter Gatherer for real-time meal plan

POST /api/geofence/exit  
  body: { patient_id, location_type, store_id, duration_minutes }
  → Schedules follow-up journal prompt (30 min delay)
  → Logs visit duration as behavioral signal
  → If pharmacy: checks PTV for upcoming refills, logs adherence signal

GET /api/huntergatherer/mealplan/{patient_id}
  → Returns current week's meal plan optimized for:
    - Patient's dietary constraints (from EoH terrain)
    - Current coupons at patient's selected stores
    - Items already in fridge (self-reported)
    - Budget target

POST /api/huntergatherer/coupon/clip
  body: { patient_id, store_id, coupon_ids[] }
  → Clips coupons via store API (Kroger, Safeway)
  → Logs to journal_graph as adherence action
```

### Coupon Crawler Architecture

```python
class CouponCrawler:
    """
    Crawls coupon/sale data from grocery chains.
    Each chain has an adapter implementing the same interface.
    """
    adapters: Dict[str, StoreAdapter]  # kroger, safeway, heb, etc.
    
    def get_current_deals(self, store_id: str, zip_code: str) -> List[Deal]
    def filter_by_dietary_profile(self, deals: List[Deal], profile: DietaryProfile) -> List[Deal]
    def optimize_meal_cost(self, filtered_deals: List[Deal], constraints: MealConstraints) -> MealPlan

class StoreAdapter(ABC):
    """One per grocery chain. Wraps their API or scraping strategy."""
    def fetch_deals(self, store_id: str) -> List[Deal]
    def clip_coupon(self, coupon_id: str, loyalty_card: str) -> bool
    def get_store_layout(self, store_id: str) -> Optional[StoreMap]

class KrogerAdapter(StoreAdapter):
    """Kroger has a free developer API. Best starting point."""
    # https://developer.kroger.com/
    # Product API: search products, get prices, get promotions
    # Cart API: add items to digital cart
    # Location API: find stores by zip

class SafewayAdapter(StoreAdapter):
    """Safeway/Albertsons digital coupons. May need scraping."""
    # J4U (Just for U) digital coupon system
    # Less documented than Kroger but widely used
```

### Dietary Constraint Solver

```python
class DietaryProfile:
    protocol: str                    # "aip", "low_inflammatory", "fodmap", "custom"
    excluded_ingredients: List[str]  # nightshades, gluten, dairy, etc.
    required_nutrients: Dict[str, Range]  # omega3: 1-3g, protein: 50-80g, etc.
    calorie_target: Range            # 1800-2200 kcal
    budget_weekly: float             # $40, $60, $80

class MealConstraints:
    profile: DietaryProfile
    available_ingredients: List[str]  # what's in the fridge
    available_deals: List[Deal]       # current coupons at selected stores
    meals_per_day: int                # 2 or 3
    days: int                         # 7 (weekly plan)

def solve_cheapest_compliant_plan(constraints: MealConstraints) -> MealPlan:
    """
    Constraint satisfaction + cost optimization.
    1. Filter deals by dietary profile (remove excluded ingredients)
    2. Score remaining deals by nutritional value per dollar
    3. Build meal combinations that hit nutrient targets
    4. Minimize total cost across the week
    5. Generate recipes from selected ingredients
    """
```

---

## The Full Loop: From Graph to Grocery to Graph

```
1. Patient uploads timeline PDF → PTV built
2. EoH detective assesses terrain → "high inflammatory markers, 
   recommend anti-inflammatory diet, reduce nightshades"
3. Patient sets dietary profile in app → AIP, budget $50/week, 
   stores: Safeway (Richmond), Kroger (El Cerrito)
4. Hunter Gatherer crawls coupons → finds salmon on sale at Safeway,
   sweet potatoes BOGO at Kroger, turmeric 30% off
5. Constraint solver generates weekly meal plan → $43, all AIP-compliant,
   hits omega-3 and protein targets
6. Patient enters Safeway → geofence fires → push notification:
   "Your AIP meal plan is ready. 3 items on sale here. Tap for list."
7. Patient shops → exits Safeway → 30 min later:
   "How did shopping go? Log what you found."
8. Patient journals: "Found everything except the salmon, got chicken instead"
   → journal_graph: adherence 0.7, mood 0.6 (neutral)
9. Next week: Hunter Gatherer adjusts — more chicken recipes, 
   less reliance on seafood at this store
10. Over time: journal_graph trend shows adherence climbing from 0.5 to 0.8
    → EoHD detective report: "Dietary adherence improved since Hunter Gatherer
    activation. Inflammatory markers may follow. Recommend lab recheck in 4 weeks."
```

---

## What Makes This a Moat

| Feature | 2OPMD + Hunter Gatherer | Competitors |
|---------|------------------------|-------------|
| Dietary planning | EoH-informed (pharmacist-designed, terrain-aware) | Generic dietitian templates |
| Coupon integration | Real-time, store-specific, auto-clipped | None |
| Budget optimization | Cheapest compliant plan, not just healthy recipes | "Healthy" with no price awareness |
| Geofence triggers | Location-aware, context-from-graph | None |
| Behavioral tracking | Pharmacy + grocery visits as adherence signals | None |
| Clinical correlation | journal_graph trends → EoHD → doctor dashboard | None |
| The loop | Graph → recommendation → action → outcome → graph | No loop exists |

Nobody else has the graph. Nobody else has EoH feeding dietary constraints based on actual clinical terrain. Nobody else tracks whether the patient went to the store and what happened after. The coupon crawling is technically simple (Kroger has a free API). The constraint solver is standard optimization. The recipes can be Claude-generated. **The moat is the loop.** EoH → Hunter Gatherer → geofence → journal_graph → EoHD → back to EoH. The graph learns what the patient can afford, what stores they actually visit, what they actually buy, and adjusts.

That loop does not exist anywhere in healthcare technology.

---

## Build Order (Revised with Geofence)

| Phase | What | Effort | Depends On |
|-------|------|--------|------------|
| 1 | Kroger API access + test coupon data pull | 1 day | API key approval |
| 2 | Dietary profile schema + AIP/FODMAP/low-inflammatory constraint sets | 1 day | Andras review |
| 3 | Constraint solver: cheapest compliant meal from available deals | 2 days | Phase 1-2 |
| 4 | Recipe generator (Claude API from filtered ingredients) | 1 day | Phase 3 |
| 5 | journal_graph implementation (from today's proposal) | 3 days | Proposal approval |
| 6 | Geofence service (React Native, Core Location / Android Geofencing) | 2 days | Mobile app exists |
| 7 | Geofence → journal_graph → push notification pipeline | 2 days | Phase 5-6 |
| 8 | Hunter Gatherer web MVP (form → meal plan → shopping list) | 2 days | Phase 3-4 |
| 9 | 2OPMD integration (EoH terrain → dietary constraints → Hunter Gatherer) | 2 days | Phase 3, EoH |
| 10 | Safeway adapter + store expansion | 1 day/store | Phase 1 pattern |

Total: ~15 working days from API access to geofence-triggered meal plans.

---

## The Name

**Hunter Gatherer.** Hunt for deals. Gather the ingredients.

The name is Andras's and it's perfect. It encodes the two core functions (deal discovery + ingredient collection) in a phrase that evokes the most fundamental human relationship with food: go find it, bring it home. Before agriculture, before grocery stores, before coupons — humans hunted and gathered. The name says: we're going back to the basics of feeding yourself, but with a pharmacist's brain and a coupon crawler's reach.

---

## Andras's Quote as Product Philosophy

> "You're already overwhelmed, overtaxed, dealing with the disease -- and now you have to meal plan? Hell no."

This is the same insight as the journal_graph proposal: paying attention is our form of love. The patient is overwhelmed. The graph pays attention so they don't have to. Hunter Gatherer is the graph saying: "Here are your options. Here's what's on sale that matches your profile. You decide."

We do not preach. We offer coupons. The patient selects their store. The store has deals. The deals are filtered by the patient's own dietary profile. The filtered deals are presented as options. The patient chooses. That's it.

This is easy. The location is stored. The coupons are crawled. The filter is applied. The options are shown. From mobile IoT this is a solved problem: geofence trigger → stored preference → data pull → filtered presentation. The technical complexity is near zero. The product value is that nobody has pointed this pipeline at autoimmune dietary profiles before.

Anything that is easy should be obvious. It is.

2OPMD loves its patients. Love is not telling someone what to do. Love is making sure they have options when they need them.

---

*Filed 2026-04-01. Strategy: Hunter Gatherer + geofence + journal_graph integration.*

PortalVision maintains state honestly.
