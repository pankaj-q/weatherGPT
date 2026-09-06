import os
from dotenv import load_dotenv
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from src.agent import build_weather_agent

load_dotenv()

st.set_page_config(
    page_title="WeatherGPT Dashboard",
    page_icon="🌤️",
    layout="wide"  # Uses full screen width
)

# Custom CSS for cards and metrics styling
st.markdown("""
<style>
    .metric-card {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .alert-banner {
        padding: 10px 14px;
        border-radius: 8px;
        font-weight: 600;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Initialize Session State
# -------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "latest_telemetry" not in st.session_state:
    st.session_state.latest_telemetry = {
        "location": "No search yet",
        "temp": "--",
        "humidity": "--",
        "wind": "--",
        "rain_prob": "--",
        "alert_status": "Normal"
    }

# -------------------------------------------------------------
# Header
# -------------------------------------------------------------
st.title("🌤️ WeatherGPT Assisstance")
st.caption("AI-powered weather forecasting, hyper-local advisories, and disaster alerts.")
st.divider()

# -------------------------------------------------------------
# Main Layout: 60% Chat, 40% Live Data Cards
# -------------------------------------------------------------
col_chat, col_data = st.columns([1.3, 0.9], gap="large")

# === LEFT COLUMN: CONVERSATIONAL AGENT ===
with col_chat:
    st.subheader("💬 Weather Assistant")
    
    # Scrollable chat message container
    chat_container = st.container(height=520)
    with chat_container:
        for msg in st.session_state.messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            with st.chat_message(role):
                st.markdown(msg.content)

    # Chat Input
    if user_input := st.chat_input("Ask about weather, rain forecasts, or crop advice..."):
        st.session_state.messages.append(HumanMessage(content=user_input))
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)

        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Analyzing atmospheric models..."):
                    agent = build_weather_agent()
                    history = st.session_state.messages[:-1]
                    result = agent.invoke({"input": user_input, "chat_history": history})
                    response_text = result["output"]
                    
                    st.markdown(response_text)
                    st.session_state.messages.append(AIMessage(content=response_text))
                    
                    # Optional: Parse simple metrics for the right panel if available
                    st.rerun()

# === RIGHT COLUMN: DYNAMIC TELEMETRY CARDS ===
with col_data:
    st.subheader("📊 Live Weather Insights")
    
    telemetry = st.session_state.latest_telemetry
    
    # 1. Location & Alert Status Card
    with st.container():
        st.markdown(f"### 📍 **{telemetry['location']}**")
        if telemetry["alert_status"] == "Warning":
            st.error("⚠️ High Rain/Wind Warning Active")
        else:
            st.success("🟢 Atmospheric Status: Normal")

    # 2. Key Metrics Grid
    m1, m2 = st.columns(2)
    with m1:
        st.metric(label="🌡️ Temperature", value=f"{telemetry['temp']} °C")
        st.metric(label="💨 Wind Speed", value=f"{telemetry['wind']} km/h")
    with m2:
        st.metric(label="💧 Humidity", value=f"{telemetry['humidity']} %")
        st.metric(label="🌧️ Rain Probability", value=f"{telemetry['rain_prob']} %")

    st.divider()

    # 3. Actionable Quick Checklist
    st.markdown("#### 🚜 Advisory Checklist")
    st.markdown("""
    * **Farming/Spraying:** Check 24-hr rain risk before chemical application.
    * **Travel/Commute:** Safe driving conditions unless wind > 40 km/h.
    * **Disaster Protocol:** Monitor yellow/orange alerts for severe rainfall.
    """)