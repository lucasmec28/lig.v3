"""Conferências pontuais de exemplos publicados; não representam validação integral."""
import math
from .engine import elastic_bolts,interaction,plate_ltb,block_strength
from .local_checks import pure_moment_coefficient,single_cope_moment,coped_section
from .models import Profile
from .support_checks import web_yield_lines


def benchmarks():
    values=[]
    def add(name,calc,reference,unit,tol,source):
        values.append(dict(verificação=name,calculado=calc,referência=reference,unidade=unit,erro=abs(calc-reference),tolerância=tol,atende=abs(calc-reference)<=tol,fonte=source))
    f=elastic_bolts(2,75,45000,0,45000*37.5)
    add('Referência · força no parafuso (e = a/2)',max(math.hypot(x,y) for x,y in f)/1000,31.82,'kN',.01,'Anotações de aula, PDF p.4; geometria original, V puro')
    add('Referência · ruptura ao corte da chapa',.6*400*(155-2*22.55)*6.3/1.35/1000,123.0,'kN',.15,'Anotações de aula, PDF p.5; espessura e furação originais')
    add('AISC II.A-17B · interação de escoamento',interaction(60,327,188,1180,75,218),.181,'—',.002,'P901-23W, IIA-187 / PDF p.727')
    add('AISC II.A-17B · interação de ruptura',interaction(60,232,188,840,75,139),.500,'—',.002,'P901-23W, IIA-188 / PDF p.728')
    add('AISC II.A-19B · interação de ruptura',interaction(60,332,731,1260,75,199),.592,'—',.003,'P901-23W, IIA-223 / PDF p.763')
    # Unidades kip/in/ksi para manter os dados originais sem adaptação brasileira.
    mn,_=plate_ltb(15,.75,9.75,50,elastic_modulus=29000,Cb=1.84)
    add('AISC II.A-19B · momento nominal da chapa',mn,2110,'kip·in',2,'P901-23W, IIA-219/220 / PDF p.759–760')
    add('AISC II.A-19B · bloco U da chapa',block_strength(7.5,4.83,5.44,50,65,gamma=1),542,'kip',1,'P901-23W, IIA-226 / PDF p.766; áreas arredondadas do exemplo')
    add('AISC II.A-19A · CIR sob momento puro',pure_moment_coefficient(4,3,2,3),26.0,'in',.05,'P901-23W PDF p.747; coeficiente C′ do Manual')
    add('AISC II.A-19B · CIR sob momento puro',pure_moment_coefficient(5,3,2,3),38.7,'in',.05,'P901-23W PDF p.755; coeficiente C′ do Manual')
    sec=coped_section(Profile('W21x62','W',1,21,8.24,.4,.615,19,18),8,0)
    mn,_=single_cope_moment(21,13,.4,9,50,sec['S'],sec['Z'],E=29000)
    add('AISC II.A-6 · recorte superior, momento nominal',mn,1230,'kip·in',5,'P901-23W PDF p.620–623; integração da seção sem raios')
    mn,_=plate_ltb(10.5,.305,9.5,50,elastic_modulus=29000,Cb=1.94)
    add('AISC II.A-7 · recorte duplo, momento nominal',mn,421,'kip·in',1,'P901-23W PDF p.637–639')
    add('AISC II.A-19B · plastificação da alma',web_yield_lines(5.90,4.73,11.4,15,.440,50,gamma=1)['nominal'],42.4,'kip',.1,'P901-23W PDF p.768 / IIA-228; eq.9-45; dados arredondados publicados')
    add('Kapp · Exemplo 3, placa apoiada',web_yield_lines(1.3125,1.3125,6.125,9,.5,36,gamma=1)['nominal'],69.74,'kip',.05,'Kapp (1974), Engineering Journal 11(2), p.40; eq.8, sem fator de segurança')
    return values
