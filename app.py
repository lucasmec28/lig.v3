import json
import hashlib
from dataclasses import replace
import streamlit as st
import pandas as pd
from lro.models import Connection,Profile,profiles,STEELS,BOLTS,DIAMETERS,THICKNESSES,KGF,VERSION
from lro.engine import evaluate
from lro.examples import presets
from lro.drawing import image_bytes
from lro.report import create_report,display,number,BRAND,LINK
from lro.benchmarks import benchmarks

st.set_page_config(page_title='LRO Ligações',page_icon='🔩',layout='wide')
st.markdown('''<style>
 .block-container {padding-top:2rem;max-width:1500px}
 [data-testid="stMetricValue"] {font-size:1.65rem}
 h1 {letter-spacing:-.045em!important;font-weight:750!important}
 .eyebrow {font-size:.78rem;letter-spacing:.16em;color:#397895;font-weight:700}
 .muted {color:#65798a;font-size:.95rem;line-height:1.5}
 [data-testid="stSidebar"] {background:#f3f6f8}
 div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:12px}
 </style>''',unsafe_allow_html=True)

P=profiles();PRESETS=presets()


def seed(c):
    state=st.session_state
    for key,value in c.__dict__.items():
        if key not in ('beam','support','V','N'):state[key]=value
    state['V_kgf']=c.V/KGF;state['N_kgf']=c.N/KGF
    state['center_plate']=abs(c.plate_top-(c.beam.d-c.hp)/2)<1e-6
    state['db_label']=next(k for k,v in DIAMETERS.items() if abs(c.db-v)<1e-6)
    state['tp_label']=next((k for k,v in THICKNESSES.items() if abs(c.tp-v)<1e-6),'5/16"')
    state['custom_t']=not any(abs(c.tp-v)<1e-6 for v in THICKNESSES.values());state['real_t']=c.tp
    for prefix,p in [('beam',c.beam),('support',c.support)]:
        state[prefix+'_name']=p.name if p.name in P else 'Seção I personalizada'
        for key in ['d','bf','tw','tf','clear']:state[prefix+'_'+key]=float(getattr(p,key))
        state[prefix+'_manual_name']=p.name
    state.pop('report',None)


def load_example():seed(PRESETS[st.session_state['example']])


def import_file():
    # O callback executa antes da criação dos widgets, evitando alterar suas
    # chaves depois de instanciados no mesmo ciclo do Streamlit.
    try:
        uploaded=st.session_state.project_upload
        if uploaded is None:raise ValueError('Selecione um arquivo de projeto.')
        if len(uploaded.getvalue())>200_000:raise ValueError('Arquivo maior que o limite de projeto.')
        imported=Connection.from_dict(json.loads(uploaded.getvalue()))
        ir=evaluate(imported)
        if any(x.severity=='error' for x in ir.issues):raise ValueError('; '.join(x.text for x in ir.issues if x.severity=='error'))
        seed(imported)
        st.session_state.pop('import_error',None)
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        st.session_state['import_error']='Não foi possível abrir: '+str(exc)


if 'beam_name' not in st.session_state:seed(next(iter(PRESETS.values())))


def profile_changed(prefix):
    name=st.session_state[prefix+'_name']
    if name in P:
        p=P[name]
        st.session_state[prefix+'_steel']='ASTM A36' if p.family in ('CS','CVS','VS') else 'ASTM A572 Gr.50'


def profile_widget(prefix,label):
    name=st.selectbox(label,['Seção I personalizada']+list(P),key=prefix+'_name',on_change=profile_changed,args=(prefix,))
    if name in P:return P[name]
    with st.expander('Dimensões da seção personalizada',expanded=True):
        name=st.text_input('Designação',key=prefix+'_manual_name')
        cols=st.columns(2)
        vals={}
        for i,(key,text) in enumerate([('d','Altura d'),('bf','Largura bf'),('tw','Alma tw'),('tf','Mesa tf'),('clear','Altura livre sem concordâncias')]):
            with cols[i%2]:vals[key]=st.number_input(text+' (mm)',min_value=.1,max_value=3000.,key=prefix+'_'+key)
        area=2*vals['bf']*vals['tf']+(vals['d']-2*vals['tf'])*vals['tw']
        return Profile(name,'Soldado',max(area,1)*.00785,area=max(area,1),**vals)


