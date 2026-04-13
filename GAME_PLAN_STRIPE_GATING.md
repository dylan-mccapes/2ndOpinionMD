# GAME_PLAN — Stripe Subscription Gating
**Goal:** Gate Timeline and Detective behind a paid subscription. Journal remains free forever.  
**Payment processor:** Stripe → Mercury bank account  
**Model:** Free tier (Journal) + Pro tier (Timeline + Detective)

---

## Product philosophy

> Journaling over time is the foundation. With eoh-llama 8b analyzing entries locally, a free user already gets genuine clinical value. Timeline and Detective unlock the full EoH reasoning loop — they require ingested data, which requires infrastructure cost. That cost maps to a paid tier.

### Tiers

| Tier | Price | Features |
|---|---|---|
| **Free** | $0/mo | Symptom Journal (unlimited entries), AI journal query, pattern analysis |
| **Clinical** | $12/mo or $99/yr | Everything Free + Timeline upload + Health Insights analytics + Detective + Flare Report |

The free tier is not a trial. It is permanent and does not expire.

---

## Prerequisites
- Stripe account linked to Mercury checking account (Stripe → Settings → Bank accounts → Add)
- Stripe product `2opmd_clinical` with monthly and annual prices created in dashboard
- Stripe CLI installed locally for webhook testing
- Backend: user model updated with `stripe_customer_id`, `subscription_status`, `subscription_tier`

---

## Block 0 — Stripe account and product config (manual, ~30 min)

### 0.1 Connect Mercury to Stripe
1. Log into Stripe dashboard → Settings → External payout accounts
2. Add Mercury routing + account number
3. Set payout schedule (recommend: daily or weekly)
4. Stripe will send two micro-deposits to verify — confirm in Mercury

### 0.2 Create products and prices
In Stripe dashboard → Products:
```
Product: 2ndOpinionMD Clinical
  Price 1: $12.00 / month  →  save price_id as STRIPE_PRICE_MONTHLY
  Price 2: $99.00 / year   →  save price_id as STRIPE_PRICE_ANNUAL
```

### 0.3 Configure webhook endpoint
- Endpoint: `POST /api/billing/webhook`
- Events to listen for:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_failed`

### 0.4 Environment variables
```
# .env (backend)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_MONTHLY=price_...
STRIPE_PRICE_ANNUAL=price_...

# .env.local (frontend)
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

---

## Block 1 — Backend: subscription model and Stripe customer lifecycle (~2 hrs)

### 1.1 DB migration — extend User model
```python
# server/models/user.py additions
stripe_customer_id: str | None       # created on first checkout
subscription_status: str             # "free" | "active" | "past_due" | "canceled"
subscription_tier: str               # "free" | "clinical"
subscription_period_end: datetime | None
```

Migration: `alembic revision --autogenerate -m "add_stripe_fields"` then `alembic upgrade head`.

For the **dev bypass** path: `subscription_tier = "clinical"` is hardcoded in `dev_fixtures.py` so all features remain available during development without Stripe calls.

### 1.2 Stripe customer creation
- On first checkout attempt, create Stripe customer if `stripe_customer_id` is null
- Store `stripe_customer_id` back on the user row

### 1.3 New routes — `server/api/billing_routes.py`

```
POST /api/billing/create-checkout-session
  → creates Stripe Checkout session, returns {url}
  → accepts {price_id, success_url, cancel_url}

POST /api/billing/portal
  → creates Stripe Customer Portal session, returns {url}
  → used for: upgrade, downgrade, cancel, view invoices

POST /api/billing/webhook
  → validates Stripe-Signature header
  → handles: checkout.session.completed, subscription.*, invoice.payment_failed
  → updates user.subscription_status and subscription_tier in DB

GET /api/billing/status
  → returns {tier, status, period_end, features: {timeline, detective, journal}}
  → auth required
```

### 1.4 Feature guard dependency

```python
# server/api/deps.py
async def require_clinical(current_user = Depends(get_current_user)):
    if current_user.subscription_tier != "clinical":
        raise HTTPException(403, detail="clinical_subscription_required")
    return current_user
```

Apply to:
- `GET /api/timeline/*` — all timeline endpoints
- `POST /api/timeline/upload`
- `POST /api/rag/ask_stream` (Detective)
- `POST /api/rag/flare_report`

