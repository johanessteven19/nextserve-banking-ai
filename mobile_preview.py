"""Read-only phone rendering of the shared banking journey state."""
from html import escape
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from services import transaction, money, explain_transaction, similar_transactions
from payment_context import history_context, MERCHANTS


def text(value):
    return escape(str(value))


def action(label, primary=False):
    return f'<div class="action {"primary" if primary else ""}">{text(label)}</div>'


def card(title, content):
    return f'<section><h3>{text(title)}</h3>{content}</section>'


def build_phone(s):
    view = s['transaction_view']
    t = transaction(s)
    title = {'history':'Transactions', 'details':'Payment details', 'learn':'Understand this payment',
             'recognized':'Payment recognized', 'protect':'Protect your card', 'replace':'Replace your card',
             'dispute':'Report a payment', 'track':'Track your case', 'cases':'Your cases'}[view]
    content = ''
    if view == 'history':
        content += '<div class="account"><small>Everyday account · 4821</small><strong>S$48,650.00</strong><small>Available balance</small></div><h3>Recent activity</h3>'
        for item in s['transactions']:
            content += f'<div class="transaction"><div class="row"><b>{text(item["statement_descriptor"])}</b><strong>{text(money(item["amount"]))}</strong></div><small>{text(item["date"])} · {text(item["status"])}</small><span class="chevron">›</span></div>'
    elif view == 'cases':
        for case in s['cases'].values():
            content += card(case['id'], f'<b>{text(case["merchant"])}</b><p>{text(case["status"])}</p>')
        if not content:
            content = card('No cases to show', '<p>Your submitted reports will appear here.</p>')
    else:
        content += f'<div class="payment"><span class="merchant-icon">↗</span><h2>{text(t["friendly_name"])}</h2><div class="amount">{text(money(t["amount"]))}</div><span class="status">{text(t["status"])}</span><p>{text(t["date"])}</p><small>{text(t["statement_descriptor"])}</small></div>'
        if view in ['details', 'learn']:
            headline, explanation = explain_transaction(t)
            content += card(headline, '<p>' + text(explanation) + '</p>')
            if view == 'learn':
                result = history_context(s['transactions'], t)
                body = '<b>' + text(result['headline']) + '</b>'
                if result['monthly'] and t['status'] == 'Posted':
                    series = result['series']
                    body += f'<p>{len(series)} monthly payments from {text(series[0]["date"].split(" · ")[0])} to {text(series[-1]["date"].split(" · ")[0])}. Typical amount: {text(money(result["typical"]))}.</p>'
                else:
                    body += f'<p>{max(0,len(result["matches"])-1)} earlier payments to this merchant group. No confirmed subscription pattern for this payment.</p>'
                body += '<small>A pattern does not confirm who authorized a payment.</small>'
                content += card('✦ AI payment context', body)
                profile = MERCHANTS.get(t['merchant_group'])
                if profile:
                    content += card('About the merchant', '<b>' + text(profile[0]) + '</b><p>' + text(profile[2] or 'Review public merchant information and compare it with your receipt.') + '</p><small>Merchant guidance and public search sources</small>')
                body = ''.join(f'<p><b>{text(part["Statement text"])}</b><br>{text(part["Plain-language meaning"])}</p>' for part in t['descriptor_parts'])
                content += card('Your statement, explained', body)
                content += card('Does this look familiar?', '<p>' + text(t['recognition_tip']) + '</p>')
            content += action('I recognize this', True)
            if view == 'details':
                content += action('Learn More')
            content += action('I don’t recognize this')
        elif view == 'recognized':
            content += '<div class="success">✓ Thanks for confirming. No further action is needed for this payment.</div>' + action('Back to transactions', True)
        elif view == 'protect':
            content += card('1 · Secure your card', '<p>' + ('Your card is locked. Existing payments are not cancelled.' if s['card']['locked'] else 'Block new card purchases while you review this payment.') + '</p>' + action('Card locked' if s['card']['locked'] else 'Lock card', True))
            if s['pending']:
                content += card('Confirm card lock', '<p>Lock card ending 4821?</p>' + action('Confirm card lock', True) + action('Cancel'))
            content += card('2 · Next steps', action('Replace card') + action('File dispute') + action('Track case'))
        elif view == 'replace':
            if s['replacement']:
                content += '<div class="success">✓ Replacement request received<br>' + text(s['replacement']['id']) + '</div>'
            else:
                content += card('Card ending 4821', '<p>Your original card will stay locked while we review your request.</p><p>□ I want to request a replacement</p>' + action('Confirm replacement request', True))
            content += action('Continue to file dispute')
        elif view == 'dispute':
            content += card('Tell us what happened', '<p>Your transaction details are attached.</p><div class="field">I do not recognize this transaction and would like it investigated.</div><p>□ I confirm I want to submit this report</p>' + action('Submit dispute', True))
        elif view == 'track':
            case = s['cases'].get(t['id'])
            if case:
                content += '<div class="success">✓ Report received · ' + text(case['id']) + '</div>'
                content += card(case['status'], '<p>' + text(case['reason']) + '</p><small>' + text(case['created']) + '</small>')
                content += card('Your protection', '<p>Card: ' + ('Locked' if s['card']['locked'] else 'Active') + '</p>' + ('<p>Replacement: ' + text(s['replacement']['status']) + '</p>' if s['replacement'] else ''))
                matches = similar_transactions(s, t['id'])
                content += card('Similar payments to review', ''.join('<p><b>' + text(item['merchant']) + '</b> · ' + text(money(item['amount'])) + '<br><small>' + text(' · '.join(reasons)) + '</small></p>' for item, reasons in matches) or '<p>No similar payments found.</p>')
        if view in ['protect','replace','dispute','track']:
            key = s['cases'].get(t['id'], {}).get('id', t['id'])
            sent = s['agent_handoffs'].get(key)
            content += card('Human agent review', '<div class="success">✓ Summary sent for review<br>' + text(sent['id']) + '</div>' if sent else action('Send summary to human agent', True))
    css = Path(__file__).with_name('mobile_preview.css').read_text(encoding='utf-8')
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>{css}</style></head><body><div class="phone"><div class="statusbar"><span>9:41</span><span>●●● ▰</span></div><header><b>DBS</b><span>digibank</span><span class="avatar">AM</span></header><div class="page-title">‹ &nbsp;{text(title)}</div><main>{content}</main><footer><span>⌂<br>Home</span><span class="selected">▤<br>Accounts</span><span>⇄<br>Pay</span><span>◌<br>More</span></footer><div class="home-indicator"></div></div></body></html>'


def render_mobile(s):
    st.markdown('### digibank mobile view')
    st.caption('Preview follows your selections on the left. Scroll inside the phone to see the full screen.')
    components.html(build_phone(s), height=830, scrolling=False)
