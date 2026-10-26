# Atlas Global 1.0 — Protótipo

Aplicativo Streamlit com rankings individuais e gráficos históricos de 30 países (América Latina + BRICS, Brasil contado uma vez).

## Instalação

1. Instale Python 3.10 ou mais recente.
2. Abra um terminal na pasta do projeto.
3. Execute `pip install -r requirements.txt`.
4. Execute `streamlit run app.py`.
5. Abra o endereço local informado pelo Streamlit.

## Publicação

Crie um repositório no GitHub, envie `app.py` e `requirements.txt`, entre em https://share.streamlit.io e escolha o repositório e o arquivo `app.py`.

## Escopo

Esta versão conecta 13 dos 23 indicadores planejados ao Banco Mundial. Não inclui ainda FMI, UNESCO UIS, OIT, PNUD, IBPT e OCIndex. A API do Banco Mundial requer conexão com a internet para a primeira consulta. Lacunas de dados são exibidas sem preenchimento artificial.
