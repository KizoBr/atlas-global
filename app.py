import html
import re
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Atlas Global", page_icon="🌎", layout="wide")

LATAM = {'ARG':'Argentina','BOL':'Bolívia','BRA':'Brasil','CHL':'Chile','COL':'Colômbia','CRI':'Costa Rica','CUB':'Cuba','DOM':'República Dominicana','ECU':'Equador','SLV':'El Salvador','GTM':'Guatemala','HTI':'Haiti','HND':'Honduras','MEX':'México','NIC':'Nicarágua','PAN':'Panamá','PRY':'Paraguai','PER':'Peru','URY':'Uruguai','VEN':'Venezuela'}
BRICS = {'BRA':'Brasil','RUS':'Rússia','IND':'Índia','CHN':'China','ZAF':'África do Sul','EGY':'Egito','ETH':'Etiópia','IRN':'Irã','ARE':'Emirados Árabes Unidos','IDN':'Indonésia','SAU':'Arábia Saudita'}
COUNTRIES = dict(sorted((LATAM | BRICS).items(), key=lambda item: item[1]))

# O catálogo mantém todos os 23 indicadores. Apenas os que têm código
# do Banco Mundial validado nesta etapa estão disponíveis para consulta.
INDICATORS = {
    'PIB total': dict(code='NY.GDP.MKTP.CD', unit='US$ correntes', category='Economia e finanças públicas', description='Valor monetário dos bens e serviços finais produzidos dentro do país em um ano, a preços correntes.', formula='PIB = consumo + investimento + gasto do governo + exportações − importações.'),
    'PIB per capita (PPC)': dict(code='NY.GDP.PCAP.PP.KD', unit='dólares internacionais constantes', category='Economia e finanças públicas', description='Produção econômica real por habitante, corrigida pelas diferenças de poder de compra entre países.', formula='PIB real ajustado por PPC ÷ população.'),
    'Crescimento real do PIB': dict(code='NY.GDP.MKTP.KD.ZG', unit='%', category='Economia e finanças públicas', description='Variação percentual anual da produção econômica descontando alterações de preços.', formula='[(PIB real no ano t ÷ PIB real no ano t−1) − 1] × 100.'),
    'Inflação anual': dict(code='FP.CPI.TOTL.ZG', unit='%', category='Economia e finanças públicas', description='Variação média anual dos preços ao consumidor, medida por índice nacional.', formula='Variação percentual anual do índice de preços ao consumidor (método de média anual da fonte).'),
    'Taxa de desemprego': dict(code='SL.UEM.TOTL.ZS', unit='% da força de trabalho', category='Economia e finanças públicas', description='Parcela da força de trabalho sem emprego, disponível e procurando trabalho; série modelada pela OIT.', formula='Desempregados ÷ força de trabalho × 100.'),
    'Produtividade do trabalho': dict(code=None, unit='PIB real por hora trabalhada', category='Economia e finanças públicas', description='Produção econômica ajustada por preços e poder de compra em relação ao total de horas trabalhadas.', formula='PIB real em PPC ÷ total de horas trabalhadas.'),
    'Dívida pública (% do PIB)': dict(code=None, unit='% do PIB', category='Economia e finanças públicas', description='Dívida bruta do governo geral, relativa ao tamanho da economia.', formula='Dívida bruta do governo geral ÷ PIB × 100.'),
    'Carga tributária (% do PIB)': dict(code=None, unit='% do PIB', category='Economia e finanças públicas', description='Receitas tributárias e contribuições sociais obrigatórias conforme metodologia harmonizada a definir.', formula='Receitas tributárias abrangidas ÷ PIB × 100.'),
    'Gasto total do governo (% do PIB)': dict(code=None, unit='% do PIB', category='Economia e finanças públicas', description='Despesas totais do governo geral, incluindo serviços, investimentos, transferências e demais funções.', formula='Despesa total do governo geral ÷ PIB × 100.'),
    'Expectativa de vida': dict(code='SP.DYN.LE00.IN', unit='anos', category='Saúde', description='Número médio de anos que um recém-nascido viveria sob as taxas de mortalidade do período.', formula='Estimativa de tábua de vida baseada em taxas de mortalidade por idade; não é uma simples média de idades ao morrer.'),
    'Mortalidade infantil': dict(code='SP.DYN.IMRT.IN', unit='óbitos por 1.000 nascidos vivos', category='Saúde', description='Probabilidade de morrer antes de completar um ano de idade, expressa por mil nascidos vivos.', formula='Probabilidade de óbito antes de 1 ano × 1.000 (estimativa de mortalidade).'),
    'Gastos com saúde (% do PIB)': dict(code='SH.XPD.CHEX.GD.ZS', unit='% do PIB', category='Saúde', description='Despesas correntes com saúde de fontes públicas e privadas, como porcentagem do PIB.', formula='Gastos correntes com saúde ÷ PIB × 100; exclui investimento em capital.'),
    'Gastos com saúde por habitante': dict(code='SH.XPD.CHEX.PC.CD', unit='US$ correntes por pessoa', category='Saúde', description='Gasto corrente com saúde por habitante, em dólares correntes.', formula='Despesas correntes com saúde ÷ população, convertidas para US$ correntes.'),
    'Taxa de alfabetização de adultos': dict(code='SE.ADT.LITR.ZS', unit='% (15 anos ou mais)', category='Educação', description='Proporção da população com 15 anos ou mais capaz de ler e escrever uma declaração curta e simples.', formula='Adultos alfabetizados ÷ população com 15 anos ou mais × 100.'),
    'Gastos públicos com educação (% do PIB)': dict(code='SE.XPD.TOTL.GD.ZS', unit='% do PIB', category='Educação', description='Despesas governamentais em educação, em proporção ao PIB.', formula='Despesa pública com educação ÷ PIB × 100.'),
    'Gasto público por aluno — primário': dict(code=None, unit='US$ PPC constantes por aluno', category='Educação', description='Despesa pública por estudante do ensino primário, ajustada por poder de compra.', formula='Despesa pública do nível primário ÷ estudantes do nível primário, convertida para PPC constante.'),
    'Gasto público por aluno — secundário': dict(code=None, unit='US$ PPC constantes por aluno', category='Educação', description='Despesa pública por estudante do ensino secundário, ajustada por poder de compra.', formula='Despesa pública do nível secundário ÷ estudantes do nível secundário, convertida para PPC constante.'),
    'Gasto público por aluno — superior': dict(code=None, unit='US$ PPC constantes por aluno', category='Educação', description='Despesa pública por estudante do ensino superior, ajustada por poder de compra.', formula='Despesa pública do nível superior ÷ estudantes do nível superior, convertida para PPC constante.'),
    'Índice de Desenvolvimento Humano (IDH)': dict(code=None, unit='índice de 0 a 1', category='Desenvolvimento social', description='Índice sintético de saúde, educação e renda elaborado pelo PNUD.', formula='Média geométrica dos índices normalizados de saúde, educação e renda.'),
    'Índice IRBES': dict(code=None, unit='índice metodológico do IBPT', category='Desenvolvimento social', description='Índice de Retorno de Bem-Estar à Sociedade do IBPT, que relaciona carga tributária e desenvolvimento humano.', formula='Cálculo específico publicado pelo IBPT; consultar a metodologia da edição antes de comparar.'),
    'Índice de Gini': dict(code='SI.POV.GINI', unit='pontos (0 a 100)', category='Desenvolvimento social', description='Mede a desigualdade na distribuição de renda ou consumo nas pesquisas domiciliares da fonte.', formula='Gini = área entre linha de igualdade e curva de Lorenz ÷ área total abaixo da linha de igualdade × 100.'),
    'Índice Global de Crime Organizado': dict(code=None, unit='índice de 1 a 10', category='Segurança', description='Mede a presença e extensão de mercados e atores criminosos, conforme o Índice Global de Crime Organizado.', formula='Agregação de dimensões de criminalidade segundo a metodologia e ponderações da edição oficial.'),
    'Homicídios intencionais (violência letal)': dict(code='VC.IHR.PSRC.P5', unit='por 100 mil habitantes', category='Segurança', description='Homicídios intencionais por 100 mil habitantes; indicador nacional de violência letal, não exclusivamente urbana.', formula='Número de homicídios intencionais ÷ população × 100.000.'),
}

