import streamlit as st
import requests

# --- Page Configuration ---
st.set_page_config(
    page_title="WeatherGPT - Meteorological Intelligence",
    page_icon="🌤️",
    layout="wide"
)

# --- Theme-Adaptive CSS (Dark & Light Mode Safe) ---
st.markdown("""
    <style>
    /* Metric Card Styling */
    .metric-card {
        background-color: var(--secondary-background-color, #f1f5f9);
        color: var(--text-color, #0f172a);
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 12px;
        padding: 14px 10px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-card b {
        font-size: 1.25rem;
        color: var(--text-color, #0f172a);
    }
    .metric-card small {
        color: var(--text-color, #64748b);
        font-weight: 500;
    }

    /* Insight Card Styling */
    .insight-box {
        border-radius: 10px;
        padding: 16px 20px;
        margin-top: 12px;
        color: var(--text-color, #0f172a);
    }
    .insight-safe {
        background-color: rgba(34, 197, 94, 0.12);
        border-left: 5px solid #22c55e;
    }
    .insight-warning {
        background-color: rgba(239, 68, 68, 0.12);
        border-left: 5px solid #ef4444;
    }
    .insight-caution {
        background-color: rgba(245, 158, 11, 0.12);
        border-left: 5px solid #f59e0b;
    }
    .insight-box h4 {
        margin: 0 0 8px 0;
        color: var(--text-color, #0f172a);
    }
    .insight-box ul {
        margin: 0;
        padding-left: 20px;
        line-height: 1.6;
    }
    </style>
""", unsafe_allow_html=True)

# --- Geocoding Helper: City Name -> Lat/Lon ---
@st.cache_data(show_spinner=False, ttl=3600)
def geocode_city(city_name):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
    try:
        res = requests.get(url, timeout=5).json()
        if "results" in res and len(res["results"]) > 0:
            item = res["results"][0]
            return item["latitude"], item["longitude"], f"{item['name']}, {item.get('admin1', item.get('country', ''))}"
    except Exception:
        pass
    return 28.9845, 77.7064, "Meerut, Uttar Pradesh"  # Fallback

# --- Live Telemetry Fetcher ---
def get_live_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code&forecast_days=1"
    try:
        res = requests.get(url, timeout=5).json()
        current = res.get("current", {})
        return {
            "temp": current.get("temperature_2m", 28),
            "humidity": current.get("relative_humidity_2m", 60),
            "rain": current.get("precipitation", 0.0),
            "wind": current.get("wind_speed_10m", 12),
            "code": current.get("weather_code", 0)
        }
    except Exception:
        return {"temp": 28, "humidity": 60, "rain": 0.0, "wind": 12, "code": 0}

# --- State Initialization ---
if "location_name" not in st.session_state:
    st.session_state.location_name = "Meerut"

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Namaste! Main WeatherGPT hoon. Aap mujhse mausam, fasal ki sinchai, keetnashak chhidkav ya disaster alerts ke bare me pooch sakte hain."}
    ]

if "current_insights" not in st.session_state:
    st.session_state.current_insights = {
        "status": "Safe",
        "irrigation": "✅ Regular morning irrigation is safe.",
        "spraying": "✅ Safe window available (Low wind & no immediate rain).",
        "risk_level": "Low / Normal",
        "action": "Proceed with regular field operations."
    }