Journal endpoints (`/api/journal/*`) remain open to all authenticated users.

---

## Block 2 — Mock server: subscription state and gating (~45 min)

### 2.1 Add subscription fixture
```python
# server/mock/fixtures/billing.py
SUBSCRIPTION = {
    "tier": "free",          # toggle to "clinical" to test paid UI
    "status": "active",
    "period_end": None,
    "features": {
        "timeline": False,
        "detective": False,
        "journal": True,
    }
}
```

### 2.2 Add mock billing routes
```
GET  /api/billing/status       → returns SUBSCRIPTION fixture
POST /api/billing/create-checkout-session → returns {url: "https://checkout.stripe.com/mock"}
POST /api/billing/portal        → returns {url: "https://billing.stripe.com/mock"}
```

### 2.3 Mock gating behavior
When `SUBSCRIPTION["tier"] == "free"`, timeline and detective endpoints return:
```json
{"detail": "clinical_subscription_required"}
```
with HTTP 403 — same contract as production.

Toggle `SUBSCRIPTION["tier"] = "clinical"` in the fixture to develop the paid UI without Stripe.

---

## Block 3 — Frontend: subscription context (~1 hr)

### 3.1 `SubscriptionContext` — `src/contexts/SubscriptionContext.tsx`

```typescript
interface SubscriptionState {
  tier: "free" | "clinical" | "loading";
  features: { timeline: boolean; detective: boolean; journal: boolean };
  refresh: () => void;
}
```

- Fetches `GET /api/billing/status` on mount
- Exposes `useSub()` hook
- Caches result; re-fetches after Stripe redirect (reads `?upgraded=1` query param on `/patient`)

### 3.2 Wrap app in provider
Add `<SubscriptionProvider>` inside `AuthProvider` in `App.tsx`.

---

## Block 4 — Frontend: upgrade flow UI (~2 hrs)

