import streamlit as st
import _mysql_connector
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import AzureChatOpenAI
import pandas as pd
import json
import mysql.connector
import mysql
import pymysql
import re
import os
from dotenv import load_dotenv

load_dotenv()

# api and password
uri = os.getenv('uri')

# declare llm
llm = AzureChatOpenAI(
    deployment_name=os.getenv('deployment_name'),
    openai_api_version=os.getenv('openai_api_version'),
    openai_api_key=os.getenv('openai_api_key'),
    azure_endpoint=os.getenv('azure_endpoint')
)

# connect database
db_uri = uri
db = SQLDatabase.from_uri(db_uri)

# connect database v2
cnx = mysql.connector.connect(
  host=os.getenv('host'),
  user=os.getenv('user'),
  password=os.getenv('password'),
  database = os.getenv('database')
)

# get schema
db_schema = db.get_table_info()

# run query
def run_query(query):
    return db.run(query)

# create table for chat history
history_message = pd.DataFrame(columns=["question", "answer"])

# template
template = """
Below listed the database schema, write MySQL query based on the text inputted, always write the table name when selecting column.
you should consider Message History when creating SQL query just in case it is a follow-up question from previous question:
{schema}

Question: {question}
Message History: {history_message}
SQL Query:
"""
aiprompt = ChatPromptTemplate.from_template(template)

# second template
template = """
Based on the table schema below, question, sql query, and sql response, write a natural language response:
{schema}

Question: {question}
SQL Query: {query}
SQL Response: {response}
"""
prompt = ChatPromptTemplate.from_template(template)

# create chain
sql_chain = (
    aiprompt
    | llm.bind(stop="\nSQL Result:")
    | StrOutputParser()
)

# create full chain
full_chain = (
     prompt
    | llm
    | StrOutputParser()
)


########################## MAIN APP #####################################
st.title("XERATIC DATABASE CHATBOT")

if 'prompt' not in st.session_state:
    st.session_state['prompt'] = ""

# Input field for the user to type a message
prompt = st.chat_input("Enter your message:")
if prompt:
    st.session_state['prompt'] = prompt
try:
    if st.session_state['prompt']:
        with st.spinner("Processing..."):
            # run query directly without using langchain
            jawaban = sql_chain.invoke({"schema": db_schema, "question": st.session_state['prompt'], "history_message": history_message})
            cursor=cnx.cursor()
            query=(jawaban)
            cursor.execute(query)
            data = []
            for row in cursor:
                data.append(row)
            df = pd.DataFrame(data, columns=cursor.column_names)
            respon = full_chain.invoke({"question": st.session_state['prompt'], "query": jawaban, "response": df, "schema": db_schema})
            push_history = {'question': st.session_state['prompt'], 'answer':respon}
            history_message.loc[len(history_message)] = push_history

        tab_titles = ["Result", "Query", "Reason"]
        tabs = st.tabs(tab_titles)
        
        with tabs[1]:
            st.write("Generate Query:")
            st.code(jawaban, language="sql")
        with tabs[0]:
            st.write("Database Output:")
            st.write(df)
        with tabs[2]:
            st.write("Reason:")
            st.write(respon)

except Exception as e:
    st.write(f"An error occurred: {e}")
