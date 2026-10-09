"""Componentes locais do apoio, sem equivalência com validação do nó completo.

Linhas de plastificação: AISC Manual 16, 9-45 / P901 II.A-19B.
Soldas: grupo elástico de linhas, integrado analiticamente; NBR 8800, 6.2.5.
O modelo acoplado chapa entre mesas/alma do apoio permanece explicitamente bloqueado.
"""
from dataclasses import dataclass
import math
from .models import Check, STEELS


def web_yield_lines(a, b, w, length, thickness, fy, gamma=1.1):
    """Eq. 9-45: bordas apoiadas, sem momento de engastamento nas mesas.

    a,b: faixas livres transversais; w: distância entre apoios transversais;
    length: dimensão da área carregada paralela ao eixo da barra de apoio.
    Não converter h da chapa em length quando a barra de apoio é uma viga!
    """
    values=(a,b,w,length,thickness,fy,gamma)
    if not all(math.isfinite(x) and x>0 for x in values):
        raise ValueError('Dimensões e propriedades positivas são obrigatórias.')
    if a+b>w+1e-8:raise ValueError('Faixas livres incompatíveis com a altura do painel.')
    S=(a+b)/(a*b)
    coefficient=4*math.sqrt(2*w*S)+length*S
    nominal=fy*thickness**2/4*coefficient
    spread=math.sqrt(2*w/S)
    return dict(nominal=nominal,resistance=nominal/gamma,spread=spread,
                required_end_distance=length/2+spread,coefficient=coefficient)


def web_patch(c):
    """Orientação da chapa na ALMA DE VIGA, usando d−2tf sem ganho dos raios."""
    a=c.beam_level+c.plate_top-c.support.tf
    b=c.support.d-c.support.tf-(c.beam_level+c.plate_top+c.hp)
    return web_yield_lines(a,b,c.root_height,c.tp,c.support.tw,STEELS[c.support_steel].fy)


@dataclass(frozen=True)
class WeldLine:
    name: str
    x1: float
    y1: float
    x2: float
    y2: float
    leg: float
    count: int = 2

    @property
    def length(self):return math.hypot(self.x2-self.x1,self.y2-self.y1)
    @property
    def throat(self):return self.leg/math.sqrt(2)
    @property
    def area(self):return self.count*self.throat*self.length


def elastic_weld_group(lines, fx, fy, moment):
    """N, mm e Nmm. Momento fornecido em relação ao centroide do grupo.

    Tensões de cisalhamento vetoriais no modelo de linha de garganta.
    O máximo de uma função quadrática convexa em um segmento ocorre nas pontas.
    Retorna também integrais de equilíbrio independentes das pontas.
    """
    if not lines or any(not all(math.isfinite(v) for v in (l.x1,l.y1,l.x2,l.y2,l.leg)) or l.length<=0 or l.leg<=0 or type(l.count) is not int or l.count<1 for l in lines):
        raise ValueError('Segmentos de solda inválidos.')
    if not all(math.isfinite(x) for x in (fx,fy,moment)):
        raise ValueError('Esforços não finitos.')
    A=sum(l.area for l in lines)
    xc=sum(l.area*(l.x1+l.x2)/2 for l in lines)/A
    yc=sum(l.area*(l.y1+l.y2)/2 for l in lines)/A
    J=sum(l.area*((((l.x1+l.x2)/2-xc)**2+((l.y1+l.y2)/2-yc)**2)+l.length**2/12) for l in lines)
    if J<=0:raise ValueError('Inércia polar nula.')
    rows=[]
    force_x=force_y=torque=0.0
    for l in lines:
        x=(l.x1+l.x2)/2-xc;y=(l.y1+l.y2)/2-yc
        sx=fx/A-moment*y/J;sy=fy/A+moment*x/J
        Fxl=l.area*sx;Fyl=l.area*sy
        Ml=l.area*(moment*l.length**2/(12*J))+x*Fyl-y*Fxl
        force_x+=Fxl;force_y+=Fyl;torque+=Ml
        endpoints=[]
        for xx,yy in ((l.x1,l.y1),(l.x2,l.y2)):
            sx=fx/A-moment*(yy-yc)/J;sy=fy/A+moment*(xx-xc)/J
            endpoints.append(dict(x=xx,y=yy,sx=sx,sy=sy,tau=math.hypot(sx,sy)))
        peak=max(endpoints,key=lambda x:x['tau'])
        rows.append(dict(name=l.name,stress=peak['tau'],q=l.count*l.throat*peak['tau'],
                         fx=Fxl,fy=Fyl,moment=Ml,length=l.length,leg=l.leg))
    return dict(area=A,xc=xc,yc=yc,J=J,lines=rows,fx=force_x,fy=force_y,moment=torque)