# Explicações editoriais: significado, utilidade e método de cálculo.
UTILITY = {
    'PIB total': 'Dimensiona o tamanho da economia e permite comparações de escala produtiva. Por usar dólares correntes, a série também responde a mudanças cambiais e à inflação.',
    'PIB per capita (PPC)': 'Ajuda a comparar a produção econômica média por habitante, descontando diferenças de preços entre países. Não representa a renda efetivamente recebida por cada pessoa nem sua distribuição.',
    'Crescimento real do PIB': 'Mostra a expansão ou contração da atividade econômica sem o efeito da inflação. É útil para acompanhar ciclos econômicos e o ritmo de crescimento.',
    'Inflação anual': 'Indica a evolução do custo médio de uma cesta de consumo. É útil para avaliar estabilidade de preços e perda de poder de compra da moeda.',
    'Taxa de desemprego': 'Permite acompanhar a parcela da força de trabalho sem ocupação, segundo critérios internacionais. Não mede, isoladamente, informalidade ou subocupação.',
    'Produtividade do trabalho': 'Avalia a produção econômica gerada por hora trabalhada e permite estudar eficiência produtiva e crescimento de longo prazo. Diferenças setoriais e de mensuração importam.',
    'Dívida pública (% do PIB)': 'Compara a dívida bruta do governo geral ao tamanho da economia. É útil para observar a evolução do endividamento, mas não basta, isoladamente, para concluir sobre sustentabilidade fiscal.',
    'Carga tributária (% do PIB)': 'Mostra o peso da arrecadação tributária em relação à atividade econômica. Permite comparar estruturas fiscais, respeitando diferenças de abrangência e contribuições sociais.',
    'Gasto total do governo (% do PIB)': 'Mede quanto o governo geral despende em proporção à economia, incluindo serviços, benefícios, investimentos e outras despesas. Não equivale apenas ao custo da burocracia.',
    'Expectativa de vida': 'Sintetiza as condições de mortalidade de uma população em determinado período. É útil para acompanhar resultados de saúde, saneamento e condições sociais.',
    'Mortalidade infantil': 'Indica o risco de morte antes do primeiro aniversário. É amplamente utilizada para acompanhar saúde materno-infantil e condições de vida.',
    'Gastos com saúde (% do PIB)': 'Mostra a proporção dos recursos econômicos destinados a despesas correntes de saúde. Não indica, isoladamente, a qualidade dos serviços prestados.',
    'Gastos com saúde por habitante': 'Permite comparar o volume médio de recursos correntes de saúde por pessoa. Como usa dólares correntes, taxas de câmbio podem afetar comparações históricas.',
    'Taxa de alfabetização de adultos': 'Acompanha a proporção de adultos capazes de ler e escrever uma mensagem simples. Não mede diretamente proficiência ou qualidade da aprendizagem.',
    'Gastos públicos com educação (% do PIB)': 'Apresenta o esforço financeiro público em educação relativamente ao PIB. A qualidade e a distribuição dos gastos exigem outras medidas.',
    'Gasto público por aluno — primário': 'Compara recursos públicos por estudante do ensino primário. Pode ajudar a analisar financiamento, sem determinar isoladamente os resultados educacionais.',
    'Gasto público por aluno — secundário': 'Compara recursos públicos por estudante do ensino secundário, com ajuste por poder de compra conforme a fonte.',
    'Gasto público por aluno — superior': 'Compara recursos públicos por estudante do ensino superior, considerando a definição de gasto e matrícula adotada pela fonte.',
    'Índice de Desenvolvimento Humano (IDH)': 'Resume dimensões de longevidade, educação e renda, permitindo comparações amplas de desenvolvimento humano. Não cobre diretamente desigualdade, segurança ou sustentabilidade.',
    'Índice IRBES': 'Relaciona carga tributária e indicadores de bem-estar na metodologia do IBPT. A abrangência de países e edições pode ser restrita, e o índice não deve ser recalculado sem documentação oficial.',
    'Índice de Gini': 'Quantifica o grau de desigualdade na distribuição de renda ou consumo. Valores mais altos correspondem a maior desigualdade; pesquisas nacionais podem diferir em cobertura e conceito.',
    'Índice Global de Crime Organizado': 'Avalia dimensões de mercados e atores criminosos, úteis para comparações internacionais. Trata-se de índice composto de avaliação, não de uma contagem direta de crimes.',
    'Homicídios intencionais (violência letal)': 'Compara a intensidade da violência letal entre países considerando o tamanho populacional. A medida é nacional e não representa apenas a violência urbana.',
}

