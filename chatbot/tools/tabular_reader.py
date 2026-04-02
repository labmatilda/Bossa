from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from chatbot.utils import measure_time, read_yaml
from config.paths import SYSTEM_PROMPTS, ROOT
from pandasql import sqldf
from pathlib import Path
import chardet
import pandas as pd
import os
import uuid
import torch
import re
from chatbot.tools.utils import write_yaml, download_resource, GovPath
from config.paths import GOV_DATA
from chatbot.utils import debug  

def log_tabular_queries(filename:str, logdata: dict):
    path = ROOT/ Path("Chatbot/Testes/LogSQLqueries.yaml")
    
    log_history = read_yaml(path)
    file_history=None

    if log_history:
        file_history = log_history.get(filename)
    debug()(file_history)
            
    if file_history:
        updated_history = {filename: {str(uuid.uuid4()): logdata, **file_history}} # Atualizando
        #log_history.update({filename: file_history})
    else:
        updated_history = {filename: {str(uuid.uuid4()): logdata}}
    
    debug()(file_history)
    write_yaml(path=path, data=updated_history, overwrite=False)


def user_query(user_question: str, filepath)->HumanMessage:

    #filename = Path(str(Path(os.path.basename(link)).stem) + '_analysis.yaml')
    #dirname = Path(os.path.basename(link)).stem

    metadata = read_yaml(path=filepath)

    dataset_description = ""
    rows = metadata['shape'][0]
    columns = metadata['shape'][1]
    column_type_dictionary = metadata['dtypes']
    sample_data = metadata['sample_data']
    basic_statistical_analysis = ""

    input= str(f'''   
    <METADATA>
    Description: {dataset_description}
    Dimensions: {rows} rows x {columns} columns
    Schema (Columns and Data Types): {column_type_dictionary}
    Sample_data: {sample_data}
    Statistical Summary: {basic_statistical_analysis}
    </METADATA>

    <USER_QUESTION>
    {user_question}
    </USER_QUESTION>
    ''')

    return HumanMessage(content=input)

def log_events(data:dict, filepath: str, format:str='yaml')->None:
    if format=='yaml':
        write_yaml(data=data, path=filepath, overwrite=False)

def encoding_type(file_path):
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)
        encoding = chardet.detect(raw_data)['encoding']
    return encoding

def pre_analysis(filepath: str, data)->None:
    metadata = {
    "success": True,
    # Descreve cada coluna identificando valores de mínimo, máximo e desvio padrão (numeros), 
    # tipos mais frequentes, frequencia dos tipos mais frequentes e tipos unicos (texto)
    "describe": data.describe().to_dict(),
    "kurtosis": data.select_dtypes(include=['number']).kurtosis().to_dict(),
    "skewness": data.select_dtypes(include=['number']).skew().to_dict(),
    "correlation_matrix": data.select_dtypes(include=['number']).corr().to_dict(),
    "shape": list(data.shape), # dimensões da matriz
    "columns": data.columns.tolist(), # colunas
    "dtypes": data.dtypes.astype(str).to_dict(), # tipos de cada coluna
    "sample_data": data.head(n=5).to_dict('records'),
    "null_counts": data.isnull().sum().to_dict(), # contagem de células vazias
    "memory_usage": float(data.memory_usage(deep=True).sum()/(1024**2)) # Quantidade de memoria RAM em Mb
    }

    write_yaml(path=filepath, data=metadata, overwrite=True)

    return metadata

def generate_query(query: HumanMessage, llm: any)->str:
    system_prompt = read_yaml(SYSTEM_PROMPTS).get('system_prompt_queries').get('sql_sqlite')
    system_message = SystemMessage(content=system_prompt)
    debug()(system_prompt)
    response = llm.invoke([system_message, query])

    #code = re.sub(r"</?code>", "", response.content).strip() # retira tags

    return response

def tabular_analysis(query: str, llm: any, link: str=None, execute_code:bool=False)->tuple[str, pd.DataFrame|str|None]:
    paths = GovPath(link)
    
    dt_table = pd.read_csv(paths.datapath, encoding=encoding_type(paths.datapath), on_bad_lines='skip', sep=';', decimal=',') #on_bad_lines='warn'
    debug()("DataFrame carregado")
    error_type = "No error"

    pre_analysis(filepath=paths.analysispath, data=dt_table)
    debug()("pre-análise concluida...")

    query = user_query(query, paths.analysispath)

    response, inferencetime = measure_time(generate_query)(query, llm)
    debug()(f"Codigo gerado, Tempo: {inferencetime}")
    
    result=None
    if execute_code:
        if '<code>' in response.content:
            sql_query = re.sub(r"</?code>", "", response.content).strip() # retira tags
            try:
                result = sqldf(sql_query, {'dt_table': dt_table})
                
            except Exception as e:
                error_type = str(e)
                result = str(e)
                debug()(f"Erro ao executar código: {e}")
            #debug()(sql_query)
        else:
            result = response.content

    #log_tabular_queries(
    #    logdata={'UserQuery': query.content, 'LLMResponse': response.content, 
    #           'InferenceTime': inferencetime, 'Device':torch.cuda.get_device_name(0), 'Error': error_type},
    #   filename=paths.basename,)

    return {'code': response.content, 'dataframe': result}