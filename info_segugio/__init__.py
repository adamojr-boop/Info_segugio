import json
import chainlit as cl
from openai import OpenAI
from config import Config
from tavily import TavilyClient
from prompts import query_writer_instructions, summarized_instructions, reflection_instructions

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
    max_results = 3
    include_raw = False

    client = TavilyClient(api_key=Config.TAVILY_API_KEY)
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

#Funzione per riassumere le informazioni raccolte dalle ricerche web
def summarize_sources(web_research_results, research_topic, running_summary = None):

    #current_results = web_research_results[-1]
    current_results = "\n".join(web_research_results)

    if running_summary:
        message = (
            f"estendi questo riassunto: {running_summary}\n\n"
            f"Con queste nuove informazioni: {current_results}"
            f"Sul tema: {research_topic}"
        )
    else:
        message = (
            f"Riassumi queste informazioni: {current_results}"
            f"Sul tema: {research_topic}"
        )

    output_formatter = None

    return llm(summarized_instructions, message, 0.1, output_formatter)

#Analizza il riassunto e suggerisci la prossima query di ricerca
def reflect_on_summary(research_topic, running_summary):
    result = llm(
        reflection_instructions.format(research_topic = research_topic),
        f"Identifica una lacuna e genera una domanda per la prossima ricerca basandosi su: {running_summary}"
    )
    return json.loads(result)

@cl.on_message
async def main(message: cl.Message):
    #generazione della query di ricerca
    user_message = message.content
    osq = optimize_search_query(user_message)
    
    #Feedback all'utente con la query ottimizzata
    query, aspect, reason = osq["query"], osq["aspect"], osq["reason"]

    await cl.Message(author="system_assistant",
                     content=f"Query di ricerca ottimizzata:\n {query}.\n Mi sono soffermato su questo aspetto:\n {aspect}.\n Per questo motivo:\n {reason}.\n").send()

    #Ciclo di ricerca
    running_summary = None
    max_cycles = 3

    while True:
        #Ricerca web
        results = web_research(query)

        titles = "\n".join(results["sources_gathered"])

        #Feddback all'utente con i risultati della ricerca web
        await cl.Message(
            author="system_assistant",
            content=f"Fonti trovate:\n {titles}"
        ).send()

        #Aggiorna il riassunto
        summary = summarize_sources(results['web_research_results'], query, running_summary)
        running_summary = summary

        #Feedback all'utente
        await cl.Message(
            author="system_assistant",
            content=f"Riassunto delle informazioni trovate:\n {summary}"
        ).send()

        max_cycles -= 1
        if max_cycles <= 0:
            break

        #Genera la prossima query di ricerca
        ros = reflect_on_summary(query, summary)

        query = ros.get('domanda_approfondimento', f"Dimmi di più su {query}")
        lacuna_conoscenza = ros.get('lacuna_conoscenza', "")

        #Feedback all'utente
        await cl.Message(
            author="system_assistant",
            content=f"Prossima query di ricerca suggerita:\n {query}.\n Mi sono soffermato su questo perché:\n {lacuna_conoscenza}."
        ).send()

    #Risultato finale della ricerca
    await cl.Message(
        author="segugio_assistant",
        content=f"Ciclo di ricerca completato.\n\n {message.content} \n\nRisposta finale:\n\n  {running_summary} "
    ).send()
        
    

    