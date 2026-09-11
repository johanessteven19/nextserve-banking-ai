# NextServe — One conversation. Every next step.

A local Streamlit hackathon prototype of an AI-first banking service experience. All customers, transactions, policies and actions are fictional. No bank systems, credentials or API keys are needed.

Customer-facing screens now use banking-app copy without demo labels. Transaction and case references use PAY, CASE, RPL, FEE and SR prefixes. This copy change does not connect the app to banking systems or a human support team: all actions, notices, fees and statuses remain fictional and stored in session memory. The sidebar reset is now **Reset session**; preset shortcuts are **Explain a payment**, **QR payment help**, and **Prepare for Japan**.

The interface now uses a DBS-inspired red, charcoal and white theme with a red account card, compact dark headers, white navigation and matching chart accents. This is a hackathon concept, not an official DBS app or exact reproduction of its design system. Styling is isolated in `theme.css`, with native widget colors in `.streamlit/config.toml`.

## Setup and run

On this computer, double-click **Start Demo.cmd** to use the prepared local dependencies, then open http://127.0.0.1:8501 in your browser. Keep the launcher running during the demo. If the app is already running, use the existing browser address rather than starting another instance. For another computer or a copy of the ZIP, follow the setup below first.

Requires Python 3.10 or newer. Open a terminal in this folder:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

On macOS/Linux, replace `.venv\Scripts\python` with `.venv/bin/python`.
Open http://localhost:8501. Internet is needed only to install dependencies. Stop the server with Ctrl+C.

## Hosting

The project is ready for Streamlit Community Cloud: publish this folder to a GitHub repository, choose `app.py` as the main file, and keep the default Python environment. It also includes a `Dockerfile` for container hosts such as Render or Railway. All state is session-local and the app uses dummy banking data only.

Validated with Python 3.12 and Streamlit 1.63.0: all 10 service/UI tests passed. The local server was started and its health endpoint checked. The Codex in-app browser blocked the local URL, so a screenshot/visual browser review could not be completed in this session.

## Three-minute management demo

**Mobile efficiency update:** The mobile-only layouts in `mobile_journey.py` offer search, payment-status filters, chronological date groups, single-tap transaction rows and eight-row progressive loading. Details prioritize a short explanation and the next action. Learn More leads with the history finding, with prior payments, statement decoding and external sources inside expanders. Card protection prioritizes locking and reporting; replacement is optional. The shared desktop renderer is unchanged. Mobile navigation mounts a fresh scroll container per journey step.

**Desktop / Mobile switch:** Banking experience has a view selector at the top. Mobile is a fully interactive, scrollable digibank-inspired phone layout with the same transaction selection, recognition, Learn More, card protection, replacement, dispute, case tracking and human-handoff controls. Use the Transactions and My cases buttons at the bottom of the phone to navigate. Both views share account and journey state, so switching preserves the selected payment and completed actions. It is a proposed mobile treatment, not a verified reproduction of the official digibank interface. The earlier read-only side panel is no longer used.

**AI payment context:** Learn More now analyzes prior merchant payments and separately looks up public merchant information. Open **NETFLIX.COM SG** to see six monthly payments from April through September 2026 at S$19.98; Google Play has five monthly entries. History analysis requires at least three completed payments with the same descriptor and intervals of 26–35 days, uses only records up to the selected payment, and does not assert authorization or the original subscription start date. Pending holds do not establish recurrence. There are now 25 seeded transactions.

`payment_context.py` uses deterministic history analysis and a public Bing RSS search (no model/API key). Search sends only a predefined merchant name and returns up to three labelled snippets with links. The lookup times out after five seconds and the UI caches results for 15 minutes. If blocked or unavailable, the UI says so and provides a search link; Google and Netflix also have separately labelled saved official guidance. It does not fabricate successful search results. External search needs internet access, while internal history analysis works offline. Search snippets are untrusted external content and do not execute actions or establish a payment's legitimacy.

The history now shows fictional statement-style merchant descriptors (for example, `GRAB* A-7K2M9 SG`), with separate demo payment references. Details show a friendly merchant label beside the original descriptor. **Learn More** breaks down the abbreviated merchant name, reference and location label, then suggests how to compare the payment with receipts or merchant activity. It also states what the descriptor cannot establish, such as the purchased item or who authorized it. These examples are not an official DBS template or a universal parsing standard. Disputes and agent summaries preserve the original descriptor and payment reference.

The current demo has **16 fictional transactions in Singapore dollars (S$ / SGD)**, with two decimal places. Values are newly seeded dummy amounts, not conversions from the earlier rupiah data. Currency updates reset the old session to avoid mixing datasets.

After submitting a dispute, the case page immediately suggests similar payments. Matches use the same merchant group, or an amount within 5% (minimum S$1 tolerance), the same channel and a date within 7 days. Each suggestion explains its match and opens the individual transaction for review. No extra dispute is filed automatically and similarity does not establish fraud.