st.markdown('''<style>
.stApp {background: #f5f7fb; color: #17233b;}
.block-container {max-width: 1260px; padding-top: 1.5rem;}
.hero {background:linear-gradient(125deg,#101e3c,#243e68);border-radius:18px;padding:17px 23px;margin-bottom:12px;color:white;}
.hero h1{font-size:1.8rem;margin:0;color:#fff;}
.hero p{color:#d7e2f2;margin:7px 0 0;}
.indicator-head {border-left:4px solid #1a4d89;background:white;padding:13px 18px;border-radius:10px;margin:8px 0 13px;box-shadow:0 4px 18px #17233b12;}
.indicator-head h2 {font-size:1.48rem;line-height:1.2;margin:4px 0 8px;color:#142c52;}
.eyebrow {text-transform:uppercase;font-size:.69rem;letter-spacing:.09em;font-weight:800;color:#23599b;}
.indicator-head p{margin:3px 0 6px;color:#293c58;font-size:.86rem;line-height:1.43;}
.indicator-head h3 {font-size:.87rem;font-weight:750;margin:7px 0 2px;color:#173963;}
.formula {font-size:.85rem;background:#eef4fb;padding:8px 11px;border-radius:8px;margin-top:7px;color:#193654;line-height:1.45;}
.ranking-shell {overflow-x:auto;background:white;border-radius:15px;box-shadow:0 5px 24px #18234014;padding:6px;margin-top:12px;}
.ranking-table {width:100%;border-collapse:separate;border-spacing:0;min-width:500px;font-size:1.04rem;color:#17233b;}
.ranking-table th {background:#e9eef6;color:#17233b;text-transform:uppercase;letter-spacing:.04em;font-size:.86rem;padding:16px 12px;text-align:left;}
.ranking-table th:first-child,.ranking-table td:first-child {text-align:center;width:100px;}
.ranking-table th:last-child,.ranking-table td:last-child {text-align:right;padding-right:24px;}
.ranking-table td{padding:12px;border-bottom:1px solid #e5eaf2;font-weight:550;}
.ranking-table tr:last-child td{border-bottom:0;}
.ranking-table tbody tr:nth-child(even):not(.brazil){background:#f8fafc;}
.ranking-table tbody tr.brazil td{background:linear-gradient(90deg,#f6df9a,#dfb84e);font-weight:800;color:#1d2637;border-bottom-color:#cca444;}
.ranking-table tbody tr.brazil td:first-child{border-radius:8px 0 0 8px;}
.ranking-table tbody tr.brazil td:last-child{border-radius:0 8px 8px 0;}
.flag-img {width:29px;height:20px;object-fit:cover;vertical-align:middle;margin-right:12px;border:1px solid #d9e0e9;border-radius:2px;}
.smallnote{font-size:.88rem;color:#66728b;margin:9px 0 4px;}
div[data-testid="stSelectbox"] label p {font-size:1.08rem;font-weight:800;color:#182b4b;}
/* Barra lateral branca; seleções em azul escuro, texto claro nos chips. */
section[data-testid="stSidebar"] {background:#fff;}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {color:#183153;}
section[data-testid="stSidebar"] [data-baseweb="tag"] {background:#173d72!important;}
section[data-testid="stSidebar"] [data-baseweb="tag"] span {color:#fff!important;}
section[data-testid="stSidebar"] [data-baseweb="tag"] svg {fill:#fff!important;color:#fff!important;}
section[data-testid="stSidebar"] [data-baseweb="radio"] input:checked + div {background:#174e99!important;border-color:#174e99!important;}
section[data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] [data-baseweb="radio"] > div:first-child {background:#174e99!important;border-color:#174e99!important;}
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {background:#174e99!important;color:white!important;border-color:#174e99!important;}
section[data-testid="stSidebar"] [data-testid="stMultiSelect"]:focus-within {border-color:#174e99;}
/* Itens selecionados e controles da barra lateral sempre azuis. */
section[data-testid="stSidebar"] [data-baseweb="tag"] {background-color:#173d72!important;border-color:#173d72!important;}
section[data-testid="stSidebar"] [data-baseweb="tag"] span, section[data-testid="stSidebar"] [data-baseweb="tag"] svg {color:white!important;fill:white!important;}
section[data-testid="stSidebar"] [data-baseweb="select"] [aria-selected="true"],
section[data-testid="stSidebar"] [data-baseweb="option"][aria-selected="true"] {background:#e8f0fd!important;color:#173d72!important;}
section[data-testid="stSidebar"] input:focus {outline-color:#173d72!important;}

</style>''',unsafe_allow_html=True)

