"""Single plate em corte simples. Procedimentos e limites em docs/METODOLOGIA.md.

NBR 8800:2024 + errata 2025 para resistências. AISC e material didático são complementos
identificados, nunca tabelas LRFD convertidas por um fator global.
"""
import math
from dataclasses import replace
from .models import SUPPORT_WEB_EXCLUSION
from .models import Connection, Check, Issue, Result, STEELS, BOLTS, DIAMETERS

from .additional_checks import additional_checks
from .column_checks import column_checks,design_factor
from .support_checks import support_component_checks,web_patch
from .local_checks import (grip_factor, elastic_group, elastic_moment_bound, coped_section,
                           single_cope_moment, web_shear, required_development_weld)

G1, G2, E = 1.10, 1.35, 200000.0
NBR = "ABNT NBR 8800:2024, versão corrigida 2025"


def bolt_shear(db, fub, threads=True, gamma=G2):
    return (0.45 if threads else 0.56)*math.pi*db**2/4*fub/gamma


def elastic_bolts(n, pitch, V, N, M):
    """Forças resistentes do grupo, coordenadas y positivas para cima."""
    return elastic_group(n,pitch,1,0,V,N,M)


def bearing(db, dh, edge, pitch, t, fu):
    lc=max(0,min(edge-dh/2,pitch-dh))
    return min(1.2*lc*t*fu,2.4*db*t*fu)/G2,lc


def block_strength(Agv, Anv, Ant, fy, fu, gamma=G2):
    return min(0.6*fu*max(0,Anv)+fu*max(0,Ant),0.6*fy*max(0,Agv)+fu*max(0,Ant))/gamma


def net_plastic_modulus(h,t,n,p,dh):
    # Integração exata de |y|: contempla também o furo sobre o eixo neutro.
    integral=lambda y:0.5*y*abs(y)
    void=sum(integral((i-(n-1)/2)*p+dh/2)-integral((i-(n-1)/2)*p-dh/2) for i in range(n))
    return t*(h*h/4-void)


def plate_ltb(h,t,L,fy,elastic_modulus=E,Cb=1.84):
    """Resistência nominal AISC F11, procedimento do P901 II.A-17B/19B."""
    lam=L*h/t**2;lp=.08*elastic_modulus/fy;lr=1.9*elastic_modulus/fy
    Mp=fy*t*h*h/4;My=fy*t*h*h/6
    if lam<=lp: Mn=Mp
    elif lam<=lr: Mn=min(Mp,Cb*(1.52-.274*lam*fy/elastic_modulus)*My)
    else: Mn=min(Mp,1.9*elastic_modulus*Cb/lam*(t*h*h/6))
    return Mn,lam


def interaction(N,Nr,M,Mr,V,Vr,My=0,Myr=1):
    """AISC Manual 16 ed., 12-2/12-3. Expoente 2 no colchete inteiro."""
    p=abs(N)/Nr;b=abs(M)/Mr+abs(My)/Myr
    return (p/2+b if p<.2 else p+8*b/9)**2+(abs(V)/Vr)**2


