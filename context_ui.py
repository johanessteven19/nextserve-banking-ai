import streamlit as st
from urllib.parse import urlencode, urlparse
from payment_context import history_context, search_merchant
from services import money


@st.cache_data(ttl=900, show_spinner=False)
def merchant_lookup(group):
    return search_merchant(group)


def render_context(s, t):
    evidence = history_context(s['transactions'], t)
    with st.container(border=True):
        st.subheader('✦ AI payment context')
        st.caption('A concise check of your transaction history')
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
        with st.expander('Public sources (optional)'):
            st.warning('External links open a separate website. Check the destination before continuing.')
            allow_external = st.checkbox('I understand and want to view public sources', key='external_sources_' + t['id'])
            if allow_external:
                with st.spinner('Checking public sources…'):
                    results = merchant_lookup(t['merchant_group'])
                if results['error']:
                    st.info(results['error'])
                else:
                    st.caption('Search results · retrieved ' + results['checked'])
                    for row in results['rows']:
                        st.link_button(row['title'] or urlparse(row['url']).netloc, row['url'])
                        st.text(row['snippet'])
                if results['query']:
                    st.link_button('Open public search', 'https://www.bing.com/search?' + urlencode({'q':results['query']}))
                st.caption('Only the merchant name is used for this search. Public sources cannot confirm who authorized a payment.')
