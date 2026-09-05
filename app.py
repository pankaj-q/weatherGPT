import streamlit as st
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from src.agent import build_weather_agent

load_dotenv()

st.set_page_config(page_title="WeatherGPT", page_icon="🌤️", layout="centered")
st.title("🌤️ WeatherGPT Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

if user_input := st.chat_input("Ask about weather, forecasts, or agro-advisories..."):
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append(HumanMessage(content=user_input))
    
    with st.chat_message("assistant"):
        with st.spinner("Fetching meteorological telemetry..."):
            agent = build_weather_agent()
            history = st.session_state.messages[:-1]
            result = agent.invoke({"input": user_input, "chat_history": history})
            st.markdown(result["output"])
            st.session_state.messages.append(AIMessage(content=result["output"]))