with st.sidebar:
    st.markdown('<div class="eyebrow">LRO · ENGENHARIA</div>',unsafe_allow_html=True)
    st.title('Ligações')
    st.caption(f'Versão {VERSION} · single plate retangular')
    st.text_input('Projeto ou identificação',key='project')
    st.selectbox('Carregar exemplo',list(PRESETS),key='example')
    st.button('Usar este exemplo',on_click=load_example,width='stretch')
    with st.expander('Abrir projeto salvo'):
        uploaded=st.file_uploader('Arquivo JSON do LRO Ligações',type=['json'],key='project_upload')
        st.button('Abrir arquivo',disabled=uploaded is None,on_click=import_file)
        if 'import_error' in st.session_state:st.error(st.session_state.import_error)
    st.divider()
    st.caption('Nesta versão')
    st.markdown('**Single plate**\n\nViga–viga e viga–mesa de pilar. Um caso de esforços já majorados.')
    with st.expander('Próximas ligações'):
        st.write('Prioridade: concluir os modelos de single plate, incluindo recortes, apoio sob tração e enrijecedores. Depois, cantoneira simples e dupla.')
    st.link_button('LinkedIn · Lucas Oliveira',LINK,width='stretch')

st.markdown('<div class="eyebrow">LIGAÇÕES DE AÇO</div>',unsafe_allow_html=True)
st.title('Single plate')
st.caption('Escopo: single plate retangular. Chapa/enrijecedores entre mesas não são avaliados nesta versão.')
st.markdown('<p class="muted">Escolha os perfis, ajuste o detalhe e acompanhe as verificações. A memória usa os mesmos dados e o mesmo desenho.</p>',unsafe_allow_html=True)

