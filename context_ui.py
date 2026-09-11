import streamlit as st
from urllib.parse import urlencode, urlparse
from payment_context import history_context, search_merchant, MERCHANTS
from services import money


@st.cache_data(ttl=900, show_spinner=False)
def merchant_lookup(group):
    return search_merchant(group)


def render_context(s, t):
    evidence = history_context(s['transactions'], t)
    with st.container(border=True):
        st.subheader('✦ AI payment context')
        st.caption('Your history + public merchant information')
        st.markdown('#### ' + evidence['headline'])
        if evidence['monthly'] and t['status'] == 'Posted':
            series = evidence['series']
            st.write(f"I found {len(series)} completed payments with the same statement description, "
                     f"from {series[0]['date'].split(' · ')[0]} to {series[-1]['date'].split(' · ')[0]} "
                     f"({evidence['elapsed']} days of history). They occur roughly every month.")
            st.write(f"{'Each payment is' if evidence['stable'] else 'The typical payment is'} {money(evidence['typical'])}.")
        else:
            st.write(f"I found {max(0, len(evidence['matches'])-1)} earlier payments to this merchant group. "
                     'The available records do not establish that this payment is a subscription.')
        st.caption('Based on the history available up to this payment. A recurring pattern does not confirm that you authorized it or when a subscription originally started.')
        with st.expander('See the payments behind this finding'):
            for previous in evidence['matches']:
                st.write(f"{previous['date']} · {money(previous['amount'])} · {previous['status']}")
                st.text(previous['statement_descriptor'])
        st.markdown('#### About the merchant')
        profile = MERCHANTS.get(t['merchant_group'])
        if profile:
            st.write('Merchant name: **' + profile[0] + '**')
            st.caption('Matched from the merchant information attached to your payment.')
            if profile[1]:
                st.write(profile[2])
                st.link_button('Merchant billing guidance', profile[1])
                st.caption('Saved official guidance · checked 11 September 2026')
        with st.spinner('Searching public merchant information…'):
            results = merchant_lookup(t['merchant_group'])
        if results['error']:
            st.info(results['error'])
        else:
            st.caption('Bing search results · retrieved ' + results['checked'])
            for row in results['rows']:
                st.link_button(row['title'] or urlparse(row['url']).netloc, row['url'])
                st.text(row['snippet'])
        if results['query']:
            st.link_button('Open merchant search', 'https://www.bing.com/search?' + urlencode({'q':results['query']}))
            st.caption('Search uses only the merchant name. Search snippets are external information, not confirmation of this transaction.')
