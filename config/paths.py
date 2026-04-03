from pathlib import Path
from Testes import utils

ROOT = Path(__file__).parent.parent.resolve()
TOOLS = ROOT / Path("chatbot/tools/tools_description.yaml")
MODEL_CONFIG = ROOT / Path("config/model_config.yaml")
VECTOR_STORE = ROOT / Path("metadados/VectorStore")
SYSTEM_PROMPTS = ROOT / Path("config/SystemPrompts.yaml")
GOV_DATA = ROOT/Path("GovData") 
SQL_TESTS = ROOT/Path('SQLTests')

MODELOS = {'Qwen3-4B-Instruct-2507-UD-Q4_K_XL': ROOT/Path("modelos_locais/llm/Qwen3-4B-Instruct-2507-UD-Q4_K_XL.gguf")}

if __name__ == "__main__":
    import os
    r = {'link': 'asd.pdf'}
    print(os.path.basename(Path(r['link'])).rpartition('.')[-1])
    pass