def full_depth_weld_lines(c):
    y0=c.support.tf;y1=c.support.d-c.support.tf
    return [WeldLine('alma',0,y0+c.corner_clip,0,y1-c.corner_clip,c.weld),
            WeldLine('mesa superior',c.corner_clip,y0,c.root_width,y0,c.flange_weld),
            WeldLine('mesa inferior',c.corner_clip,y1,c.root_width,y1,c.flange_weld)]


def support_component_checks(c,V,N,case):
    """Cálculos isolados. Não removem os bloqueios de domínio de geometry()."""
    checks=[]
    def add(id,name,S,R,u,ref,eq,subs,variables):
        checks.append(Check(id,name,S,R,u,ref,eq,subs,variables,case))
    s=STEELS[c.support_steel];p=STEELS[c.plate_steel]
    if c.kind=='beam_web' and not c.full_depth and N>0 and not c.support_web_combined_excluded:
        patch=web_patch(c)
        add('support_web_n','Alma do apoio — linhas de plastificação sob N',N,patch['resistance'],'N',
            'AISC Manual 16, eq.9-45; P901 II.A-19B, IIA-228; Kapp (1974), eq.8; γa1=1,10 da NBR',
            'NRd = fy·tw²[4√(2wuv(u+v)) + L(u+v)]/(4γa1uv)',
            f'u={c.beam_level+c.plate_top-c.support.tf:.4f}; v={c.support.d-c.support.tf-c.beam_level-c.plate_top-c.hp:.4f}; w={c.root_height:.4f}; L=tp={c.tp:.4f}; tw={c.support.tw:g}; fy={s.fy:g}; NRd={patch["resistance"]:.3f}',
            f'u e v: faixas livres acima e abaixo da chapa, distintas da cota a do desenho; w=d−2tf; L=tp é a dimensão paralela ao eixo da viga de apoio, sem ganho da solda. Bordas apoiadas. Espaço longitudinal necessário de cada lado do eixo da chapa: {patch["required_end_distance"]:.2f} mm. Verificação isolada de N; não cobre a interação com a torção do apoio causada por V nem a excentricidade vertical de N.')
        perimeter=2*(c.hp+c.tp)
        add('support_web_punch_n','Alma do apoio — ruptura por punção sob N',N,.6*s.fu*perimeter*c.support.tw/1.35,'N',
            'NBR 8800:2024, 6.5.5(b); AISC Manual Parte 9, cisalhamento perimetral',
            'NRd = 0,6fu·2(hp+tp)·tw/γa2',
            f'perímetro={perimeter:.3f} mm; tw={c.support.tw:g}; fu={s.fu:g}; γa2=1,35',
            'Perímetro da projeção da chapa, sem acréscimo da solda. Verificação isolada de tração normal ao plano da alma; não substitui a plastificação nem a interação do nó.')
    if c.full_depth:
        lines=full_depth_weld_lines(c)
        props=elastic_weld_group(lines,0,0,0)
        yN=c.beam_level+c.beam.d/2
        # Envoltória dos dois sentidos de V. N permanece em tração.
        groups=[elastic_weld_group(lines,N,sign*abs(V),sign*abs(V)*(c.bolt_centroid_x-props['xc'])-N*(yN-props['yc'])) for sign in (-1,1)]
        resistance=.6*c.fw/1.35
        for i,line in enumerate(lines):
            peak=max(g['lines'][i]['stress'] for g in groups)
            q=max(g['lines'][i]['q'] for g in groups)
            title=line.name
            add('full_weld_'+str(i),'Entre mesas — solda à '+title,peak,resistance,'MPa',
                'NBR 8800:2024, 6.2.5/tabela 9; grupo elástico de linhas',
                'τ = √[(N/Aw − M·y/Jw)² + (V/Aw + M·x/Jw)²] ≤ 0,6fw/γw2',
                f'Aw={props["area"]:.4f} mm²; xG={props["xc"]:.4f}; yG={props["yc"]:.4f}; Jw={props["J"]:.4f} mm⁴; L={line.length:.4f}; w={line.leg:g}; N={N:.3f}; |V|={abs(V):.3f} N; M−={groups[0]["moment"]:.3f}; M+={groups[1]["moment"]:.3f} Nmm; τmax={peak:.5f} MPa',
                'Aw: soma das áreas de garganta; Jw: inércia polar das gargantas; x,y: coordenadas relativas ao centroide G. M±=±|V|(e−xG)−N(yN−yG), com yN no eixo da viga; e é a distância ao centro do grupo de parafusos. Dois filetes por segmento; alívios sem solda. Modelo elástico isolado, sem crédito do enrijecedor oposto; distribuição real chapa/alma/mesas e rotação ainda exigem validação.')
            ts=c.support.tw if i==0 else c.support.tf
            rd=min(.6*p.fy*c.tp/1.1,.6*p.fu*c.tp/1.35,.6*s.fy*ts/1.1,.6*s.fu*ts/1.35)
            add('full_base_'+str(i),'Entre mesas — metal-base junto à '+title,q,rd,'N/mm',
                'NBR 8800:2024, 6.5.5; resultante local no grupo elástico',
                'qSd ≤ min(0,6fy,p·tp/γa1; 0,6fu,p·tp/γa2; 0,6fy,s·ts/γa1; 0,6fu,s·ts/γa2)',
                f'qSd={q:.5f}; qRd={rd:.5f} N/mm; ts={ts:g}; tp={c.tp:g}',
                'Duas gargantas transferem a resultante para o metal-base. Critério local conservador de cisalhamento; não cobre a estabilidade do trecho entre mesas ou flexão da alma do apoio.')
        limit=200/math.sqrt(p.fy)
        add('full_compactness','Entre mesas — esbeltez do trecho enrijecedor',c.root_width/c.tp,limit,'—',
            'Motallebi, Lignos e Rogers (2018), JCSR 148, seção 6; limite CSA citado pelos autores',
            'br/tp ≤ 200/√fy   (fy em MPa)',
            f'br={c.root_width:g}; tp={c.tp:g}; br/tp={c.root_width/c.tp:.5f}; limite={limit:.5f}',
            'Condição complementar de compacidade, sem aprovação da resistência ou da capacidade de rotação. Não representa índice de utilização sob a carga aplicada.')
        if c.opposite_stiffener:
            st=STEELS[c.stiffener_steel]
            add('opposite_compactness','Enrijecedor oposto — esbeltez',c.stiffener_width/c.stiffener_t,200/math.sqrt(st.fy),'—',
                'Motallebi et al. (2018); condição geométrica complementar',
                'be/te ≤ 200/√fy',
                f'be={c.stiffener_width:g}; te={c.stiffener_t:g}; fy={st.fy:g}',
                'Não se atribui força ou ganho de resistência sem a validação do modelo acoplado e de suas soldas. Um enrijecedor oposto não equivale a uma segunda viga com reação contrabalançando a primeira.')
    return checks
