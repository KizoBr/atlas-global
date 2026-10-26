import html
import re
import io
from datetime import date
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Atlas Global", page_icon="🌎", layout="wide")

LATAM = {'ARG':'Argentina','BOL':'Bolívia','BRA':'Brasil','CHL':'Chile','COL':'Colômbia','CRI':'Costa Rica','CUB':'Cuba','DOM':'República Dominicana','ECU':'Equador','SLV':'El Salvador','GTM':'Guatemala','HTI':'Haiti','HND':'Honduras','MEX':'México','NIC':'Nicarágua','PAN':'Panamá','PRY':'Paraguai','PER':'Peru','URY':'Uruguai','VEN':'Venezuela'}
BRICS = {'BRA':'Brasil','RUS':'Rússia','IND':'Índia','CHN':'China','ZAF':'África do Sul','EGY':'Egito','ETH':'Etiópia','IRN':'Irã','ARE':'Emirados Árabes Unidos','IDN':'Indonésia','SAU':'Arábia Saudita'}
COUNTRIES = dict(sorted((LATAM | BRICS).items(), key=lambda item: item[1]))

# Catálogo com 25 indicadores; 22 possuem integração programada (algumas fontes podem falhar).
INDICATORS = {
    'PIB total': dict(code='NY.GDP.MKTP.CD', unit='US$ correntes', category='Economia e finanças públicas', description='Valor monetário dos bens e serviços finais produzidos dentro do país em um ano, a preços correntes.', formula='PIB = consumo + investimento + gasto do governo + exportações − importações.'),
    'PIB per capita (PPC)': dict(code='NY.GDP.PCAP.PP.KD', unit='dólares internacionais constantes', category='Economia e finanças públicas', description='Produção econômica real por habitante, corrigida pelas diferenças de poder de compra entre países.', formula='PIB real ajustado por PPC ÷ população.'),
    'Crescimento real do PIB': dict(code='NY.GDP.MKTP.KD.ZG', unit='%', category='Economia e finanças públicas', description='Variação percentual anual da produção econômica descontando alterações de preços.', formula='[(PIB real no ano t ÷ PIB real no ano t−1) − 1] × 100.'),
    'Inflação anual': dict(code='FP.CPI.TOTL.ZG', unit='%', category='Economia e finanças públicas', description='Variação média anual dos preços ao consumidor, medida por índice nacional.', formula='Variação percentual anual do índice de preços ao consumidor (método de média anual da fonte).'),
    'Taxa de desemprego': dict(code='SL.UEM.TOTL.ZS', unit='% da força de trabalho', category='Economia e finanças públicas', description='Parcela da força de trabalho sem emprego, disponível e procurando trabalho; série modelada pela OIT.', formula='Desempregados ÷ força de trabalho × 100.'),
    'Produtividade do trabalho': dict(code='labor-productivity-per-hour-pennworldtable', provider='OWID/Penn World Table', unit='dólares internacionais de 2021 por hora', category='Economia e finanças públicas', description='Produção econômica ajustada por preços e poder de compra em relação ao total de horas trabalhadas.', formula='PIB real em PPC ÷ total de horas trabalhadas.'),
    'Dívida pública (% do PIB)': dict(code='GGXWDG_NGDP', provider='FMI', unit='% do PIB', category='Economia e finanças públicas', description='Dívida bruta do governo geral, relativa ao tamanho da economia.', formula='Dívida bruta do governo geral ÷ PIB × 100.'),
    'Carga tributária (% do PIB)': dict(code=None, unit='% do PIB', category='Economia e finanças públicas', description='Receitas tributárias e contribuições sociais obrigatórias conforme metodologia harmonizada a definir.', formula='Receitas tributárias abrangidas ÷ PIB × 100.'),
    'Gasto total do governo (% do PIB)': dict(code='GGX_NGDP', provider='FMI', unit='% do PIB', category='Economia e finanças públicas', description='Despesas totais do governo geral, incluindo serviços, investimentos, transferências e demais funções.', formula='Despesa total do governo geral ÷ PIB × 100.'),
    'Expectativa de vida': dict(code='SP.DYN.LE00.IN', unit='anos', category='Saúde', description='Número médio de anos que um recém-nascido viveria sob as taxas de mortalidade do período.', formula='Estimativa de tábua de vida baseada em taxas de mortalidade por idade; não é uma simples média de idades ao morrer.'),
    'Mortalidade infantil': dict(code='SP.DYN.IMRT.IN', unit='óbitos por 1.000 nascidos vivos', category='Saúde', description='Probabilidade de morrer antes de completar um ano de idade, expressa por mil nascidos vivos.', formula='Probabilidade de óbito antes de 1 ano × 1.000 (estimativa de mortalidade).'),
    'Gastos com saúde (% do PIB)': dict(code='SH.XPD.CHEX.GD.ZS', unit='% do PIB', category='Saúde', description='Despesas correntes com saúde de fontes públicas e privadas, como porcentagem do PIB.', formula='Gastos correntes com saúde ÷ PIB × 100; exclui investimento em capital.'),
    'Gastos com saúde por habitante': dict(code='SH.XPD.CHEX.PC.CD', unit='US$ correntes por pessoa', category='Saúde', description='Gasto corrente com saúde por habitante, em dólares correntes.', formula='Despesas correntes com saúde ÷ população, convertidas para US$ correntes.'),
    'Taxa de alfabetização de adultos': dict(code='SE.ADT.LITR.ZS', unit='% (15 anos ou mais)', category='Educação', description='Proporção da população com 15 anos ou mais capaz de ler e escrever uma declaração curta e simples.', formula='Adultos alfabetizados ÷ população com 15 anos ou mais × 100.'),
    'Gastos públicos com educação (% do PIB)': dict(code='SE.XPD.TOTL.GD.ZS', unit='% do PIB', category='Educação', description='Despesas governamentais em educação, em proporção ao PIB.', formula='Despesa pública com educação ÷ PIB × 100.'),
    'Gasto público por aluno — primário': dict(code='SE.XPD.PRIM.PC.ZS', provider='UNESCO/Banco Mundial (estimativa PPC)', unit='dólares internacionais constantes de 2021 por aluno', category='Educação', description='Estimativa da despesa pública por estudante do ensino primário, expressa em dólares internacionais constantes de 2021 por conversão do indicador UNESCO de gasto por estudante em % do PIB per capita.', formula='(Gasto por aluno como % do PIB per capita ÷ 100) × PIB per capita PPC real constante de 2021, no mesmo ano.'),
    'Gasto público por aluno — secundário': dict(code='SE.XPD.SECO.PC.ZS', provider='UNESCO/Banco Mundial (estimativa PPC)', unit='dólares internacionais constantes de 2021 por aluno', category='Educação', description='Estimativa da despesa pública por estudante do ensino secundário, expressa em dólares internacionais constantes de 2021 por conversão do indicador UNESCO de gasto por estudante em % do PIB per capita.', formula='(Gasto por aluno como % do PIB per capita ÷ 100) × PIB per capita PPC real constante de 2021, no mesmo ano.'),
    'Gasto público por aluno — superior': dict(code='SE.XPD.TERT.PC.ZS', provider='UNESCO/Banco Mundial (estimativa PPC)', unit='dólares internacionais constantes de 2021 por aluno', category='Educação', description='Estimativa da despesa pública por estudante do ensino superior, expressa em dólares internacionais constantes de 2021 por conversão do indicador UNESCO de gasto por estudante em % do PIB per capita.', formula='(Gasto por aluno como % do PIB per capita ÷ 100) × PIB per capita PPC real constante de 2021, no mesmo ano.'),
    'Índice de Desenvolvimento Humano (IDH)': dict(code='hdi', provider='PNUD', unit='índice de 0 a 1', category='Desenvolvimento social', description='Índice sintético de saúde, educação e renda elaborado pelo PNUD.', formula='Média geométrica dos índices normalizados de saúde, educação e renda.'),
    'Índice IRBES': dict(code=None, unit='índice metodológico do IBPT', category='Desenvolvimento social', description='Índice de Retorno de Bem-Estar à Sociedade do IBPT, que relaciona carga tributária e desenvolvimento humano.', formula='Cálculo específico publicado pelo IBPT; consultar a metodologia da edição antes de comparar.'),
    'Índice de Gini': dict(code='SI.POV.GINI', unit='pontos (0 a 100)', category='Desenvolvimento social', description='Mede a desigualdade na distribuição de renda ou consumo nas pesquisas domiciliares da fonte.', formula='Gini = área entre linha de igualdade e curva de Lorenz ÷ área total abaixo da linha de igualdade × 100.'),
    'Taxa de pobreza': dict(code='SI.POV.UMIC', unit='% da população', category='Desenvolvimento social', description='Parcela da população que vive com renda ou consumo inferior a US$ 8,30 por pessoa ao dia (PPC de 2021). É uma linha internacional de pobreza para países de renda média-alta, mais ampla que a de pobreza extrema.', formula='(Pessoas com renda ou consumo por pessoa abaixo de US$ 8,30/dia, PPC de 2021 ÷ população pesquisada) × 100.'),
    'Pessoas em situação de fome (subalimentação)': dict(code='SN.ITK.DEFC.ZS', unit='% da população', category='Desenvolvimento social', description='Parcela estimada da população cujo consumo habitual de energia alimentar é insuficiente para sustentar uma vida ativa e saudável, segundo a FAO.', formula='Estimativa estatística da proporção abaixo da necessidade mínima de energia alimentar, baseada na distribuição do consumo de energia alimentar; não é contagem direta de indivíduos.'),
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
    'Taxa de pobreza': 'Permite comparar a proporção de pessoas abaixo de uma linha internacional de pobreza mais ampla, inclusive em economias de renda média. Não equivale às linhas nacionais de pobreza e não mede a profundidade da privação.',
    'Pessoas em situação de fome (subalimentação)': 'Acompanha a insuficiência persistente de energia alimentar na população e contribui para avaliar segurança alimentar entre países e ao longo do tempo. Não mede diretamente cada episódio de fome ou a qualidade nutricional da dieta.',
    'Índice de Gini': 'Quantifica o grau de desigualdade na distribuição de renda ou consumo. Valores mais altos correspondem a maior desigualdade; pesquisas nacionais podem diferir em cobertura e conceito.',
    'Índice Global de Crime Organizado': 'Avalia dimensões de mercados e atores criminosos, úteis para comparações internacionais. Trata-se de índice composto de avaliação, não de uma contagem direta de crimes.',
    'Homicídios intencionais (violência letal)': 'Compara a intensidade da violência letal entre países considerando o tamanho populacional. A medida é nacional e não representa apenas a violência urbana.',
}