The case page also supports **multiple related disputes**. Tick the payments you also do not recognize, confirm the shared reason, and choose **Submit selected disputes**. Each selected payment receives its own case reference and remains independently reviewable; previously reported payments cannot be selected again.

**Send dispute summary to human agent** saves a case-specific snapshot and shows a persistent confirmation that the summary was sent for review, together with a simulated reference and timestamp. Repeated clicks reuse the handoff. No real agent receives anything. The sent summary contains the dispute statement and case reference as well as transaction details and completed actions.

**New primary journey:** Banking experience starts on Transactions. Open **View transaction** for a plain-language explanation, then choose **I recognize this**, **Learn More**, or **I don’t recognize this**. Recognition ends the journey with no new action. Learn More adds timing, original data and matching approved SGQR notices. Unrecognized payments lead to confirmation-gated **Lock card**, **Replace card**, **File dispute**, and **Track case**. Replacement is optional; reporting does not require a replacement. Case creation attaches the transaction automatically and repeated submissions reuse the existing reference.

Pending-payment reports show **Awaiting transaction completion**; posted payments show **Awaiting review**. Tracking includes the submission time, report, card status and replacement request. **Track my cases** on history reopens reports. No refund, delivery or live case progress is claimed. Existing cases and card locks are not undone by later recognizing a transaction. All state is local to this demo session.

The original three preset demos below are now under **Service companion**. The primary transaction flow is in `transactions_ui.py`.

1. **Trust (60–75 seconds):** Service companion → `01 · Trust`. Show the pending authorization explanation and expand its structured data. Ask `I don't recognize this`, choose **Lock card**, then **Confirm action**. Prepare the human handoff and show that the lock and conversation are included. Nothing asserts that a pending transaction is legitimate.
2. **Agility (35 seconds):** Select `02 · Agility` before publishing: the assistant admits it has no approved incident notice. Open **Knowledge studio**, approve and publish the preset SGQR notice. Return to Service companion and select Agility again. The new notice is immediately used with its source ID. A custom promo also works when its title/keywords overlap the question.
3. **Continuity (45 seconds):** Use **Reset entire demo** to clear the locked card, then `03 · Continuity`. Confirm overseas enablement, ask **Check my limit**, optionally adjust it, then choose **Understand FX charges**. Show the persistent three-step checklist.
4. **Impact (25 seconds):** Open **Impact & evidence**. Explain the assumptions and vary the containment sliders. End with the pilot measures, not a claim of proven reduction.

For fee reversal, open Service companion and select the annual membership fee in the transaction list, choose **Request fee reversal**, and confirm. The request remains awaiting review; no refund is issued. Repeating submission returns the same reference.

## What's implemented

- Mobile-style transaction activity and fictional account/card profile.
- Contextual assistant with structured transaction sources, uncertainty language and suggested actions.
- Confirmation-gated overseas enablement, card lock, spending-limit change and fee-review request.
- Admin publishing with explicit demo approval, title/keyword retrieval and source attribution.
- Japan travel checklist that persists across turns.
- Generated, downloadable human handoff with context, card state, completed actions and conversation; simulated queue button.
- Adjustable impact model plus separately labelled session activity.

## Scope and architecture

`app.py` owns Streamlit screens and confirmation UI. `services.py` owns deterministic intent routing, retrieval, state changes, handoff generation and arithmetic. `data.json` holds seed data. `test_services.py` verifies the key service flows; `test_app.py` verifies UI interactions.

**The assistant is an offline simulation, not a connected language model.** It uses explicit intent rules, approved keyword retrieval and grounded response templates. It demonstrates the intended AI-first servicing experience reliably without secrets or external calls. Arbitrary language understanding is limited; unsupported questions receive a fallback with human support. A real model integration is future work, as are authenticated admin roles, production retrieval, audited banking APIs and evaluation.

All changes live in Streamlit session memory. Switching screens preserves them; resetting the demo, starting a new browser session or restarting the app clears them. Admin is a demonstration view in the same session, not a separately authenticated shared knowledge service. Publishing a newer matching notice makes it rank first, but does not revoke older notices. The handoff is a snapshot: prepare it again after further actions. No actual agent receives it. The FX rate/fee illustration is fictional, not financial guidance or current pricing.

## Business-case calculation

The supplied approximate monthly inputs are 45,200 total inquiries, 27,600 transaction-detail inquiries, and 11,300 fee-reversal inquiries. With 70% and 30% containment:

```
27,600 × 70% = 19,320
11,300 × 30% =  3,390
Total        = 22,710
22,710 / 45,200 = 50.243...% ≈ 50.2%
```

The previous discussion's ~50.3% was a rough estimate. This app displays the exact arithmetic from the stated rounded inputs rather than altering a baseline to force that result. Baselines are user-supplied and not independently verified. The calculation assumes disjoint categories and full reach; it is an illustrative potential within this baseline, not measured bank-wide call reduction. A pilot should validate adoption, resolution, recontact within 7 days and customer satisfaction.

## Tests

```powershell
.venv\Scripts\python -m unittest discover -v
```
