import os


### Local LLM
#class Config:
#    LLM_MODEL = "llama3.2" "deepseek-r1:1.5b"
#    LLM_MODEL_LOW = "llama3.2" "deepseek-r1:1.5b" 
#    AI_API_URL = "http://localhost:11434/v1"
#    OPENAI_API_KEY= "ollama"

### OpenAI LLM
class Config:
    LLM_MODEL = "gpt-4o"
    LLM_MODEL_LOW = "gpt-4o-mini"
    AI_API_URL = "https://api.openai.com/v1"
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]