# Contexto metodológico adicional, exibido de forma compacta.
DETAILS = {'PIB total': 'É registrado pelo critério territorial: conta a produção realizada no país, independentemente da nacionalidade das empresas. A ótica da despesa soma consumo das famílias, investimento, consumo do governo e exportações líquidas. Para avaliar bem-estar médio ou evolução real, complemente com PIB por habitante e séries a preços constantes.', 'PIB per capita (PPC)': 'A paridade de poder de compra ajusta diferenças de níveis de preços, permitindo comparar o volume real de bens e serviços entre economias. A série escolhida é expressa em dólares internacionais constantes; o ano-base depende da publicação da fonte. Como é uma média, não informa desigualdade, qualidade dos serviços públicos ou renda disponível das famílias.', 'Crescimento real do PIB': 'Compara o volume de produção em anos consecutivos, removendo a variação de preços por meio de deflatores. Taxas positivas indicam expansão e taxas negativas indicam contração. Um crescimento expressivo após uma recessão pode refletir recuperação de uma base baixa, e não necessariamente aceleração sustentada.', 'Inflação anual': 'O índice de preços ao consumidor acompanha a variação do custo de uma cesta representativa de bens e serviços. A série anual mede a variação média do índice ao longo do ano, que pode diferir da inflação acumulada em doze meses até dezembro. A cesta e os pesos variam entre países.', 'Taxa de desemprego': 'A força de trabalho reúne pessoas ocupadas e desempregadas; quem está fora dela não entra no denominador. Os dados internacionais harmonizados podem incluir estimativas modeladas pela OIT. Por isso, compare junto com participação no mercado de trabalho, informalidade e horas trabalhadas.', 'Produtividade do trabalho': 'O numerador usa valor adicionado ou PIB em termos reais, ajustado por paridade de poder de compra; o denominador é o total de horas efetivamente trabalhadas. Ganhos de produtividade podem decorrer de capital, tecnologia, organização ou composição setorial, não apenas do esforço individual. A cobertura e o método de harmonização ainda serão definidos na integração da fonte.', 'Dívida pública (% do PIB)': 'O governo geral abrange os níveis de governo e suas entidades cobertas pela metodologia fiscal. A dívida bruta contabiliza obrigações sem descontar integralmente ativos financeiros. O indicador é um estoque relativo ao PIB anual; juros, moeda, vencimentos e capacidade de arrecadação são fundamentais para avaliar risco fiscal.', 'Carga tributária (% do PIB)': 'A abrangência precisa incluir regras consistentes para impostos, taxas e contribuições sociais obrigatórias, pois diferentes fontes usam conceitos distintos. O indicador aproxima o peso da tributação na economia, mas não mostra quem paga, a progressividade nem a qualidade dos serviços financiados. A fonte harmonizada será definida antes da comparação.', 'Gasto total do governo (% do PIB)': 'O governo geral inclui despesas de diferentes esferas administrativas conforme as contas públicas da fonte. A medida incorpora remuneração, benefícios sociais, juros e investimentos, conforme o padrão estatístico adotado. Não é uma medida isolada do tamanho da burocracia, da eficiência ou da qualidade dos serviços públicos.', 'Expectativa de vida': 'É um indicador de período obtido pela aplicação das taxas correntes de mortalidade por idade a uma população hipotética. Não é uma previsão exata da duração de vida de quem nasceu naquele ano. Pode variar por crises sanitárias e mudanças de mortalidade, mesmo sem alterações imediatas na estrutura etária.', 'Mortalidade infantil': 'Apresenta a probabilidade estimada de morte antes do primeiro aniversário para cada mil nascimentos vivos. É sensível a condições materno-infantis, saneamento, atenção pré-natal e acesso ao sistema de saúde. As estimativas internacionais também buscam corrigir sub-registro e diferenças na qualidade dos registros vitais.', 'Gastos com saúde (% do PIB)': 'Abrange gastos correntes de governos, seguros, empresas e famílias com serviços e bens de saúde. Não equivale à despesa exclusivamente pública, nem incorpora necessariamente a formação de capital. Uma participação maior pode refletir prioridade de gasto, preços elevados, envelhecimento ou ineficiência, exigindo análise contextual.', 'Gastos com saúde por habitante': 'Divide o gasto corrente total em saúde pelo número de residentes e converte o resultado para dólares correntes. Facilita a comparação de escala financeira, mas taxas de câmbio e diferenças de preços afetam o resultado. Uma série PPC pode ser mais adequada para comparação do volume de serviços comprados.', 'Taxa de alfabetização de adultos': 'Considera pessoas de 15 anos ou mais e a capacidade de ler e escrever uma frase simples com compreensão, segundo a definição operacional da fonte. Pesquisas e censos podem utilizar perguntas e periodicidades diferentes. A medida não captura integralmente proficiência leitora, escolaridade ou alfabetização funcional.', 'Gastos públicos com educação (% do PIB)': 'Compara despesas governamentais em educação, de acordo com o escopo da fonte, com o valor total da produção econômica. Pode incluir diferentes níveis de ensino e despesas correntes e de capital. Não indica automaticamente qualidade, eficiência ou equidade do sistema educacional.', 'Gasto público por aluno — primário': 'Divide o gasto público destinado ao ensino primário pelo número de estudantes do mesmo nível. Para comparações internacionais robustas, ambos precisam seguir o mesmo recorte institucional e período. Valores em PPC constantes ajudam a reduzir distorções de preços, mas não asseguram comparabilidade de custos ou resultados.', 'Gasto público por aluno — secundário': 'Relaciona a despesa pública alocada ao ensino secundário às matrículas nesse nível. É importante verificar se o país inclui ensino geral e técnico, instituições privadas subsidiadas e investimentos. Não é um indicador direto de aprendizagem ou de eficiência de gasto.', 'Gasto público por aluno — superior': 'Relaciona os recursos públicos do ensino superior ao contingente de estudantes considerado na fonte. Pesquisa universitária, bolsas, hospitais universitários e critérios de matrícula podem alterar comparações. A série em PPC e valores constantes requer validação específica na fonte UNESCO.', 'Índice de Desenvolvimento Humano (IDH)': 'A saúde é representada pela expectativa de vida ao nascer; a educação combina anos médios e esperados de escolaridade; e a dimensão econômica usa a renda nacional bruta per capita em PPC. Os componentes passam por normalização e são agregados por média geométrica. O IDH não capta diretamente desigualdades internas, liberdade, violência ou sustentabilidade ambiental.', 'Índice IRBES': 'O indicador do IBPT busca relacionar tributação e retorno percebido em bem-estar por meio de sua metodologia própria. Não é um índice universal calculado anualmente para todos os países. As séries devem respeitar exatamente as edições, a amostra e a fórmula que o IBPT efetivamente publicar; não serão atribuídos valores para países ausentes.', 'Taxa de pobreza': 'A linha de US$ 8,30 por pessoa ao dia (PPC de 2021) representa um padrão internacional de referência para economias de renda média-alta. Os dados usam renda ou consumo observados em pesquisas domiciliares. Diferem das linhas nacionais de pobreza e podem apresentar intervalos sem dados; revisões do Banco Mundial podem alterar séries históricas.', 'Pessoas em situação de fome (subalimentação)': 'O indicador da FAO, conhecido como prevalência de subalimentação, é uma estimativa baseada na disponibilidade ou consumo de calorias, na desigualdade de acesso alimentar e nas necessidades energéticas da população. Não equivale à insegurança alimentar moderada ou grave. Valores próximos ao limite inferior podem ser apresentados pela fonte como inferiores a 2,5%, exigindo cautela na comparação.', 'Índice de Gini': 'É derivado da curva de Lorenz, que ordena a população do menor para o maior valor de renda ou consumo e calcula sua parcela acumulada. Zero significa igualdade perfeita e cem representa desigualdade máxima teórica. A interpretação entre países exige verificar renda versus consumo, rendimentos brutos versus líquidos e qualidade das pesquisas domiciliares.', 'Índice Global de Crime Organizado': 'O índice publicado pela Global Initiative Against Transnational Organized Crime combina dimensões de mercados ilícitos e atores criminosos, a partir de critérios e avaliação estruturada. As pontuações não equivalem a quantidade de crimes registrados. O projeto mostrará apenas edições oficiais disponíveis, sem preencher anos intermediários.', 'Homicídios intencionais (violência letal)': 'O numerador considera mortes decorrentes de homicídio intencional segundo definições internacionais; o denominador é a população do período. É uma medida de violência letal comparável por tamanho populacional, mas não cobre integralmente roubos, agressões ou violência não letal. Além disso, é uma taxa nacional: não separa áreas urbanas e rurais.'}

