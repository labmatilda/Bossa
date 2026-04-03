from transformers import AutoTokenizer, AutoModelForCausalLM

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.prebuilt import ToolNode # Classe que chama tools
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
# add_message é uma reduce_function, função que dita como um dado será modificado ao ser atualizado
# Nesse caso, add_message concatena messagens anteriores com novas sem reescrever dados anteriores

from langchain_core.messages import BaseMessage   # Classe pai que dá origem a todos os tipos de messagem no langchain
from langchain_core.messages import ToolMessage   # Classe que gerencia messagens/respotas das tools
from langchain_core.messages import HumanMessage
from langchain_core.messages import AIMessage
from langchain_core.messages import SystemMessage # Classe que gerencia messagens de sistema, ordens a LLM
from langchain_core.runnables import RunnableConfig

from typing import TypedDict, Dict
from typing import Annotated # Adiciona decrição a variaveis, variavel = Annotaded[tipo_variavel, "descrição"]
from typing import Sequence  # Cria uma sequência dado um tipo EX: Sequence[int], Sequence[str]...

from chatbot.tools.tools import search_resources, tabular_query, answering_question
from chatbot.llm import LLM
from chatbot.utils import read_yaml
from config.paths import TOOLS, VECTOR_STORE, SYSTEM_PROMPTS

from chatbot.utils import debug

tools_description = read_yaml(TOOLS)['tools']
tools = [tools_description['answering_question']]#, tools_description['search_resources']]

# Herda da classe TypedDict, permite declarar tipos para classe
# Esta classe serve para gerenciar o estado atual do agente
''' Ver mais informações nas importações de cada função/classe''' 
# Esse tipo de classe não deve ser instanciada, serve como um blueic para criação e gerenciamento de dicionarios
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages] # Troca de messagens entre chat e usuário
    gov_resources: Annotated[Sequence[ToolMessage], add_messages] # Recursos do governo
    tabular_data: Annotated[Sequence[ToolMessage], add_messages]
    text_data: Annotated[Sequence[ToolMessage], add_messages]
    # tipo da variavel messages: sequence[BaseMessages]
    # conteudo: add_messages

def init_state(state: AgentState, config: RunnableConfig):
    debug()('Inicializando...')
    return {'messages': [],
            'gov_resources': [ToolMessage(content="", tool_call_id="init")]}

def llm_call(state: AgentState, config: RunnableConfig):
    llm = config['configurable']['llm_wrapper']
    system_message = read_yaml(path=SYSTEM_PROMPTS)['system_prompt_tools']['v1']
    response = llm.invoke([system_message] + state['messages'], tools) #  + [state['gov_resources'][-1]],
    debug()(response)
    return {'messages': [response]}

def tool_call(state: AgentState, config: RunnableConfig):
    # Tipo AIMessage(content:str, tool_calls:dict('name': 'func_name', 'args': {}, 'id': 'id'), additional_kwargs:dict)
    ai_message = state['messages'][-1]
    '''OBS: Por enquanto utlizaremos tool_calls[0], permitindo a chamada de apenas uma tool por vez'''
    func_name = ai_message.tool_calls[0].get('name')
    func = globals()[func_name]
    args = ai_message.tool_calls[0].get('args')
    result= None
    
    if callable(func):
        results = func(state=state, config=config, **args)
        debug()(results)
        return results
        # return messages_router(func_name, results)
    
    return {'messages': [SystemMessage(content="Função retornada não existe")]}

def should_continue(state: AgentState)-> AgentState:
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls: # testa se ultima mensagem foi uma chamada de ferramenta
        return 'continue'
    else:
        return 'user_input_node' 

def kill_robot(state: AgentState):

    last_message = state['messages'][1].content

    if last_message.lower() == "hasta la vista":
        return 'hasta la vista baby'
    else:
        return 'continue'

def user_input(state: AgentState)-> AgentState:
    '''Entrada do usuário'''

    user_input = interrupt("Entrada de dados usuário")
    
    return {'messages': [HumanMessage(content=user_input)]}


