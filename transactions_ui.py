"""Transaction-first customer journey, with explicit mock-action confirmations."""
import streamlit as st
from context_ui import render_context
from services import (transaction, money, explain_transaction, execute, answer,
                      request_replacement, file_dispute, file_disputes, handoff, similar_transactions, send_to_agent, case_for,
                      connect_digibot, send_customer_summary)


def navigate(s, view):
    s['transaction_view'] = view
    s['pending'] = None


def open_transaction(s, tx_id):
    s['selected'] = tx_id
    s['handoff'] = None
    navigate(s, 'details')


def recognize(s):
    if s['selected'] not in s['recognized']:
        s['recognized'].append(s['selected'])
    s['messages'].append({'role': 'user', 'text': 'I recognize this transaction.', 'transaction': s['selected']})
    navigate(s, 'recognized')


def unrecognized(s):
    if s['selected'] in s['recognized']:
        s['recognized'].remove(s['selected'])
    s['messages'].append({'role': 'user', 'text': 'I do not recognize this transaction.', 'transaction': s['selected']})
    navigate(s, 'protect')


def render_transactions(s, mobile=False):
    if mobile:
        from mobile_journey import render_mobile_journey
        if render_mobile_journey(s):
            return
    view = s['transaction_view']
    if view == 'history':
        st.caption('DBS / EVERYDAY BANKING')
        st.title('Transactions')
        st.write('Select a payment to understand what happened and decide what to do next.')
        st.caption('All amounts are shown in Singapore dollars (SGD).')
        if mobile:
            account = st.container()
            history = st.container()
        else:
            history, account = st.columns([1.7, 1], gap='large')
        with history:
            st.subheader('Recent activity')
            for t in s['transactions']:
                with st.container(border=True):
                    info, amount = st.columns([2, 1])
                    info.text(t['statement_descriptor'])
                    info.caption(t['date'] + ' · ' + t['channel'])
                    info.caption('REF ' + t['payment_reference'])
                    amount.markdown('**' + money(t['amount']) + '**')
                    amount.caption(t['status'])
                    case = case_for(s, t['id'])
                    if case:
                        st.caption('Disputed · ' + case['id'] + ' · ' + case['status'])
                    elif t['id'] in s['recognized']:
                        st.caption('Recognized by you')
                    st.button('View transaction', key='view_' + t['id'], on_click=open_transaction,
                              args=(s, t['id']), use_container_width=True)
        with account:
            st.markdown('<div class="bank-card"><div class="card-top"><span>Everyday account</span><strong>DBS</strong></div><div class="balance">S$48,650.00</div><small>Available balance</small><div class="card-bottom"><span>•••• 4821</span><span>VISA</span></div></div>', unsafe_allow_html=True)
            st.write('**Card status:** ' + ('Locked' if s['card']['locked'] else 'Active'))
            st.button('Track my cases', on_click=navigate, args=(s, 'cases'), use_container_width=True)
        return

    st.button('← All transactions', on_click=navigate, args=(s, 'history'))
    if view == 'cases':
        st.title('Your cases')
        all_cases = dict(s.get('sample_cases', {}))
        all_cases.update(s.get('cases', {}))
        if not all_cases:
            st.info('You have no submitted cases. Start by opening a transaction.')
        for tx_id, case in all_cases.items():
            with st.container(border=True):
                st.markdown(f"**{case['id']} · {case['merchant']}**")
                st.write('Disputed · ' + case['status'])
                st.caption('Last update · ' + case.get('updated', case['created']))
                if st.button('View case', key='case_' + tx_id):
                    s['selected'] = tx_id
                    navigate(s, 'track')
                    st.rerun()
        return

    t = transaction(s)
    if not mobile:
        st.caption('TRANSACTIONS / ' + {'details':'DETAILS', 'learn':'LEARN MORE', 'recognized':'CONFIRMED',
               'protect':'UNRECOGNIZED PAYMENT', 'replace':'REPLACE CARD', 'dispute':'FILE DISPUTE', 'track':'TRACK CASE'}[view])
    st.title({'details':'Transaction details', 'learn':'A little more clarity', 'recognized':'You recognize this payment',
              'protect':'Let’s secure your account', 'replace':'Request a replacement card',
              'dispute':'Tell us what happened', 'track':'Your case, in one place'}[view])
    with st.container(border=True):
        st.subheader(t['friendly_name'])
        st.markdown(f"### {money(t['amount'])}")
        st.caption(t['date'] + ' · ' + t['channel'] + ' · ' + t['id'])
        if not mobile:
            st.caption('As shown on your statement')
            st.text(t['statement_descriptor'])
        case = case_for(s, t['id'])
        if case:
            st.warning('Disputed · ' + case['id'] + ' · ' + case['status'])

    if view == 'recognized':
        st.success('Thanks for confirming. No further action is needed for this transaction.')
        if case_for(s, t['id']) or s['card']['locked']:
            st.info('Any existing case or card lock remains in place. Recognizing a transaction does not cancel an existing request or unlock the card.')
        st.button('Back to transactions', type='primary', on_click=navigate, args=(s, 'history'))
        st.button('Review transaction again', on_click=navigate, args=(s, 'details'))
        return

    if view in ['details', 'learn']:
        headline, explanation = explain_transaction(t)
        st.subheader(headline)
        st.write(explanation)
        st.caption('Based on this transaction’s recorded status: ' + t['status'] + '. This does not confirm who authorized it.')
        if view == 'learn':
            render_context(s, t)
            st.markdown('#### From statement code to plain language')
            st.text(t['statement_descriptor'])
            st.dataframe(t['descriptor_parts'], hide_index=True, use_container_width=True)
            st.caption('Reference ' + t['payment_reference'] + ' identifies this payment. Use it when contacting us about the transaction.')
            st.markdown('#### How to check whether this was yours')
            st.write(t['recognition_tip'])
            st.markdown('#### What else should I know?')
            st.write(t['detail'])
            st.write(t['timing'])
            if t['type'] == 'authorization':
                st.write('A temporary hold reserves part of your available spending amount. It can become a completed payment or be released. The transaction record cannot tell us why the merchant created it or whether you approved it.')
            if t['type'] == 'sgqr':
                # Retrieve approved knowledge afresh on every visit, without repeating chat history.
                n = len(s['messages'])
                notice = answer(s, 'Why is my SGQR payment pending?')
                sources = s['messages'][-1].get('sources', [])
                del s['messages'][n:]
                st.info(notice)
                if sources:
                    st.caption('Approved source: ' + ' | '.join(sources))
            with st.expander('View original transaction record'):
                st.json(t)
            st.button('Back to details', on_click=navigate, args=(s, 'details'))
        st.markdown('#### What would you like to do?')
        options = [st.container() for _ in range(3)] if mobile else st.columns(3)
        options[0].button('I recognize this', on_click=recognize, args=(s,), use_container_width=True)
        options[1].button('Learn More', on_click=navigate, args=(s, 'learn'), disabled=view == 'learn', use_container_width=True)
        options[2].button('I don’t recognize this', on_click=unrecognized, args=(s,), type='primary', use_container_width=True)
        return

    if view == 'protect':
        st.write('You don’t recognize this payment. Secure your card, then tell us what needs investigating. Your transaction details stay with you at every step.')
        if t['type'] == 'sgqr':
            st.info('This is a SGQR payment. Locking your card does not stop SGQR or account payments; request human support for account protection. You can still report this payment below.')
        st.markdown('#### 1 · Secure your card')
        if s['card']['locked']:
            st.success('Card •••• 4821 is locked. Existing payments are not cancelled.')
        else:
            st.write('Temporarily stop new card purchases. This does not reverse this payment.')
            if st.button('Lock card', type='primary'):
                s['pending'] = ('lock', None)
            if s['pending']:
                st.warning('Lock card •••• 4821? New card purchases will be blocked until the card is reactivated.')
                yes, no = st.columns(2)
                if yes.button('Confirm card lock', type='primary'):
                    execute(s, 'lock')
                    s['pending'] = None
                    st.rerun()
                if no.button('Cancel lock'):
                    s['pending'] = None
                    st.rerun()
        st.markdown('#### 2 · Replace your card, if needed')
        st.write('Request a new card if you think your card details have been exposed.')
        st.button('Replace card', on_click=navigate, args=(s, 'replace'), disabled=not s['card']['locked'])
        st.markdown('#### 3 · Report this payment')
        st.write('File a dispute for review. You can report the payment without requesting a replacement.')
        st.button('File dispute', on_click=navigate, args=(s, 'dispute'), type='primary')
        st.markdown('#### 4 · Keep track')
        st.button('Track case', on_click=navigate, args=(s, 'track'), disabled=case_for(s, t['id']) is None)
        st.button('Back to details', on_click=navigate, args=(s, 'details'))

    elif view == 'replace':
        if s['replacement']:
            st.success(s['replacement']['id'] + ' · ' + s['replacement']['status'])
            st.write('Your original card remains locked. Your replacement request is awaiting review. Delivery details will be confirmed once it is processed.')
        else:
            st.write('Your original card will stay locked while we review your replacement request. Any applicable fees and delivery details will be confirmed before processing.')
            with st.form('replacement_form'):
                confirmed = st.checkbox('I want to request a replacement for card •••• 4821')
                if st.form_submit_button('Confirm replacement request', type='primary'):
                    if not confirmed:
                        st.error('Confirm the replacement request before continuing.')
                    else:
                        try:
                            request_replacement(s)
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
        st.button('Continue to file dispute', on_click=navigate, args=(s, 'dispute'), type='primary')
        st.button('Back to protection steps', on_click=navigate, args=(s, 'protect'))

    elif view == 'dispute':
        if case_for(s, t['id']):
            st.info('You have already reported this transaction. Track the existing case below.')
            st.button('Track case', on_click=navigate, args=(s, 'track'), type='primary')
        else:
            if t['status'] == 'Pending':
                st.info('This payment is still pending. We can record your report now and review the transaction once it completes. Submitting a report does not guarantee a refund.')
            st.caption('Your transaction details are already attached. Tell us why you are reporting this payment.')
            with st.form('dispute_' + t['id']):
                reason = st.text_area('Describe the issue', 'I do not recognize this transaction and would like it investigated.')
                confirmed = st.checkbox('I confirm I do not recognize this transaction and want to submit this report')
                if st.form_submit_button('Submit dispute', type='primary'):
                    try:
                        file_dispute(s, t['id'], reason, confirmed)
                        navigate(s, 'track')
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
        st.button('Back to protection steps', on_click=navigate, args=(s, 'protect'))

    elif view == 'track':
        case = case_for(s, t['id'])
        if not case:
            st.info('No case has been submitted for this transaction yet.')
            st.button('File dispute', on_click=navigate, args=(s, 'dispute'))
        else:
            st.success('Report received · ' + case['id'])
            st.markdown('**Current status: ' + case['status'] + '**')
            st.caption('Submitted ' + case['created'] + ' · Last update ' + case.get('updated', case['created']))
            st.write('**Your report:** ' + case['reason'])
            st.markdown('#### Case timeline')
            for milestone in case.get('timeline', []):
                marker = '✓' if milestone['status'] == 'Complete' else ('◷' if milestone['status'] == 'In progress' else '○')
                st.write(f"{marker} **{milestone['label']}** · {milestone['status']}")
                st.caption(milestone['timestamp'])
            st.divider()
            st.write('**Card:** ' + ('Locked' if s['card']['locked'] else 'Active'))
            if s['replacement']:
                st.write('**Replacement:** ' + s['replacement']['id'] + ' · ' + s['replacement']['status'])
            st.caption('Keep your case reference for any follow-up enquiries.')
            st.download_button('Download case summary', '\n'.join(f'{k}: {v}' for k, v in case.items()), file_name=case['id'] + '.txt')
            st.markdown('#### Do you recognize these similar transactions?')
            st.caption('Select one or more related payments to report together, or review them individually. Similarity does not mean a payment is unauthorized.')
            matches = similar_transactions(s, t['id'])
            if not matches:
                st.info('No similar transactions were found in your history.')
            available = [(candidate, reasons) for candidate, reasons in matches if not case_for(s, candidate['id'])]
            if available:
                with st.form('related_disputes_' + t['id']):
                    st.markdown('**Report multiple payments together**')
                    st.caption('Tick every recurring or similar payment you also do not recognize. They will receive separate case references under one submission.')
                    for candidate, reasons in available:
                        st.checkbox(
                            f"{candidate['merchant']} · {money(candidate['amount'])} · {candidate['date'].split(' · ')[0]}",
                            key='select_related_' + t['id'] + '_' + candidate['id'])
                        st.caption(candidate['statement_descriptor'] + ' · ' + ' · '.join(reasons))
                    batch_reason = st.text_area(
                        'Reason for selected payments',
                        'I do not recognize these related payments and would like them investigated.',
                        key='related_reason_' + t['id'])
                    batch_confirmed = st.checkbox(
                        'I confirm I do not recognize each selected payment and want to submit these reports',
                        key='related_confirm_' + t['id'])
                    batch_submitted = st.form_submit_button('Submit selected disputes', type='primary')
                if batch_submitted:
                    selected_ids = [candidate['id'] for candidate, _ in available
                                    if st.session_state.get('select_related_' + t['id'] + '_' + candidate['id'], False)]
                    try:
                        submitted_cases = file_disputes(s, selected_ids, batch_reason, batch_confirmed)
                        s['batch_dispute_notice'] = (
                            f"{len(submitted_cases)} related dispute{'s' if len(submitted_cases) != 1 else ''} submitted. "
                            'Each payment now has its own case reference.'
                        )
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
            for candidate, reasons in matches:
                with st.container(border=True):
                    st.markdown(f"**{candidate['merchant']} · {money(candidate['amount'])}**")
                    st.text(candidate['statement_descriptor'])
                    st.caption(candidate['date'] + ' · ' + candidate['status'])
                    st.write(' · '.join(reasons))
                    candidate_case = case_for(s, candidate['id'])
                    if candidate_case:
                        st.caption('Disputed · ' + candidate_case['id'] + ' · ' + candidate_case['status'])
                    st.button('Review this transaction', key='similar_' + candidate['id'],
                              on_click=open_transaction, args=(s, candidate['id']))
            batch_notice = s.pop('batch_dispute_notice', None)
            if batch_notice:
                st.success(batch_notice)
        st.button('Back to protection steps', on_click=navigate, args=(s, 'protect'))

    with st.container(border=True, key='digibot_panel'):
        st.markdown('#### Connect to Digibot')
        st.write('Continue with a service assistant that already has this transaction and your completed actions in context.')
        if s.get('digibot_connected'):
            st.success('Digibot is connected and ready to help with this transaction.')
        elif st.button('Connect to Digibot', type='primary', use_container_width=True):
            connect_digibot(s)
            st.rerun()

    with st.container(border=True, key='customer_summary_panel'):
        st.markdown('#### Summary of actions')
        st.write('Send a record of the steps you have taken in this session to your registered contact channels.')
        summary = s.get('customer_summary')
        if not summary:
            st.caption('Delivery channels · Email · Push notification')
            if st.button('Send summary to customer', use_container_width=True):
                send_customer_summary(s)
                st.rerun()
        else:
            st.success('Summary sent to your email and push notifications.')
            st.caption('Sent · ' + summary['sent'] + ' · ' + summary['id'])
            st.write('**Channels:** ' + ' · '.join(summary['channels']))
            with st.expander('View summary'):
                st.write('\n'.join('• ' + item for item in summary['actions']))
