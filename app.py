import streamlit as st
import importlib
from pathlib import Path
# Streamlit can rerun this entry point while retaining older helper modules.
# Refresh services before importing the UI that depends on their public API.
import services
importlib.reload(services)
import transactions_ui
importlib.reload(transactions_ui)
render_transactions = transactions_ui.render_transactions
from services import initial_state, money, transaction, answer, execute, publish, handoff, impact, send_to_agent

st.set_page_config(page_title='DBS | NextServe', page_icon='🔴', layout='wide')
st.markdown('<style>' + Path(__file__).with_name('theme.css').read_text(encoding='utf-8') + '</style>', unsafe_allow_html=True)

if 'bank' not in st.session_state or st.session_state.bank.get('data_version') != 2:
    st.session_state.bank = initial_state()
s = st.session_state.bank
if s.get('history_revision') != 4:
    s['transactions'] = initial_state()['transactions']
    s['descriptor_data_loaded'] = True
    s['history_revision'] = 4
for key, value in {'transaction_view': 'history', 'recognized': [], 'cases': {}, 'replacement': None}.items():
    s.setdefault(key, value)


def ask(prompt):
    answer(s, prompt)


def scenario(name):
    s['pending'] = None
    s['handoff'] = None
    s['messages'] = []
    s['journey'] = name == 'travel'
    if name == 'trust':
        s['selected'] = 'TX-1001'
        ask('Explain this pending transaction')
    elif name == 'agility':
        s['selected'] = 'TX-1002'
        ask('Why is my SGQR payment pending?')
    else:
        ask('Can I use my card in Japan?')


def stage(action, value=None):
    s['pending'] = (action, value)


with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-name">DBS</span><span class="brand-divider"></span><span class="brand-product">NextServe</span></div>', unsafe_allow_html=True)
    st.caption('BANKING MADE CLEAR')
    page = st.radio('Workspace', ['Banking experience', 'Service companion', 'Knowledge studio', 'Impact & evidence'])
    st.divider()
    st.markdown('**Session**')
    st.caption('Start a new session to clear your current activity.')
    if st.button('Reset session', use_container_width=True):
        st.session_state.bank = initial_state()
        st.rerun()
    st.divider()

if page == 'Banking experience':
    display_mode = st.radio('View', ['Desktop', 'Mobile'], horizontal=True, key='display_mode')
    if display_mode == 'Desktop':
        render_transactions(s)
    else:
        with st.container(key='mobile_app'):
            st.markdown('<div class="mobile-status"><span>9:41</span><span>●●● ▰</span></div><div class="mobile-brand"><strong>DBS</strong><span>digibank</span></div>', unsafe_allow_html=True)
            with st.container(height=680, border=False, key='mobile_screen_' + s['transaction_view']):
                render_transactions(s, mobile=True)
            nav = st.columns(2)
            nav[0].button('Transactions', key='mobile_home', use_container_width=True,
                          on_click=transactions_ui.navigate, args=(s, 'history'))
            nav[1].button('My cases', key='mobile_cases', use_container_width=True,
                          on_click=transactions_ui.navigate, args=(s, 'cases'))
            st.markdown('<div class="mobile-home-indicator"></div>', unsafe_allow_html=True)

