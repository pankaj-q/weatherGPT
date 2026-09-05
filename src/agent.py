import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from src.tools.weather_tool import fetch_weather_data

load_dotenv()

def build_weather_agent(api_key: str = None):
    key = api_key or os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, openai_api_key=key)
    tools = [fetch_weather_data]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are WeatherGPT, an AI meteorological assistant. Use `fetch_weather_data` to get live atmospheric metrics and provide actionable agricultural and safety guidance."),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)