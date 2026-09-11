"""Compact mobile-only layouts; the desktop renderer is left intact."""
import streamlit as st
from services import transaction, money, explain_transaction, execute, answer
from payment_context import date_of, history_context, MERCHANTS
from context_ui import merchant_lookup
from urllib.parse import urlencode


def render_mobile_journey(s):
    from transactions_ui import navigate, open_transaction, recognize, unrecognized
    view = s['transaction_view']
    if view not in ['history', 'details', 'learn', 'protect']:
        return False
    if view == 'history':
        st.title('Transactions')
        st.caption('Everyday account · •••• 4821 · SGD')
        query = st.text_input('Search transactions', placeholder='Merchant, amount or reference', key='mobile_search')
        status = st.radio('Payments', ['All', 'Pending', 'Posted'], horizontal=True, label_visibility='collapsed', key='mobile_filter')
        matches = [t for t in s['transactions'] if (status == 'All' or t['status'] == status)
                   and query.casefold() in (t['statement_descriptor'] + ' ' + t['merchant'] + ' ' +
                       t['friendly_name'] + ' ' + t['payment_reference'] + ' ' + money(t['amount'])).casefold()]
        matches.sort(key=date_of, reverse=True)
        count = s.get('mobile_visible_count', 8)
        if not matches:
            st.info('No payments match your search. Try another merchant or filter.')
        last_date = None
        for t in matches[:count]:
            date = t['date'].split(' · ')[0]
            if date != last_date:
                st.caption(date)
                last_date = date
            suffix = ' · Case open' if t['id'] in s['cases'] else ' · Recognized' if t['id'] in s['recognized'] else ''
            st.button(f"{t['statement_descriptor']}\n\n{money(t['amount'])} · {t['status']}{suffix}  ›",
                      key='view_' + t['id'], on_click=open_transaction, args=(s,t['id']), use_container_width=True)
        if len(matches) > count and st.button('Show more payments', use_container_width=True):
            s['mobile_visible_count'] = count + 8
            st.rerun()
        return True

    st.button('‹ Transactions' if view == 'details' else '‹ Payment details',
              on_click=navigate, args=(s,'history' if view == 'details' else 'details'))
    t = transaction(s)
    st.subheader(t['friendly_name'])
    st.markdown('## ' + money(t['amount']))
    st.caption(t['date'] + ' · ' + t['status'])

    if view == 'details':
        headline, detail = explain_transaction(t)
        st.markdown('**' + headline + '**')
        st.write(detail)
        st.button('Learn More', type='primary', use_container_width=True, on_click=navigate, args=(s,'learn'))
        st.button('I recognize this', use_container_width=True, on_click=recognize, args=(s,))
        st.button('I don’t recognize this', use_container_width=True, on_click=unrecognized, args=(s,))
        with st.expander('Statement & payment information'):
            st.text(t['statement_descriptor'])
            st.caption(t['payment_reference'] + ' · ' + t['channel'])
            st.write(t['timing'])
        return True

    if view == 'learn':
        evidence = history_context(s['transactions'], t)
        st.markdown('#### ✦ What we found')
        st.write(evidence['headline'])
        if evidence['monthly'] and t['status'] == 'Posted':
            series = evidence['series']
            st.write(f"{len(series)} monthly payments · {money(evidence['typical'])} typical amount")
            st.caption(series[0]['date'].split(' · ')[0] + ' – ' + series[-1]['date'].split(' · ')[0])
        else:
            st.caption(f"{max(0,len(evidence['matches'])-1)} earlier payments to this merchant group. No confirmed subscription pattern.")
        st.caption('A pattern does not confirm who authorized a payment.')
        st.button('I recognize this', type='primary', use_container_width=True, on_click=recognize, args=(s,))
        st.button('I don’t recognize this', use_container_width=True, on_click=unrecognized, args=(s,))
        with st.expander('Previous payments'):
            for old in evidence['matches']:
                st.write(old['date'] + ' · ' + money(old['amount']))
                st.caption(old['statement_descriptor'] + ' · ' + old['status'])
        with st.expander('Understand the statement description'):
            st.text(t['statement_descriptor'])
            for part in t['descriptor_parts']:
                st.markdown('**' + part['Statement text'] + '**')
                st.write(part['Plain-language meaning'])
            st.write(t['recognition_tip'])
        with st.expander('Public sources (optional)'):
            st.warning('External links open a separate website. Check the destination before continuing.')
            allow_external = st.checkbox('I understand and want to view public sources', key='mobile_external_sources_' + t['id'])
            if allow_external:
                with st.spinner('Checking public sources…'):
                    results = merchant_lookup(t['merchant_group'])
                if results['error']:
                    st.info(results['error'])
                for row in results['rows']:
                    st.link_button(row['title'], row['url'])
                    st.write(row['snippet'])
                if results['query']:
                    st.link_button('Open public search', 'https://www.bing.com/search?' + urlencode({'q':results['query']}))
                st.caption('Only the merchant name is used for this search. Public sources cannot confirm who authorized a payment.')
        with st.expander('Payment timing & further help'):
            st.write(t['timing'])
            if t['type'] == 'sgqr':
                n = len(s['messages'])
                st.info(answer(s, 'Why is my SGQR payment pending?'))
                del s['messages'][n:]
        return True

    st.markdown('#### Secure your card')
    if t['type'] == 'sgqr':
        st.info('Card locking does not stop SGQR payments. Contact a specialist for account protection.')
    if s['card']['locked']:
        st.success('Card •••• 4821 is locked')
    else:
        st.write('Block new card purchases while you review this payment.')
        if not s['pending'] and st.button('Lock card', type='primary', use_container_width=True):
            s['pending'] = ('lock', None)
            st.rerun()
        if s['pending']:
            st.warning('Lock card •••• 4821? Existing payments will not be cancelled.')
            if st.button('Confirm card lock', type='primary', use_container_width=True):
                execute(s, 'lock')
                s['pending'] = None
                st.rerun()
            if st.button('Cancel lock', use_container_width=True):
                s['pending'] = None
                st.rerun()
    st.button('File dispute', type='primary' if s['card']['locked'] else 'secondary',
              use_container_width=True, on_click=navigate, args=(s,'dispute'))
    with st.expander('Replace your card, if needed'):
        st.write('If your card details were exposed, request a replacement after locking your card.')
        st.button('Replace card', disabled=not s['card']['locked'], use_container_width=True,
                  on_click=navigate, args=(s,'replace'))
    if t['id'] in s['cases']:
        st.button('Track case', use_container_width=True, on_click=navigate, args=(s,'track'))
    with st.expander('Need a person?'):
        from services import send_to_agent
        key = s['cases'].get(t['id'], {}).get('id',t['id'])
        if st.button('Send summary to human agent', disabled=key in s['agent_handoffs']):
            send_to_agent(s)
            st.rerun()
        if key in s['agent_handoffs']:
            st.success('Your summary has been sent for review.')
    return True
