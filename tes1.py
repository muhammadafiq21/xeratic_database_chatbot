import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import AzureChatOpenAI
import pandas as pd
import json
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
uri = os.getenv('uri')
db_uri = uri

# Connect to the database
db = SQLDatabase.from_uri(db_uri)
db_schema = db.get_table_info()

# Initialize Azure Chat OpenAI
llm = AzureChatOpenAI(
    deployment_name=os.getenv('deployment_name'),
    openai_api_version=os.getenv('openai_api_version'),
    openai_api_key=os.getenv('openai_api_key'),
    azure_endpoint=os.getenv('azure_endpoint')
)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Create table for chat history
history_message = pd.DataFrame(columns=["question", "answer"])

# Define chat prompt template for database query
db_template = """
Below listed the database schema, write MySQL query based on the text inputted, always write the table name when selecting column.
you should consider Message History when creating SQL query just in case it is a follow-up question from previous question:
{schema}

Question: {question}
Message History: {history_message}
SQL Query:
"""

db_prompt = ChatPromptTemplate.from_template(db_template)

# Define chat prompt template for SQL response
sql_template = """
Based on the table schema below, question, sql query, and sql response, write a natural language response:
{schema}

Question: {question}
SQL Query: {query}
SQL Response: {response}
"""

sql_prompt = ChatPromptTemplate.from_template(sql_template)

# Create chain for SQL queries
sql_chain = (
    db_prompt
    | llm.bind(stop="\nSQL Result:")
    | StrOutputParser()
)

# Create full chain
full_chain = (
    sql_prompt
    | llm
    | StrOutputParser()
)

########################## MAIN APP #####################################
st.title("XERATIC DATABASE CHATBOT")

# Accept user input
user_input = st.chat_input("Enter your message:")

if user_input:
    st.session_state.messages.append({"role": "User", "content": user_input})

    try:
        # Run SQL query
        with st.spinner("Processing..."):
            query_response = sql_chain.invoke({"schema": db_schema, "question": user_input, "history_message": history_message})
            st.session_state.messages.append({"role": "Chatbot (SQL Response)", "content": query_response})

            # Connect to MySQL
            cnx = mysql.connector.connect(
                host=os.getenv('host'),
                user=os.getenv('user'),
                password=os.getenv('password'),
                database=os.getenv('database')
            )

            # Execute query and get response
            cursor = cnx.cursor()
            cursor.execute(query_response)
            data = []
            for row in cursor:
                data.append(row)
            df = pd.DataFrame(data, columns=cursor.column_names)

            # Add query response to chat history
            st.session_state.messages.append({"role": "Database Output", "content": df})

            # Generate a natural language response
            natural_response = full_chain.invoke({"question": user_input, "query": query_response, "response": df, "schema": db_schema})
            st.session_state.messages.append({"role": "Chatbot (Natural Language Response)", "content": natural_response})

    except Exception as e:
        st.error(f"An error occurred: {e}")

# Display chat history
for message in st.session_state.messages:
    with st.expander(f"{message['role']}"):
        st.write(message['content'])
