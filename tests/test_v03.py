"""Verificações independentes de equilíbrio, exemplos e fronteiras de domínio."""
from dataclasses import replace
import math
import pytest
from lro.models import Profile,profiles
from lro.examples import presets
from lro.engine import evaluate,bolt_shear,plate_ltb
from lro.local_checks import (elastic_group,pure_moment_coefficient,grip_factor,
    coped_section,single_cope_moment,web_shear,required_development_weld)


def checks(c):return {x.id:x for x in evaluate(c).checks}


@pytest.mark.parametrize('V,N,M',[(11000,2000,1320000),(-11000,2000,-1320000),(0,2000,400000)])
def test_two_column_group_equilibrium(V,N,M):
    f=elastic_group(5,80,2,70,V,N,M)
    coords=[((j-.5)*70,(i-2)*80) for j in range(2) for i in range(5)]
    assert sum(x for x,y in f)==pytest.approx(N)
    assert sum(y for x,y in f)==pytest.approx(V)
    assert sum(x*fy-y*fx for (x,y),(fx,fy) in zip(coords,f))==pytest.approx(M)


def test_published_p901_moment_only_coefficients():
    # P901 II.A-19A/19B, tabelas do Manual; comprimentos originais em polegadas.
    assert pure_moment_coefficient(4,3,2,3)==pytest.approx(26.0,abs=.05)
    assert pure_moment_coefficient(5,3,2,3)==pytest.approx(38.7,abs=.05)


def test_p901_ii_a_6_whole_cope_section():
    # AISC v16 PDF p.620-624, todas as dimensões em polegadas/ksi.
    p=Profile('W21x62','W',1,21,8.24,.400,.615,19,18)
    s=coped_section(p,8,0)
    assert s['Z']==pytest.approx(32.2,abs=.05)
    assert s['S']==pytest.approx(17.8,abs=.08) # integração sem raios; tabela arredondada
    mn,par=single_cope_moment(21,13,.4,9,50,s['S'],s['Z'],E=29000)
    assert par['k1']==pytest.approx(3.47,abs=.02)
    assert mn==pytest.approx(1230,rel=.003)
    assert .9*mn/9.5==pytest.approx(116,abs=1)


def test_p901_ii_a_7_double_cope():
    # Manual F11, II.A-7 PDF p.637-639.
    mn,lam=plate_ltb(10.5,.305,9.5,50,elastic_modulus=29000,Cb=1.94)
    assert mn==pytest.approx(421,abs=1)
    assert .9*mn/10==pytest.approx(37.9,abs=.1)


def test_section_integration_with_holes_conserves_area():
    p=profiles()['W 360 x 39,0']
    g=coped_section(p,25,0);n=coped_section(p,25,0,[(100,120),(170,190)])
    assert g['A']-n['A']==pytest.approx(40*p.tw)
    assert n['I']<g['I'] and n['Z']<g['Z']


def test_long_grip_norm_boundary():
    assert grip_factor(5*19.05,19.05)==1
    assert grip_factor(5*19.05+15,19.05)==pytest.approx(.90)


def test_current_nbr_bolt_strength_not_historical_coefficient():
    expected=.45*math.pi*19.05**2/4*830/1.35
    assert bolt_shear(19.05,830)==pytest.approx(expected)
    assert expected/(.4*math.pi*19.05**2/4*830/1.35)==pytest.approx(1.125)


def test_usi350_development_weld_has_reference_not_pending():
    c=replace(list(presets().values())[1],plate_steel='USI-CIVIL 350')
    r=evaluate(c)
    assert not any(i.severity=='pending' and 'solda' in i.text for i in r.issues)
    assert checks(c)['weld_development'].passed
    assert required_development_weld(8,450,485)>required_development_weld(8,350,485)


def test_g10_on_column_flange_and_actionable_edge_limit():
    c=replace(next(iter(presets().values())),kind='column_flange',a=75,gap=10,restrained=True)
    r=evaluate(c)
    assert r.status=='ATENDE AO ESCOPO VERIFICADO'
    fail=evaluate(replace(c,a=120,gap=40))
    assert any('a − g = 120 − 40 = 80' in i.text and '78' in i.text for i in fail.issues)
    assert evaluate(replace(c,a=120,gap=10)).status=='GEOMETRIA INVÁLIDA'


def test_cope_complete_for_pure_shear_and_braced_beam():
    c=replace(next(iter(presets().values())),a=75,gap=10,cope='top',N=0,restrained=True)
    r=evaluate(c)
    assert r.status=='ATENDE AO ESCOPO VERIFICADO'
    assert all(k in checks(c) for k in ('cope_interaction','cope_rupture','cope_block'))
    assert replace(c,restrained=False).restrained is True
    assert evaluate(replace(c,restrained=False)).status==r.status
    assert evaluate(replace(c,V=1000000)).status=='NÃO ATENDE'


def test_welded_column_assumes_cjp_and_checks_its_base_metal():
    c=replace(list(presets().values())[-1],support=profiles()['CS 600 x 281'],support_steel='ASTM A36')
    assert evaluate(c).status=='ATENDE AO ESCOPO VERIFICADO'
    assert 'support_joint_base' in checks(c)
    assert 'support_joint_weld' not in checks(c)
    assert checks(replace(c,support_joint_weld=6))['support_joint_base'].ratio==checks(c)['support_joint_base'].ratio
    assert not checks(replace(c,V=1000000))['support_joint_base'].passed


def test_sci_punch_alternative_is_linear_and_not_used_with_axial():
    c=replace(next(iter(presets().values())),N=0,restrained=True,plate_steel='ASTM A572 Gr.50')
    r=evaluate(c);ck=checks(c)['support_punch']
    expected=c.support.tw**2*450*c.hp**2/(6*(c.V*r.minimum_factor)*c.a*1.35)
    assert ck.resistance==pytest.approx(expected)
    assert checks(replace(c,N=1))['support_punch'].resistance==pytest.approx(c.support.tw*450/(345*1.35))


def test_buckling_reduces_shear_and_source_limits_are_continuous():
    fy=345;lp=1.1*math.sqrt(5.34*200000/fy)
    r,cv=web_shear(lp*5,5,fy)
    assert cv==pytest.approx(1)
    assert web_shear(lp*5*(1+1e-6),5,fy)[1]<1
    assert web_shear(2000,5,fy)[1]<.1


def test_two_columns_net_cut_deducts_one_vertical_hole_line():
    c=replace(next(iter(presets().values())),kind='column_flange',N=0,restrained=True,bolt_columns=2)
    r=checks(c)
    assert r['plate_vu'].resistance==pytest.approx(.6*400*(c.hp-c.n*c.dh_net)*c.tp/1.35)
    assert len(r)>=24


def test_partial_new_checks_do_not_approve_full_depth_or_web_tension():
    c=replace(next(iter(presets().values())),restrained=True)
    assert evaluate(c).status=='ATENDE ÀS VERIFICAÇÕES REALIZADAS'
    full=evaluate(replace(c,plate_shape='between_flanges',bolt_columns=2))
    assert not full.checks
    assert all(x.id.startswith(('full_','opposite_')) for x in full.checks)
    assert full.status=='GEOMETRIA INVÁLIDA'