left,right=st.columns([1,1.65],gap='large')
with left:
    with st.container(border=True):
        st.subheader('1 · Ligação e esforços')
        st.selectbox('Tipo de apoio',['beam_web','column_flange'],format_func=lambda x:'Alma de viga — viga a 90°' if x=='beam_web' else 'Mesa de pilar — alinhada à alma',key='kind')
        beam=profile_widget('beam','Viga apoiada')
        support=profile_widget('support','Perfil de apoio')
        loads=st.columns(2)
        with loads[0]:vk=st.number_input('Cortante Vd (kgf)',min_value=-1.e7,max_value=1.e7,key='V_kgf',format='%.3f')
        with loads[1]:nk=st.number_input('Tração Nd (kgf)',min_value=0.,max_value=1.e7,key='N_kgf',format='%.3f')
        st.caption(f'{vk*KGF/1000:.3f} kN de cortante · {nk*KGF/1000:.3f} kN de tração. Entrada já majorada.')
        st.caption('Modelo no plano: cortante vertical, tração axial e momento local em torno da maior inércia. Viga apoiada com contenção eficaz por hipótese fixa.')
    with st.container(border=True):
        st.subheader('2 · Detalhamento')
        st.selectbox('Colunas de parafusos',[1,2],key='bolt_columns',help='Calcula o grupo bidimensional de parafusos e os caminhos de ruptura da chapa retangular.')
        if st.session_state.bolt_columns==2:st.number_input('Passo horizontal s (mm)',1.,400.,key='gauge')
        cols=st.columns(2)
        with cols[0]:
            st.selectbox('Parafuso Ø (pol.)',list(DIAMETERS),key='db_label')
            st.number_input('Número de linhas de parafusos',2,12,key='n',step=1)
            st.number_input('Passo p (mm)',min_value=1.,max_value=400.,key='pitch')
            st.number_input('Borda vertical eᵥ (mm)',min_value=1.,max_value=200.,key='edge_v')
            st.number_input('Face → parafusos a (mm)',min_value=10.,max_value=1000.,key='a')
        with cols[1]:
            st.selectbox('Chapa tₚ (pol.)',list(THICKNESSES),key='tp_label')
            st.number_input('Solda chapa → apoio: filete w (mm)',min_value=1.,max_value=25.,key='weld')
            st.number_input('Borda livre eₕ (mm)',min_value=1.,max_value=200.,key='edge_h')
            st.number_input('Folga face do apoio → ponta da viga g (mm)',min_value=1.,max_value=900.,key='gap',help='Sugestão usual: 10 mm. A borda do primeiro parafuso na viga é a − g. Em viga–viga, confira também a projeção das mesas e os recortes.')
            st.caption(f'Borda na viga: a − g = {st.session_state.a-st.session_state.gap:.2f} mm. Para g = 10 mm, o limite máximo desta borda permite a ≤ {10+min(12*beam.tw,150):.2f} mm.')
        centered=st.checkbox('Centralizar chapa na altura da viga',key='center_plate')
        if centered:
            st.session_state.plate_top=(beam.d-(2*st.session_state.edge_v+(st.session_state.n-1)*st.session_state.pitch))/2
        position_label='Topo da mesa superior → topo da aba parafusada z (mm)' if st.session_state.plate_shape=='between_flanges' else 'Topo da mesa superior → topo da chapa z (mm)'
        st.number_input(position_label,-5000.,5000.,key='plate_top',disabled=centered,
                        help='Medida vertical a partir da face superior da mesa da viga apoiada, antes de qualquer recorte. Valor negativo é inválido e bloqueia o cálculo.')
        st.caption('Para subir a chapa, desmarque a centralização e reduza z. A geometria e a excentricidade de N são recalculadas automaticamente.')
        with st.expander('Recortes e desnível entre vigas'):
            if st.session_state.kind=='beam_web':st.number_input('Topo da viga apoiada abaixo do apoio (mm)',-1500.,1500.,key='beam_level')
            st.selectbox('Recorte',['none','top','both'],format_func=lambda x:{'none':'Sem recorte','top':'Mesa superior','both':'Mesas superior e inferior'}[x],key='cope')
            if st.session_state.cope!='none':
                st.caption('Calcula flexão, estabilidade, ruptura e bloco na região recortada. A contenção lateral na raiz do recorte deve existir no detalhe real.')
                st.number_input('Comprimento do recorte (mm)',1.,1000.,key='cope_length')
                st.number_input('Profundidade superior (mm)',1.,1000.,key='cope_top')
                if st.session_state.cope=='both':st.number_input('Profundidade inferior (mm)',1.,1000.,key='cope_bottom')
        with st.expander('Montagem e hipóteses'):
            st.number_input('Folga mínima entre peças (mm)',0.,50.,key='clearance')
            st.number_input('Raio do envelope de montagem (mm)',1.,80.,key='tool_radius',help='Envelope de porca, arruela e ferramenta. Valor inicial ilustrativo, ajustável ao sistema de montagem.')
            st.checkbox('Furos executados com broca',key='drilled',help='Retira o acréscimo de 2 mm no desconto da seção líquida, conforme 5.2.4.')
            st.checkbox('Borda da solda da chapa com execução reforçada especificada',key='reinforced_weld')
            st.checkbox('Verificar mínimo normativo de 45 kN',key='norm_minimum')
            st.checkbox('Informar espessura real da chapa',key='custom_t')
            if st.session_state.custom_t:st.number_input('Espessura real tₚ (mm)',1.,50.,key='real_t',format='%.4f')
    centered_n=abs(beam.d/2-(st.session_state.plate_top+(2*st.session_state.edge_v+(st.session_state.n-1)*st.session_state.pitch)/2))<1e-8
    if st.session_state.kind=='beam_web' and nk>0 and vk==0 and centered_n and st.session_state.plate_shape=='rectangular':
        with st.expander('Alma do apoio sob tração',expanded=True):
            st.number_input('Menor distância livre longitudinal na alma (mm)',0.,100000.,key='support_edge_distance',help='Do eixo da chapa até a extremidade, abertura ou outra região carregada mais próxima, medida ao longo da viga de apoio. O mesmo valor conservador vale para os dois sentidos. Zero = não informado.')
            st.caption('A plastificação usa a orientação real da chapa: sua altura atravessa a alma e sua espessura fica na direção longitudinal do apoio. Modelo aplicável à tração direta centrada, sem cortante.')
    with st.expander('Materiais e especificações'):
        def material_options(profile,key):
            welded=profile.family in ('CS','CVS','VS','Soldado')
            return [s.name for s in STEELS.values() if s.rolled_allowed or welded or s.name==st.session_state[key]]
        st.selectbox('Aço da viga',material_options(beam,'beam_steel'),key='beam_steel')
        st.selectbox('Aço do apoio',material_options(support,'support_steel'),key='support_steel')
        st.selectbox('Aço da chapa',[s.name for s in STEELS.values() if s.plate_allowed],key='plate_steel')
        if any(st.session_state[k].startswith('USI-CIVIL') for k in ('beam_steel','support_steel','plate_steel')):
            st.caption('USI-CIVIL: chapas grossas de 6 a 75 mm e perfis soldados dessas chapas. fy/fu mínimos: 300/400 MPa ou 350/500 MPa. Fonte: Usiminas, catálogo de chapas grossas, p.29.')
        st.selectbox('Especificação dos parafusos',list(BOLTS),key='bolt')
        st.checkbox('Rosca no plano de corte',key='threads')
        st.selectbox('Resistência do eletrodo fw (MPa)',[415.,485.,550.],key='fw')
        st.text_area('Observações do detalhe',key='notes')
    with st.expander('Premissas fixas do modelo'):
        st.write('Viga apoiada com contenção eficaz. Sem cortante horizontal nem momento no eixo de menor inércia; tração axial mantida. Perfis soldados com juntas internas de penetração total e metal de adição compatível. No pilar, admite-se impedido o deslocamento lateral relativo entre suas mesas na região da ligação; é uma premissa do projeto, não uma consequência da penetração total. A análise global dos membros é externa.')