elif page == 'Service companion':
    st.markdown('<div class="hero"><div class="eyebrow">Your banking companion</div><h1>Clarity. Then the next step.</h1><p>Understand your payments, manage your card and get help when you need it.</p></div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for col, label, key in zip(cols, ['Explain a payment', 'QR payment help', 'Prepare for Japan'], ['trust', 'agility', 'travel']):
        col.button(label, use_container_width=True, on_click=scenario, args=(key,))
    st.write('')
    mobile, assistant = st.columns([0.9, 1.6], gap='large')
    with mobile:
        with st.container(border=True):
            st.caption('9:41                                      ●●●  ▰')
            st.subheader('Good morning, Alex')
            st.caption('Your everyday banking, with a little more clarity.')
            st.markdown('<div class="bank-card"><div class="card-top"><span>Everyday account</span><strong>DBS</strong></div><div class="balance">S$48,650.00</div><small>Available balance</small><div class="card-bottom"><span>•••• 4821</span><span>VISA</span></div></div>', unsafe_allow_html=True)
            st.markdown('**Recent activity**')
            for t in s['transactions']:
                chosen = s['selected'] == t['id']
                if st.button(f"{'● ' if chosen else ''}{t['merchant']}\n\n{money(t['amount'])} · {t['status']}", key=t['id'], use_container_width=True, type='primary' if chosen else 'secondary'):
                    s['selected'] = t['id']
                    s['pending'] = None
                    ask('Explain this transaction')
                    st.rerun()
            st.caption('Tap a transaction to ask with its context attached.')
            st.divider()
            st.markdown('**Card controls · •••• 4821**')
            st.write(f"{'🔒 Locked' if s['card']['locked'] else '● Active'} · Overseas {'ON' if s['card']['overseas'] else 'OFF'}")
            st.caption(f"Daily spending limit: {money(s['card']['limit'])}")
    with assistant:
        st.subheader('✦ Your service companion')
        st.caption(f"Context attached: {s['selected']} · {transaction(s)['merchant']}")
        with st.container(height=360, border=True):
            if not s['messages']:
                st.markdown('### What would you like to understand?')
                st.write('Choose a transaction or ask a question. I can explain your payment, help with the next step, or pass your details to a service specialist.')
                st.caption('Try “Explain this transaction” or “Can I use my card in Japan?”')
            for m in s['messages']:
                with st.chat_message(m['role']):
                    st.markdown(m['text'])
                    if m.get('sources'):
                        st.caption('Source: ' + ' | '.join(m['sources']))
                    if m.get('transaction'):
                        st.caption('Attached: ' + m['transaction'])
        prompt = st.chat_input('Ask about this transaction, SGQR, or your trip…')
        if prompt:
            ask(prompt)
            st.rerun()
        quick = st.columns(3)
        for c, label in zip(quick, ["I don't recognize this", 'When will it disappear?', 'Check my limit']):
            c.button(label, on_click=ask, args=(label,), use_container_width=True)
        with st.expander('View transaction information'):
            st.json(transaction(s))
        if s['journey']:
            with st.container(border=True):
                st.markdown('#### Japan, with fewer loose ends')
                steps = [s['card']['overseas'] and not s['card']['locked'], s['limit_reviewed'], s['fx_reviewed']]
                st.progress(sum(steps) / 3)
                st.caption(' → '.join(f"{'✓' if done else '○'} {name}" for name, done in zip(['Overseas usage', 'Limit reviewed', 'FX understood'], steps)))
                if s['card']['locked']:
                    st.warning('Card is locked. Travel readiness requires human review of reactivation.')
                elif all(steps):
                    st.success('Travel checklist complete. Merchant acceptance and available funds still apply.')
                else:
                    st.info('Next: ' + next(name for name, done in zip(['enable overseas usage', 'review your spending limit', 'understand FX costs'], steps) if not done))
                st.button('Understand FX charges', on_click=ask, args=('Explain FX charges',))
        st.markdown('#### Take the next step')
        actions = st.columns(3)
        actions[0].button('Enable overseas usage', on_click=stage, args=('overseas',), disabled=s['card']['overseas'] or s['card']['locked'], use_container_width=True)
        actions[1].button('Lock card', on_click=stage, args=('lock',), disabled=s['card']['locked'], use_container_width=True)
        actions[2].button('Request fee reversal', on_click=stage, args=('fee', s['selected']), disabled=transaction(s)['type'] != 'fee', use_container_width=True)
        with st.expander('Check / change daily spending limit'):
            st.write(f"Current: **{money(s['card']['limit'])}**")
            limit = st.number_input('New limit (SGD)', min_value=1000, max_value=100000, value=s['card']['limit'], step=1000)
            st.button('Review limit change', on_click=stage, args=('limit', limit))
        if s['pending']:
            action, value = s['pending']
            limit_description = money(value or 0) if action == 'limit' else ''
            descriptions = {
                'overseas': 'Enable overseas transactions for card 4821',
                'lock': 'Lock card 4821. Existing transactions are not cancelled',
                'fee': f'Submit fee reversal request for {transaction(s)["merchant"]}; approval is not guaranteed',
                'limit': f'Change daily spending limit to {limit_description}',
            }
            with st.container(border=True):
                st.warning('Confirm: ' + descriptions[action] + '.')
                yes, no = st.columns(2)
                if yes.button('Confirm action', type='primary', use_container_width=True):
                    try:
                        result = execute(s, action, value)
                        s['pending'] = None
                        st.toast(result)
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                if no.button('Cancel', use_container_width=True):
                    s['pending'] = None
                    st.rerun()
        st.divider()
        if st.button('Send summary to human agent', use_container_width=True):
            s['handoff'] = send_to_agent(s)['summary']
        if s['handoff']:
            st.success('Your summary has been sent to a service specialist for review.')
            st.text_area('Summary sent for review', s['handoff'], height=200)
            st.download_button('Download summary', s['handoff'], file_name='nextserve-handoff.txt')

elif page == 'Knowledge studio':
    st.markdown('<div class="hero"><div class="eyebrow">Agility / Approved knowledge</div><h1>New issue. Ready to answer.</h1><p>Publish an approved update, then ask the assistant immediately.</p></div>', unsafe_allow_html=True)
    form, library = st.columns([1.15, 1], gap='large')
    with form:
        st.subheader('Publish a service notice or promo')
        st.caption('Review and approve a notice before making it available to customers.')
        with st.form('publish'):
            title = st.text_input('Title', 'SGQR intermittent payment delays')
            keywords = st.text_input('Matching keywords (comma separated)', 'SGQR, payment, pending, delay')
            body = st.text_area('Approved answer', 'SGQR payments are experiencing intermittent delays at present. Check transaction status before retrying to avoid duplicate payment. The operations team targets resolution by 15:00 SGT on 10 September 2026; this is an estimate, not a guarantee. If still pending after that time, request human support.', height=170)
            approved = st.checkbox('I approve this content for customer use')
            submitted = st.form_submit_button('Publish approved knowledge', type='primary')
            if submitted:
                try:
                    item = publish(s, title, keywords, body, approved)
                    st.success(f"{item['id']} is available immediately. Open a SGQR transaction and choose Learn More, or use Agility in Service companion.")
                except ValueError as e:
                    st.error(str(e))
    with library:
        st.subheader('Live knowledge library')
        for k in reversed(s['knowledge']):
            with st.container(border=True):
                st.markdown('**' + k['title'] + '**')
                st.caption(f"APPROVED · {k['id']} · {k['published']}")
                st.write(k['body'])
                st.caption('Keywords: ' + k['keywords'])

else:
    st.markdown('<div class="hero"><div class="eyebrow">Service performance / Planning</div><h1>A measurable path to fewer calls.</h1><p>Focus on repetitive clarification and servicing. Keep people available for complex cases.</p></div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    tx_rate = a.slider('Transaction-detail containment assumption (%)', 0, 100, 70)
    fee_rate = b.slider('Fee-reversal containment assumption (%)', 0, 100, 30)
    avoided, reduction = impact(tx_rate, fee_rate)
    metrics = st.columns(4)
    for col, label, val in zip(metrics, ['Monthly inquiry baseline', 'Potentially avoided', 'Potential reduction', 'Remaining inquiries'], ['45,200', f'{avoided:,.0f}', f'{reduction:.1f}%', f'{45200-avoided:,.0f}']):
        col.metric(label, val)
    st.write('')
    st.dataframe([
        {'Category': 'Transaction details', 'Monthly baseline': 27600, 'Assumed containment': f'{tx_rate}%', 'Potential avoided': round(27600*tx_rate/100)},
        {'Category': 'Fee reversal', 'Monthly baseline': 11300, 'Assumed containment': f'{fee_rate}%', 'Potential avoided': round(11300*fee_rate/100)},
        {'Category': 'Other inquiries', 'Monthly baseline': 6300, 'Assumed containment': '0%', 'Potential avoided': 0},
    ], use_container_width=True, hide_index=True)
    st.bar_chart({'Inquiries': {'Baseline': 45200, 'Potential avoided': avoided, 'Remaining': 45200-avoided}}, color='#c8102e', horizontal=True)
    st.info('Planning estimate, not measured results. Projected reduction is based on the selected containment assumptions and the monthly inquiry baseline.')
    st.caption('The projection assumes separate inquiry categories and full reach among eligible customers. Adoption and repeat contacts may reduce the achieved impact.')
    with st.expander('What a pilot must prove', expanded=True):
        st.write('Measure successful digital resolution with no assisted recontact within 7 days, adoption among eligible customers, repeat-contact rate, escalation quality and customer satisfaction. Validate call categories and compare with a control group before claiming reduction.')
    st.markdown('#### Current session · Service activity')
    c1, c2, c3 = st.columns(3)
    c1.metric('Completed actions', len(s['actions']))
    c2.metric('Fee requests awaiting review', len(s['requests']))
    c3.metric('Approved knowledge records', len(s['knowledge']))
    st.caption('Session activity is not evidence of call containment.')
