import json
import chainlit as cl
from openai import OpenAI
from config import Config
from tavily import TavilyClient
from prompts import query_writer_instructions

#inizializzazione del client OpenAI con le configurazioni necessarie
client = OpenAI(base_url = Config.AI_API_URL, api_key = Config.OPENAI_API_KEY)

#Funzione per interagire
def llm(developer_prompt, user_prompt, temperature = 0, response_format = {"type": "json_object"}):
    response = client.chat.completions.create(
        model=Config.LLM_MODEL_LOW,
        messages=[
            {"role": "developer", "content": developer_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        response_format=response_format
    )
    return response.choices[0].message.content

#Genera una query ottimizzata per i motori di ricerca
def optimize_search_query(research_topic):
    formatted_instructions = query_writer_instructions.format(research_topic = research_topic)
    result = llm(formatted_instructions, "genera una query di ricerca ottimizzata:")
    obj = json.loads(result)
    return obj

def _format_content(result):
    return f"""
Fonte {result['title']}:\n===\n
URL: {result['url']}\n===\n
Contenuto rilevante:\n{result['content']}\n===\n
    """

def web_research(search_query):
    tavily_api_key = "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"
    max_results = 1
    include_raw = False

    client = TavilyClient(api_key=tavily_api_key)
    response = client.search(
        query = search_query,
        max_results = max_results,
        include_raw_content = include_raw
    )
    results = response.get("results", [])
    titles = [result['title'] for result in results]
    contents = [_format_content(result) for result in results]

    return {
        "sources_gathered": titles,
        "web_research_results": contents
    }

@cl.on_message
async def main(message: cl.Message):

    user_message = message.content
    osq = optimize_search_query(user_message)
    
    #Feedback all'utente con la query ottimizzata
    query, aspect, reason = osq["query"], osq["aspect"], osq["reason"]

    await cl.Message(author="system_assistant",
                     content=f"Query di ricerca ottimizzata:\n {query}.\n Mi sono soffermato su questo aspetto:\n {aspect}.\n Per questo motivo:\n {reason}.\n").send()

    #Ricerca web
    results = web_research(query)

    #Feddback all'utente con i risultati della ricerca web
    await cl.Message(
        author="system_assistant", 
        content=f"Fonti trovate:\n {results["sources_gathered"][0]}"
        ).send()