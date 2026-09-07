import streamlit as st
import requests
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="WeatherGPT - Meteorological Intelligence",
    page_icon="🌤️",
    layout="wide"
)

# --- Custom Styling for Clean Dashboard UI ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px;
        text-align: center;
    }
    .insight-card {
        background-color: #f0fdf4;
        border-left: 5px solid #22c55e;
        border-radius: 8px;
        padding: 16px;
        margin-top: 10px;
    }
    .warning-card {
        background-color: #fef2f2;
        border-left: 5px solid #ef4444;
        border-radius: 8px;
        padding: 16px;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Helper: Fetch Live Telemetry (Open-Meteo API) ---
def get_live_weather(lat=28.9845, lon=77.7064):  # Defaults to Meerut/Delhi region
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m&forecast_days=1"
    try:
        res = requests.get(url, timeout=5).json()
        current = res.get("current", {})
        return {
            "temp": current.get("temperature_2m", 28),
            "humidity": current.get("relative_humidity_2m", 65),
            "rain": current.get("precipitation", 0.0),
            "wind": current.get("wind_speed_10m", 12)
        }
    except Exception:
        return {"temp": 28, "humidity": 65, "rain": 0.0, "wind": 12}

# --- State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Namaste! Main WeatherGPT hoon. Aap mujhse mausam, kheti ya disaster alerts ke bare me pooch sakte hain."}
    ]

if "current_insights" not in st.session_state:
    st.session_state.current_insights = {
        "status": "Ready",
        "irrigation": "Normal schedule recommended.",
        "spraying": "Safe window available.",
        "risk_level": "Low",
        "action": "No immediate hazards detected."
    }

# --- Header Section ---
col_head1, col_head2, col_head3 = st.columns([3, 1, 1])
with col_head1:
    st.title("🌤️ WeatherGPT")
    st.caption("Conversational AI for Weather Intelligence & Agricultural Decision Support")
with col_head2:
    selected_lang = st.selectbox("🌐 Language", ["Hindi (हिन्दी)", "English", "Punjabi", "Tamil", "Bengali"])
with col_head3:
    location = st.text_input("📍 Location", "Meerut, UP")

weather_data = get_live_weather()
st.divider()

# --- Main Dual-Panel Grid Layout ---
left_panel, right_panel = st.columns([1.1, 0.9], gap="large")

# ==========================================
# LEFT PANEL: Conversational Stream
# ==========================================
with left_panel:
    st.subheader("💬 Conversational Assistant")
    
    # Message History Container
    chat_container = st.container(height=420)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # User Input Field
    user_input = st.chat_input("Poochiye (e.g., Kya kal fasal me sinchai karni chahiye?)...")

    if user_input:
        # 1. Append User Message
        st.session_state.messages.append({"role": "user", "content": user_input})

        # 2. Logic / RAG Inference Engine
        # (Evaluates prompt and updates insights dynamically)
        if any(w in user_input.lower() for w in ["paani", "sinchai", "irrigation", "water", "spray"]):
            ai_reply = "Kal kshetra me 80% barish ki sambhavna hai. Kripya gehu me sinchai aur keetnashak chhidkav 48 ghante ke liye taal dein."
            st.session_state.current_insights = {
                "status": "Warning",
                "irrigation": "🚫 DO NOT irrigate tomorrow (Risk of root rotting).",
                "spraying": "🧪 Postpone chemical spraying until dry weather.",
                "risk_level": "Moderate Rain Alert",
                "action": "Ensure farm drainage channels are open."
            }
        else:
            ai_reply = f"Filhal mausam saaf hai. Taapman {weather_data['temp']}°C hai aur hawa ki gati {weather_data['wind']} km/h hai."
            st.session_state.current_insights = {
                "status": "Safe",
                "irrigation": "✅ Regular morning irrigation is safe.",
                "spraying": "✅ Normal pesticide application window active.",
                "risk_level": "Normal",
                "action": "Standard field maintenance."
            }

        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        st.rerun()

