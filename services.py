"""Deterministic, grounded demo orchestration. No model or banking API calls."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


def initial_state():
    data = json.loads(Path(__file__).with_name('data.json').read_text(encoding='utf-8'))
    return dict(**data, card={'overseas': False, 'locked': False, 'limit': 20000},
                messages=[], actions=[], requests=[], selected='TX-1001', journey=False,
                limit_reviewed=False, fx_reviewed=False, pending=None, handoff=None,
                transaction_view='history', recognized=[], cases={}, replacement=None,
                sample_cases=_sample_cases(), data_version=2, agent_handoffs={},
                digibot_connected=False, customer_summary=None)


def _timeline(created, pending=False):
    """Return a readable case timeline with a timestamp on every milestone."""
    base = datetime.strptime(created, '%d %b %Y · %H:%M UTC').replace(tzinfo=timezone.utc)
    if pending:
        milestones = [
            ('Report submitted', 'Complete', base),
            ('Payment completion check', 'In progress', base + timedelta(minutes=2)),
            ('Specialist review', 'Queued next', base + timedelta(minutes=5)),
            ('Review outcome', 'Decision pending', base + timedelta(minutes=8)),
        ]
    else:
        milestones = [
            ('Report submitted', 'Complete', base),
            ('Payment details captured', 'Complete', base + timedelta(minutes=2)),
            ('Specialist review', 'In progress', base + timedelta(minutes=5)),
            ('Review outcome', 'Decision pending', base + timedelta(minutes=8)),
        ]
    return [{'label': label, 'status': status,
             'timestamp': stamp.strftime('%d %b %Y · %H:%M UTC')}
            for label, status, stamp in milestones]


def _sample_cases():
    """Curated case history shown in the app so the tracking view is useful on first visit."""
    samples = [
        ('TX-1008', 'CASE-024', '09 Sep 2026 · 14:20 UTC', 'Under specialist review'),
        ('TX-1014', 'CASE-021', '08 Sep 2026 · 10:05 UTC', 'Awaiting review'),
        ('TX-1016', 'CASE-019', '06 Sep 2026 · 16:45 UTC', 'Payment completion check'),
    ]
    cases = {}
    data = json.loads(Path(__file__).with_name('data.json').read_text(encoding='utf-8'))
    for tx_id, case_id, created, status in samples:
        t = next(t for t in data['transactions'] if t['id'] == tx_id)
        cases[tx_id] = {
            'id': case_id, 'transaction': tx_id, 'merchant': t['merchant'],
            'statement_descriptor': t['statement_descriptor'],
            'payment_reference': t['payment_reference'], 'amount': t['amount'],
            'currency': 'SGD',
            'reason': 'I do not recognize this payment and would like it investigated.',
            'status': status, 'created': created, 'updated': created,
            'timeline': _timeline(created, pending=t['status'] == 'Pending'),
        }
    return cases


def explain_transaction(t):
    explanations = {
        'authorization': ('This payment was authorized and is awaiting completion.',
                          'The merchant has reserved this amount. A pending authorization cannot be stopped, recalled or reversed by the bank. If you do not recognize it, lock your card and file a dispute.'),
        'sgqr': ('This payment was authorized and is awaiting confirmation.',
                 'The payment was sent, but the merchant has not confirmed it. A pending SGQR payment cannot be stopped, recalled or reversed by the bank. If you do not recognize it, lock your card and file a dispute.'),
        'fee': ('This is your yearly card membership fee.',
                'This charge is for keeping your credit card membership for another year.'),
        'purchase': ('This payment has been completed.',
                     'The merchant has received the payment. It is no longer waiting for confirmation.'),
    }
    return explanations[t['type']]


def request_replacement(s):
    if not s['card']['locked']:
        raise ValueError('Lock the card before requesting a replacement.')
    if not s['replacement']:
        s['replacement'] = {'id': 'RPL-001', 'status': 'Request received'}
        s['actions'].append('Replacement requested: RPL-001. Original card stays locked.')
    return s['replacement']


def file_dispute(s, transaction_id, reason, confirmed):
    t = next((t for t in s['transactions'] if t['id'] == transaction_id), None)
    if not t or not confirmed or not reason.strip():
        raise ValueError('Select a transaction, describe the issue and confirm your statement.')
    if transaction_id not in s['cases']:
        created = datetime.now(timezone.utc).strftime('%d %b %Y · %H:%M UTC')
        case = {'id': f'CASE-{len(s["cases"])+1:03}', 'transaction': transaction_id,
                'merchant': t['merchant'], 'statement_descriptor': t['statement_descriptor'],
                'payment_reference': t['payment_reference'], 'amount': t['amount'], 'currency': 'SGD', 'reason': reason.strip(),
                'status': 'Awaiting transaction completion' if t['status'] == 'Pending' else 'Awaiting review',
                'created': created, 'updated': created,
                'timeline': _timeline(created, pending=t['status'] == 'Pending')}
        s['cases'][transaction_id] = case
        s['actions'].append(f"{case['id']} submitted for {transaction_id}: {case['status']}. No refund issued.")
    return s['cases'][transaction_id]


def case_for(s, transaction_id):
    """Return a submitted case, or a pre-populated case history item."""
    return s.get('cases', {}).get(transaction_id) or s.get('sample_cases', {}).get(transaction_id)


def file_disputes(s, transaction_ids, reason, confirmed):
    """Submit one confirmed report for a selected group of related payments."""
    ids = list(dict.fromkeys(transaction_ids or []))
    if not ids or not confirmed or not reason.strip():
        raise ValueError('Select at least one payment, describe the issue and confirm your statement.')
    return [file_dispute(s, tx_id, reason, confirmed) for tx_id in ids]


def money(value):
    return f'S${value:,.2f}'


def similar_transactions(s, tx_id):
    source = next(t for t in s['transactions'] if t['id'] == tx_id)
    found = []
    for t in s['transactions']:
        if t['id'] == tx_id:
            continue
        reasons = []
        if source.get('merchant_group') and t.get('merchant_group') == source['merchant_group']:
            reasons.append('Same merchant group')
        days = abs((datetime.strptime(t['date'].split(' · ')[0], '%d %b %Y') -
                    datetime.strptime(source['date'].split(' · ')[0], '%d %b %Y')).days)
        if (t['channel'] == source['channel'] and days <= 7 and
                abs(t['amount'] - source['amount']) <= max(1, source['amount'] * .05)):
            reasons.append('Similar amount on the same channel within 7 days')
        if reasons:
            found.append((t, reasons))
    return sorted(found, key=lambda item: (-len(item[1]), item[0]['id']))


def send_to_agent(s):
    """Queue a local handoff snapshot; never contacts an actual agent."""
    tx_id = s['selected']
    case = case_for(s, tx_id)
    key = case['id'] if case else tx_id
    if key not in s['agent_handoffs']:
        summary = handoff(s)
        if case:
            summary += '\n\nDISPUTE\n' + '\n'.join(f'{k}: {v}' for k, v in case.items())
        s['agent_handoffs'][key] = {'id': f'SR-{len(s["agent_handoffs"])+1:03}',
            'summary': summary, 'sent': datetime.now(timezone.utc).strftime('%d %b %Y · %H:%M UTC')}
        s['actions'].append(f'{key} summary sent to human agent for review.')
    return s['agent_handoffs'][key]


def connect_digibot(s):
    """Start a Digibot conversation using the current banking context."""
    if not s.get('digibot_connected'):
        s['digibot_connected'] = True
        s['actions'].append('Digibot connected with transaction context.')
    return 'Digibot is connected with your transaction context.'


def send_customer_summary(s):
    """Create a mock customer notification across email and push channels."""
    if not s.get('customer_summary'):
        sent = datetime.now(timezone.utc).strftime('%d %b %Y · %H:%M UTC')
        actions = list(s.get('actions', []))
        s['customer_summary'] = {
            'id': f'NTF-{len(actions)+1:03}',
            'sent': sent,
            'channels': ['Email', 'Push notification'],
            'actions': actions or ['No account actions recorded yet.'],
        }
    return s['customer_summary']


def transaction(s):
    return next(t for t in s['transactions'] if t['id'] == s['selected'])


def retrieve(s, prompt):
    words = set(re.findall(r'\w+', prompt.lower()))
    scored = [(len(words & set(re.findall(r'\w+', k['keywords'].lower() + ' ' + k['title'].lower()))), i, k)
              for i, k in enumerate(s['knowledge']) if k['approved']]
    return [k for score, _, k in sorted(scored, key=lambda x: (x[0], x[1]), reverse=True) if score][:2]


def answer(s, prompt):
    q = prompt.lower().replace('’', "'")
    t = transaction(s)
    sources = []
    if any(x in q for x in ["don't recognize", 'unfamiliar', 'not mine', 'fraud', 'unrecognized']):
        reply = (f"I can't verify whether you authorized {t['merchant']} ({money(t['amount'])}). "
                 'You can lock your card below, then request a human review. Locking does not cancel an existing transaction or open a dispute.')
        sources = [t['id']]
    elif any(x in q for x in ['human', 'agent', 'escalat']):
        reply = 'Choose Connect to Digibot below to continue with your transaction context.'
    elif any(x in q for x in ['japan', 'travel', 'overseas']):
        s['journey'] = True
        status = 'locked' if s['card']['locked'] else 'active'
        enabled = 'ON' if s['card']['overseas'] else 'OFF'
        reply = (f"Let's prepare your card for Japan. Your card is {status}; overseas usage is {enabled}. "
                 'Follow the travel checklist below: overseas usage → spending limit → FX. Each change needs your confirmation.')
        sources = ['Card details · 4821', 'KB-001']
    elif any(x in q for x in ['limit', 'spending']):
        s['limit_reviewed'] = True
        reply = f"Your daily spending limit is {money(s['card']['limit'])}. You can request a new limit between S$1,000.00 and S$100,000.00 below. Next, review FX costs for your trip."
        sources = ['Card details · 4821']
    elif any(x in q for x in ['lock', 'block']):
        reply = 'Your card is already locked.' if s['card']['locked'] else 'Choose Lock card below and confirm to secure your card.'
    elif 'sgqr' in q:
        notices = [k for k in retrieve(s, prompt) if 'sgqr' in (k['keywords'] + k['title']).lower()]
        if notices:
            reply = '\n\n'.join(k['body'] for k in notices)
            sources = [f"{k['id']} · {k['title']} · {k['published']}" for k in notices]
        else:
            reply = "I don't have an approved SGQR service notice yet, so I can't confirm a service-wide issue. Check the payment status before retrying. You can request human support if this remains unresolved."
    elif any(x in q for x in ['fx', 'exchange', 'currency']):
        s['fx_reviewed'] = True
        k = s['knowledge'][0]
        reply = k['body'] + ' For example: a converted S$1,000.00 purchase plus 2.5% would total S$1,025.00. This is not a live exchange quote.'
        sources = [k['id']]
    elif any(x in q for x in ['fee', 'reversal', 'refund']):
        reply = s['knowledge'][1]['body'] + ' Select the annual membership fee transaction to initiate a request below.'
        sources = ['KB-002']
    elif any(x in q for x in ['transaction', 'pending', 'hold', 'disappear', 'explain', 'charge']):
        reply = f"**{t['merchant']} · {money(t['amount'])}**\n\nStatus: **{t['status']}**. {t['detail']} {t['timing']}"
        if t['status'] == 'Pending':
            reply += " The bank cannot stop, recall or reverse a pending payment. If you don't recognize it, lock your card and file a dispute."
        sources = [f"{t['id']} · {t['channel']} · {t['date']}"]
    else:
        hits = retrieve(s, prompt)
        reply = '\n\n'.join(k['body'] for k in hits) if hits else "I don't have enough approved information to answer that. I can help with a selected transaction, card settings, fee requests, SGQR notices, or Japan travel. Human support is available below."
        sources = [f"{k['id']} · {k['title']}" for k in hits]
    s['messages'].extend([{'role': 'user', 'text': prompt, 'transaction': t['id']},
                          {'role': 'assistant', 'text': reply, 'sources': sources}])
    return reply


def execute(s, action, value=None):
    """Called only after the UI's explicit confirmation."""
    if action == 'overseas':
        if s['card']['locked']:
            raise ValueError('Card is locked. A human can review reactivation before overseas use.')
        s['card']['overseas'] = True
        result = 'Overseas usage enabled'
    elif action == 'limit':
        if not isinstance(value, int) or not 1000 <= value <= 100000:
            raise ValueError('Limit must be between S$1,000.00 and S$100,000.00.')
        s['card']['limit'] = value
        s['limit_reviewed'] = True
        result = f'Daily spending limit changed to {money(value)}'
    elif action == 'lock':
        s['card']['locked'] = True
        result = 'Card ending 4821 locked'
    elif action == 'fee':
        if value != 'TX-1003':
            raise ValueError('Only the annual membership fee is eligible for this request.')
        if s['requests']:
            return 'Fee request already submitted: FEE-001'
        s['requests'].append({'id': 'FEE-001', 'transaction': value, 'status': 'Awaiting review'})
        result = 'Fee reversal requested: FEE-001 · Awaiting review, no refund issued'
    else:
        raise ValueError('Unknown action')
    s['actions'].append(result)
    s['messages'].append({'role': 'assistant', 'text': '✓ ' + result, 'sources': ['Card services']})
    return result


