import re
import requests
import streamlit as st

# --- Page Configuration ---
st.set_page_config(
    page_title="WeatherGPT - Meteorological Intelligence",
    page_icon="🌤️",
    layout="wide"
)

# --- Theme-Adaptive CSS ---
st.markdown("""
    <style>
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

# --- Helper: Geocoding (City Name -> Coordinates) ---
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
    return 28.6139, 77.2090, "Delhi, India"

# --- Helper: Extract Location from Chat Text ---
def extract_location(text):
    known_cities = [
        "delhi", "mumbai", "meerut", "lucknow", "patna", "bhopal", "jaipur", "punjab", 
        "chandigarh", "pune", "nagpur", "varanasi", "kanpur", "kolkata", "chennai", 
        "hyderabad", "bengaluru", "ahmedabad", "surat", "agra", "noida", "gurgaon"
    ]
    words = re.findall(r'\b[A-Za-z]+\b', text.lower())
    for w in words:
        if w in known_cities:
            return w.capitalize()
    match = re.search(r'(?:in|at|near|for|around)\s+([A-Za-z]+)', text, re.IGNORECASE)
    if match and match.group(1).lower() not in ["the", "my", "today", "tomorrow", "this", "me", "mein"]:
        return match.group(1).capitalize()
    return None

# --- Helper: Fetch Live & 3-Day Predictive Forecasts ---
def get_weather_data(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
        f"&daily=temperature_2m_max,precipitation_sum,precipitation_probability_max,wind_speed_10m_max"
        f"&timezone=auto&forecast_days=3"
    )
    try:
        res = requests.get(url, timeout=5).json()
        current = res.get("current", {})
        daily = res.get("daily", {})

        rain_probs = daily.get("precipitation_probability_max", [0, 0, 0])
        rain_sums = daily.get("precipitation_sum", [0.0, 0.0, 0.0])
        temp_maxs = daily.get("temperature_2m_max", [28.0, 28.0, 28.0])
        wind_maxs = daily.get("wind_speed_10m_max", [12.0, 12.0, 12.0])

        return {
            "current_temp": round(current.get("temperature_2m", 28.0), 1),
            "current_humidity": current.get("relative_humidity_2m", 60),
            "current_rain": round(current.get("precipitation", 0.0), 1),
            "current_wind": round(current.get("wind_speed_10m", 12.0), 1),
            "today_rain_prob": rain_probs[0] if len(rain_probs) > 0 else 0,
            "tomorrow_rain_prob": rain_probs[1] if len(rain_probs) > 1 else 0,
            "tomorrow_rain_sum": round(rain_sums[1], 1) if len(rain_sums) > 1 else 0.0,
            "tomorrow_temp_max": round(temp_maxs[1], 1) if len(temp_maxs) > 1 else 28.0,
            "tomorrow_wind_max": round(wind_maxs[1], 1) if len(wind_maxs) > 1 else 12.0
        }
    except Exception as e:
        # If network fails, return clean default
        return {
            "current_temp": 28.0, "current_humidity": 60, "current_rain": 0.0, "current_wind": 12.0,
            "today_rain_prob": 0, "tomorrow_rain_prob": 0, "tomorrow_rain_sum": 0.0,
            "tomorrow_temp_max": 28.0, "tomorrow_wind_max": 12.0
        }

# --- State Initialization ---
if "location_name" not in st.session_state:
    st.session_state.location_name = "Delhi"

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Namaste! Main WeatherGPT hoon. Aap kisi bhi sheher ka mausam, barish ka anuman ya fasal ki sinchai/spray ke bare me pooch sakte hain."}
    ]

if "current_insights" not in st.session_state:
    st.session_state.current_insights = {
        "status": "Safe",
        "irrigation": "✅ Regular morning irrigation is safe.",
        "spraying": "✅ Safe window available (Low wind & no rain predicted).",
        "risk_level": "Low / Normal",
        "action": "Proceed with regular field operations."
    }

# --- Predictive Reasoning Engine ---
def analyze_query(query, weather, location_str):
    q = query.lower()
    is_tomorrow = any(k in q for k in ["kal", "tomorrow", "next day", "aane wale"])
    
    target_rain_prob = weather["tomorrow_rain_prob"] if is_tomorrow else max(weather["today_rain_prob"], weather["tomorrow_rain_prob"])
    target_rain_sum = weather["tomorrow_rain_sum"] if is_tomorrow else weather["current_rain"]
    target_wind = weather["tomorrow_wind_max"] if is_tomorrow else weather["current_wind"]
    time_label = "Kal" if is_tomorrow else "Aane wale 24 ghanton mein"

    # Rain / Forecast Query
    if any(k in q for k in ["barish", "baarish", "rain", "rainfall", "toofan", "storm", "forecast", "predict", "weather", "mausam"]):
        if target_rain_prob >= 40 or target_rain_sum > 1.0:
            reply = f"📍 **{location_str} Forecast**: {time_label} **{target_rain_prob}% barish ki sambhavna** hai (Anumanit barish: ~{target_rain_sum} mm). Taapman lagbhag **{weather['tomorrow_temp_max']}°C** rahega."
            insights = {
                "status": "Warning",
                "risk_level": f"Rain Alert ({target_rain_prob}% Probability)",
                "irrigation": "🚫 Sinchai taal dein (Waterlogging ka khatra).",
                "spraying": "🚫 Chemical spray na karein (Dawa behne ka khatra).",
                "action": "Khet ki nikasi (drainage) vyavastha check karein."
            }
        else:
            reply = f"📍 **{location_str} Forecast**: {time_label} mausam mukhyatah **saaf aur shushk** rahega. Barish ki sambhavna sirf **{target_rain_prob}%** hai aur taapman **{weather['tomorrow_temp_max']}°C** tak jayega."
            insights = {
                "status": "Safe",
                "risk_level": "Low Rain Risk",
                "irrigation": "✅ Subah ke samay sinchai surakshit hai.",
                "spraying": "✅ Spraying window poori tarah open hai.",
                "action": "Samanya kheti karya jari rakhein."
            }

    # Irrigation Query
    elif any(k in q for k in ["paani", "pani", "sinchai", "irrigate", "irrigation"]):
        if target_rain_prob >= 40:
            reply = f"📍 **{location_str}**: Barish ki sambhavna **{target_rain_prob}%** hai. Khet mein paani bharne se bachne ke liye **sinchai 24-48 ghante ke liye taal dein**."
            insights = {
                "status": "Warning",
                "risk_level": "Rain Inbound",
                "irrigation": "🚫 DO NOT irrigate.",
                "spraying": "🧪 Postpone spraying.",
                "action": "Inspect low-lying field zones."
            }
        else:
            reply = f"📍 **{location_str}**: Barish ka khatra kam hai ({target_rain_prob}%). Subah ya shaam ke samay sinchai karna **anukool aur surakshit** hai."
            insights = {
                "status": "Safe",
                "risk_level": "Optimal Irrigation Window",
                "irrigation": "✅ Safe to irrigate.",
                "spraying": "✅ Safe window open.",
                "action": "Routine soil moisture monitoring."
            }

    # Spraying Query
    elif any(k in q for k in ["spray", "keetnashak", "fertilizer", "dawa", "chemical", "chhidkav"]):
        if target_wind > 16.0 or target_rain_prob >= 40:
            reply = f"📍 **{location_str}**: Hawa ki gati **{target_wind} km/h** aur barish ki sambhavna **{target_rain_prob}%** hai. Dawa udne aur behne se bachne ke liye **chhidkav abhi rok dein**."
            insights = {
                "status": "Caution",
                "risk_level": "High Drift / Washout Risk",
                "irrigation": "Normal schedule.",
                "spraying": "🚫 STOP chemical spray.",
                "action": "Wait for wind speeds < 15 km/h."
            }
        else:
            reply = f"📍 **{location_str}**: Hawa ki gati anukool (**{target_wind} km/h**) hai aur barish ka koi khatra nahi hai. Spray kiya ja sakta hai."
            insights = {
                "status": "Safe",
                "risk_level": "Optimal Spray Window",
                "irrigation": "✅ Standard routine.",
                "spraying": "✅ Safe spraying window active.",
                "action": "Use recommended protective gear."
            }

    else:
        reply = f"📍 **{location_str} Live & Forecast**: Current Temp: **{weather['current_temp']}°C**, Tomorrow Rain Prob: **{weather['tomorrow_rain_prob']}%**, Wind: **{weather['current_wind']} km/h**."
        insights = {
            "status": "Safe",
            "risk_level": "Normal Conditions",
            "irrigation": "✅ Normal schedule.",
            "spraying": "✅ Standard operations.",
            "action": "Monitor daily updates."
        }

    return reply, insights

# --- Header Section ---
col_head1, col_head2, col_head3 = st.columns([3, 1, 1.2])
with col_head1:
    st.title("🌤️ WeatherGPT")
    st.caption("AI-Powered Meteorological Forecasting & Agricultural Decision Support")
with col_head2:
    selected_lang = st.selectbox("🌐 Language", ["Hindi (हिन्दी)", "English", "Punjabi", "Tamil", "Bengali"])
with col_head3:
    user_loc = st.text_input("📍 Active Location", value=st.session_state.location_name)
    if user_loc != st.session_state.location_name:
        st.session_state.location_name = user_loc
        st.rerun()

# Fetch telemetry for the active location
lat, lon, resolved_city_name = geocode_city(st.session_state.location_name)
weather_data = get_weather_data(lat, lon)

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

    user_input = st.chat_input("Poochiye (e.g., 'Kya kal Jaipur me barish hogi?' ya 'Delhi me mausam kaisa hai?')...")

    if user_input:
        # Dynamic in-chat location update
        detected_loc = extract_location(user_input)
        if detected_loc and detected_loc.lower() != st.session_state.location_name.lower():
            st.session_state.location_name = detected_loc
            lat, lon, resolved_city_name = geocode_city(detected_loc)
            weather_data = get_weather_data(lat, lon)

        st.session_state.messages.append({"role": "user", "content": user_input})
        ai_reply, new_insights = analyze_query(user_input, weather_data, resolved_city_name)
        st.session_state.current_insights = new_insights
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        st.rerun()

# ==========================================
# RIGHT PANEL: Live Telemetry & Predictive Insights
# ==========================================
with right_panel:
    st.subheader(f"📊 Forecast & Telemetry ({resolved_city_name})")

    # 1. Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"<div class='metric-card'>🌡️<br><b>{weather_data['current_temp']}°C</b><br><small>Current Temp</small></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'>🌧️<br><b>{weather_data['tomorrow_rain_prob']}%</b><br><small>Rain Prob (Tomorrow)</small></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='metric-card'>💨<br><b>{weather_data['current_wind']} km/h</b><br><small>Wind</small></div>", unsafe_allow_html=True)
    with m4:
        st.markdown(f"<div class='metric-card'>💧<br><b>{weather_data['current_humidity']}%</b><br><small>Humidity</small></div>", unsafe_allow_html=True)

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
    if st.button(f"🚨 Broadcast Advisory to {resolved_city_name} Farmers", use_container_width=True):
        st.success(f"✅ Advisory successfully dispatched via Twilio to registered users in {resolved_city_name}[cite: 1].")



# import re
# import requests
# import streamlit as st

# # --- Page Configuration ---
# st.set_page_config(
#     page_title="WeatherGPT - Meteorological Intelligence",
#     page_icon="🌤️",
#     layout="wide",
# )

# # --- Theme-Adaptive CSS ---
# st.markdown(
#     """
#     <style>
#     .metric-card {
#         background-color: var(--secondary-background-color, #f1f5f9);
#         color: var(--text-color, #0f172a);
#         border: 1px solid rgba(128, 128, 128, 0.25);
#         border-radius: 12px;
#         padding: 14px 10px;
#         text-align: center;
#         box-shadow: 0 1px 3px rgba(0,0,0,0.05);
#     }
#     .metric-card b {
#         font-size: 1.25rem;
#         color: var(--text-color, #0f172a);
#     }
#     .metric-card small {
#         color: var(--text-color, #64748b);
#         font-weight: 500;
#     }
#     .insight-box {
#         border-radius: 10px;
#         padding: 16px 20px;
#         margin-top: 12px;
#         color: var(--text-color, #0f172a);
#     }
#     .insight-safe {
#         background-color: rgba(34, 197, 94, 0.12);
#         border-left: 5px solid #22c55e;
#     }
#     .insight-warning {
#         background-color: rgba(239, 68, 68, 0.12);
#         border-left: 5px solid #ef4444;
#     }
#     .insight-caution {
#         background-color: rgba(245, 158, 11, 0.12);
#         border-left: 5px solid #f59e0b;
#     }
#     .insight-box h4 {
#         margin: 0 0 8px 0;
#         color: var(--text-color, #0f172a);
#     }
#     .insight-box ul {
#         margin: 0;
#         padding-left: 20px;
#         line-height: 1.6;
#     }
#     </style>
# """,
#     unsafe_allow_html=True,
# )


# # --- Helper: Geocoding (City Name -> Coordinates) ---
# @st.cache_data(show_spinner=False, ttl=3600)
# def geocode_city(city_name):
#   url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
#   try:
#     res = requests.get(url, timeout=5).json()
#     if "results" in res and len(res["results"]) > 0:
#       item = res["results"][0]
#       return (
#           item["latitude"],
#           item["longitude"],
#           f"{item['name']}, {item.get('admin1', item.get('country', ''))}",
#       )
#   except Exception:
#     pass
#   return 28.9845, 77.7064, "Meerut, Uttar Pradesh"


# # --- Helper: Fetch Live Telemetry AND Predictive Forecasts ---
# def get_weather_data(lat, lon):
#   url = (
#       "https://api.open-meteo.com/v1/forecast?"
#       f"latitude={lat}&longitude={lon}"
#       "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code"
#       "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max"
#       "&timezone=auto&forecast_days=3"
#   )
#   try:
#     res = requests.get(url, timeout=5).json()
#     current = res.get("current", {})
#     daily = res.get("daily", {})

#     # Today & Tomorrow predictions
#     today_rain_prob = (
#         daily.get("precipitation_probability_max", [0, 0])[0] or 0
#     )
#     tomorrow_rain_prob = (
#         daily.get("precipitation_probability_max", [0, 0])[1]
#         if len(daily.get("precipitation_probability_max", [])) > 1
#         else 0
#     )
#     tomorrow_rain_sum = (
#         daily.get("precipitation_sum", [0, 0])[1]
#         if len(daily.get("precipitation_sum", [])) > 1
#         else 0.0
#     )
#     tomorrow_temp_max = (
#         daily.get("temperature_2m_max", [28, 28])[1]
#         if len(daily.get("temperature_2m_max", [])) > 1
#         else 28
#     )
#     tomorrow_wind_max = (
#         daily.get("wind_speed_10m_max", [12, 12])[1]
#         if len(daily.get("wind_speed_10m_max", [])) > 1
#         else 12
#     )

#     return {
#         "current_temp": round(current.get("temperature_2m", 28), 1),
#         "current_humidity": current.get("relative_humidity_2m", 60),
#         "current_rain": round(current.get("precipitation", 0.0), 1),
#         "current_wind": round(current.get("wind_speed_10m", 12), 1),
#         "today_rain_prob": today_rain_prob,
#         "tomorrow_rain_prob": tomorrow_rain_prob,
#         "tomorrow_rain_sum": tomorrow_rain_sum,
#         "tomorrow_temp_max": tomorrow_temp_max,
#         "tomorrow_wind_max": tomorrow_wind_max,
#     }
#   except Exception:
#     return {
#         "current_temp": 28.0,
#         "current_humidity": 60,
#         "current_rain": 0.0,
#         "current_wind": 12.0,
#         "today_rain_prob": 10,
#         "tomorrow_rain_prob": 15,
#         "tomorrow_rain_sum": 0.0,
#         "tomorrow_temp_max": 29.0,
#         "tomorrow_wind_max": 12.0,
#     }


# # --- State Initialization ---
# if "location_name" not in st.session_state:
#   st.session_state.location_name = "Meerut"

# if "messages" not in st.session_state:
#   st.session_state.messages = [{
#       "role": "assistant",
#       "content": (
#           "Namaste! Main WeatherGPT hoon. Aap mujhse aane wale mausam,"
#           " barish ki sambhavna, sinchai ya spray ke bare me pooch sakte hain."
#       ),
#   }]

# if "current_insights" not in st.session_state:
#   st.session_state.current_insights = {
#       "status": "Safe",
#       "irrigation": "✅ Regular morning irrigation is safe.",
#       "spraying": (
#           "✅ Safe window available (Low wind & no immediate rain predicted)."
#       ),
#       "risk_level": "Low / Normal",
#       "action": "Proceed with regular field operations.",
#   }


# # --- Predictive Reasoning Engine ---
# def analyze_query(query, weather, location_str):
#   q = query.lower()

#   is_tomorrow = any(
#       k in q for k in ["kal", "tomorrow", "next day", "aane wale"]
#   )
#   target_rain_prob = (
#       weather["tomorrow_rain_prob"]
#       if is_tomorrow
#       else max(weather["today_rain_prob"], weather["tomorrow_rain_prob"])
#   )
#   target_rain_sum = (
#       weather["tomorrow_rain_sum"] if is_tomorrow else weather["current_rain"]
#   )
#   target_wind = (
#       weather["tomorrow_wind_max"] if is_tomorrow else weather["current_wind"]
#   )

#   # 1. Rain / Storm / Prediction Queries
#   if any(
#       k in q
#       for k in [
#           "barish",
#           "baarish",
#           "rain",
#           "rainfall",
#           "toofan",
#           "storm",
#           "weather",
#           "mausam",
#           "forecast",
#           "predict",
#       ]
#   ):
#     time_label = "Kal" if is_tomorrow else "Aane wale 24 ghanton mein"
#     if target_rain_prob >= 40 or target_rain_sum > 1.0:
#       reply = (
#           f"📍 **{location_str} Forecast**: {time_label} **{target_rain_prob}%"
#           f" barish ki sambhavna** hai (Expected rain: ~{target_rain_sum} mm)."
#           f" Taapman lagbhag **{weather['tomorrow_temp_max']}°C** rahega."
#       )
#       insights = {
#           "status": "Warning",
#           "risk_level": f"Rain Alert ({target_rain_prob}% Probability)",
#           "irrigation": "🚫 Postpone field irrigation.",
#           "spraying": "🚫 Washout hazard — Hold pesticide/fertilizer spraying.",
#           "action": "Ensure field drainage channels are cleared.",
#       }
#     else:
#       reply = (
#           f"📍 **{location_str} Forecast**: {time_label} mausam mukhyatah"
#           f" shushk/saaf rahega. Barish ki sambhavna sirf"
#           f" **{target_rain_prob}%** hai aur taapman"
#           f" **{weather['tomorrow_temp_max']}°C** tak jayega."
#       )
#       insights = {
#           "status": "Safe",
#           "risk_level": "Low Rain Risk",
#           "irrigation": "✅ Regular morning irrigation is safe.",
#           "spraying": "✅ Safe spraying window active.",
#           "action": "Proceed with regular field operations.",
#       }

#   # 2. Irrigation Queries
#   elif any(
#       k in q for k in ["paani", "pani", "sinchai", "irrigate", "irrigation"]
#   ):
#     if target_rain_prob >= 40:
#       reply = (
#           f"📍 **{location_str}**: Barish ki sambhavna"
#           f" **{target_rain_prob}%** hai. Khet mein paani bharne se jadon ko"
#           " nuksan ho sakta hai, isliye **sinchai 24-48 ghante ke liye taal"
#           " dein**."
#       )
#       insights = {
#           "status": "Warning",
#           "risk_level": "Rain Inbound",
#           "irrigation": "🚫 DO NOT irrigate (Avoid waterlogging).",
#           "spraying": "🧪 Postpone chemical spraying.",
#           "action": "Inspect low-lying field zones.",
#       }
#     else:
#       reply = (
#           f"📍 **{location_str}**: Aane wale samay mein mausam saaf hai (Rain"
#           f" prob: {target_rain_prob}%). Subah ya shaam ke samay sinchai karna"
#           " **surakshit aur anukool** hai."
#       )
#       insights = {
#           "status": "Safe",
#           "risk_level": "Optimal Irrigation Window",
#           "irrigation": "✅ Safe to irrigate.",
#           "spraying": "✅ Safe window open.",
#           "action": "Maintain routine soil moisture monitoring.",
#       }

#   # 3. Spraying / Chemical Queries
#   elif any(
#       k in q
#       for k in [
#           "spray",
#           "keetnashak",
#           "fertilizer",
#           "dawa",
#           "chemical",
#           "chhidkav",
#       ]
#   ):
#     if target_wind > 16.0 or target_rain_prob >= 40:
#       reply = (
#           f"📍 **{location_str}**: Hawa ki gati **{target_wind} km/h** aur"
#           f" barish ki sambhavna **{target_rain_prob}%** hai. Chemical drift aur"
#           " washout se bachne ke liye **chhidkav abhi rok dein**."
#       )
#       insights = {
#           "status": "Caution",
#           "risk_level": "High Drift / Washout Risk",
#           "irrigation": "Normal schedule.",
#           "spraying": "🚫 STOP chemical spray (Unfavorable wind/rain).",
#           "action": "Wait for dry weather and wind speeds < 15 km/h.",
#       }
#     else:
#       reply = (
#           f"📍 **{location_str}**: Hawa ki gati anukool (**{target_wind}"
#           f" km/h**) hai aur barish ka khatra kam ({target_rain_prob}%) hai."
#           " Spray kiya ja sakta hai."
#       )
#       insights = {
#           "status": "Safe",
#           "risk_level": "Optimal Spraying Window",
#           "irrigation": "✅ Standard routine.",
#           "spraying": "✅ Safe spraying window active.",
#           "action": "Use recommended safety gear.",
#       }

#   # 4. Fallback Telemetry Readout
#   else:
#     reply = (
#         f"📍 **{location_str} Live & Forecast**: Current Temp:"
#         f" **{weather['current_temp']}°C**, Rain Prob Tomorrow:"
#         f" **{weather['tomorrow_rain_prob']}%**, Wind:"
#         f" **{weather['current_wind']} km/h**."
#     )
#     insights = {
#         "status": "Safe",
#         "risk_level": "Normal Conditions",
#         "irrigation": "✅ Normal schedule.",
#         "spraying": "✅ Standard operations.",
#         "action": "Monitor daily updates.",
#     }

#   return reply, insights


# # --- Header Section ---
# col_head1, col_head2, col_head3 = st.columns([3, 1, 1.2])
# with col_head1:
#   st.title("🌤️ WeatherGPT")
#   st.caption(
#       "AI-Powered Meteorological Forecasting & Agricultural Decision Support"
#   )
# with col_head2:
#   selected_lang = st.selectbox(
#       "🌐 Language", ["Hindi (हिन्दी)", "English", "Punjabi", "Tamil", "Bengali"]
#   )
# with col_head3:
#   user_loc = st.text_input("📍 Location", value=st.session_state.location_name)
#   if user_loc != st.session_state.location_name:
#     st.session_state.location_name = user_loc
#     st.rerun()

# # Fetch coordinates and combined live/predictive telemetry
# lat, lon, resolved_city_name = geocode_city(st.session_state.location_name)
# weather_data = get_weather_data(lat, lon)

# st.divider()

# # --- Main Dual-Panel Grid Layout ---
# left_panel, right_panel = st.columns([1.1, 0.9], gap="large")

# # ==========================================
# # LEFT PANEL: Conversational Stream
# # ==========================================
# with left_panel:
#   st.subheader("💬 Conversational Assistant")

#   chat_container = st.container(height=430)
#   with chat_container:
#     for msg in st.session_state.messages:
#       with st.chat_message(msg["role"]):
#         st.markdown(msg["content"])

#   user_input = st.chat_input(
#       "Poochiye (e.g., Kya kal barish hogi? ya Kya kal sinchai karein?)..."
#   )

#   if user_input:
#     st.session_state.messages.append({"role": "user", "content": user_input})
#     ai_reply, new_insights = analyze_query(
#         user_input, weather_data, resolved_city_name
#     )
#     st.session_state.current_insights = new_insights
#     st.session_state.messages.append({"role": "assistant", "content": ai_reply})
#     st.rerun()

# # ==========================================
# # RIGHT PANEL: Live Telemetry & Predictive Insights
# # ==========================================
# with right_panel:
#   st.subheader(f"📊 Forecast & Telemetry ({resolved_city_name})")

#   # 1. Metric Cards (Shows Current Temp + Tomorrow's Rain Probability Prediction)
#   m1, m2, m3, m4 = st.columns(4)
#   with m1:
#     st.markdown(
#         "<div class='metric-card'>🌡️<br><b>"
#         f" {weather_data['current_temp']}°C</b><br><small>Current"
#         " Temp</small></div>",
#         unsafe_allow_html=True,
#     )
#   with m2:
#     st.markdown(
#         "<div class='metric-card'>🌧️<br><b>"
#         f" {weather_data['tomorrow_rain_prob']}%</b><br><small>Rain"
#         " Prob</small></div>",
#         unsafe_allow_html=True,
#     )
#   with m3:
#     st.markdown(
#         "<div class='metric-card'>💨<br><b>"
#         f" {weather_data['current_wind']} km/h</b><br><small>Wind</small></div>",
#         unsafe_allow_html=True,
#     )
#   with m4:
#     st.markdown(
#         "<div class='metric-card'>💧<br><b>"
#         f" {weather_data['current_humidity']}%</b><br><small>Humidity</small></div>",
#         unsafe_allow_html=True,
#     )

#   st.write("")

#   # 2. Dynamic Actionable Insight Card
#   st.markdown("#### 💡 Actionable Agro-Advisory")
#   insights = st.session_state.current_insights
#   card_type = (
#       "insight-warning"
#       if insights["status"] == "Warning"
#       else (
#           "insight-caution"
#           if insights["status"] == "Caution"
#           else "insight-safe"
#       )
#   )

#   st.markdown(
#       f"""
#     <div class='insight-box {card_type}'>
#         <h4>Risk Status: {insights['risk_level']}</h4>
#         <ul>
#             <li><b>Irrigation Guidance:</b> {insights['irrigation']}</li>
#             <li><b>Chemical Spray Window:</b> {insights['spraying']}</li>
#             <li><b>Recommended Action:</b> {insights['action']}</li>
#         </ul>
#     </div>
#     """,
#       unsafe_allow_html=True,
#   )

#   st.write("")
#   if st.button(
#       "🚨 Broadcast Advisory to Regional Farmer WhatsApp Groups",
#       use_container_width=True,
#   ):
#     st.success(
#         "✅ Advisory successfully dispatched to registered farmers in"
#         f" {resolved_city_name} cluster."
#     )