### 4.1 `UpgradeModal` component — `src/components/UpgradeModal.tsx`
- Triggered when a free user clicks Timeline or Detective
- COMFORT_UX: dark card, `LeftTrack` (cyan), clean typography
- Content:
  - Feature list (what they're unlocking)
  - Price: `$12 / month or $99 / year`
  - `[ UPGRADE MONTHLY ]` and `[ UPGRADE ANNUALLY ]` buttons
  - Link: "Already subscribed? Manage billing"
- On button click: `POST /api/billing/create-checkout-session` → redirect to Stripe Checkout

### 4.2 `BillingPortalLink` component
- Small text link in `SettingsPage` for subscribed users: "Manage billing →"
- Calls `POST /api/billing/portal` → redirect to Stripe Customer Portal

### 4.3 Post-checkout return
On `success_url` (`/patient?upgraded=1`):
- `SubscriptionContext` detects query param, re-fetches billing status
- Shows a one-time `InlineMessage` (green): "Clinical tier activated. Timeline and Detective are now unlocked."
- Clears `?upgraded=1` from URL

---

## Block 5 — Frontend: feature gating (~1.5 hrs)

### 5.1 Gate `PatientNav` tabs
In `PatientNav` (inside `src/lib/ui.tsx`):
- TIMELINE and DETECTIVE tabs show a small `🔒` lock indicator for free users
- Clicking a locked tab opens `UpgradeModal` instead of navigating

### 5.2 Gate tools panel in `PatientPortalPage`
For TIMELINE and DETECTIVE tool cards:
- Free user sees tool card with a `CLINICAL` badge (cyan) and subtle lock
- Clicking opens `UpgradeModal`

### 5.3 Route-level guard
In `App.tsx` or route definitions, wrap `<TimelinePage>` and `<EohdPage>` with a `<RequiresClinical>` component:
```typescript
// If tier is "free", redirect to /patient?upgrade=timeline
// If tier is "loading", show skeleton
// If tier is "clinical", render children
```

### 5.4 Paywall state in TimelineChartCard
If timeline fetch returns 403, show an `InlineMessage` (muted):
> "Health Insights requires a Clinical subscription. [Upgrade →]"

---

## Block 6 — Settings page billing section (~1 hr)

Add a `BILLING` section to `SettingsPage`:

**Free users:**
```
YOUR PLAN
  Free tier — Journal access included
  [ UPGRADE TO CLINICAL → ]
```

**Clinical users:**
```
YOUR PLAN
  Clinical — active through [date]
  $12/mo · [Manage billing →]
```

Both states use `DS` tokens and `LeftTrack` (green for active, cyan for upgrade prompt).

---

## Block 7 — Local webhook testing with Stripe CLI (~30 min)

```bash
# Install Stripe CLI in WSL
curl -s https://packages.stripe.dev/api/stable/stripe-cli/metadata.json \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['debian']['url'])" \
  | xargs -I{} wget -O stripe-cli.deb {}
sudo dpkg -i stripe-cli.deb

# Login
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/api/billing/webhook

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger customer.subscription.deleted
```

Add `MKB_STRIPE_WEBHOOK` entry to `MakefileBook` for one-command webhook proxy startup.

---

## Block 8 — Testing matrix

| Scenario | Expected behavior |
|---|---|
| Free user visits Timeline tab | `UpgradeModal` opens |
| Free user visits Detective tab | `UpgradeModal` opens |
| Free user visits Journal | Full access, no prompt |
| Free user completes Stripe Checkout | Tier upgrades, `/patient?upgraded=1` shows success message |
| Clinical user visits Timeline | Full access |
| Clinical user cancels subscription | After `period_end`, returns to free tier |
| `invoice.payment_failed` webhook | `subscription_status = "past_due"`, UI shows warning banner |
| DEV_AUTH_BYPASS mode | `subscription_tier = "clinical"` always (fixtures) |

---

## Files to create / modify

```
NEW
  server/api/billing_routes.py          Stripe customer, checkout, portal, webhook
  server/mock/fixtures/billing.py       Mock subscription state
  server/mock/routes/billing.py         Mock billing endpoints
  frontend/src/contexts/SubscriptionContext.tsx
  frontend/src/components/UpgradeModal.tsx
  frontend/src/components/RequiresClinical.tsx

MODIFY
  server/models/user.py                 +stripe fields
  server/api/deps.py                    +require_clinical()
  server/api/app_postgres.py            +include billing_routes
  server/mock/main.py                   +include mock billing routes
  frontend/src/App.tsx                  +SubscriptionProvider, +RequiresClinical routes
  frontend/src/lib/ui.tsx               +PatientNav lock indicators
  frontend/src/pages/PatientPortalPage.tsx  +tool card lock states
  frontend/src/pages/SettingsPage.tsx   +billing section
  frontend/src/pages/TimelinePage.tsx   +403 paywall message
  frontend/src/pages/EohdPage.tsx       +403 paywall message
  server/dev_fixtures.py                +subscription_tier = "clinical"
  .env / .env.local                     +Stripe keys
```

---

## Sequence

```
Block 0  Manual setup (Stripe dashboard + Mercury)   ← do this first, 30 min
Block 1  Backend model + routes + guard              ← 2 hrs
Block 2  Mock server subscription state              ← 45 min
Block 3  Frontend SubscriptionContext                ← 1 hr
Block 4  UpgradeModal + post-checkout UX             ← 2 hrs
Block 5  Feature gating — nav, routes, 403 states    ← 1.5 hrs
Block 6  Settings billing section                    ← 1 hr
Block 7  Stripe CLI webhook testing                  ← 30 min
Block 8  Full scenario test matrix                   ← 1 hr
```

**Total estimated:** ~10 hrs implementation + Block 0 manual work

---

## Notes

- Mercury connection to Stripe is routing-number-level — Stripe handles the ACH. No code required; it's a dashboard setting.
- Stripe Checkout (hosted) is used for the initial upgrade. No PCI scope on the backend.
- Stripe Customer Portal handles all self-service: upgrade, downgrade, cancel, invoice history. Zero backend code for those flows.
- When `DEV_AUTH_BYPASS=true`, `subscription_tier` is always `"clinical"` so the entire app is accessible during development.
- The free tier is permanent — no expiry, no trial clock. This matters for trust with autoimmune patients who may be in a financial rough patch.

---

*Filed 2026-04-13 — 2ndOpinionMD GAME_PLAN series*