def geometry(c:Connection):
    out=[]
    def issue(level,text,ref="Geometria e domínio do modelo",origin="model"):out.append(Issue(level,text,ref,origin))
    if any(type(getattr(c,k)) is not bool for k in ('threads','restrained','norm_minimum','drilled','reinforced_weld','opposite_stiffener')):
        issue('error','As opções sim/não do projeto devem conter valores booleanos válidos.');return out,{}
    vals=[c.db,c.pitch,c.edge_v,c.edge_h,c.a,c.gap,c.tp,c.weld,c.fw,c.plate_top,c.beam_level,c.V,c.N,c.tool_radius,c.clearance,c.cope_top,c.cope_bottom,c.cope_length,c.root_width,c.corner_clip,c.flange_weld,c.stiffener_t,c.stiffener_width,c.stiffener_weld,c.gauge,c.support_joint_weld,c.support_edge_distance]
    if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in vals):
        issue("error","Todos os valores precisam ser números finitos.");return out,{}
    if c.kind not in ("column_flange","beam_web") or c.cope not in ("none","top","both") or c.plate_shape not in ('rectangular','between_flanges') or c.bolt_columns not in (1,2):
        issue("error","Configuração de ligação não reconhecida.");return out,{}
    if not isinstance(c.n,int) or not 2<=c.n<=12:
        issue("error","O app permite de 2 a 12 linhas de parafusos em uma ou duas colunas.");return out,{}
    if min(c.db,c.pitch,c.edge_v,c.edge_h,c.a,c.tp,c.weld,c.fw)<=0 or min(c.gap,c.clearance,c.tool_radius,c.plate_top)<0:
        issue("error","Dimensões positivas são obrigatórias; folgas e cotas de posicionamento não podem ser negativas.");return out,{}
    if not any(abs(c.db-v)<1e-8 for v in DIAMETERS.values()):
        issue("error","Diâmetro fora do catálogo em polegadas desta versão.");return out,{}
    if c.bolt not in BOLTS or any(x not in STEELS for x in (c.beam_steel,c.support_steel,c.plate_steel,c.stiffener_steel)):
        issue("error","Material não reconhecido.");return out,{}
    for p in (c.beam,c.support):
        pv=[p.d,p.bf,p.tw,p.tf,p.clear,p.area,p.mass]
        if not all(isinstance(x,(int,float)) and math.isfinite(x) and x>0 for x in pv) or p.d<=2*p.tf or p.bf<=p.tw or p.clear>p.d-2*p.tf+1:
            issue("error",f"Geometria inconsistente do perfil {p.name}.");return out,{}
    if c.support_joint_weld<0:issue("error","Filete mesa–alma não pode ser negativo.")
    if c.support_edge_distance<0:issue('error','Distância longitudinal livre na alma do apoio não pode ser negativa.')
    if c.N<0:issue("pending","Compressão axial está fora do domínio validado desta versão. Os cálculos de tração não serão aplicados a esse caso.")
    if c.full_depth or c.opposite_stiffener:
        issue('error','Chapa entre mesas e enrijecedor oposto não são avaliados nesta versão. Este projeto pertence à variante retirada; nenhum cálculo ou aprovação será reaproveitado. Inicie uma ligação retangular.','Escopo definido para a versão 0.5','configuration')
        return out,{}
    if c.cope!="none" and (min(c.cope_top,c.cope_length)<=0 or (c.cope=="both" and c.cope_bottom<=0)):
        issue("error","As dimensões dos recortes ativos devem ser positivas.")
    if c.coped_top+c.coped_bottom>=c.beam.d:
        issue("error","Os recortes eliminam a seção da viga.")
    if c.cope!="none":
        if c.coped_top<c.beam.tf or (c.cope=='both' and c.coped_bottom<c.beam.tf):
            issue('error','O modelo de recorte exige a retirada integral da mesa na região recortada.')
        if c.cope_length>2*c.beam.d or c.coped_top>.5*c.beam.d or c.coped_bottom>.5*c.beam.d:
            issue('pending','Recorte profundo/longo fora do domínio verificado: comprimento ≤ 2d e profundidade ≤ d/2.','AISC Manual Parte 9')
        if (c.beam.d-c.coped_top-c.coped_bottom)/c.beam.tw>260:issue('pending','Região recortada com h/tw > 260: fora do limite de esbeltez do modelo de corte adotado.','NBR 8800, 5.4.3.3')
        if c.cope=='top' and c.hp<.5*(c.beam.d-c.coped_top):
            issue('pending','A altura conectada deve ser pelo menos metade da seção remanescente no modelo de recorte superior.','AISC Manual Parte 9; Dowswell (2018)')
    if c.support_web_combined_excluded:
        issue('excluded',SUPPORT_WEB_EXCLUSION,'Escopo definido para a versão 0.5.1')
    elif c.kind=="beam_web" and c.N>0 and not c.full_depth:
        try:
            patch=web_patch(c)
            required=patch['required_end_distance']
            if c.support_edge_distance<required:
                issue('pending',f'Alma sob tração: informar/conferir distância livre longitudinal de pelo menos {required:.2f} mm, em cada sentido a partir do eixo da chapa, até extremidades, aberturas ou regiões de introdução de outras cargas. Valor informado: {c.support_edge_distance:g} mm (zero = não informado).','Kapp (1974), eq.7; domínio do mecanismo AISC 9-45','data')
            if c.hp/c.root_height>.8:
                issue('pending','Chapa ocupa mais de 80% da altura entre mesas: o modelo isolado de plastificação não é liberado para conclusão nessa faixa.','Limite conservador de implementação; interação dos mecanismos localizados')
        except ValueError:
            pass # As inconsistências geométricas são detalhadas nos demais avisos.
    if not c.norm_minimum:
        issue("pending","Mínimo de 45 kN desativado: modo de comparação, sem conclusão de atendimento normativo.","NBR 8800, 6.1.5.2","configuration")
    for label,steel,thicknesses,plate in [("Chapa",c.plate_steel,[c.tp],True),("Viga",c.beam_steel,[c.beam.tf,c.beam.tw],c.beam.family in ('CS','CVS','VS','Soldado')),("Apoio",c.support_steel,[c.support.tf,c.support.tw],c.support.family in ('CS','CVS','VS','Soldado'))]:
        s=STEELS[steel];limit=s.plate_max if plate else s.profile_max
        minimum=s.plate_min if plate else s.profile_min
        if (plate and not s.plate_allowed) or (not plate and not s.rolled_allowed) or max(thicknesses)>limit or min(thicknesses)<minimum:
            issue("error",f"{label}: produto/espessura fora do intervalo cadastrado para {steel}. Intervalo: {minimum:g} a {limit:g} mm; conferir mesa e alma separadamente.",s.source)
    pmin=max(2.7*c.db,c.dh+c.db)
    tmin=min(c.tp,c.beam.tw)
    pmax=min(24*tmin,300)
    if c.pitch<pmin:issue("error",f"Passo p = {c.pitch:g} mm inferior ao mínimo {pmin:.2f} mm.","NBR 8800, 6.3.9")
    if c.pitch>pmax:issue("error",f"Passo p excede {pmax:.2f} mm para elementos pintados ou não sujeitos à corrosão.","NBR 8800, 6.3.10(a)")
    if c.bolt_columns==2 and not pmin<=c.gauge<=pmax:issue('error',f'Espaçamento horizontal deve estar entre {pmin:.2f} e {pmax:.2f} mm.','NBR 8800, 6.3.9 e 6.3.10')
    if c.beam_edge<=c.dh/2:issue("error","O furo intercepta a extremidade da viga; aumentar a ou reduzir g.")
    emin={12.7:19,15.875:22,19.05:25,22.225:28,25.4:32,28.575:38,31.75:41}[c.db]
    for label,e in [("borda vertical da chapa",c.edge_v),("borda livre da chapa",c.edge_h),("extremidade da viga",c.beam_edge)]:
        if e<c.dh/2:issue("error",f"O furo intercepta a {label}.")
        elif e<emin:issue("info",f"Distância à {label} = {e:.2f} mm abaixo da tabela 16 ({emin} mm): aplicada sua exceção mediante a verificação conservadora de pressão de contato/rasgamento calculada abaixo.","NBR 8800, 6.3.11 / tabela 16")
    for label,e,t in [("borda vertical da chapa",c.edge_v,c.tp),("borda livre da chapa",c.edge_h,c.tp),("extremidade da viga",c.beam_edge,c.beam.tw)]:
        if e>min(12*t,150):
            detail=(f' a − g = {c.a:g} − {c.gap:g} = {e:g} mm; limite = {min(12*t,150):g} mm. Para manter g = {c.gap:g} mm, use a ≤ {c.gap+min(12*t,150):g} mm, respeitando também as bordas mínimas.' if label=='extremidade da viga' else f' Valor = {e:g} mm; limite = {min(12*t,150):g} mm.')
            issue("error",f"Distância à {label} excede min(12t; 150 mm)."+detail,"NBR 8800, 6.3.12")
    limit_t=c.db/2+(1.6 if c.n<=5 else -1.6)
    ductile=(min(c.tp,c.beam.tw) if c.bolt_columns==1 else max(c.tp,c.beam.tw))<=limit_t and min(c.edge_h,c.beam_edge)>=2*c.db
    if c.bolt=="ASTM A307":issue("pending","O detalhamento de ductilidade da single plate com parafusos comuns A307 não está validado nesta versão.")
    k=(c.beam.d-c.beam.clear)/2
    if c.plate_top<max(k,c.coped_top)+c.weld or c.plate_top+c.hp>min(c.beam.d-k,c.beam.d-c.coped_bottom)-c.weld:
        issue("error","A chapa/solda invade a região de mesa, concordância ou recorte da viga apoiada. Ajustar altura ou posição da chapa.")
    for y in c.y_bolts:
        if min(y-max(k,c.coped_top),min(c.beam.d-k,c.beam.d-c.coped_bottom)-y)<c.tool_radius:
            issue("error","Há interferência do envelope de montagem de parafuso/porca com mesa, concordância ou recorte.");break
    if c.a<c.weld+c.tool_radius:issue("error","Envelope de montagem do parafuso invade a solda/face do apoio.")
    ts=c.support.tf if c.kind=="column_flange" else c.support.tw
    smaller=min(c.tp,ts)
    wmin=3 if smaller<=6.3 else 5 if smaller<=12.5 else 6 if smaller<=19 else 8
    if c.weld<wmin:issue("error",f"Filete inferior ao mínimo de {wmin} mm para a menor espessura da junta.","NBR 8800, 6.2.6.2.1 / tabela 11")
    wmax=c.tp if c.tp<6.3 else c.tp-1.5
    if c.weld>wmax+1e-8 and not c.reinforced_weld:issue("error",f"Filete superior a {wmax:.2f} mm na borda da chapa. Redimensionar ou especificar execução reforçada.","NBR 8800, 6.2.6.2.2")
    if c.hp<max(4*c.weld,40):issue("error","Comprimento de solda inferior ao mínimo.","NBR 8800, 6.2.6.2.3")
    if c.kind=="beam_web":
        ks=(c.support.d-c.support.clear)/2
        py=c.beam_level+c.plate_top
        if py<ks+c.weld or py+c.hp>c.support.d-ks-c.weld:
            issue("error","Chapa/solda interfere nas mesas ou concordâncias da viga de apoio.")
        projection=(c.support.bf-c.support.tw)/2
        # Nas faixas ocupadas pelas mesas do apoio, é necessário afastar a ponta
        # da viga ou retirar material. Folga de montagem explicitamente configurável.
        full_low=c.beam_level;full_high=full_low+c.beam.d
        for label,lo,hi,depth in [("superior",-c.clearance,c.support.tf+c.clearance,c.coped_top),("inferior",c.support.d-c.support.tf-c.clearance,c.support.d+c.clearance,c.coped_bottom)]:
            overlaps=full_high>lo and full_low<hi
            if overlaps and c.gap<projection+c.clearance:
                enough_length=c.cope!="none" and c.gap+c.cope_length>=projection+c.clearance
                enough_depth=(full_low+depth>=hi) if label=="superior" else (full_high-depth<=lo)
                if not (enough_length and enough_depth):issue("error",f"Interferência com a mesa {label} da viga de apoio. Afastar a ponta ou ajustar o recorte e a folga.")
    if c.plate_top+c.hp>c.beam.d:issue("error","A chapa ultrapassa a altura da viga apoiada.")
    if grip_factor(c.tp+c.beam.tw,c.db)<=0:issue("error","Pega fora do domínio da redução positiva de resistência dos parafusos.","NBR 8800, 6.3.7")
    if c.gap<c.weld:issue("error", "A ponta da alma apoiada interfere no filete junto ao apoio: g deve superar o alcance da solda.")
    if c.N>0 and abs(c.eccentric_n)>1e-6:
        issue("info",f"N é referido ao eixo da viga. Incluído |N·eN|, com eN = {c.eccentric_n:.2f} mm, no momento local.")
    g=dict(hp=c.hp,width=c.width,dh=c.dh,dh_net=c.dh_net,beam_edge=c.beam_edge,e=c.bolt_centroid_x,emin=emin,pmin=pmin,pmax=pmax,ductile=ductile,ts=ts)
    return out,g