state=st.session_state
hp=2*state.edge_v+(state.n-1)*state.pitch
top=(beam.d-hp)/2 if state.center_plate else state.plate_top
base=next(iter(PRESETS.values()))
kwargs={k:state[k] for k in base.__dict__ if k in state and k not in ('beam','support','V','N','db','tp','plate_top')}
c=Connection(beam=beam,support=support,V=vk*KGF,N=nk*KGF,db=DIAMETERS[state.db_label],tp=state.real_t if state.custom_t else THICKNESSES[state.tp_label],plate_top=top,**kwargs)
r=evaluate(c)
payload=json.dumps(c.to_dict(),ensure_ascii=False,indent=2,allow_nan=False)
digest=hashlib.sha256(payload.encode()).hexdigest()

@st.cache_data(show_spinner=False,max_entries=25)
def drawing_cached(raw,fmt):return image_bytes(Connection.from_dict(json.loads(raw)),fmt)

with right:
    with st.container(border=True):
        st.subheader('3 · Geometria e resultado')
        if r.geometry:
            st.image(drawing_cached(payload,'png'),width='stretch')
        if r.status=='GEOMETRIA INVÁLIDA':st.error(r.status)
        elif r.status=='NÃO ATENDE':st.error(r.status+' · revisar os itens com índice > 1')
        elif r.status=='VERIFICAÇÃO INCOMPLETA':st.warning(r.status)
        else:st.success(r.status)
        ms=st.columns(3)
        ms[0].metric('Aba parafusada (mm)' if c.full_depth else 'Chapa (mm)',f'{c.width:g} × {c.hp:g}',f't = {c.tp:.3f} mm',delta_color='off')
        ms[1].metric('Momento local de entrada',f'{(abs(c.V)*c.bolt_centroid_x+abs(c.N*c.eccentric_n))/(KGF*1000):.2f}','kgf·m',delta_color='off')
        ms[2].metric('Maior índice resistente',number(r.governing.ratio,3) if r.governing else '—')
        st.caption(f'Furo padrão Ø {c.dh:.4f} mm · {c.beam_steel} / {c.support_steel} / chapa {c.plate_steel}')
        if r.governing:st.caption('Determina: '+r.governing.name+' · '+r.governing.case)
        if any(x.id=='support_punch' and not x.passed for x in r.checks):
            st.info('O requisito de hierarquia contra punção é uma condição do método: compara a espessura da chapa com um limite, não esforço com resistência. Seu descumprimento exige revisar o detalhe ou fazer uma verificação específica do apoio.')
        for issue in r.issues:
            if issue.severity=='excluded':
                st.caption('Nota: '+issue.text)
                continue
            f=st.error if issue.severity=='error' else st.warning if issue.severity=='pending' else st.info
            f((issue.origin_label+': ' if issue.severity=='pending' else '')+issue.text+'  ['+issue.reference+']')
        if c.full_depth:
            st.error('SEM CONCLUSÃO GLOBAL: os índices abaixo abrangem apenas componentes isolados. Parafusos, estabilidade acoplada e rotação desta variante permanecem sem validação.')
        if r.checks:
            st.caption('Todos os índices exibidos abaixo incluem o mínimo normativo quando aplicável. Os índices se referem somente às verificações realizadas.')
    with st.container(border=True):
        st.subheader('4 · Salvar e exportar')
        detailed=st.checkbox('Memória detalhada',value=False,help='A compacta desenvolve os itens determinantes por componente; todas as verificações aparecem no quadro resumo.')
        can_detail=bool(r.geometry) and not any(i.severity=='error' for i in r.issues)
        if can_detail and not r.checks:st.caption('O Word será um pré-detalhamento com pendências, sem conclusão de resistência.')
        if st.button('Gerar memória Word',type='primary',disabled=not can_detail,width='stretch'):
            with st.spinner('Preparando imagem, equações e memória...'):
                state['report']=(digest,detailed,create_report(c,r,detailed))
        if 'report' in state and state.report[:2]==(digest,detailed):
            st.download_button('Baixar memória .docx',state.report[2],file_name='Memoria_LRO_single_plate.docx',mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',width='stretch')
        files=st.columns(2)
        files[0].download_button('Salvar projeto',payload,file_name='Projeto_LRO_ligacao.json',mime='application/json',width='stretch')
        if r.geometry:files[1].download_button('Desenho vetorial SVG',drawing_cached(payload,'svg'),file_name='Ligacao_LRO.svg',mime='image/svg+xml',width='stretch')

tabs=st.tabs(['Verificações','Equações e referências','Validação','Escopo da versão'])
with tabs[0]:
    if r.checks:
        table_rows=[]
        for x in r.checks:
            sd,u=display(x.demand,x.unit);rd,_=display(x.resistance,x.unit)
            table_rows.append({'Verificação':x.name,'Tipo':x.category,'Sd / valor':sd,'Rd / limite':rd,'Unidade':u,'Índice':round(x.ratio,5),'Resultado':'Atende' if x.passed else 'Não atende'})
        st.dataframe(pd.DataFrame(table_rows),hide_index=True,width='stretch',column_config={'Índice':st.column_config.NumberColumn(format='%.3f')})
    else:st.info('Não há resistências calculadas. Consulte os avisos de geometria e de cobertura do modelo.')
with tabs[1]:
    for x in r.checks:
        with st.expander(x.name):
            st.write(x.equation);st.write(x.substitution);st.write(x.variables);st.caption(x.reference)
    st.caption('O Word contém equações editáveis. Os procedimentos complementares AISC/SCI são identificados; as tabelas LRFD não são convertidas em bloco para NBR.')
with tabs[2]:
    vals=benchmarks();st.metric('Conferências pontuais contra exemplos',f"{sum(v['atende'] for v in vals)} / {len(vals)}")
    st.dataframe(pd.DataFrame(vals),hide_index=True,width='stretch')
    st.info('Estas conferências validam componentes identificados, não a reprodução integral de todos os exemplos. No app usa-se a distância completa da face ao centro do grupo: e=a na coluna única; e=a+s/2 em duas colunas, inclusive em corte puro. O material didático original usa e=a/2 no grupo convencional; a comparação acima preserva essa hipótese apenas no teste. A NBR atual adota 0,45 e fub=830 MPa para A325; o exemplo antigo usa 0,40 e 825 MPa.')
with tabs[3]:
    st.markdown('''**Cálculo implementado:** single plate retangular, uma ou duas colunas de 2–12 linhas de parafusos, cortante e tração, parafusos por contato, furos padrão e dois filetes de oficina. Inclui desenho proporcional, importação e exportação de projeto e memória Word.

**Chapa/enrijecedores entre mesas:** retirados da seleção. Esta variante não é avaliada; projetos antigos dessa variante não geram resultados nesta versão.

**Cobertura atual:** recortes dentro do domínio, ductilidade, solda chapa–apoio e metal-base das juntas de penetração total do perfil de pilar são calculados. No pilar, o momento é transportado à alma e suas zonas de tração/compressão são verificadas. A alma sob tração direta centrada, sem cortante, recebe cálculo por linhas de plastificação e punção, dentro de seu domínio. A interação fora do plano sob N+V ou N excêntrico é excluída do cálculo e indicada por uma nota junto ao resultado. A contenção eficaz da viga apoiada é hipótese fixa. Não se aplicam cortante horizontal nem momento no eixo de menor inércia. O apoio conserva suas próprias verificações locais; a estabilidade global permanece no projeto estrutural e o impedimento de deslocamento relativo das mesas do pilar é uma premissa registrada na memória.

**Prioridade de desenvolvimento:** concluir e validar as pendências das duas ligações antes de ampliar para cantoneiras. A revisão consolidada acompanha o pacote em docs/REVISAO_TECNICA.md.

O P902-23W contém tabelas complementares; suas tabelas 10-A/10-B são para paredes de perfis tubulares e não são aplicadas às almas dos perfis I desta versão.''')
st.divider()
st.caption(BRAND)
st.link_button('Contato no LinkedIn',LINK)
