from langchain_core.messages import ToolMessage
import json
import uuid
import os
from chatbot.utils import read_yaml
from chatbot.tools.utils import download_resource, GovPath
from chatbot.tools.tabular_reader import tabular_analysis
from pathlib import Path
from config.paths import VECTOR_STORE
from chatbot.utils import debug
from chatbot.tools.pdf_reader import text_query
#from chatbot.graph import AgentState, RunnableConfig

def answering_question(state: dict, config:dict, query: str):

    # 1. Busca por recursos relevantes
    # 2. Baixa recursos
    # 3. Organiza por tipo de formato(CSV, XML, PDF...)
    # 4. Analiza com base no tipo de formato

    # 1.
    resources = search_resources(state=state, config=config, query=query)
    results = {}

    #2. 
    #download_resource()
    #debug()(resources[:3])
    
    llm_wrapper = config['configurable']['llm_wrapper']

    for r in resources[0:3]:
        format = format = os.path.basename(Path(r['link'])).rpartition('.')[-1] # Alguns recursos, por exemplo, dizem ser csv mas apontam para uma http ou zip contendo csv
        link = r['link']
        source = {'source_type': 'link', 'link': link}
        paths = GovPath(link=link)
        
        debug()(f"teste {link}")

        if not Path(paths.datapath).exists():
            status = download_resource(link)
            if status == 200:
                debug()(f"Download concluído. Link: {link}")
            else:
                debug()(f"Erro ao realizar download. Status: {status}, Link: {link}")
                continue
        
        debug()(format) 
        if format.upper() == "CSV" :#or format == "XML":
            dataframe = tabular_analysis(query=query, link=link, llm=llm_wrapper, execute_code=True)['dataframe']
            results.update({'tabular_data': ToolMessage(content='a', additional_kwargs={'origin': link, 'dataframe': dataframe.to_dict("list")}, tool_call_id=uuid.uuid4())})
            
        elif format.upper() == "PDF":
            chunks = text_query(query=query, config=config, source=source)
            results.update({'text_data': ToolMessage(content='a', additional_kwargs={'origin': link, 'chunk': chunks}, tool_call_id=uuid.uuid4())})
        else:
            debug()(f"Formato {format} não suportado")

    if not results:
        results.update({'messages': "A busca não foi capaz de encontrar dados"})

    debug()("answering_question concluido")
    return results

def search_resources(state: dict, config:dict, query: str) -> list:
    '''
    Busca por datasets no banco de dados do governo federeal com base na query do usuário

    Args:
        query: Assunto requisitado pelo usuário

    '''
    collection_name = "Recurso_metadados"

    encoder = config['configurable']['encoder']
    client = config['configurable']['client']
    
    hits = vectorstore_search(encoder=encoder, client=client, query=query, collection_name=collection_name)
    
    resources = []

    for hit in hits:
        id = hit.payload.get('id')
    
        resources.append({
        "score": hit.score,
        "Titulo": hit.payload.get('titulo'),
        "descricao": hit.payload.get('descricao'),
        "formato": hit.payload.get('formato'),
        "id": hit.payload.get('id'),
        "id conjunto": hit.payload.get('idConjuntoDados'),
        "link": hit.payload.get('link')
        })
    return resources #[{'gov_resources': ToolMessage(content=resources, tool_call_id=uuid.uuid4())}]

def tabular_query(query:str, state, config, source:dict=None):
    '''
    Responde perguntas sobre dados em formato de tabelas como CSV, XLSX, XML... e bancos de dados relacionais (SQL)
    
    Args:
        query: Pergunta do usuário sobre a tabela
    '''

    llm_wrapper = config['configurable']['llm_wrapper']

    link = source['link']

    paths = GovPath(link=link)
        
    debug()(f"teste {link}")

    if not Path(paths.datapath).exists():
        status = download_resource(link)
        if status == 200:
            debug()(f"Download concluído. Link: {link}")
        else:
            debug()(f"Erro ao realizar download. Status: {status}, Link: {link}")

    response = tabular_analysis(query=query, link=link, llm=llm_wrapper, execute_code=True)


    return response

        
def vectorstore_search(collection_name:str, query:str, encoder, client):
    hits = client.query_points(
        collection_name=collection_name,
        query=encoder.encode(query).tolist(),
        limit=10
    ).points

    return hits

def tool_desc_jinja():
    from transformers import AutoTokenizer
    models = ["Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen3-0.6B"]
    model_name = models[1]

    tools = []
    my_tools = [search_resources]
    tools_description = read_yaml(path="tools/tools_description.yaml")
    
    for tool in my_tools:
        tools.append(tools_description.get(tool.__name__))
    
    debug()(tools_description)
    debug()(tools)

    messages = [{'role': 'assistant', 'content': 'teste'}]
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    text = tokenizer.apply_chat_template(
        messages, 
        tools=tools, # lista de dicionarios contendo informações de cada tool, segundo padrão jinja
        tokenize=False,
        #**self.model_config[self.model.config.name_or_path]['template']
    )
    debug()(text)


def teste_search_resources():
    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient

    query = "Crimes Rio de janeiro"

    encoder = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", device='cpu')
    client = QdrantClient(path=VECTOR_STORE) # Carrega vectorstore em disco

    config = {'configurable':{'encoder': encoder, 'client': client}}
    state = {}

    result = search_resources(state=state,query=query, config=config)
    debug()(result)

if __name__ == '__main__':
    #testes = [tool_desc_jinja, teste_search_resources]
    #testes[1]()
    pass