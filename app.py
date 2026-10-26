import html
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

st.markdown('''<style>
.stApp {background: #f5f7fb; color: #17233b;}
.block-container {max-width: 1260px; padding-top: 1.6rem;}
.hero {background:linear-gradient(125deg,#101e3c,#243e68);border-radius:18px;padding:24px 28px;margin-bottom:20px;color:white;}
.hero h1{font-size:2.1rem;margin:0;color:#fff;letter-spacing:.01em;}
.hero p{color:#d7e2f2;margin:7px 0 0;}
.indicator-head {border-left:6px solid #d3a83d;background:white;padding:18px 22px;border-radius:10px;margin:10px 0 16px;box-shadow:0 4px 18px #17233b0b;}
.indicator-head h2 {font-size:1.72rem;line-height:1.2;margin:5px 0;color:#17233b;}
.eyebrow {text-transform:uppercase;font-size:.77rem;letter-spacing:.13em;font-weight:750;color:#8a6b20;}
.indicator-head p{margin:6px 0;color:#33415a;}
.formula {font-size:.93rem;background:#f3f5fa;padding:9px 11px;border-radius:7px;margin-top:10px;color:#253451;}
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
.flag{display:inline-block;margin-right:12px;font-size:1.22rem;}
.smallnote{font-size:.88rem;color:#66728b;margin:9px 0 4px;}
div[data-testid="stSelectbox"] label p {font-size:1.08rem;font-weight:800;color:#182b4b;}
</style>''',unsafe_allow_html=True)

FLAG_OVERRIDE = {'CHN':'🇨🇳','IND':'🇮🇳','BRA':'🇧🇷','RUS':'🇷🇺','ZAF':'🇿🇦','EGY':'🇪🇬','ETH':'🇪🇹','IRN':'🇮🇷','ARE':'🇦🇪','IDN':'🇮🇩','SAU':'🇸🇦'}
def flag(iso3):
    iso2 = {'ARG':'AR','BOL':'BO','BRA':'BR','CHL':'CL','COL':'CO','CRI':'CR','CUB':'CU','DOM':'DO','ECU':'EC','SLV':'SV','GTM':'GT','HTI':'HT','HND':'HN','MEX':'MX','NIC':'NI','PAN':'PA','PRY':'PY','PER':'PE','URY':'UY','VEN':'VE','RUS':'RU','IND':'IN','CHN':'CN','ZAF':'ZA','EGY':'EG','ETH':'ET','IRN':'IR','ARE':'AE','IDN':'ID','SAU':'SA'}.get(iso3)
    return ''.join(chr(127397+ord(char)) for char in iso2) if iso2 else '🌐'

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

categories=list(dict.fromkeys(item['category'] for item in INDICATORS.values()))
category=st.selectbox('1. ESCOLHA A CATEGORIA',categories)
choices=[name for name,meta in INDICATORS.items() if meta['category']==category]
indicator=st.selectbox('2. ESCOLHA O INDICADOR',choices)
meta=INDICATORS[indicator]

with st.sidebar:
    st.header('Configurações')
    group=st.radio('Grupo de países',['Todos','América Latina','BRICS'])
    universe=COUNTRIES if group=='Todos' else LATAM if group=='América Latina' else BRICS
    chosen=st.multiselect('Países',list(universe),default=list(universe),format_func=lambda iso:universe[iso])
    mode=st.radio('Visualização',['Ranking','Evolução histórica'])

safe_title=html.escape(indicator)
safe_desc=html.escape(meta['description'])
safe_formula=html.escape(meta['formula'])
st.markdown(f'<div class="indicator-head"><div class="eyebrow">Indicador selecionado</div><h2>{safe_title}</h2><p>{safe_desc}</p><div class="formula"><strong>Cálculo / metodologia:</strong> {safe_formula}</div></div>',unsafe_allow_html=True)

if not chosen:
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
        table_html+=f'<tr{css}><td>{int(row["Posição"])}º</td><td><span class="flag">{flag(row["ISO3"])}</span>{country}</td><td>{nice_number(row["Valor"],code)}</td></tr>'
    table_html+='</tbody></table>'
    st.subheader(head)
    st.markdown(f'<div class="ranking-shell">{table_html}</div>',unsafe_allow_html=True)
    if missing:
        st.warning('Sem dados para o ano escolhido: '+', '.join(sorted(missing)))
    if not ranking.empty:
        colors=['#c89c2f' if iso=='BRA' else '#32557e' for iso in ranking['ISO3']]
        fig=px.bar(ranking,x='Valor',y='País',orientation='h',title=f'{indicator} — {year}')
        fig.update_traces(marker_color=colors)
        fig.update_layout(yaxis={'categoryorder':'array','categoryarray':list(reversed(ranking['País']))},height=max(400,32*len(ranking)),paper_bgcolor='#f5f7fb')
        st.plotly_chart(fig,use_container_width=True)
    csv=ranking[['Posição','País','Ano','Valor']].to_csv(index=False).encode('utf-8-sig')
    st.download_button('Baixar ranking (CSV)',csv,file_name=f'ranking_{code}_{year}.csv',mime='text/csv')
else:
    minyear,maxyear=int(data['Ano'].min()),int(data['Ano'].max())
    if minyear==maxyear:
        start=end=minyear
        st.caption(f'Apenas {minyear} disponível para esta seleção.')
    else:
        start,end=st.slider('Período',min_value=minyear,max_value=maxyear,value=(max(minyear,maxyear-20),maxyear))
    history=data[data['Ano'].between(start,end)].sort_values(['País','Ano'])
    if history.empty:
        st.warning('Sem dados no período escolhido.')
    else:
        fig=px.line(history,x='Ano',y='Valor',color='País',markers=True,title=indicator)
        fig.update_layout(yaxis_title=meta['unit'],paper_bgcolor='#f5f7fb')
        if 'Brasil' in history['País'].values:
            fig.for_each_trace(lambda trace: trace.update(line={'width':4},marker={'size':9}) if trace.name=='Brasil' else None)
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(history[['País','Ano','Valor']],hide_index=True,use_container_width=True)
        csv=history[['País','Ano','Valor']].to_csv(index=False).encode('utf-8-sig')
        st.download_button('Baixar série histórica (CSV)',csv,file_name=f'historico_{code}.csv',mime='text/csv')
st.caption('Observação: dados sujeitos a revisão, anos sem informação não são preenchidos e maior valor nem sempre significa melhor resultado.')