def strength(c:Connection, V:float, N:float, case="Entrada"):
    rows=[]
    def add(id,name,S,R,unit,ref,eq,subst,variables):
        rows.append(Check(id,name,S,R,unit,ref,eq,subst,variables,case))
    b=STEELS[c.beam_steel];s=STEELS[c.support_steel];p=STEELS[c.plate_steel]
    V=abs(V);N=abs(N);h=c.hp;t=c.tp;dn=c.dh_net
    M=V*c.bolt_centroid_x+N*abs(c.eccentric_n)  # envoltória dos sinais da excentricidade axial
    F=elastic_group(c.n,c.pitch,c.bolt_columns,c.gauge,V,N,M);Fmax=max(math.hypot(x,y) for x,y in F)
    grip=grip_factor(c.tp+c.beam.tw,c.db)
    add("bolts","Parafusos em corte simples",Fmax,grip*bolt_shear(c.db,BOLTS[c.bolt],c.threads or c.bolt=="ASTM A307"),"N",f"{NBR}, 6.3.3.2","F_Rd = kpega·α·π·db²·fub / (4·γa2)",f"kpega = {grip:.6f}; pega = {c.tp+c.beam.tw:.3f} mm; Fmax = {Fmax:.2f} N; α = {0.45 if c.threads or c.bolt=='ASTM A307' else 0.56}; db = {c.db:g}; fub = {BOLTS[c.bolt]:g}; γa2 = {G2}","kpega: redução por pega longa, 6.3.7; Fmax: resultante do parafuso crítico; db: diâmetro; fub: ruptura do aço do parafuso; α: coeficiente do plano de corte.")
    for id,label,th,fu,edge in [("bearing_plate","Contato e rasgamento da chapa",t,p.fu,min(c.edge_h,c.edge_v,c.gauge-c.dh/2 if c.bolt_columns>1 else math.inf)),("bearing_beam","Contato e rasgamento da alma",c.beam.tw,b.fu,min(c.beam_edge,c.gauge-c.dh/2 if c.bolt_columns>1 else math.inf,c.pitch-c.dh/2,min(c.y_bolts)-c.coped_top,c.beam.d-c.coped_bottom-max(c.y_bolts)))]:
        R,lc=bearing(c.db,c.dh,edge,c.pitch,th,fu)
        add(id,label,Fmax,R,"N",f"{NBR}, 6.3.3.3(a)","F_Rd = min(1,2·lc·t·fu; 2,4·db·t·fu) / γa2",f"lc conservador = {lc:.3f} mm; t = {th:g}; fu = {fu:g}; Fmax = {Fmax:.2f} N","lc: menor distância livre possível a bordas ou furos, adotada para qualquer direção da força; t: espessura ligada; fu: ruptura do metal-base.")
    Ag=h*t;An=(h-c.n*dn)*t;Zg=t*h*h/4;Zn=net_plastic_modulus(h,t,c.n,c.pitch,dn)
    Vy=.6*p.fy*Ag/G1;Vu=.6*p.fu*An/G2;Ny=p.fy*Ag/G1;Nu=p.fu*An/G2
    Cb=1.0 if N>0 and abs(c.eccentric_n)>1e-9 else 1.84
    Mnom,lam=plate_ltb(h,t,c.bolt_centroid_x,p.fy,Cb=Cb);My=Mnom/G1;Mu=p.fu*Zn/G2
    for id,label,dem,cap,unit,ref,eq,sub,vars in [
        ("plate_vy","Chapa — escoamento por corte",V,Vy,"N","6.5.5(a)","V_Rd = 0,60·fy·Ag / γa1",f"Ag = {h:.3f}×{t:.4f} = {Ag:.3f} mm²; fy = {p.fy:g}","Ag: área bruta; fy: escoamento; γa1 = 1,10."),
        ("plate_vu","Chapa — ruptura por corte",V,Vu,"N","6.5.5(b)","V_Rd = 0,60·fu·An / γa2",f"An = ({h:.3f} − {c.n}×{dn:.4f})×{t:.4f} = {An:.3f} mm²","An: área líquida; desconto do furo inclui acréscimo de 2 mm, salvo furação com broca; γa2 = 1,35."),
        ("plate_ny","Chapa — escoamento por tração",N,Ny,"N","6.5.3(a)","N_Rd = fy·Ag / γa1",f"{p.fy:g}×{Ag:.3f}/{G1}","N: força axial de tração; Ag: área bruta."),
        ("plate_nu","Chapa — ruptura por tração",N,Nu,"N","6.5.3(b)","N_Rd = fu·An / γa2",f"{p.fu:g}×{An:.3f}/{G2}","Área diretamente conectada da chapa; Ct = 1,0; não é uma emenda de barras."),
        ("plate_mu","Chapa — ruptura por flexão",M,Mu,"Nmm","6.5; complemento AISC Manual 9-8","M_Rd = fu·Zn / γa2",f"Zn = {Zn:.3f} mm³; fu = {p.fu:g}; M = |V|e + |N·eN| = {M:.3f} Nmm","Zn: módulo plástico líquido integrado descontando todos os furos; M: momento local, não momento de engaste."),
    ]: add(id,label,dem,cap,unit,f"{NBR}, {ref}",eq,sub,vars)
    add("plate_ltb","Chapa — flexão e estabilidade",M,My,"Nmm","P901 II.A-17B/19B, AISC F11; γa1 da NBR 8800","Mn = min(Mp; Cb·(1,52 − 0,274·λ·fy/E)·fy·W); M_Rd = Mn/γa1",f"λ = e·h/t² = {lam:.3f}; Cb = {Cb:.2f}; Mp = {p.fy*Zg:.3f} Nmm; Mn = {Mnom:.3f} Nmm","E = 200 000 MPa; Cb=1,0 quando há momento adicional de N excêntrico, e 1,84 no caso de referência; Lb = e; W = th²/6; Mp = fyth²/4. Usar Mp se λ ≤ 0,08E/fy; para λ > 1,9E/fy, Mn = min(Mp; 1,9ECbW/λ).")
    minor=0.0  # contenção fixa: sem momento em torno da menor inércia
    minor_y=p.fy*h*t*t/4/G1;minor_u=p.fu*(h-c.n*dn)*t*t/4/G2
    for suffix,Nr,Mr,Vr,Myr,label in [("y",Ny,My,Vy,minor_y,"escoamento e estabilidade"),("u",Nu,Mu,Vu,minor_u,"ruptura")]:
        eta=interaction(N,Nr,M,Mr,V,Vr,minor,Myr)
        add("interaction_"+suffix,"Chapa — interação N V M / "+label,eta,1,"—","AISC Manual 16ª ed., 12-2/12-3; resistências NBR explícitas","η = [n/2 + m]² + v² (n < 0,2); η = [n + 8m/9]² + v² (n ≥ 0,2)",f"n = {N/Nr:.6f}; m = {M/Mr+minor/Myr:.6f}; v = {V/Vr:.6f}; η = {eta:.6f}","n = N/NRd; m = Mx/MxRd + My/MyRd; v = V/VRd; My=0: hipótese fixa de contenção eficaz; não há solicitação no eixo de menor inércia. Complemento técnico, não equação da NBR.")
    # Caminhos L e U envolvendo todas as colunas; furos descontados em cada ramo.
    L=c.edge_v+(c.n-1)*c.pitch
    le=c.edge_h+(c.bolt_columns-1)*c.gauge;lenet=le-(c.bolt_columns-.5)*dn
    Av=L*t;Anv=(L-(c.n-.5)*dn)*t;At=lenet*t
    Bv=block_strength(Av,Anv,At,p.fy,p.fu)
    Bn=block_strength(le*t,lenet*t,(L-(c.n-.5)*dn)*t,p.fy,p.fu)
    Bu=block_strength(2*le*t,2*lenet*t,((c.n-1)*c.pitch-(c.n-1)*dn)*t,p.fy,p.fu)
    blockeq="R_Rd = min(0,6·fu·Anv + fu·Ant; 0,6·fy·Agv + fu·Ant) / γa2"
    add("block_plate","Chapa — bloco L sob N e V",(V/Bv)**2+(N/Bn)**2,1,"—","NBR 8800, 6.5.6; AISC Manual 12-1",blockeq+"; η = (V/Rv)² + (N/Rn)²",f"Rv = {Bv:.3f} N; Rn = {Bn:.3f} N; Agv,V = {Av:.3f}; Anv,V = {Anv:.3f}; Ant,V = {At:.3f} mm²","Agv, Anv: áreas bruta/líquida ao corte; Ant: área líquida à tração; Cts = 1,0 no caminho L desta geometria.")
    add("block_plate_u","Chapa — bloco U sob tração",N,Bu,"N",f"{NBR}, 6.5.6",blockeq,f"Agv = {2*le*t:.3f}; Anv = {2*lenet*t:.3f}; Ant = {((c.n-1)*c.pitch-(c.n-1)*dn)*t:.3f} mm²","Caminho U entre a borda livre e os furos extremos; Cts = 1,0.")
    beam_h=c.beam.d-c.coped_top-c.coped_bottom
    Hb=min(c.beam.clear,beam_h);Ab=Hb*c.beam.tw;Anb=(Hb-c.n*dn)*c.beam.tw
    add("beam_v","Alma apoiada — corte local",V,.6*b.fy*Ab/G1,"N",f"{NBR}, 6.5.5(a)","V_Rd = 0,60·fy·hweb·tw/γa1",f"hweb = {Hb:.3f}; tw = {c.beam.tw:g}; fy = {b.fy:g}","hweb: altura livre da alma considerada localmente; verificação global da viga é externa ao app.")
    # Somente a faixa da alma conectada é usada na resistência axial (limite conservador).
    Ax=min(Hb,h)*c.beam.tw;Axn=(min(Hb,h)-c.n*dn)*c.beam.tw
    add("beam_n","Alma apoiada — tração na faixa conectada",N,min(b.fy*Ax/G1,b.fu*Axn/G2),"N",f"{NBR}, 6.5.3; 5.2.4","N_Rd = min(fy·Aweb/γa1; fu·Anweb/γa2)",f"Aweb = {Ax:.3f}; Anweb = {Axn:.3f} mm²; fy = {b.fy:g}; fu = {b.fu:g}","Adota apenas a alma, sem contribuição das mesas: limite conservador para introdução da tração.")
    eb=c.beam_edge+(c.bolt_columns-1)*c.gauge;ebn=eb-(c.bolt_columns-.5)*dn
    Bu_b=block_strength(2*eb*c.beam.tw,2*ebn*c.beam.tw,((c.n-1)*(c.pitch-dn))*c.beam.tw,b.fy,b.fu)
    add("block_beam_u","Alma apoiada — bloco U sob tração",N,Bu_b,"N",f"{NBR}, 6.5.6",blockeq,f"Agv = {2*eb*c.beam.tw:.3f}; Anv = {2*ebn*c.beam.tw:.3f}; Ant = {(c.n-1)*(c.pitch-dn)*c.beam.tw:.3f} mm²","Caminho U na extremidade da alma apoiada; Cts = 1,0.")
    # Mecanismo de interação da alma do roteiro didático / SCI, acrescido de N linear.
    ell=(c.n-1)*c.pitch
    Vbc=V*ell/beam_h;VbcR=.6*b.fy*ell*c.beam.tw/G1
    reduction=max(0,1-(2*Vbc/VbcR-1)**2) if Vbc>.5*VbcR else 1
    Mbc=c.beam.tw*ell**2/6*b.fy/G1*reduction
    Vab=.6*b.fy*c.beam_edge*c.beam.tw/G1
    webM=Mbc+Vab*ell
    Mweb=V*c.x_bolts[-1]+N*abs(c.eccentric_n)
    add("beam_vm","Alma apoiada — interação local",Mweb/webM+N/(b.fy*h*c.beam.tw/G1) if webM>0 else math.inf,1,"—","Material didático de ligações flexíveis p.41; SCI/BCSA 2014; extensão conservadora linear para N","η = M/(M_BC,Rd + V_AB,Rd·ℓ) + N/Nweb,Rd",f"Mweb = {Mweb:.3f}; braço = {c.x_bolts[-1]:.3f}; ℓ = {ell:.3f}; M_BC,Rd = {Mbc:.3f}; V_AB,Rd = {Vab:.3f}; M_Rd = {webM:.3f} Nmm","ℓ: altura entre furos extremos; BC: faixa vertical; AB: ligamento horizontal. M_BC é reduzido quando V_BC > 0,5V_BC,Rd. Interação linear adicional de N é opção conservadora de implementação.")
    # Dois filetes: análise elástica de linha, sem majoração direcional de resistência.
    q=math.hypot(N/(2*h)+3*M/h**2,V/(2*h))
    qr=.6*c.fw*(c.weld/math.sqrt(2))/G2
    add("weld","Soldas — metal de adição",q,qr,"N/mm",f"{NBR}, 6.2.5 / tabela 9","qmax = √[(N/2h + 3M/h²)² + (V/2h)²]; qRd = 0,6·fw·(w/√2)/γw2",f"qmax = {q:.5f}; qRd = {qr:.5f}; h = {h:.3f}; w = {c.weld:g}; fw = {c.fw:g}","Dois filetes verticais; γw2 = 1,35. Envoltória conservadora com o momento local completo também na solda; sem aumento direcional da resistência.")
    ts=c.support.tf if c.kind=="column_flange" else c.support.tw
    add("base_plate","Metal-base da chapa junto à solda",2*q,min(.6*p.fy*t/G1,.6*p.fu*t/G2),"N/mm",f"{NBR}, 6.5.5","qRd = min(0,6·fy·tp/γa1; 0,6·fu·tp/γa2)",f"qSd = 2×{q:.5f}; tp = {t:.4f}; fy = {p.fy:g}; fu = {p.fu:g}","Resultante por unidade de comprimento; critério de cisalhamento conservador para a resultante combinada.")
    add("support_shear","Apoio — corte e ruptura local",math.hypot(V,N),min(.6*s.fy*2*h*ts/G1,.6*s.fu*2*h*ts/G2),"N",f"{NBR}, 6.5.5; P901 II.A-17B/19B","R_Rd = min(0,6·fy·2h·ts/γa1; 0,6·fu·2h·ts/γa2)",f"h = {h:.3f}; ts = {ts:g}; fy = {s.fy:g}; fu = {s.fu:g}","ts: espessura efetivamente soldada, mesa do pilar ou alma da viga. Esta verificação não cobre flexão fora do plano da alma do apoio.")
    # SCI P358, p.128: duas alternativas. A rigorosa publicada é para V puro.
    conservative=ts*s.fu/(p.fy*G2)
    rigorous=ts*ts*s.fu*h*h/(6*V*c.bolt_centroid_x*G2) if V>0 and N==0 else 0
    punch_limit=max(conservative,rigorous)
    add("support_punch","Apoio — requisito contra punção",t,punch_limit,"mm",
        "SCI P358 (2014), p.128, Check 10; γa2 da NBR 8800",
        "tp ≤ max[ts·fu,s/(fy,p·γa2); ts²·fu,s·hp²/(6V·e·γa2)] (segunda parcela apenas V puro)",
        f"tp={t:.4f}; limite conservador={conservative:.4f}; limite por V puro={rigorous:.4f}; adotado={punch_limit:.4f} mm",
        "Condição do método. A expressão rigorosa é linear, sem raiz quadrada. Para N>0 mantém-se o requisito conservador; não se estende a fórmula de V puro à tração simultânea. Não substitui a verificação fora do plano do apoio.")
    rows.extend(column_checks(c,V,N,case))
    rows.extend(additional_checks(c,V,N,M,case,bolt_shear,plate_ltb,block_strength))
    rows.extend(support_component_checks(c,V,N,case))
    return rows


def evaluate(c:Connection):
    issues,g=geometry(c);r=Result(issues=issues,geometry=g)
    if any(i.severity=="error" for i in issues) or c.N<0:return r
    try:
        calculator=support_component_checks if c.full_depth else strength
        r.actual=calculator(c,c.V,c.N,'Entrada')
        R=math.hypot(c.V,c.N)
        factor=design_factor(c)
        r.minimum_factor=factor
        r.checks=calculator(c,c.V*factor,c.N*factor,"Mínimo normativo de 45 kN" if factor>1 else "Entrada")
        if R==0:r.issues.append(Issue("pending","Esforços nulos: a direção do mínimo normativo não está definida. Informe o caso de cálculo."))
        if factor>1:r.issues.append(Issue("info",f"Entrada preservada. Verificação adicional com resultante de 45 kN na mesma direção: V = {c.V*factor/1000:.3f} kN; N = {c.N*factor/1000:.3f} kN.","NBR 8800, 6.1.5.2"))
    except (ZeroDivisionError,ValueError,OverflowError) as exc:
        r.issues.append(Issue("error","Geometria produz áreas ou resistências inválidas. Revise furos, recortes e dimensões."))
        r.actual=[];r.checks=[]
    return r