ISO2 = {'ARG':'ar','BOL':'bo','BRA':'br','CHL':'cl','COL':'co','CRI':'cr','CUB':'cu','DOM':'do','ECU':'ec','SLV':'sv','GTM':'gt','HTI':'ht','HND':'hn','MEX':'mx','NIC':'ni','PAN':'pa','PRY':'py','PER':'pe','URY':'uy','VEN':'ve','RUS':'ru','IND':'in','CHN':'cn','ZAF':'za','EGY':'eg','ETH':'et','IRN':'ir','ARE':'ae','IDN':'id','SAU':'sa'}
def flag_image(iso3, name):
    iso2 = ISO2.get(iso3)
    if not iso2:
        return ''
    return f'<img class="flag-img" src="https://flagcdn.com/w40/{iso2}.png" alt="Bandeira de {html.escape(name, quote=True)}" loading="lazy">'

def nice_number(x, code):
    # Conservar casas decimais úteis e a unidade no cabeçalho da tabela.
    if code == 'NY.GDP.MKTP.CD':
        return f'{x / 1e9:,.1f}'.replace(',','X').replace('.',',').replace('X','.')
    return f'{x:,.2f}'.replace(',','X').replace('.',',').replace('X','.')

@st.cache_data(ttl=86400, show_spinner=False)
def load_indicator(code):
    url=f'https://api.worldbank.org/v2/country/{";".join(COUNTRIES)}/indicator/{code}'
    response=requests.get(url,params={'format':'json','per_page':20000,'date':'1960:2026'},timeout=45)
    response.raise_for_status()
    payload=response.json()
    if not isinstance(payload,list) or len(payload)<2 or payload[1] is None:
        raise ValueError('A fonte não retornou uma série válida para este indicador.')
    rows=[]
    for entry in payload[1]:
        iso=entry.get('countryiso3code')
        if iso in COUNTRIES and entry.get('value') is not None:
            rows.append({'ISO3':iso,'País':COUNTRIES[iso],'Ano':int(entry['date']),'Valor':float(entry['value'])})
    return pd.DataFrame(rows,columns=['ISO3','País','Ano','Valor'])

