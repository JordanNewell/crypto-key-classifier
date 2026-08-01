# ckc-pro — Opportunity Scan

**Subject:** Commercial sibling to `crypto-key-classifier` (ckc)
**Author of ckc:** Jordan Newell
**Date:** 2026-08-01
**Status:** Scan, not commitment. Read, pick one, decide.

---

## Context

ckc is a working MIT-licensed CLI: 17 validators, ~50 chains, aggressive repair, cross-chain re-encoding, zero network calls. That skill sits in a nervous part of the stack — keys, loss, forensics, onboarding. Nervous markets are where people pay.

Five candidates. Most will fail. The goal is finding the one that fails *latest*.

---

## Candidate 1: Wallet Recovery-as-a-Service (KeyMedic)

**Thesis:** Distressed users with corrupted/partial keys will pay success-based fees to recover funds they cannot otherwise access.
**Target user:** Non-technical holder with a partial seed phrase, OCR'd key screenshot, unreadable wallet.dat, or broken backup. Arrives via "recover lost bitcoin" in panic.
**Wedge:** Landing page ingests a damaged string, runs ckc's repair pipeline + a heavier dictionary/brute-force pass against known wallet formats, returns "recoverable: yes/no" before payment.
**Why now:** Wallet UX still hostile; multi-chain holdings create partial-key confusion. Older BTC holders aging out of backups. Existing recovery firms charge 20-30% — room below that ceiling.
**What's hard:** (1) Trust — customers hand life savings to a stranger; one theft accusation is fatal. (2) You become a high-value target. (3) Most "unrecoverable" keys really are unrecoverable, so the funnel is thin.
**Build cost:** M — ~2-3k LOC plus infra (airgapped recovery workstation, secure intake, escrow). ~120 hours over 6 weeks; ongoing ops.
**Monetization:** Hypothesis: $50-500 per successful recovery, scaled by amount. 5-30 paid recoveries/month at maturity.
**Adjacent players:** Wallet Recovery Services, WalletRecoveryTools, KeychainX.
**Honesty check:** Services business wearing a product costume. You become a custodian of secrets — opposite of ckc's zero-network-call principle. Solo + custodial = one incident and it ends.

---

## Candidate 2: Forensics & Compliance Workstation (ckc-forensics)

**Thesis:** Exchanges, fund-recovery firms, auditors, and law-enforcement contractors need a defensible, auditable multi-chain classification tool and will pay per-seat for it.
**Target user:** Compliance analyst at a mid-tier exchange; investigator at a chain-analytics firm; fund-recovery paralegal. Persona: "person who writes a report with a citation next to every claim about an address."
**Wedge:** ckc's engine in a desktop/web app with case management, evidence-grade audit logs (every classification signed + timestamped), PDF/CSV report export with hashes, batch processing of seized-wallet exports, chain-of-custody trail. Self-hosted — buyers won't send keys to vendor SaaS.
**Why now:** OFAC sanctions screening expanded to addresses; Tornado Cash indictments created demand for defensible attribution; multi-chain forensics outpaces single-chain tools. "Cite this in court" is under-served.
**What's hard:** (1) Enterprise sales motion — security questionnaire, SOC 2 or equivalent, patience. (2) Free tiers from Chainalysis / TRM may cover the 80% case. (3) One wrong classification in a real case is real liability.
**Build cost:** L — ~5-8k LOC for app + case management + audit plumbing. ~250 hours plus SOC 2 / pen-test overhead.
**Monetization:** Hypothesis: $5k/seat/yr for investigators; $15-50k/site/yr for exchanges. 3-10 paying orgs in year one would be strong.
**Adjacent players:** Chainalysis, TRM Labs, Elliptic, Misttrack.
**Honesty check:** Rewards field sales and compliance certs — anti-patterns for a solo technical founder. Classification is commoditizing; the real moat (case management, report generation) is a different product than ckc.

---

## Candidate 3: Validation API for Fintech Onboarding (ckc-validate)

**Thesis:** Custody providers, neobanks, tax software, and payment processors need a metered "is this address valid, and for what chain" endpoint and will pay per-call rather than maintain it in-house.
**Target user:** Backend engineer at a fintech adding crypto withdrawals; tax-software dev parsing user-pasted addresses; custody platform onboarding new chains. Persona: "engineer with a 'support multichain withdrawals' ticket who wants to outsource the edge cases."
**Wedge:** A single REST/gRPC endpoint — `POST /v1/validate { key }` → `{ best_guess, chain, checksum_status, cross_chain_alternates, repair_suggestions }`. Free tier (1k/month), metered above. SLA, usage dashboard, TS/Python/Go SDKs.
**Why now:** Every fintech adding crypto rails; chain fragmentation (50+ L2s, Cosmos HRP explosion) makes in-house validation painful; the alternative is a hand-rolled regex library that drifts.
**What's hard:** (1) Customers won't send mainnet keys to an API — must prove zero-retention, offer client-side SDKs, ideally self-host. (2) Validation is a feature, not a product; many will lift the logic. (3) Unit economics brutal — $0.001/call means millions of calls to matter.
**Build cost:** S — ~1-2k LOC for gateway, auth, billing, dashboards. Engine already exists. ~60-80 hours.
**Monetization:** Hypothesis: $0.0005-0.005 per call tiered; $99-999/month flat tiers. Breakeven ~50M calls/month — optimistic.
**Adjacent players:** Tatum, Alchemy, QuickNode, Moralis.
**Honesty check:** Most buildable, also most commodity. Validation is a checkbox on every larger crypto-API vendor's roadmap. Differentiation has to be repair + cross-chain re-encoding — narrowing the audience to "fintechs that care about recovery flows," a smaller niche than "fintechs that validate addresses."