def publish(s, title, keywords, body, approved):
    if not approved or not all(x.strip() for x in [title, keywords, body]):
        raise ValueError('Title, keywords, content and approval are required.')
    item = dict(id=f'KB-{len(s["knowledge"])+1:03}', title=title.strip(), keywords=keywords.strip(),
                body=body.strip(), approved=True, published=datetime.now(timezone.utc).strftime('%H:%M UTC'))
    s['knowledge'].append(item)
    return item


def handoff(s):
    t = transaction(s)
    transcript = '\n'.join(f"{m['role'].upper()} [{m.get('transaction', ', '.join(m.get('sources', [])))}]: {m['text']}" for m in s['messages'])
    return (f"SERVICE REVIEW SUMMARY\nCustomer: Alex Morgan · Card 4821\n"
            f"Selected transaction: {t['id']} | {t['merchant']} | {money(t['amount'])} | {t['status']}\n"
            f"Statement: {t['statement_descriptor']} | Reference: {t['payment_reference']}\n"
            f"Goal: {'Japan travel preparation' if s['journey'] else 'Banking service inquiry'}\n"
            f"Card: {'Locked' if s['card']['locked'] else 'Active'} | Overseas: {s['card']['overseas']} | Limit: {money(s['card']['limit'])}\n"
            f"Confirmed actions: {'; '.join(s['actions']) or 'None'}\n"
            "Unresolved: Customer requests human assistance; review conversation and confirm resolution.\n"
            "Next step: Review transaction authorization or service issue with the customer. No dispute decision has been made.\n\n"
            f"Conversation (includes transaction context in the app):\n{transcript or 'No conversation yet.'}")


def impact(tx_rate=70, fee_rate=30):
    avoided = 27600 * tx_rate / 100 + 11300 * fee_rate / 100
    return avoided, avoided / 45200 * 100
