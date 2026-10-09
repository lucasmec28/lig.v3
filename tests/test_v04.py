"""Equilíbrio, publicação independente e barreiras de conclusão da candidata."""
from dataclasses import replace
from pathlib import Path
import json
import math
import pytest
from lro.models import Connection
from lro.examples import presets
from lro.engine import evaluate
from lro.support_checks import WeldLine,elastic_weld_group,web_yield_lines,web_patch,full_depth_weld_lines


def user_case():
    return Connection.from_dict(json.loads((Path(__file__).parents[1]/'examples/Teste_usuario_v03_original.json').read_text()))


def test_aics_manual_945_published_column_example():
    r=web_yield_lines(5.90,4.73,11.4,15,.440,50,gamma=1)
    assert r['nominal']==pytest.approx(42.4,abs=.1)
    assert r['resistance']==r['nominal']


def test_kapp_published_supported_doubler_and_affected_length():
    r=web_yield_lines(1.3125,1.3125,6.125,9,.5,36,gamma=1)
    assert r['nominal']==pytest.approx(69.74,abs=.01)
    assert r['spread']==pytest.approx(1.3125*math.sqrt(2+3.5/1.3125))


def test_beam_web_orientation_and_plate_position():
    c=user_case();r=web_patch(c)
    a=c.beam_level+c.plate_top-c.support.tf
    b=c.support.d-c.support.tf-c.beam_level-c.plate_top-c.hp
    assert a+b+c.hp==pytest.approx(c.root_height)
    assert r==web_yield_lines(a,b,c.root_height,c.tp,c.support.tw,345)
    # Trocar L por hp reproduziria uma coluna, não esta alma de viga.
    wrong=web_yield_lines(a,b,c.root_height,c.hp,c.support.tw,345)
    assert wrong['resistance']>r['resistance']
    assert web_patch(replace(c,plate_top=c.plate_top-15))['resistance']!=r['resistance']


@pytest.mark.parametrize('factor', [.5,2,10])
def test_yieldline_units_scaling(factor):
    r=web_yield_lines(60,100,380,8,6.4,345)
    scaled=web_yield_lines(60*factor,100*factor,380*factor,8*factor,6.4*factor,345)
    assert scaled['resistance']==pytest.approx(factor**2*r['resistance'])
    assert scaled['spread']==pytest.approx(factor*r['spread'])


@pytest.mark.parametrize('forces',[(11000,2000,1320000),(-11000,2000,-1320000),(0,45000,0)])
def test_weld_group_integrated_force_and_moment_equilibrium(forces):
    c=replace(user_case(),plate_shape='between_flanges',flange_weld=6)
    fx,fy,moment=forces
    r=elastic_weld_group(full_depth_weld_lines(c),fx,fy,moment)
    assert (r['fx'],r['fy'],r['moment'])==pytest.approx((fx,fy,moment),abs=1e-8)


def test_weld_group_matches_known_two_vertical_fillets():
    h=220;w=5;N=2000;V=11000;M=1320000
    r=elastic_weld_group([WeldLine('dupla',0,0,0,h,w)],N,V,M)
    old_q=math.hypot(N/(2*h)+3*M/h**2,V/(2*h))
    assert r['lines'][0]['stress']==pytest.approx(old_q/(w/math.sqrt(2)))
    assert r['lines'][0]['q']==pytest.approx(2*old_q)


def test_weld_group_rigid_translation_and_linear_load_scaling():
    lines=[WeldLine('a',0,0,0,220,5),WeldLine('b',20,0,60,0,6)]
    r=elastic_weld_group(lines,2000,11000,1320000)
    shifted=[replace(l,x1=l.x1+123,y1=l.y1-45,x2=l.x2+123,y2=l.y2-45) for l in lines]
    s=elastic_weld_group(shifted,4000,22000,2640000)
    assert s['xc']==pytest.approx(r['xc']+123)
    assert s['yc']==pytest.approx(r['yc']-45)
    assert s['J']==pytest.approx(r['J'])
    assert [x['stress'] for x in s['lines']]==pytest.approx([2*x['stress'] for x in r['lines']])


def test_old_project_preserves_loads_geometry_and_applies_requested_fixed_restraint():
    c=user_case();r=evaluate(c)
    assert c.a==120 and c.gap==80 and c.N==pytest.approx(2000) and c.V==11000
    assert c.restrained is True and c.support_edge_distance==0
    assert c.to_dict()["fixed_assumptions"]["contained_supported_beam"] is True
    assert r.status=='ATENDE ÀS VERIFICAÇÕES REALIZADAS'
    assert not {'support_web_n','support_web_punch_n'} & {x.id for x in r.checks}


def test_centered_pure_tension_needs_space_and_combined_mechanism_is_excluded():
    c=replace(user_case(),V=0,restrained=True,support_edge_distance=1000)
    r=evaluate(c)
    assert r.status=='ATENDE AO ESCOPO VERIFICADO'
    assert evaluate(replace(c,support_edge_distance=0)).status=='VERIFICAÇÃO INCOMPLETA'
    assert evaluate(replace(c,V=11000)).status=='ATENDE ÀS VERIFICAÇÕES REALIZADAS'
    assert any('N excêntrico' in i.text for i in evaluate(replace(c,plate_top=c.plate_top-10)).issues)


def test_removed_full_depth_has_no_resistance_or_approval():
    c=replace(user_case(),plate_shape='between_flanges')
    r=evaluate(c)
    assert r.status=='GEOMETRIA INVÁLIDA'
    assert not r.checks and not r.actual
    assert any('variante retirada' in i.text for i in r.issues)


def test_zero_weld_length_and_invalid_yieldline_are_rejected():
    with pytest.raises(ValueError):elastic_weld_group([WeldLine('x',0,0,0,0,5)],1,2,3)
    with pytest.raises(ValueError):web_yield_lines(-1,100,380,8,6.4,345)
    with pytest.raises(ValueError):web_yield_lines(300,100,380,8,6.4,345)