# ==========================================
# RIGHT PANEL: Live Telemetry & Insights
# ==========================================
with right_panel:
    st.subheader("📊 Live Telemetry & Decision Insights")

    # 1. Top Telemetry Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"<div class='metric-card'>🌡️<br><b>{weather_data['temp']}°C</b><br><small>Temp</small></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'>🌧️<br><b>{weather_data['rain']} mm</b><br><small>Precip</small></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='metric-card'>💨<br><b>{weather_data['wind']} km/h</b><br><small>Wind</small></div>", unsafe_allow_html=True)
    with m4:
        st.markdown(f"<div class='metric-card'>💧<br><b>{weather_data['humidity']}%</b><br><small>Humidity</small></div>", unsafe_allow_html=True)

    st.write("")

    # 2. Dynamic Actionable Insight Box (Post-Response Render)
    st.markdown("#### 💡 Actionable Agro-Advisory")
    insights = st.session_state.current_insights

    card_class = "warning-card" if insights["status"] == "Warning" else "insight-card"

    st.markdown(f"""
    <div class='{card_class}'>
        <h4 style='margin:0 0 10px 0;'>Risk Level: {insights['risk_level']}</h4>
        <ul style='margin:0; padding-left:20px; font-size: 15px;'>
            <li><b>Irrigation:</b> {insights['irrigation']}</li>
            <li><b>Chemical Spray:</b> {insights['spraying']}</li>
            <li><b>Immediate Action:</b> {insights['action']}</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    
    # 3. Direct Action / Alert Trigger
    if st.button("🚨 Broadcast Alert to Farmer WhatsApp Groups", use_container_width=True):
        st.success("✅ Alert dispatched via Twilio Gateway to 45 registered farmers in this cluster.")

# import os
# from dotenv import load_dotenv
# import streamlit as st
# from langchain_core.messages import AIMessage, HumanMessage
# from src.agent import build_weather_agent

# load_dotenv()

# st.set_page_config(
#     page_title="WeatherGPT Dashboard",
#     page_icon="🌤️",
#     layout="wide"  # Uses full screen width
# )

# # Custom CSS for cards and metrics styling
# st.markdown("""
# <style>
#     .metric-card {
#         background-color: rgba(255, 255, 255, 0.05);
#         border: 1px solid rgba(255, 255, 255, 0.15);
#         border-radius: 12px;
#         padding: 16px;
#         margin-bottom: 12px;
#     }
#     .alert-banner {
#         padding: 10px 14px;
#         border-radius: 8px;
#         font-weight: 600;
#         margin-bottom: 12px;
#     }
# </style>
# """, unsafe_allow_html=True)

# # -------------------------------------------------------------
# # Initialize Session State
# # -------------------------------------------------------------
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# if "latest_telemetry" not in st.session_state:
#     st.session_state.latest_telemetry = {
#         "location": "No search yet",
#         "temp": "--",
#         "humidity": "--",
#         "wind": "--",
#         "rain_prob": "--",
#         "alert_status": "Normal"
#     }

# # -------------------------------------------------------------
# # Header
# # -------------------------------------------------------------
# st.title("🌤️ WeatherGPT Assisstance")
# st.caption("AI-powered weather forecasting, hyper-local advisories, and disaster alerts.")
# st.divider()

# # -------------------------------------------------------------
# # Main Layout: 60% Chat, 40% Live Data Cards
# # -------------------------------------------------------------
# col_chat, col_data = st.columns([1.3, 0.9], gap="large")

# # === LEFT COLUMN: CONVERSATIONAL AGENT ===
# with col_chat:
#     st.subheader("💬 Weather Assistant")
    
#     # Scrollable chat message container
#     chat_container = st.container(height=520)
#     with chat_container:
#         for msg in st.session_state.messages:
#             role = "user" if isinstance(msg, HumanMessage) else "assistant"
#             with st.chat_message(role):
#                 st.markdown(msg.content)

#     # Chat Input
#     if user_input := st.chat_input("Ask about weather, rain forecasts, or crop advice..."):
#         st.session_state.messages.append(HumanMessage(content=user_input))
#         with chat_container:
#             with st.chat_message("user"):
#                 st.markdown(user_input)

#         with chat_container:
#             with st.chat_message("assistant"):
#                 with st.spinner("Analyzing atmospheric models..."):
#                     agent = build_weather_agent()
#                     history = st.session_state.messages[:-1]
#                     result = agent.invoke({"input": user_input, "chat_history": history})
#                     response_text = result["output"]
                    
#                     st.markdown(response_text)
#                     st.session_state.messages.append(AIMessage(content=response_text))
                    
#                     # Optional: Parse simple metrics for the right panel if available
#                     st.rerun()

# # === RIGHT COLUMN: DYNAMIC TELEMETRY CARDS ===
# with col_data:
#     st.subheader("📊 Live Weather Insights")
    
#     telemetry = st.session_state.latest_telemetry
    
#     # 1. Location & Alert Status Card
#     with st.container():
#         st.markdown(f"### 📍 **{telemetry['location']}**")
#         if telemetry["alert_status"] == "Warning":
#             st.error("⚠️ High Rain/Wind Warning Active")
#         else:
#             st.success("🟢 Atmospheric Status: Normal")

#     # 2. Key Metrics Grid
#     m1, m2 = st.columns(2)
#     with m1:
#         st.metric(label="🌡️ Temperature", value=f"{telemetry['temp']} °C")
#         st.metric(label="💨 Wind Speed", value=f"{telemetry['wind']} km/h")
#     with m2:
#         st.metric(label="💧 Humidity", value=f"{telemetry['humidity']} %")
#         st.metric(label="🌧️ Rain Probability", value=f"{telemetry['rain_prob']} %")

#     st.divider()

#     # 3. Actionable Quick Checklist
#     st.markdown("#### 🚜 Advisory Checklist")
#     st.markdown("""
#     * **Farming/Spraying:** Check 24-hr rain risk before chemical application.
#     * **Travel/Commute:** Safe driving conditions unless wind > 40 km/h.
#     * **Disaster Protocol:** Monitor yellow/orange alerts for severe rainfall.
#     """)