---

## Candidate 4: Key-Migration Assistant for Forks & Airdrops (ckc-migrate)

**Thesis:** Every chain fork, snapshot, and airdrop creates a wave of users who need to figure out eligibility, re-derive addresses across the family, and move funds. A guided tool has a natural per-event revenue spike.
**Target user:** Mid-frequency holder with funds on a hardware wallet who wakes up to "there was an airdrop for ATOM holders" and wants to know what they're owed and how to claim without doxxing to a sketchy site.
**Wedge:** Desktop/web app — paste one address or connect a hardware wallet (read-only), get a report of every chain-fork / airdrop / snapshot you're eligible for, with claim instructions and cross-chain re-derivations done. Per-event fee for major airdrops; subscription for monitoring.
**Why now:** Airdrop farming and retroactive distributions are a sustained pattern (Cosmos, Solana, Arbitrum, Jito); snapshots create eligibility confusion; claim UX is uniformly bad. ckc's cross-chain re-encoding is the missing piece for "do I own the matching address on chain X."
**What's hard:** (1) High trust bar — users connect wallets; one phishing accusation is fatal. (2) Airdrop metadata is a moving target. (3) Revenue lumpy, market-cycle-correlated.
**Build cost:** M — ~3-4k LOC, mostly app shell + airdrop metadata curation + hardware-wallet read integration. ~150 hours; ongoing maintenance.
**Monetization:** Hypothesis: $10-30 per major-claim report; $5-15/month monitoring subscription. Break-even ~1k paying users — a real marketing problem.
**Adjacent players:** Zapper, DeBank, EarnDrop, Airdrops.io.
**Honesty check:** Crowded with well-funded consumer products. ckc's edge (cross-chain re-encoding) is genuinely useful but probably not the wedge — UX and trust are, where everyone else competes. Cyclical demand lines up poorly with solo cash flow.

---

## Comparison Matrix

| # | Candidate | Build | Sales | Trust | Market | ckc reuse | Solo fit |
|---|---|---|---|---|---|---|---|
| 1 | Recovery-as-a-Service | M | Services | V.high | Medium | High | Low |
| 2 | Forensics Workstation | L | Enterprise | Medium | Sm-mid | High | Low |
| 3 | Validation API | S | PLG | Med-low | Large | Medium | Medium |
| 4 | Migration Assistant | M | Consumer | High | Large | Medium | Low |

---

## Rejected candidates (briefly)

- **Self-hosted enterprise ckc with SSO + audit logs.** Tiny market (under 500 regulated custodians globally), 6-12 month sales cycles, heterogeneous k8s support. Buyers prefer a 50-person vendor with SOC 2. Redundant with Candidate 2's buyer profile.
- **Training-data / corpus licensing for crypto-key ML models.** No clear buyer; ML teams likely have proprietary corpora. Would require augmenting ckc's public test fixtures with realistic synthetic data.
- **Browser extension that classifies any address you hover over.** Distribution is the hard problem. Chrome Web Store economics plus the trust bar (an extension that "reads addresses" reads as spyware) make this a poor paid product. Better as a free OSS companion funneling to another candidate.

---

## Recommendation

**Investigate first:** Candidate 3 — Validation API for fintech onboarding (ckc-validate).

**Why:** Only candidate where build is small enough (S) to fail fast, sales is PLG, and ckc's engine is the product rather than a supporting character. The other three are services (1), enterprise sales plays (2), or consumer plays in crowded markets (4) — bad fits for a solo founder with agents but no sales org. Commodity status is its hedge: if the API stalls, OSS library and dev adoption remain portfolio assets, and the MVP is the smallest of any candidate.

**Smallest testable MVP (2 weeks):**
- Wrap ckc in FastAPI: `POST /v1/validate` → `{ best_guess, chain, checksum_status, cross_chain_alternates, repair_suggestions }`.
- API-key auth, rate limiting, 7-day retention + zero-retention flag.
- Deploy single-region (Fly.io or Railway). Usage dashboard: one Next.js page hitting `GET /v1/usage`.
- Publish TS + Python SDKs (~200 LOC each, generated from OpenAPI).
- Landing page with price table, zero-retention guarantee, "1k calls/month free" tier.
- No billing yet — manual invoicing for first 3 paying users.

**Success metric:** 10 orgs on free tier with >100 calls/week each within 30 days of launch, and ≥2 inbound inquiries about paid tiers.

**Kill metric:** Fewer than 3 orgs on free tier after 30 days, or zero inbound pricing inquiries. Either means the pain point isn't acute enough to pay for.