st.markdown('<div class="hero"><h1>🌎 Atlas Global</h1><p>Indicadores internacionais · América Latina e BRICS · Rankings e séries históricas</p></div>',unsafe_allow_html=True)
st.caption('Catálogo planejado: 23 indicadores. Nesta versão, 13 possuem conexão ativa; 10 aguardam integração de suas fontes.')

# Escolha a categoria e depois apenas um indicador dentro dela.
# A categoria aparece na área principal, preservando espaço para o ranking.
CATEGORIES = list(dict.fromkeys(m['category'] for m in INDICATORS.values()))
if st.session_state.get('selected_indicator') not in INDICATORS:
    st.session_state['selected_indicator'] = next(iter(INDICATORS))
if st.session_state.get('selected_category') not in CATEGORIES:
    st.session_state['selected_category'] = INDICATORS[st.session_state['selected_indicator']]['category']

def change_category():
    category = st.session_state['selected_category']
    if INDICATORS[st.session_state['selected_indicator']]['category'] != category:
        st.session_state['selected_indicator'] = next(
            name for name, item in INDICATORS.items() if item['category'] == category
        )

def choose_indicator(name):
    st.session_state['selected_indicator'] = name

with st.sidebar:
    st.header('Configurações')
    group=st.radio('Grupo de países',['Todos','América Latina','BRICS'])
    universe=COUNTRIES if group=='Todos' else LATAM if group=='América Latina' else BRICS
    mode=st.radio('Visualização',['Ranking','Evolução histórica'])
    if mode=='Ranking':
        chosen=st.multiselect('Países do ranking',list(universe),default=list(universe),format_func=lambda iso:universe[iso])
    else:
        chosen=[]
        st.caption('Na evolução histórica, escolha até cinco países acima do gráfico.')