st.markdown('''<style>
.stApp {background: #f5f7fb; color: #17233b;}
.block-container {max-width: 1260px; padding-top: 1.5rem;}
.hero {background:linear-gradient(125deg,#101e3c,#243e68);border-radius:18px;padding:23px 25px 19px;margin-bottom:12px;color:white;text-align:center;}
.hero h1{font-size:clamp(2.4rem,5vw,3.45rem);font-weight:850;letter-spacing:-.045em;line-height:1.1;margin:0;color:#fff;}
.hero p{color:#d7e2f2;margin:8px 0 0;font-size:.95rem;}
.hero .byline {font-size:.7rem;font-style:italic;font-weight:400;letter-spacing:.03em;color:#c5d4ed;margin-top:5px;}
.indicator-head {border-left:4px solid #1a4d89;background:white;padding:13px 18px;border-radius:10px;margin:8px 0 13px;box-shadow:0 4px 18px #17233b12;}
.indicator-head h2 {font-size:1.48rem;line-height:1.2;margin:4px 0 8px;color:#142c52;}
.eyebrow {text-transform:uppercase;font-size:.69rem;letter-spacing:.09em;font-weight:800;color:#23599b;}
.indicator-head p{margin:5px 0 8px;color:#293c58;font-size:.89rem;line-height:1.5;}
.indicator-head .detail {font-size:.86rem;color:#40516e;line-height:1.5;}
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
/* Azul-marinho no grupo e modelo de visualização selecionados. */
section[data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"] {accent-color:#173d72!important;}
section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radio"][aria-checked="true"] {background-color:#173d72!important;border-color:#173d72!important;box-shadow:inset 0 0 0 4px #fff!important;}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {color:#173d72!important;font-weight:700;}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has([aria-checked="true"]) {color:#173d72!important;font-weight:700;}
section[data-testid="stSidebar"] [data-baseweb="radio"] [aria-checked="true"] {border-color:#173d72!important;background-color:#173d72!important;}
section[data-testid="stSidebar"] [data-baseweb="radio"] [aria-checked="true"]::after {background:#fff!important;}


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

# Fontes adicionais: IMF DataMapper e PNUD (HDR 2025, série 1990–2023).
# Cada integração devolve exatamente as mesmas colunas do Banco Mundial.
DATA_COLUMNS = ['ISO3', 'País', 'Ano', 'Valor']
IMF_ENDPOINTS = ['https://www.imf.org/external/datamapper/api/v2', 'https://www.imf.org/external/datamapper/api/v1']
UNDP_HDI_CSV = 'https://hdr.undp.org/sites/default/files/2025_HDR/HDR25_Composite_indices_complete_time_series.csv'

@st.cache_data(ttl=14400, show_spinner=False)
def load_imf(code):
    if code not in ('GGXWDG_NGDP', 'GGX_NGDP'):
        raise ValueError('Indicador fiscal não reconhecido.')
    # API do DataMapper: testar a versão atual e a rota anterior. O servidor
    # pode bloquear requisições de provedores de nuvem (HTTP 403).
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; AtlasGlobal/1.0; public data dashboard)',
        'Accept': 'application/json',
    }
    failures = []
    for endpoint in IMF_ENDPOINTS:
        try:
            response = requests.get(f'{endpoint}/{code}', timeout=35, headers=headers)
            response.raise_for_status()
            payload = response.json()
            values = payload.get('values', {}).get(code, {})
            if not isinstance(values, dict) or not values:
                failures.append(f'{endpoint}: série não encontrada')
                continue
            rows = []
            for iso, years in values.items():
                if iso not in COUNTRIES or not isinstance(years, dict):
                    continue
                for year, value in years.items():
                    try:
                        y = int(year)
                        v = float(value)
                        if pd.notna(v) and 1980 <= y <= date.today().year:
                            rows.append({'ISO3': iso, 'País': COUNTRIES[iso], 'Ano': y, 'Valor': v})
                    except (ValueError, TypeError, OverflowError):
                        continue
            if rows:
                return pd.DataFrame(rows, columns=DATA_COLUMNS)
            failures.append(f'{endpoint}: nenhum país com valor válido')
        except (requests.RequestException, ValueError, TypeError) as err:
            failures.append(f'{endpoint}: {err}')
    if any('403' in msg for msg in failures):
        raise ValueError(
            'O servidor do FMI recusou o acesso do aplicativo (HTTP 403) '
            'nas rotas consultadas. Trata-se de uma restrição externa, '
            'não de um erro de cálculo do ranking. '
            'Será necessário usar um arquivo oficial do WEO ou outra '
            'integração aprovada para disponibilizar esta série. '
            'Consulte: https://data.imf.org/datasets/WEO'
        )
    raise ValueError('O FMI não retornou dados válidos. ' + ' | '.join(failures))

@st.cache_data(ttl=86400, show_spinner=False)
def load_undp_hdi():
    response = requests.get(UNDP_HDI_CSV, timeout=50)
    response.raise_for_status()
    # O arquivo HDR 2025 possui 1 coluna por ano (hdi_1990, ...).
    # O formato pode ser alterado em edições posteriores, por isso validamos.
    df = pd.read_csv(io.BytesIO(response.content), encoding='cp1252', low_memory=False)
    df.columns = df.columns.str.strip()
    if 'iso3' not in df.columns:
        raise ValueError('Formato do CSV do PNUD alterado: coluna iso3 não encontrada.')
    cols = [col for col in df.columns if re.fullmatch(r'hdi_\d{4}', col)]
    if not cols:
        raise ValueError('O arquivo do PNUD não contém colunas hdi_ANO.')
    df['iso3'] = df['iso3'].astype(str).str.strip().str.upper()
    df = df.loc[df['iso3'].isin(COUNTRIES), ['iso3'] + cols]
    long = df.melt(id_vars=['iso3'], var_name='indicador_ano', value_name='Valor')
    long['Ano'] = long['indicador_ano'].str[-4:].astype(int)
    long['Valor'] = pd.to_numeric(long['Valor'], errors='coerce')
    long = long.dropna(subset=['Valor'])
    long = long[long['Valor'].between(0, 1)]
    long['ISO3'] = long['iso3']
    long['País'] = long['ISO3'].map(COUNTRIES)
    if long.empty:
        raise ValueError('Nenhum valor de IDH válido encontrado para o catálogo de países.')
    return long[DATA_COLUMNS].reset_index(drop=True)

@st.cache_data(ttl=86400, show_spinner=False)
def load_productivity():
    """Série de produtividade real/hora da Penn World Table via OWID Grapher."""
    url = 'https://ourworldindata.org/grapher/labor-productivity-per-hour-pennworldtable.csv'
    response = requests.get(url, timeout=55, headers={'User-Agent': 'AtlasGlobal/1.0 (public research dashboard)'})
    response.raise_for_status()
    df = pd.read_csv(io.BytesIO(response.content), low_memory=False)
    required = {'Entity', 'Code', 'Year'}
    if not required.issubset(df.columns):
        raise ValueError('Formato da base de produtividade alterado: colunas de país/ano ausentes.')
    metric_cols = [c for c in df.columns if c not in ('Entity','Code','Year')]
    if len(metric_cols) != 1:
        raise ValueError('Esperada uma coluna numérica de produtividade; verifique o formato da fonte.')
    df['ISO3'] = df['Code'].astype(str).str.upper()
    df = df[df['ISO3'].isin(COUNTRIES)].copy()
    df['Ano'] = pd.to_numeric(df['Year'], errors='coerce')
    df['Valor'] = pd.to_numeric(df[metric_cols[0]], errors='coerce')
    df = df.dropna(subset=['Ano', 'Valor'])
    df = df[df['Valor'] >= 0]
    df['Ano'] = df['Ano'].astype(int)
    df['País'] = df['ISO3'].map(COUNTRIES)
    result = df[DATA_COLUMNS].drop_duplicates(['ISO3','Ano']).sort_values(['ISO3','Ano'])
    if result.empty:
        raise ValueError('Nenhuma observação de produtividade disponível para os países selecionados.')
    return result.reset_index(drop=True)

@st.cache_data(ttl=86400, show_spinner=False)
def load_student_spending(ratio_code):
    """Gasto por aluno PPC 2021 derivado de UNESCO %PIB per capita × PIB per capita PPC real.

    Conversão contábil, NÃO série direta UIS de gastos por aluno em PPP.
    Dados de gasto por aluno do UIS disponibilizados pelo Banco Mundial podem terminar em 2018.
    """
    allowed = {'SE.XPD.PRIM.PC.ZS', 'SE.XPD.SECO.PC.ZS', 'SE.XPD.TERT.PC.ZS'}
    if ratio_code not in allowed:
        raise ValueError('Nível educacional não reconhecido.')
    ratio = load_indicator(ratio_code)
    ppp = load_indicator('NY.GDP.PCAP.PP.KD')
    if ratio.empty or ppp.empty:
        return pd.DataFrame(columns=DATA_COLUMNS)
    joined = ratio[['ISO3','Ano','Valor']].merge(
        ppp[['ISO3','Ano','Valor']], on=['ISO3','Ano'], how='inner', suffixes=('_ratio','_ppp'))
    joined['Valor'] = joined['Valor_ratio'] * joined['Valor_ppp'] / 100.0
    joined = joined[joined['Valor'].notna() & (joined['Valor'] >= 0)]
    joined['País'] = joined['ISO3'].map(COUNTRIES)
    result = joined[DATA_COLUMNS].sort_values(['ISO3','Ano'])
    if result.empty:
        raise ValueError('Não há anos coincidentes entre gasto por aluno e PIB PPC para esses países.')
    return result.reset_index(drop=True)

def load_data(meta):
    provider = meta.get('provider', 'Banco Mundial')
    if provider == 'FMI':
        return load_imf(meta['code'])
    if provider == 'PNUD':
        return load_undp_hdi()
    if provider == 'OWID/Penn World Table':
        return load_productivity()
    if provider == 'UNESCO/Banco Mundial (estimativa PPC)':
        return load_student_spending(meta['code'])
    return load_indicator(meta['code'])

st.markdown('<div class="hero"><h1>🌎 Atlas Global</h1><p class="byline">Criado por Rafael Pires Marciano</p><p>Indicadores internacionais · América Latina e BRICS · Rankings e séries históricas</p></div>',unsafe_allow_html=True)
st.caption('Catálogo: 25 indicadores · 22 com integração programada · 3 ainda pendentes. A disponibilidade depende de cada fonte.')

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
    group=st.radio('Grupo de países', ['Todos', 'América Latina', 'BRICS', 'Personalizado'])
    # Para os grupos prontos, todos os países integrantes entram automaticamente no ranking.
    # A pesquisa e escolha individual aparecem somente no modo Personalizado.
    universe=(LATAM if group=='América Latina' else
              BRICS if group=='BRICS' else COUNTRIES)
    mode=st.radio('Visualização', ['Ranking', 'Evolução histórica'])
    if group=='Personalizado':
        st.caption('Pesquise pelo nome e escolha os países que deseja comparar.')
        chosen_custom=st.multiselect(
            'Buscar e selecionar países',
            options=list(COUNTRIES),
            default=[],
            format_func=lambda iso: COUNTRIES[iso],
            placeholder='Digite o nome de um país...',
            key='custom_country_selection',
        )
        st.caption(f'{len(chosen_custom)} país(es) selecionado(s).')
    else:
        chosen_custom=[]
    chosen=(chosen_custom if group=='Personalizado' else list(universe)) if mode=='Ranking' else []
    if mode=='Evolução histórica':
        st.caption('Escolha até cinco países acima do gráfico.')

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
safe_detail=html.escape(DETAILS[indicator])
st.markdown(f'<div class="indicator-head"><div class="eyebrow">Indicador selecionado</div><h2>{safe_title}</h2><p><strong>O que é:</strong> {safe_desc}</p><p><strong>Para que serve:</strong> {safe_utility}</p><p class="detail"><strong>Interpretação e limitações:</strong> {safe_detail}</p><div class="formula"><strong>Cálculo:</strong> {safe_formula}</div></div>',unsafe_allow_html=True)

if mode=='Ranking' and not chosen:
    st.warning('No grupo Personalizado, selecione ao menos um país no menu lateral.')
    st.stop()
if meta['code'] is None:
    st.info('📚 Indicador do catálogo ainda sem integração confirmada à fonte oficial. Não exibimos dados ou rankings simulados.')
    st.caption('Próxima etapa: integrar a fonte específica, validar unidades, anos e cobertura por país.')
    st.stop()

code=meta['code']
provider=meta.get('provider', 'Banco Mundial')
try:
    with st.spinner(f'Consultando os dados: {provider}...'):
        data=load_data(meta)
except (requests.RequestException, ValueError, pd.errors.ParserError, UnicodeError, KeyError) as error:
    st.error(f'Não foi possível obter os dados de {provider}: {error}')
    st.info('A fonte pode estar temporariamente indisponível ou ter alterado seu formato. Os demais indicadores continuam acessíveis.')
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
    missing=[COUNTRIES[c] for c in chosen if c not in set(ranking['ISO3'])]
    st.caption(f'{len(ranking)} de {len(chosen)} países com dados em {year} · Fonte: {provider} · Série: {code}')
    if provider == 'FMI' and int(year) >= date.today().year:
        st.caption('FMI: valores do ano corrente podem ser estimativas ou projeções, conforme a edição disponível.')
    if provider == 'PNUD':
        st.caption('PNUD: série harmonizada do Relatório de Desenvolvimento Humano 2025, com observações de 1990 a 2023.')
    if provider == 'UNESCO/Banco Mundial (estimativa PPC)':
        st.caption('Estimativa calculada: (gasto público por aluno em % do PIB per capita ÷ 100) × PIB per capita PPC constante de 2021, no mesmo ano. Cobertura histórica pode terminar em 2018. Não é uma série direta da UNESCO em PPP.')
    if provider == 'OWID/Penn World Table':
        st.caption('Produtividade real por hora trabalhada; Penn World Table via Our World in Data, dólares internacionais de 2021.')
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
    options=(chosen_custom if group=='Personalizado' else list(universe))
    if group=='Personalizado' and not options:
        st.info('Selecione primeiro os países no menu lateral para disponibilizá-los no gráfico.')
    selected_history=st.multiselect(
        'Países para comparar (máximo de 5)',
        options,
        default=[],
        format_func=lambda iso:COUNTRIES[iso],
        max_selections=5,
        key='historical_countries',
    )
    selected_history=[iso for iso in selected_history if iso in options]
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
                st.caption(f'Fonte: {provider} · Série: {code}' + (' · HDR 2025 (1990–2023)' if provider == 'PNUD' else ''))
                if provider == 'UNESCO/Banco Mundial (estimativa PPC)':
                    st.caption('Valor derivado das séries anuais de gasto por aluno/PIB per capita e PIB PPC constante (mesmo ano).')
                if 'Brasil' in history['País'].values:
                    fig.for_each_trace(lambda trace: trace.update(line={'width':4},marker={'size':9}) if trace.name=='Brasil' else None)
                st.plotly_chart(fig,use_container_width=True)
                with st.expander('Ver dados da evolução histórica'):
                    st.dataframe(history[['País','Ano','Valor']],hide_index=True,use_container_width=True)
                csv=history[['País','Ano','Valor']].to_csv(index=False).encode('utf-8-sig')
                st.download_button('Baixar série histórica (CSV)',csv,file_name=f'historico_{code}.csv',mime='text/csv')
st.caption('Observação: dados sujeitos a revisão, anos sem informação não são preenchidos e maior valor nem sempre significa melhor resultado.')
