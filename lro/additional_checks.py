"""Verificações locais adicionais. Sem geração de combinações de ações."""
import math
from .models import STEELS,BOLTS,Check
from .local_checks import (elastic_group,grip_factor,pure_moment_coefficient,coped_section,
                           single_cope_moment,web_shear,required_development_weld)


def additional_checks(c,V,N,M,case,bolt_shear,plate_ltb,block_strength):
    out=[];g1=1.1;g2=1.35
    def add(id,name,S,R,unit,ref,eq,sub,variables):
        out.append(Check(id,name,S,R,unit,ref,eq,sub,variables,case))
    p=STEELS[c.plate_steel];b=STEELS[c.beam_steel];s=STEELS[c.support_steel]
    tl=c.db/2+(1.6 if c.n<=5 else -1.6)
    waived=(min(c.tp,c.beam.tw) if c.bolt_columns==1 else max(c.tp,c.beam.tw))<=tl and min(c.edge_h,c.beam_edge)>=2*c.db
    if not waived:
        Cp=pure_moment_coefficient(c.n,c.pitch,c.bolt_columns,c.gauge)
        rn=bolt_shear(c.db,BOLTS[c.bolt],c.threads or c.bolt=='ASTM A307',gamma=1)*grip_factor(c.tp+c.beam.tw,c.db)
        mmax=rn*Cp;tmax=6*mmax/(p.fy*c.hp**2)
        add('ductility','Chapa — espessura máxima para ductilidade',c.tp,tmax,'mm',
            'AISC Manual 16, 10-6/10-7; P901 II.A-19B; CIR conforme Muir/Hewitt (2009); resistência nominal NBR 6.3.3.2',
            'tp ≤ 6·Mmax/(fy·hp²); Mmax = Rn,par·C′',
            f'C′ = {Cp:.5f} mm; Rn,par = {rn:.3f} N; Mmax = {mmax:.3f} Nmm; tmax = {tmax:.5f} mm',
            'C′ = Σ ri[1−exp(−3,4ri/rmax)]^0,55. CIR no centro do grupo sob momento puro. Não se aplica o aumento americano 1/0,90 à resistência nominal brasileira: adaptação conservadora. Esta condição independe da intensidade da carga de entrada.')
    wreq=required_development_weld(c.tp,p.fy,c.fw)
    add('weld_development','Solda — desenvolvimento da chapa',wreq,c.weld,'mm',
        'Muir/Hewitt (2009), p.71; AISC Manual Parte 10; P901 II.A-17B/19B',
        'w ≥ max(5tp/8; √3·tp·fy/(2fw))',
        f'w requerido = {wreq:.4f} mm; w adotado = {c.weld:.3f} mm; fy = {p.fy:g}; fw = {c.fw:g}',
        'Condição nominal de hierarquia entre chapa e solda; usa a formulação geral e preserva o mínimo 5t/8. A resistência sob esforços de cálculo é verificada separadamente pela NBR.')
    if c.bolt_columns==2:
        forces=elastic_group(c.n,c.pitch,2,c.gauge,V,N,M)
        reverse=elastic_group(c.n,c.pitch,2,c.gauge,V,N,-M)
        # Caminhos parciais da coluna junto à borda livre de cada peça.
        # Soma de módulos, sem cancelar componentes decorrentes do momento.
        for label,part,edge,th,steel in [('plate',forces[c.n:],c.edge_h,c.tp,p),('beam',forces[:c.n],c.beam_edge,c.beam.tw,b)]:
            other=reverse[c.n:] if label=='plate' else reverse[:c.n]
            nx=max(sum(abs(fx) for fx,fy in part),sum(abs(fx) for fx,fy in other))
            vy=max(sum(abs(fy) for fx,fy in part),sum(abs(fy) for fx,fy in other))
            ant=(c.n-1)*(c.pitch-c.dh_net)*th
            ru=block_strength(2*edge*th,2*(edge-.5*c.dh_net)*th,ant,steel.fy,steel.fu)
            name='Chapa' if label=='plate' else 'Alma apoiada'
            add('block_'+label+'_partial_u',name+' — bloco U da coluna externa',nx,ru,'N',
                'NBR 8800:2024, 6.5.6; caminho parcial conservador',
                'Σ|Fxi| ≤ min(0,6fuAnv+fuAnt; 0,6fyAgv+fuAnt)/γa2',
                f'Nx,col={nx:.3f} N; Rn={ru:.3f} N; borda={edge:.3f}; Ant={ant:.3f}',
                'A soma dos módulos das forças elásticas inclui o efeito do momento e não cancela parcelas de sinais opostos. Caminho U da coluna junto à extremidade livre.')
            if label=='plate' or c.cope!='none':
                lengths=[c.edge_v+(c.n-1)*c.pitch] if label=='plate' else [max(c.y_bolts)-c.coped_top]+([c.beam.d-c.coped_bottom-min(c.y_bolts)] if c.cope=='both' else [])
                ell=min(lengths);ln=ell-(c.n-.5)*c.dh_net;en=edge-.5*c.dh_net
                rv=block_strength(ell*th,ln*th,en*th,steel.fy,steel.fu)
                rn=block_strength(edge*th,en*th,ln*th,steel.fy,steel.fu)
                eta=(vy/rv)**2+(nx/rn)**2
                add('partial_'+label+'_l',name+' — bloco L da coluna externa',eta,1,'—',
                    'NBR 8800:2024, 6.5.6; AISC Manual 12-1; forças por coluna conservadoras',
                    'η = (Σ|Fyi|/Rv)² + (Σ|Fxi|/Rn)² ≤ 1',
                    f'Vcol={vy:.3f}; Ncol={nx:.3f}; Rv={rv:.3f}; Rn={rn:.3f} N',
                    'Caminho parcial da coluna mais próxima da borda livre, além dos caminhos que envolvem o grupo completo. Não cancela as forças devidas ao momento.')
    if c.cope=='none':
        vr,cv=web_shear(c.beam.clear,c.beam.tw,b.fy)
        add('beam_buckling','Alma apoiada — instabilidade ao corte',V,vr,'N',
            'NBR 8800:2024, 5.4.3.1; área local conservadora h·tw',
            'VRd = 0,6fy·h·tw·Cv/γa1',
            f'h = {c.beam.clear:g}; tw = {c.beam.tw:g}; kv = 5,34; Cv = {cv:.6f}; VRd = {vr:.3f}',
            'λ=h/tw; λp=1,10√(kvE/fy); λr=1,37√(kvE/fy). Cv=1, λp/λ ou 1,24(λp/λ)², respectivamente. Usa h·tw em vez de d·tw, sem ganho de resistência.')
    else:
        top=c.coped_top;bottom=c.coped_bottom;h=c.beam.d-top-bottom
        gross=coped_section(c.beam,top,bottom)
        holes=[(y-c.dh_net/2,y+c.dh_net/2) for y in c.y_bolts]
        net=coped_section(c.beam,top,bottom,holes)
        # Projeção dos furos em todas as seções e maior braço: envoltória conservadora.
        arm=max(c.gap+c.cope_length,c.x_bolts[-1])
        ecc=max(abs(c.beam.d/2-gross['yc']),abs(c.beam.d/2-net['yc']))
        mc=V*arm+N*ecc
        if c.cope=='top':
            mn,pars=single_cope_moment(c.beam.d,h,c.beam.tw,c.cope_length,b.fy,net['S'],net['Z'])
            md=f"k1={pars['k1']:.5f}; λ={pars['lam']:.5f}; λp={pars['lp']:.5f}"
            model='P901 II.A-6; AISC Manual 16 Parte 9; Dowswell (2018)'
            eq='Mn = Mp (λ≤λp); Mp−(Mp−My)(λ/λp−1) (λ≤2λp); 0,903Ek1S/λ² (λ>2λp)'
        else:
            cb=1.0 if N>0 and ecc>1e-9 else 1.84
            mn0,lam=plate_ltb(h,c.beam.tw,c.cope_length,b.fy,Cb=cb)
            mn=mn0*min(net['S']/gross['S'],net['Z']/gross['Z'])
            md=f'λF11={lam:.5f}; Cb={cb:.2f}; redução líquida={mn/mn0:.6f}'
            model='P901 II.A-7; AISC F11; desconto líquido conservador'
            eq='Mn = Mn,F11·min(Sn/Sg; Zn/Zg); Lb = comprimento do recorte'
        mr=mn/g1;nr=min(b.fy*net['A']/g1,b.fu*net['A']/g2)
        vr,cv=web_shear(h,c.beam.tw,b.fy,kv=1.2)
        # Não conta a contribuição da mesa na área de corte. kv=1,2 também limita o recorte duplo.
        vr=min(vr,.6*b.fu*max(0,h-c.n*c.dh_net)*c.beam.tw/g2)
        eta=N/nr+mc/mr+V/vr
        add('cope_interaction','Recorte — flexão, estabilidade, N e V',eta,1,'—',model+'; coeficientes NBR; interação linear conservadora',
            'η = N/NRd + Mc/MRd + V/VRd ≤ 1; '+eq,
            f'Ac,n={net["A"]:.3f}; Sc,n={net["S"]:.3f}; Zc,n={net["Z"]:.3f}; {md}; Mc={mc:.3f}; MRd={mr:.3f}; NRd={nr:.3f}; VRd={vr:.3f}; Cv={cv:.6f}',
            'Ac,n: área líquida; Sc,n e Zc,n: módulos elástico e plástico líquidos; h: altura recortada; c: comprimento; λ=h/tw; λp=0,475√(k1E/fy); k1=max(1,61;fk), conforme referência. Mc=|V|max(g+c; xúltimo)+|N||d/2−yc|; yc: centroide remanescente. Unidades N, mm e MPa. Furos projetados e interação linear conservadores; contenção na raiz exigida.')
        mur=b.fu*net['Z']/g2
        add('cope_rupture','Recorte — ruptura por flexão e tração',mc/mur+N/(b.fu*net['A']/g2),1,'—',
            'NBR 8800:2024, 6.5; complemento AISC Manual Parte 9; interação linear',
            'η = Mc/(fu·Zn/γa2) + N/(fu·An/γa2) ≤ 1',
            f'Mc={mc:.3f}; MRd,u={mur:.3f} Nmm; An={net["A"]:.3f}; Zn={net["Z"]:.3f}',
            'Seção líquida com desconto dos furos. Raio de concordância da seção não contribui para a resistência calculada.')
        edge=c.beam_edge+(c.bolt_columns-1)*c.gauge
        ln=edge-(c.bolt_columns-.5)*c.dh_net
        candidates=[]
        for label,ell in [('superior',max(c.y_bolts)-top)]+([('inferior',c.beam.d-bottom-min(c.y_bolts))] if bottom else []):
            lv=ell-(c.n-.5)*c.dh_net
            rv=block_strength(ell*c.beam.tw,lv*c.beam.tw,ln*c.beam.tw,b.fy,b.fu)
            rn=block_strength(edge*c.beam.tw,ln*c.beam.tw,lv*c.beam.tw,b.fy,b.fu)
            candidates.append(((V/rv)**2+(N/rn)**2,label,rv,rn))
        eta,label,rv,rn=max(candidates)
        add('cope_block','Recorte — ruptura em bloco da alma',eta,1,'—',
            'NBR 8800:2024, 6.5.6; interação AISC Manual 12-1',
            'η = (V/Rv)² + (N/Rn)² ≤ 1',
            f'Borda crítica={label}; Rv={rv:.3f} N; Rn={rn:.3f} N; distância horizontal={edge:.3f} mm',
            'Caminho L entre a extremidade da viga, borda recortada e última linha/coluna de furos. Verifica as duas bordas no recorte duplo; mesma envoltória para os dois sentidos do cortante.')
    return out
