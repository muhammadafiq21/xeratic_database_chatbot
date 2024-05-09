
# intial chat history
if "messages" not in st.session_state:
    # print("Creating session state")
    st.ssession_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("whats is up?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.spinner("Generating respone..."):
        with st.chat_message("assistant"):
            response = invoke_chain(prompt,st.session_atate.messages)
            st.markdown(response)
    st.session_state.messages.append({"role": "asisntant", "content": response})