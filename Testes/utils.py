from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from pathlib import Path
import yaml
import re
import uuid
import json
import time

def read_yaml(path: str)->dict:
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data

def write_yaml(path: str, data: dict, overwrite: bool=False)->None:
    def str_presenter(dumper, data):
        if '\n' in data:
            # Usa o estilo '|' (literal block) se encontrar uma quebra de linha
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    # 2. Adicionamos essa regra ao Dumper padrão e ao SafeDumper
    yaml.add_representer(str, str_presenter)
    yaml.SafeDumper.add_representer(str, str_presenter)
    
    if Path(path).exists() and not overwrite:
        with open(path, "r") as f:
            existing_data = yaml.safe_load(f)
        if existing_data:
            print(existing_data)
            data = {**existing_data, **data}

def measure_time(func):
    def wrapper(*args, **kwargs):
        
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        
        #print('='*50, "Tempo de execução", "="*50)
        #print(f"Tempo de execução: {end-start}")
        #print('='*100, "\n")
        
        return result, end - start
    return wrapper


def langchain_to_jinja(messages: list) -> list:
    jinja_messages = []
    for message in messages:
        if isinstance(message, SystemMessage):
            jinja_messages.append({'role': 'system', 'content': message.content})

        elif isinstance(message, HumanMessage):
            jinja_messages.append({'role': 'user', 'content': message.content})

        elif isinstance(message, ToolMessage):
            jinja_messages.append({'role': 'tool', 'content': message.content})

        elif isinstance(message, AIMessage):
            jinja_messages.append({'role': 'assistant', 'content': message.content})

    return jinja_messages

def jinja_to_langchain(ai_message: str, think: str) -> AIMessage:
    tool_pattern = r"<tool_call>.*?</tool_call>"   

    try: # Se a resposta for um tool, o objeto AIMessage as receberá
    
        tools = re.findall(tool_pattern, ai_message, flags=re.DOTALL) # extrai tools de ai_message, retorna lista de str
        tool_calls = []

        for tool in tools:
            tool_str = re.sub(r"</?tool_call>", "", tool).strip() # retira tags
            tool_json = json.loads(tool_str)
            
            #formato requisitado pelo langgraph e objeto AIMessage para reconhecer tools
            tool_calls.append({
                'name': tool_json['name'],
                'args': tool_json['arguments'],
                'id': f"call_{uuid.uuid4().hex[:8]}"
            })
        ai_message = AIMessage(content=ai_message, 
                               tool_calls=tool_calls, 
                               additional_kwargs={"thinking": think})
        
        return ai_message
    except Exception as e:
        raise(f"KeyError: {e}")
    
    except json.JSONDecodeError: # Caso a resposta não seja uma chamada de ferramenta
        raise Exception("Não é um JSON válido")
if __name__ == "__main__":
    pass