# Seleção compacta por categoria na área principal (nenhuma cor temática).
st.markdown('#### Escolha o indicador')
st.selectbox('Categoria', CATEGORIES, key='selected_category', on_change=change_category)
indicator_names = [name for name, info in INDICATORS.items()
                   if info['category'] == st.session_state['selected_category']]
style_rules = []
for pos, name in enumerate(indicator_names):
    selected = (st.session_state['selected_indicator'] == name)
    key = f'indicator_{list(INDICATORS).index(name):02d}'
    style_rules.append(
        f'.st-key-{key} button {{'
        'background:#fff!important;color:#18304c!important;'
        f'border:{"2px solid #173d72" if selected else "1px solid #d4dfed"}!important;'
        'border-radius:8px!important;min-height:32px!important;height:auto!important;'
        'padding:5px 8px!important;width:100%!important;box-shadow:none!important;'
        'line-height:1.18!important;}'
    )
    style_rules.append(
        f'.st-key-{key} button p {{font-size:.76rem!important;'
        f'font-weight:{"750" if selected else "500"}!important;'
        'color:#18304c!important;line-height:1.18!important;'
        'text-align:center!important;white-space:normal!important;}'
    )
    if selected:
        style_rules.append(f'.st-key-{key} button {{background:#eaf2ff!important;}}')
st.markdown('<style>' + '\n'.join(style_rules) + '</style>', unsafe_allow_html=True)
for row_start in range(0, len(indicator_names), 5):
    cols = st.columns(5, gap='small')
    for col, name in zip(cols, indicator_names[row_start:row_start + 5]):
        with col:
            is_active = st.session_state['selected_indicator'] == name
            st.button(('✓ ' if is_active else '') + name,
                      key=f'indicator_{list(INDICATORS).index(name):02d}',
                      use_container_width=True,
                      on_click=choose_indicator, args=(name,))

indicator=st.session_state['selected_indicator']
meta=INDICATORS[indicator]

safe_title=html.escape(indicator)
safe_desc=html.escape(meta['description'])
safe_utility=html.escape(UTILITY.get(indicator, 'Permite comparar os países conforme a definição e a unidade deste indicador.'))
safe_formula=html.escape(meta['formula'])
st.markdown(f'<div class="indicator-head"><div class="eyebrow">Indicador selecionado</div><h2>{safe_title}</h2><p><strong>O que é:</strong> {safe_desc}</p><p><strong>Utilidade:</strong> {safe_utility}</p><div class="formula"><strong>Cálculo:</strong> {safe_formula}</div></div>',unsafe_allow_html=True)

if mode=='Ranking' and not chosen:
    st.warning('Selecione ao menos um país no menu lateral.')
    st.stop()
if meta['code'] is None:
    st.info('📚 Indicador previsto no catálogo de 23, mas ainda sem integração à fonte oficial. Não exibimos dados ou rankings simulados.')
    st.caption('Próxima etapa: integrar a fonte específica, validar unidades, anos e cobertura por país.')
    st.stop()

code=meta['code']
try:
    with st.spinner('Consultando os dados do Banco Mundial...'):
        data=load_indicator(code)
except (requests.RequestException,ValueError) as error:
    st.error(f'Não foi possível obter os dados do Banco Mundial: {error}')
    st.stop()
if mode=='Ranking':
    data=data[data['ISO3'].isin(chosen)]
if data.empty:
    st.warning('Não há dados disponíveis para os países selecionados.')
    st.stop()