def chat_graph():

    graph = StateGraph(AgentState)

    graph.add_node('user_input_node', user_input)
    graph.add_node('llm_call_node', llm_call)

    #tool_node = ToolNode(tools=tools) # Objeto que executa ferramentas
    # OBS: O objeto ToolNode sempre irá guardar o retorno da ferramenta onde houver uma chamada de ferramenta
    # Nesse caso na variável messages, por isso é recomendavel criar um wrapper para desviar o conteúdo
    # da ferramenta para outra variável a fim de não sobrecarregar a llm durante a inferência

    graph.add_node('tools_node', tool_call) # Adiciona objeto que contém tools em um nó

    #graph.set_entry_point('llm_call_node')

    graph.add_node('init_state_node', init_state)

    graph.set_entry_point('init_state_node')
    #graph.add_edge(START, 'init_state_node')

    graph.add_edge('init_state_node', 'llm_call_node')

    graph.add_conditional_edges(
        source='llm_call_node', # determina a partir de qual nó haverá arestas condicionais   
        path=should_continue, # determina qual função escolherá o próximo nó
        
        path_map= # mapeia saída da função em path para qual nó seguirá (parametro opcional, entretanto a sáida de path deverá ser um nó existente)
        {
            'continue': 'tools_node',
            'user_input_node': 'user_input_node',
        }
    )

    graph.add_edge('tools_node', 'llm_call_node') # Aresta que retorna ao agente, criando uma conexão circular
    
    #graph.add_edge('user_input_node', 'llm_call_node')

    graph.add_conditional_edges(
        source='user_input_node',
        path=kill_robot,
        path_map=
        {   
            'hasta la vista baby': END,
            'continue': 'llm_call_node'
        }
    )

    checkpointer = InMemorySaver()  
    app = graph.compile(checkpointer=checkpointer)

    return app

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

def load_vectorstore(model_name="Qwen/Qwen3-Embedding-0.6B", device='cpu'):
    path = VECTOR_STORE
    encoder = SentenceTransformer(model_name, device=device)
    client = QdrantClient(path="metadados/VectorStore") # Carrega vectorstore em disco

    return encoder, client

from chatbot.llm import LLML
from config.paths import MODELOS

def teste_llama():

    # AttributeError: 'LlamaModel' object has no attribute 'sampler' ---> model_path não aceita instancia de pathlib

    encoder, client = load_vectorstore()
    
    config = {'configurable': {
            'thread_id': uuid.uuid4(),
            'llm': 'llm_model', 
            'tokenizer': 'tokenizer',
            'llm_wrapper': LLML(model_path=str(MODELOS['Qwen3-4B-Instruct-2507-UD-Q4_K_XL']), n_gpu_layers=-1, verbose=False),
            'encoder': encoder,
            'client': client
            }}

    graph = chat_graph()

    prompts = ['olá', "quero dados sobre natalidade"]
    messages = []

    for chunk in graph.stream({'messages': [prompts[0]]}, config, stream_mode='messages'):
        messages.append(chunk[0])
    
    for prompt in prompts[1:]:
        command = Command(resume=prompt)
        for chunk in graph.stream(command, config, stream_mode='messages'):
            messages.append(chunk[0])

    debug()(messages)


def testes_transformers():

    prompts = ['olá', "quero dados sobre natalidade"]
    model_name = "Qwen/Qwen3-0.6B"
    

    llm_model = AutoModelForCausalLM.from_pretrained(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    encoder, client = load_vectorstore()

    config = {'configurable': {
            'thread_id': uuid.uuid4(),
            'llm': llm_model, 
            'tokenizer': tokenizer,
            'llm_wrapper': LLM(model=llm_model, tokenizer=tokenizer),
            'encoder': encoder,
            'client': client
            }}

    graph = chat_graph()
    messages = []

    for chunk in graph.stream({'messages': [prompts[0]]}, config, stream_mode='messages'):
        messages.append(chunk[0])
    
    for prompt in prompts[1:]:
        command = Command(resume=prompt)
        for chunk in graph.stream(command, config, stream_mode='messages'):
            messages.append(chunk[0])
    
    return messages, graph.get_state(config)
    

if __name__ == '__main__':
    #messages, graph_state = testes()
    #debug()(messages)
    #debug()(graph_state)

    teste_llama()

    pass