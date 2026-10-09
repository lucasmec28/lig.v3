"""Caminho local das forças na mesa do pilar, alinhado à sua alma.

Envelope elástico de dois filetes. O plano interno da mesa recebe M + |V|tf.
Integram-se separadamente as zonas de tração e compressão da carga linear.
NBR 8800:2024 corrigida 2025, 5.7.2–5.7.5 e 6.2; ver docs/METODOLOGIA.md.
Não é análise global do pilar nem modelo de chapa soldada à alma de viga.
"""
from dataclasses import dataclass
import math
from .models import Check, STEELS

WELDED_FAMILIES = ('CS','CVS','VS','Soldado')
G1, G2, E = 1.10, 1.35, 200000.0


def design_factor(c):
    resultant=math.hypot(c.V,c.N)
    return max(1.0,45000/resultant) if c.norm_minimum and resultant>0 else 1.0


@dataclass(frozen=True)
class NormalPatch:
    tension: float
    compression: float
    tensile_length: float
    compression_length: float
    peak: float
    low: float


def normal_patch(N,M,h):
    """Integral exata de p(y)=N/h+12M y/h³, -h/2≤y≤h/2, N≥0.

    M é tomado em módulo: só troca a posição das zonas ao inverter seu sinal.
    Forças N; momento Nmm; comprimento mm; carga linear N/mm, ambos os filetes.
    """
    if not all(math.isfinite(x) for x in (N,M,h)) or h<=0 or N<0:
        raise ValueError('Carga ou comprimento inválido para o modelo de tração.')
    peak=N/h+6*abs(M)/h**2;low=N/h-6*abs(M)/h**2
    if low>=0:return NormalPatch(N,0.0,h,0.0,peak,low)
    slope=12*abs(M)/h**3
    lc=-low/slope
    compression=-low*lc/2
    return NormalPatch(N+compression,compression,h-lc,lc,peak,low)


def column_actions(c,V,N):
    M=abs(V)*(c.bolt_centroid_x+c.support.tf)+abs(N*c.eccentric_n)
    patch=normal_patch(N,M,c.hp)
    q=math.hypot(patch.peak/2,abs(V)/(2*c.hp))
    return M,patch,q


def crippling_point(tw,tf,fy):
    """NBR 5.7.4.2(b): extremo e comprimento carregado zero, menor resistência.
    Sem crédito do espalhamento da força ou da largura da zona comprimida.
    """
    return .33*tw**2*math.sqrt(E*fy*tf/tw)/G1


def column_checks(c,V,N,case):
    if c.kind!='column_flange':return []
    rows=[]
    def add(cid,name,S,R,unit,ref,eq,sub,variables):
        rows.append(Check(cid,name,S,R,unit,ref,eq,sub,variables,case))
    s=STEELS[c.support_steel];M,p,q=column_actions(c,V,N)
    actions=(f'Mma=|V|(e+tf)+|N·eN|={M:.3f} Nmm; '
             f'T={p.tension:.3f}; C={p.compression:.3f} N; '
             f'LT={p.tensile_length:.3f}; LC={p.compression_length:.3f} mm')
    assumptions=('p(y)=N/hp+12Mma·y/hp³; T=∫max(p,0)dy; C=∫max(−p,0)dy. '
                 'T−C=N. O transporte até a face interna da mesa inclui |V|tf. '
                 'Mma é um momento local de equilíbrio, não um momento de engaste aplicado pelo usuário. ')
    # Escoamento local: uma força equivalente pontual é mais desfavorável que
    # o comprimento real da zona. Não se soma espalhamento das duas zonas.
    ln=0.0 if M>0 else c.hp
    ry=1.10*(2.5*c.support.tf+ln)*s.fy*c.support.tw/G1
    add('support_web_y','Pilar — escoamento local sob N e M',max(p.tension,p.compression),ry,'N',
        'NBR 8800:2024, 5.7.3.2(b); resultantes do grupo elástico',
        'max(T; C) ≤ 1,10(2,5k+ln)fy·tw/γa1',
        actions+f'; k=tf={c.support.tf:g}; ln={ln:g}; fy={s.fy:g}; tw={c.support.tw:g}; FRd={ry:.3f} N',
        assumptions+'Caso de extremidade e k=tf, sem ganho do filete/raio. Com momento, adota-se ln=0 para cada resultante, sem ganho do comprimento da zona carregada; com tração uniforme, ln=hp.')
    if c.tp+2*c.weld>=.15*c.support.bf:
        add('support_flange','Pilar — flexão local da mesa sob tração',p.tension,.5*6.25*c.support.tf**2*s.fy/G1,'N',
            'NBR 8800:2024, 5.7.2.1–5.7.2.3',
            'T ≤ 0,5·6,25tf²·fy/γa1',actions,
            assumptions+'Redução de extremidade aplicada. Comprimento transversal carregado tp+2w ≥ 0,15bf.')
    if p.compression>1e-8:
        rc=crippling_point(c.support.tw,c.support.tf,s.fy)
        add('support_crippling','Pilar — enrugamento da alma na zona comprimida',p.compression,rc,'N',
            'NBR 8800:2024, 5.7.4.2(b); ln=0 e região de extremidade',
            'C ≤ 0,33tw²·√(E·fy·tf/tw)/γa1',
            actions+f'; tw={c.support.tw:g}; tf={c.support.tf:g}; E={E:g}; fy={s.fy:g}; FRd={rc:.3f} N',
            assumptions+'Compressão local criada pelo momento, mesmo para N global de tração. Comprimento carregado e distância à extremidade adotados conservadoramente; sem ganho do espalhamento.')
    add('support_joint_base','Perfil soldado — metal-base da junta de penetração total' if c.support.family in WELDED_FAMILIES else 'Pilar — alma junto à raiz da mesa',2*q,min(.6*s.fy*c.support.tw/G1,.6*s.fu*c.support.tw/G2),'N/mm',
        'NBR 8800:2024, 5.7.1; 6.2.5/tabela 9; 6.5.5',
        'rmax=√[(N/hp+6Mma/hp²)²+(V/hp)²] ≤ min(0,6fy·tw/γa1; 0,6fu·tw/γa2)',
        f'rmax={2*q:.5f}; Mma={M:.3f}; tw={c.support.tw:g}; fy={s.fy:g}; fu={s.fu:g}',
        'Junta interna do perfil soldado com penetração total e metal de adição compatível, por hipótese de projeto. Verifica-se o metal-base com a espessura integral da alma; não existe filete de fabricação a informar. Resultante por comprimento; não substitui os demais estados-limite ou a análise global do pilar.' if c.support.family in WELDED_FAMILIES else 'Resultante local na raiz da mesa do perfil laminado. Não substitui os demais estados-limite ou a análise global do pilar.')
    return rows
