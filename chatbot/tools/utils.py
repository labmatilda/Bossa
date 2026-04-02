from pathlib import Path
import requests
import yaml
import os
from config.paths import GOV_DATA
from icecream import ic

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
            ic(existing_data)
            data = {**existing_data, **data}
    
    with open(path, "w", encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

def download_resource(link: str):
    gov_repo = GOV_DATA
    file_name = os.path.basename(link)
    dir = Path(file_name).stem

    destination = gov_repo / dir
    destination.mkdir(parents=True, exist_ok=True)

    try:
        response = requests.get(link,  timeout=(10, 10))#headers = {"chave-api-dados-abertos" : key})
    except Exception as e:
        return f"Erro ao conectar com servidor: {e}"

    if response.status_code != 200:
        return response.status_code

    file_path = destination/file_name

    with open(file_path, 'wb') as f:
        f.write(response.content)

    return response.status_code

class GovPath():
    def __init__(self, link: str):
        
        self.dirname = Path(os.path.basename(link)).stem

        self.analysispath = GOV_DATA/self.dirname/Path('_analysis.yaml')
        
        self.dataname = os.path.basename(link)
        self.datapath = GOV_DATA/self.dirname/self.dataname