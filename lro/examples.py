from dataclasses import replace
from .models import Connection, profiles


def presets():
    ps=profiles()
    beam=ps['W 360 x 39,0'];main=ps['W 410 x 38,8']
    common=Connection(beam=beam,support=main,kind='beam_web',a=120,gap=80,plate_top=(beam.d-220)/2)
    referencia=Connection(beam=ps['W 310 x 21,0'],support=ps['W 150 x 22,5 (H)'],n=2,pitch=75,edge_v=40,edge_h=40,a=75,gap=10,tp=7.9375,weld=5,plate_top=35,V=45000,N=0,project='Exemplo de referência adaptado à V1',notes='Referência: Anotações de aula, p.4–7. Chapa alterada de 6,3 mm para 5/16\" e procedimento geral e=a. Comparações dos componentes originais em Validação.')
    referencia=replace(referencia,a=70,notes=referencia.notes+' Folga g = 10 mm preservada; a = 70 mm para respeitar a borda máxima na alma de 5,1 mm.')
    return {
        'Seu caso · W360×39 → W410×38,8':common,
        'Referência · W310×21 → mesa W150×22,5':referencia,
        'Viga–viga · g = 10 mm com recorte superior':replace(common,gap=10,a=75,cope='top',cope_length=80,cope_top=25,project='Viga–viga com recorte e g = 10 mm'),
        'W410 → CS600×281 · perfil com penetração total':replace(common,beam=main,support=ps['CS 600 x 281'],support_steel='ASTM A36',kind='column_flange',a=75,gap=10,plate_top=(main.d-220)/2,project='Exemplo com CS600×281 — perfil com penetração total'),
        'Viga → mesa de pilar W · 11 kN + 2 kN':replace(common,beam=main,support=ps['W 310 x 97,0 (H)'] if 'W 310 x 97,0 (H)' in ps else ps['W 150 x 22,5 (H)'],kind='column_flange',a=75,gap=10,plate_top=(main.d-220)/2),
    }