if mode=='Ranking':
    years=sorted(data['Ano'].unique(),reverse=True)
    left,right=st.columns([1,1])
    with left:
        year=st.selectbox('Ano de referência',years)
    with right:
        descending=st.selectbox('Ordenação',['Maior para menor','Menor para maior'])=='Maior para menor'
    ranking=data[data['Ano']==year].sort_values(['Valor','País'],ascending=[not descending,True]).reset_index(drop=True)
    ranking.insert(0,'Posição',range(1,len(ranking)+1))
    missing=[universe[c] for c in chosen if c not in set(ranking['ISO3'])]
    st.caption(f'{len(ranking)} de {len(chosen)} países com dados em {year} · Fonte: Banco Mundial · Série: {code}')
    display_unit='US$ bilhões' if code=='NY.GDP.MKTP.CD' else meta['unit']
    head=f'{safe_title.upper()} — {year}'
    table_html=f'<table class="ranking-table"><thead><tr><th>Posição</th><th>País</th><th>{html.escape(display_unit)}</th></tr></thead><tbody>'
    for _,row in ranking.iterrows():
        css=' class="brazil"' if row['ISO3']=='BRA' else ''
        country=html.escape(str(row['País']))
        table_html+=f'<tr{css}><td>{int(row["Posição"])}º</td><td><span class="flag">{flag_image(row['ISO3'], str(row['País']))}</span>{country}</td><td>{nice_number(row["Valor"],code)}</td></tr>'
    table_html+='</tbody></table>'
    st.subheader(head)
    st.markdown(f'<div class="ranking-shell">{table_html}</div>',unsafe_allow_html=True)
    if missing:
        st.warning('Sem dados para o ano escolhido: '+', '.join(sorted(missing)))
    csv=ranking[['Posição','País','Ano','Valor']].to_csv(index=False).encode('utf-8-sig')
    st.download_button('Baixar ranking (CSV)',csv,file_name=f'ranking_{code}_{year}.csv',mime='text/csv')
else:
    st.subheader('Evolução histórica')
    st.caption('Escolha de 1 a 5 países para montar o gráfico. O gráfico começa vazio.')
    options=list(universe)
    selected_history=st.multiselect(
        'Países para comparar (máximo de 5)',
        options,
        default=[],
        format_func=lambda iso:universe[iso],
        max_selections=5,
        key='historical_countries',
    )
    if not selected_history:
        st.info('Selecione os países acima para visualizar a evolução histórica deste indicador.')
    else:
        history_data=data[data['ISO3'].isin(selected_history)]
        if history_data.empty:
            st.warning('Não há dados para os países selecionados.')
        else:
            minyear,maxyear=int(history_data['Ano'].min()),int(history_data['Ano'].max())
            if minyear==maxyear:
                start=end=minyear
                st.caption(f'Apenas {minyear} disponível para esta seleção.')
            else:
                start,end=st.slider('Período',min_value=minyear,max_value=maxyear,value=(max(minyear,maxyear-20),maxyear))
            history=history_data[history_data['Ano'].between(start,end)].sort_values(['País','Ano'])
            if history.empty:
                st.warning('Sem dados no período escolhido.')
            else:
                fig=px.line(history,x='Ano',y='Valor',color='País',markers=True,title=indicator)
                fig.update_layout(yaxis_title=meta['unit'],paper_bgcolor='#f5f7fb')
                if 'Brasil' in history['País'].values:
                    fig.for_each_trace(lambda trace: trace.update(line={'width':4},marker={'size':9}) if trace.name=='Brasil' else None)
                st.plotly_chart(fig,use_container_width=True)
                with st.expander('Ver dados da evolução histórica'):
                    st.dataframe(history[['País','Ano','Valor']],hide_index=True,use_container_width=True)
                csv=history[['País','Ano','Valor']].to_csv(index=False).encode('utf-8-sig')
                st.download_button('Baixar série histórica (CSV)',csv,file_name=f'historico_{code}.csv',mime='text/csv')
st.caption('Observação: dados sujeitos a revisão, anos sem informação não são preenchidos e maior valor nem sempre significa melhor resultado.')
