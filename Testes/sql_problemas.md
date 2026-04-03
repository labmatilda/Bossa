# Problemas com geração de SQL

## Gerenciar case sensitive

lower(), upper()... escrever tabaco ao invés de Tabaco gera erros

## Dificuldade de interpretação de colunas

No csv Tabela 1 - Base de Incidência, o modelo possui dificuldades de enteder que a coluna descrição são entidades,
nomes fornecidos pelas tabelas podem ser ambiguos, adiconar que, por exemplo, Tabaco ou IOF são do tipo descrição na query do usuário ajudou significamente na interpretação do modelo, deve passar essa resposabilidade para context prompt

## Colunas compostas

Algumas colunas podem apresentar a seguinte formatação a LLM pode gerar código sem "", como Mês/Ano, o que gera
o seguinte erro: "no such column: Mês". 

Sugestão: Limpar colunas com nomes compostos


Gerado pela LLM:
~~~
    SELECT 
        Terceirizado, 
        Cargo, 
        Mês/Ano
    FROM 
        dt_table 
    WHERE 
        Empresa = 'REAL JG SERVIÇOS GERAIS'
~~~
Corrigido: 
~~~
    SELECT 
        Terceirizado, 
        Cargo, 
        "Mês/Ano" <-------
    FROM 
        dt_table 
    WHERE 
        Empresa = 'REAL JG SERVIÇOS GERAIS'
~~~
    
Fonte: "https://dados.df.gov.br/dataset/4cd9832d-959d-405e-8e21-69c40187195d/resourcefbf987e6-982b-4765-94cd-817144e5ace3/download/funcionariosterceirizados2022.csv"

# Problemas com tabelas/dados

## Tabelas não autocontidas e multiplas tabelas 

Os dados contidos dentro de alguns recursos não são suficientes para interpretação

Neste recurso a descrição das colunas e outros metadados estão contidos no PDF abaixo.

prompt = "Qual é a arrecadação de cada estado?"

https://www.tesourotransparente.gov.br/ckan/dataset/f04a675e-4e5a-4e88-98de-acc3e22bf778/resource/58a9df19-5b0f-4bac-af00-254ff2a969ff/download/Capag-Estados-2022-1-revisada.csv

https://www.tesourotransparente.gov.br/ckan/dataset/f04a675e-4e5a-4e88-98de-acc3e22bf778/resource/52163ec6-2b97-4861-a25f-447e4cfbb58c/download/Metadados-Estados.pdf

## Formato inválido
Alguns recursos não são como declarados na descrição, mesmo sendo descritos como CSV esses recursos não apontam para um CSV diretamente ou simplesmente não existem.

### caso 1

Retornou uma pagina contendo vários CSVs
prompts = ["Olá", "Quantas familias são beneficiárias do bolsa famillia?"]

"https://aplicacoes.mds.gov.br/sagi/servicos/misocial?fq=anomes_s:2016*&fq=tipo_s:mes_mu&wt=csv&q=*&fl=ibge:codigo_ibge,anomes:anomes_s,qtd_familias_beneficiarias_bolsa_familia,valor_repassado_bolsa_familia&rows=10000000&sort=anomes_s%20asc,%20codigo_ibge%20asc"

### caso 2

Retornou um arquivo .zip contendo CSVs

https://repositorio.dados.gov.br/segrt/pensionistas/PENSIONISTAS_012023.zip

### caso 3

Segundo a descrição deste recurso era para ser um XML, entretanto retorna uma pagina com CSVs e PDFs

https://www2.ifal.edu.br/acesso-a-informacao/servidores/quadro-de-referencia-dos-servidores-tecnico-administrativos-e-docentes

## Fusão de colunas e blanklines

Algumas colunas 

Alguns campos apresentam as seguintes aberrações "NELSON JOSÉ OAQUIM JUNIOR                             DIRETOR PRESIDENTE"

## Links corrompidos, inexistentes ou não acessaveis

Alguns links na não conseguiram ser acessados

http://aplicacoes.mds.gov.br/sagi/servicos/misocial/?fl=codigo_ibge%2Canomes_s%20cebas_qtd_certif_status_valida_i%20cebas_qtd_certif_status_vigente_i&fq=cebas_qtd_certif_status_valida_i%3A*%20or%20cebas_qtd_certif_status_vigente_i%3A*&q=*%3A*&rows=100000&sort=anomes_s%20desc%2C%20codigo_ibge%20asc&wt=xml&omitHeader=true (10.03.2026)

