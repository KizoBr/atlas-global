import io
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='Atlas Global', page_icon='🌎', layout='wide')

LATAM = {'ARG':'Argentina','BOL':'Bolívia','BRA':'Brasil','CHL':'Chile','COL':'Colômbia','CRI':'Costa Rica','CUB':'Cuba','DOM':'República Dominicana','ECU':'Equador','SLV':'El Salvador','GTM':'Guatemala','HTI':'Haiti','HND':'Honduras','MEX':'México','NIC':'Nicarágua','PAN':'Panamá','PRY':'Paraguai','PER':'Peru','URY':'Uruguai','VEN':'Venezuela'}
BRICS = {'BRA':'Brasil','RUS':'Rússia','IND':'Índia','CHN':'China','ZAF':'África do Sul','EGY':'Egito','ETH':'Etiópia','IRN':'Irã','ARE':'Emirados Árabes Unidos','IDN':'Indonésia','SAU':'Arábia Saudita'}
COUNTRIES = dict(sorted((LATAM | BRICS).items(), key=lambda x:x[1]))
INDICATORS = {
 'PIB total (US$ correntes)': ('NY.GDP.MKTP.CD','US$'),
 'PIB per capita (PPC, US$ internacionais constantes)': ('NY.GDP.PCAP.PP.KD','US$ internacionais constantes'),
 'Crescimento real do PIB (%)': ('NY.GDP.MKTP.KD.ZG','%'),
 'Inflação anual (%)': ('FP.CPI.TOTL.ZG','%'),
 'Taxa de desemprego (%)': ('SL.UEM.TOTL.ZS','%'),
 'Expectativa de vida (anos)': ('SP.DYN.LE00.IN','anos'),
 'Mortalidade infantil (por 1.000 nascidos vivos)': ('SP.DYN.IMRT.IN','por 1.000'),
 'Gastos correntes com saúde (% PIB)': ('SH.XPD.CHEX.GD.ZS','% PIB'),
 'Gastos correntes com saúde por habitante (US$)': ('SH.XPD.CHEX.PC.CD','US$'),
 'Alfabetização de adultos (%)': ('SE.ADT.LITR.ZS','%'),
 'Gasto público com educação (% PIB)': ('SE.XPD.TOTL.GD.ZS','% PIB'),
 'Índice de Gini (0–100)': ('SI.POV.GINI','pontos'),
 'Homicídios intencionais (por 100 mil habitantes)': ('VC.IHR.PSRC.P5','por 100 mil'),
}

@st.cache_data(ttl=86400, show_spinner=False)
def load_indicator(code):
    url=f'https://api.worldbank.org/v2/country/{";".join(COUNTRIES)}/indicator/{code}'
    resp=requests.get(url,params={'format':'json','per_page':20000,'date':'1960:2026'},timeout=40)
    resp.raise_for_status()
    payload=resp.json()
    if not isinstance(payload,list) or len(payload)<2 or payload[1] is None:
        raise ValueError('A fonte não retornou dados para este indicador.')
    records=[]
    for row in payload[1]:
        iso=row.get('countryiso3code')
        if iso in COUNTRIES and row.get('value') is not None:
            records.append({'ISO3':iso,'País':COUNTRIES[iso],'Ano':int(row['date']),'Valor':float(row['value'])})
    return pd.DataFrame(records,columns=['ISO3','País','Ano','Valor'])

st.title('🌎 Atlas Global')
st.caption('Rankings individuais e séries históricas · América Latina e BRICS · Fonte inicial: Banco Mundial')
st.info('Versão inicial: 13 indicadores conectados ao Banco Mundial. Os outros 10 indicadores serão integrados em etapas posteriores. Dados podem ter lacunas ou revisões.')
with st.sidebar:
    st.header('Filtros')
    group=st.radio('Grupo de países',['Todos','América Latina','BRICS'])
    universe=COUNTRIES if group=='Todos' else LATAM if group=='América Latina' else BRICS
    chosen=st.multiselect('Países',list(universe),default=list(universe),format_func=lambda iso:universe[iso])
    indicator=st.selectbox('Indicador',list(INDICATORS))
    mode=st.radio('Visualização',['Ranking','Evolução histórica'])

if not chosen:
    st.warning('Selecione ao menos um país.')
    st.stop()
code,unit=INDICATORS[indicator]
try:
    with st.spinner('Consultando Banco Mundial...'):
        data=load_indicator(code)
except (requests.RequestException,ValueError) as exc:
    st.error(f'Não foi possível consultar a fonte: {exc}')
    st.stop()
data=data[data.ISO3.isin(chosen)]
if data.empty:
    st.warning('Não há observações disponíveis para a seleção.')
    st.stop()
st.caption(f'Indicador: {code} · Unidade: {unit} · Fonte: Banco Mundial · Atualização automática do cache a cada 24 horas')
if mode=='Ranking':
    years=sorted(data.Ano.unique(),reverse=True)
    year=st.selectbox('Ano de referência',years)
    ascending=st.radio('Ordenação',['Maior para menor','Menor para maior'],horizontal=True)=='Menor para maior'
    result=data[data.Ano==year].sort_values(['Valor','País'],ascending=[ascending,True]).reset_index(drop=True)
    result.insert(0,'Posição',range(1,len(result)+1))
    missing=[universe[c] for c in chosen if c not in set(result.ISO3)]
    st.metric('Países com dados',f'{len(result)} de {len(chosen)}')
    st.dataframe(result[['Posição','País','Ano','Valor']],use_container_width=True,hide_index=True,column_config={'Valor':st.column_config.NumberColumn(format='%.2f')})
    if missing:
        st.warning('Sem dados no ano selecionado: '+', '.join(sorted(missing)))
    if not result.empty:
        fig=px.bar(result,x='Valor',y='País',orientation='h',title=f'{indicator} · {year}')
        fig.update_layout(yaxis={'categoryorder':'array','categoryarray':list(reversed(result['País']))},height=max(450,32*len(result)))
        st.plotly_chart(fig,use_container_width=True)
    st.download_button('Baixar ranking (CSV)',result[['Posição','País','Ano','Valor']].to_csv(index=False).encode('utf-8-sig'),file_name=f'ranking_{code}_{year}.csv',mime='text/csv')
else:
    minyear,maxyear=int(data.Ano.min()),int(data.Ano.max())
    if minyear==maxyear:
        start,end=minyear,maxyear
        st.caption(f'Único ano disponível: {minyear}')
    else:
        start,end=st.slider('Período',min_value=minyear,max_value=maxyear,value=(max(minyear,maxyear-20),maxyear))
    hist=data[data.Ano.between(start,end)].sort_values(['País','Ano'])
    if hist.empty:
        st.warning('Sem dados no período selecionado.')
    else:
        fig=px.line(hist,x='Ano',y='Valor',color='País',markers=True,title=indicator)
        fig.update_layout(yaxis_title=unit)
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(hist[['País','Ano','Valor']],hide_index=True,use_container_width=True)
        st.download_button('Baixar série histórica (CSV)',hist[['País','Ano','Valor']].to_csv(index=False).encode('utf-8-sig'),file_name=f'historico_{code}.csv',mime='text/csv')
st.caption('Aviso: valores representam os dados disponibilizados pela fonte. Indicadores de gasto não medem automaticamente eficiência ou qualidade dos serviços.')