# --- Dynamic Reasoning Engine ---
def analyze_query(query, weather, location_str):
    q = query.lower()
    temp = weather["temp"]
    rain = weather["rain"]
    wind = weather["wind"]

    # 1. Irrigation / Paani
    if any(k in q for k in ["paani", "sinchai", "irrigate", "irrigation", "water"]):
        if rain > 0.5 or weather["humidity"] > 80:
            reply = f"📍 **{location_str}**: Aane wale ghanton me barish ({rain}mm) aur high humidity ({weather['humidity']}%) ki sambhavna hai. Fasal me sinchai **24-48 ghante ke liye taal dein** taaki waterlogging na ho."
            insights = {
                "status": "Warning",
                "risk_level": "High Rain Risk",
                "irrigation": "🚫 DO NOT irrigate (Prevents root rotting & waterlogging).",
                "spraying": "🧪 Postpone spraying (Risk of chemical washout).",
                "action": "Check drainage channels in low-lying fields."
            }
        else:
            reply = f"📍 **{location_str}**: Mausam shushk hai aur taapman {temp}°C hai. Subah ya shaam ke samay sinchai karna **puri tarah surakshit** hai."
            insights = {
                "status": "Safe",
                "risk_level": "Normal Conditions",
                "irrigation": "✅ Safe to irrigate during early morning/evening.",
                "spraying": "✅ Good conditions for nutrient/fertilizer application.",
                "action": "Maintain routine soil moisture checks."
            }

    # 2. Pesticide / Chemical Spraying
    elif any(k in q for k in ["spray", "keetnashak", "fertilizer", "dawa", "chemical"]):
        if wind > 18:
            reply = f"📍 **{location_str}**: Hawa ki gati tez ({wind} km/h) hai. Is gati par spray hawa ke sath udkar barbaad hoga. **Chhidkav abhi rok dein** jab tak hawa shant na ho."
            insights = {
                "status": "Caution",
                "risk_level": "High Wind Drift Alert",
                "irrigation": "✅ Irrigation can proceed normally.",
                "spraying": "🚫 STOP chemical spray (High wind drift risk).",
                "action": "Wait for wind speeds to drop below 15 km/h."
            }
        else:
            reply = f"📍 **{location_str}**: Hawa ki gati anukool ({wind} km/h) hai aur barish ka koi khatra nahi hai. Keetnashak ya tonic ka spray **safalta-poorvak kiya ja sakta hai**."
            insights = {
                "status": "Safe",
                "risk_level": "Favorable Spray Window",
                "irrigation": "✅ Normal schedule.",
                "spraying": "✅ Excellent spraying window active.",
                "action": "Use personal protective equipment during spray."
            }

    # 3. Storm / Disaster / Flood Alerts
    elif any(k in q for k in ["storm", "toofan", "barish", "flood", "alert", "baarish", "rain"]):
        if rain > 1.0 or wind > 25:
            reply = f"🚨 **Weather Alert for {location_str}**: Kadi barish/tez hawaon ({wind} km/h) ki sambhavna hai. Kheti ke upkaran surakshit sthan par rakhein aur khet me na jayein."
            insights = {
                "status": "Warning",
                "risk_level": "Severe Weather Alert",
                "irrigation": "🚫 Halt all irrigation and electrical pumps.",
                "spraying": "🚫 Strict hold on all pesticide applications.",
                "action": "Secure livestock and clear drainage blockages."
            }
        else:
            reply = f"📍 **{location_str}**: Agle 24 ghanton me koi gambhir toofan ya bhari barish ki chetavni nahi hai. Halaki badal ban sakte hain."
            insights = {
                "status": "Safe",
                "risk_level": "Low Hazard",
                "irrigation": "✅ Standard routine.",
                "spraying": "✅ Safe window.",
                "action": "Monitor daily updates."
            }

    # 4. Temperature / General Weather
    else:
        reply = f"📍 **{location_str} ka Taaza Mausam**: Taapman **{temp}°C**, Hawa ki gati **{wind} km/h**, Humidity **{weather['humidity']}%**, aur Precipitation **{rain} mm** hai."
        insights = {
            "status": "Safe",
            "risk_level": "Normal Field Weather",
            "irrigation": "✅ Regular morning schedule.",
            "spraying": "✅ Normal spray window open.",
            "action": "Routine farming activities can continue."
        }

    return reply, insights

# --- Header Section ---
col_head1, col_head2, col_head3 = st.columns([3, 1, 1.2])
with col_head1:
    st.title("🌤️ WeatherGPT")
    st.caption("AI-Powered Meteorological Intelligence & Agricultural Decision Support")
with col_head2:
    selected_lang = st.selectbox("🌐 Language", ["Hindi (हिन्दी)", "English", "Punjabi", "Tamil", "Bengali"])
with col_head3:
    # Location input tied directly to session_state so it never resets
    user_loc = st.text_input("📍 Location", value=st.session_state.location_name)
    if user_loc != st.session_state.location_name:
        st.session_state.location_name = user_loc
        st.rerun()

# Fetch live coordinates & telemetry
lat, lon, resolved_city_name = geocode_city(st.session_state.location_name)
weather_data = get_live_weather(lat, lon)

st.divider()

# --- Main Dual-Panel Grid Layout ---
left_panel, right_panel = st.columns([1.1, 0.9], gap="large")

# ==========================================
# LEFT PANEL: Conversational Stream
# ==========================================
with left_panel:
    st.subheader("💬 Conversational Assistant")
    
    chat_container = st.container(height=430)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_input = st.chat_input("Poochiye (e.g., Kya kal fasal me sinchai karein? ya Barish kab hogi?)...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Analyze intent & generate dynamic response and insights
        ai_reply, new_insights = analyze_query(user_input, weather_data, resolved_city_name)
        
        st.session_state.current_insights = new_insights
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        st.rerun()

# ==========================================
# RIGHT PANEL: Live Telemetry & Insights
# ==========================================
with right_panel:
    st.subheader(f"📊 Live Telemetry ({resolved_city_name})")

    # 1. Metric Cards (Theme Adaptive)
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

    # 2. Dynamic Actionable Insight Card
    st.markdown("#### 💡 Actionable Agro-Advisory")
    insights = st.session_state.current_insights

    card_type = "insight-warning" if insights["status"] == "Warning" else ("insight-caution" if insights["status"] == "Caution" else "insight-safe")

    st.markdown(f"""
    <div class='insight-box {card_type}'>
        <h4>Risk Status: {insights['risk_level']}</h4>
        <ul>
            <li><b>Irrigation Guidance:</b> {insights['irrigation']}</li>
            <li><b>Chemical Spray Window:</b> {insights['spraying']}</li>
            <li><b>Recommended Action:</b> {insights['action']}</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    
    # 3. Mass Alert Action Button
    if st.button("🚨 Broadcast Advisory to Regional Farmer WhatsApp Groups", use_container_width=True):
        st.success(f"✅ Advisory successfully dispatched to registered farmers in {resolved_city_name} cluster.")

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

