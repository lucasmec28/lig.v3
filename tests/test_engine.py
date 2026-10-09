from dataclasses import replace
import math
import json
import pytest
from lro.models import Connection,KGF
from lro.engine import evaluate,elastic_bolts,geometry,plate_ltb,interaction
from lro.examples import presets
from lro.benchmarks import benchmarks


@pytest.fixture
def referencia():return list(presets().values())[1]


@pytest.mark.parametrize('row',benchmarks(),ids=lambda x:x['verificação'])
def test_published_component_benchmarks(row):
    assert row['atende'],row


@pytest.mark.parametrize('V,N,M',[(10000,2000,1400000),(-10000,2000,-1400000),(0,80000,0),(10000,0,0)])
def test_bolt_group_equilibrium(V,N,M):
    forces=elastic_bolts(5,70,V,N,M)
    assert sum(x for x,y in forces)==pytest.approx(N)
    assert sum(y for x,y in forces)==pytest.approx(V)
    recovered=sum(-((i-2)*70)*fx for i,(fx,fy) in enumerate(forces))
    assert recovered==pytest.approx(M)


def test_no_extra_factoring_and_minimum_case(referencia):
    c=replace(referencia,V=11000,N=2000,restrained=True)
    r=evaluate(c)
    assert (c.V,c.N)==(11000,2000)
    assert math.hypot(c.V*r.minimum_factor,c.N*r.minimum_factor)==pytest.approx(45000)
    assert r.actual[0].case=='Entrada'
    assert r.checks[0].case=='Mínimo normativo de 45 kN'
    assert r.checks[0].demand/r.actual[0].demand==pytest.approx(r.minimum_factor)


def test_catalog_and_units_roundtrip(referencia):
    from lro.models import profiles
    catalog=profiles()
    assert len(catalog)==560
    assert len([k for k in catalog if k.startswith('VS 300 x 28')])==2
    restored=Connection.from_dict(json.loads(json.dumps(referencia.to_dict())))
    assert restored==referencia
    assert 11000/KGF==pytest.approx(1121.687834,abs=1e-6)
    assert evaluate(restored).checks==evaluate(referencia).checks


def test_at_limit_no_rounding():
    from lro.models import Check
    c=Check('x','x',1.00001,1,'—','','','', '')
    assert not c.passed


@pytest.mark.parametrize('field,value',[('n',1),('pitch',0),('tp',0),('V',float('nan')),('N',float('inf')),('gap',100),('plate_top',-10),('db',18)])
def test_invalid_input_blocks_calculation(referencia,field,value):
    r=evaluate(replace(referencia,**{field:value}))
    assert r.status=='GEOMETRIA INVÁLIDA'
    assert not r.checks


def test_user_case_reports_only_performed_checks_with_explicit_exclusion():
    c=replace(next(iter(presets().values())),restrained=True)
    r=evaluate(c)
    assert r.status=='ATENDE ÀS VERIFICAÇÕES REALIZADAS'
    assert any(i.severity=='excluded' and 'fora do plano' in i.text for i in r.issues)


def test_compression_never_reinterpreted_as_tension(referencia):
    r=evaluate(replace(referencia,N=-2000))
    assert r.status=='VERIFICAÇÃO INCOMPLETA'
    assert not r.checks


def test_no_cope_detects_flange_interference():
    c=replace(next(iter(presets().values())),gap=10,a=75)
    assert any(i.severity=='error' and 'mesa superior' in i.text for i in evaluate(c).issues)


def test_cope_pure_shear_with_fixed_restraint_is_in_scope():
    c=replace(next(iter(presets().values())),gap=10,a=75,cope='top',cope_length=80,cope_top=25,N=0)
    r=evaluate(c)
    assert not any(i.severity=='error' for i in r.issues)
    assert r.status=='ATENDE AO ESCOPO VERIFICADO'
    assert r.geometry['e']==75


def test_spacing_exact_boundary(referencia):
    minimum=2.7*referencia.db
    low=evaluate(replace(referencia,pitch=minimum-.0001))
    exact=evaluate(replace(referencia,pitch=minimum))
    assert any('Passo p =' in i.text for i in low.issues)
    assert not any('Passo p =' in i.text for i in exact.issues)


def test_35mm_is_not_automatically_a_valid_method(referencia):
    r=evaluate(replace(referencia,edge_h=35))
    ck=next(x for x in r.checks if x.id=='ductility')
    assert ck.resistance>0
    assert ck.category=='Condição do método'
    assert not any('tabela 16' in i.text for i in r.issues)


def test_norm_hole_and_bolt_update(referencia):
    from lro.engine import bolt_shear
    assert referencia.dh==pytest.approx(20.6375)
    assert referencia.dh_net==pytest.approx(22.6375)
    assert replace(referencia,drilled=True).dh_net==pytest.approx(20.6375)
    assert bolt_shear(19.05,830)==pytest.approx(78856.88545029,rel=.0001)


def test_force_scaling_and_sign(referencia):
    small=evaluate(referencia);large=evaluate(replace(referencia,V=90000));negative=evaluate(replace(referencia,V=-45000))
    assert large.checks[0].demand==pytest.approx(2*small.checks[0].demand)
    assert [x.ratio for x in small.checks]==pytest.approx([x.ratio for x in negative.checks])


def test_weld_and_actual_support_thickness():
    c=next(iter(presets().values()));r=evaluate(c)
    assert r.geometry['ts']==c.support.tw
    assert evaluate(replace(c,kind='column_flange')).geometry['ts']==c.support.tf
    assert any('Filete inferior' in i.text for i in evaluate(replace(c,weld=3)).issues)


def test_zero_load_is_not_approved(referencia):
    assert evaluate(replace(referencia,V=0,N=0)).status=='VERIFICAÇÃO INCOMPLETA'


def test_minimum_deactivation_is_explicit(referencia):
    r=evaluate(replace(referencia,norm_minimum=False))
    assert any(i.severity=='pending' and '45 kN' in i.text for i in r.issues)


def test_reference_detects_new_conservative_column_yield_limit(referencia):
    r=evaluate(referencia)
    assert r.status=='NÃO ATENDE'
    failed=[x for x in r.checks if not x.passed]
    assert [x.id for x in failed]==['support_web_y']
    assert failed[0].ratio==pytest.approx(1.0103452672490731)
    assert len(r.checks)>=20


def test_material_product_restriction(referencia):
    assert evaluate(replace(referencia,plate_steel='ASTM A992')).status=='GEOMETRIA INVÁLIDA'


def test_welded_beam_cannot_use_rolled_only_steel(referencia):
    welded=replace(referencia.beam,family='Soldado')
    assert evaluate(replace(referencia,beam=welded,beam_steel='ASTM A992')).status=='GEOMETRIA INVÁLIDA'


def test_failed_report_never_claims_all_checks_pass(referencia):
    from io import BytesIO
    from docx import Document
    from lro.report import create_report
    overloaded=replace(referencia,V=450000)
    result=evaluate(overloaded)
    assert result.status=='NÃO ATENDE'
    document=Document(BytesIO(create_report(overloaded,result)))
    text='\n'.join(p.text for p in document.paragraphs)
    assert 'A ligação não atende' in text
    assert 'As verificações locais incluídas nesta versão atendem' not in text


def test_higher_steel_does_not_silently_extend_weld_method(referencia):
    r=evaluate(replace(referencia,plate_steel='ASTM A572 Gr.65'))
    ck=next(x for x in r.checks if x.id=='weld_development')
    assert ck.demand>referencia.weld
    assert not ck.passed


def test_ltb_all_branches_are_positive_and_capped():
    fy=250;Mp=fy*8*200**2/4
    values=[plate_ltb(200,8,L,fy)[0] for L in [1,30,2000]]
    assert all(0<x<=Mp for x in values)
    assert values==sorted(values,reverse=True)


@pytest.mark.parametrize('name,fy,fu',[('USI-CIVIL 300',300,400),('USI-CIVIL 350',350,500)])
def test_usi_catalog_and_thickness_boundaries(name,fy,fu):
    from lro.models import STEELS
    s=STEELS[name]
    assert (s.fy,s.fu,s.plate_min,s.plate_max)==(fy,fu,6,75)
    c=replace(next(iter(presets().values())),plate_steel=name,tp=5.9)
    assert any('Chapa: produto' in i.text for i in evaluate(c).issues)
    assert not any('Chapa: produto' in i.text for i in evaluate(replace(c,tp=6)).issues)
    assert not any('Chapa: produto' in i.text for i in evaluate(replace(c,tp=75)).issues)
    assert any('Chapa: produto' in i.text for i in evaluate(replace(c,tp=75.001)).issues)


def test_usi_welded_section_checks_web_as_well_as_flange():
    c=next(iter(presets().values()))
    assert any('Viga: produto' in i.text for i in evaluate(replace(c,beam_steel='USI-CIVIL 300')).issues)
    c=replace(c,beam=replace(c.beam,family='Soldado',tw=5.9),beam_steel='USI-CIVIL 300')
    assert any('Viga: produto' in i.text for i in evaluate(c).issues)
    assert not any('Viga: produto' in i.text for i in evaluate(replace(c,beam=replace(c.beam,tw=6))).issues)


def test_manual_plate_position_changes_axial_moment(referencia):
    c=replace(referencia,N=2000,restrained=True,plate_top=(referencia.beam.d-referencia.hp)/2)
    raised=replace(c,plate_top=c.plate_top-20)
    before=evaluate(c);after=evaluate(raised)
    assert not any(x.severity=='error' for x in after.issues)
    assert raised.eccentric_n==pytest.approx(20)
    mb=next(x.demand for x in before.actual if x.id=='plate_mu')
    ma=next(x.demand for x in after.actual if x.id=='plate_mu')
    assert ma-mb==pytest.approx(40000)


def test_removed_variant_still_preserves_legacy_geometry_without_approving_it():
    from lro.detailing import plate_outline,polygon_area
    c=replace(next(iter(presets().values())),plate_shape='between_flanges')
    pts=plate_outline(c)
    assert min(y for x,y in pts)==c.support.tf
    assert max(y for x,y in pts)==c.support.d-c.support.tf
    assert polygon_area(pts)==pytest.approx(c.root_width*c.root_height-c.corner_clip**2+(c.width-c.root_width)*c.hp)
    for variant in (c,replace(c,opposite_stiffener=True)):
        result=evaluate(variant)
        assert not result.checks and not result.actual
        assert any(i.severity=='error' and 'não são avaliados' in i.text for i in result.issues)


@pytest.mark.parametrize('changes,text',[
    ({'root_width':72},'ponta da viga'),
    ({'corner_clip':5},'Alívio de canto insuficiente'),
    ({'opposite_stiffener':True,'stiffener_width':100},'Largura do enrijecedor'),
    ({'kind':'column_flange'},'apenas na alma'),
    ({'flange_weld':2},'Solda às mesas'),
    ({'opposite_stiffener':True,'stiffener_weld':2},'Filete do enrijecedor'),
])
def test_full_depth_interference_and_weld_gates(changes,text):
    c=replace(next(iter(presets().values())),plate_shape='between_flanges',**changes)
    r=evaluate(c)
    assert any(x.severity=='error' and 'variante retirada' in x.text for x in r.issues)
    assert not r.checks


def test_two_columns_roundtrip_and_calculation():
    c=replace(next(iter(presets().values())),bolt_columns=2)
    assert c.bolt_centroid_x==155
    assert c.width==230
    assert c.x_bolts==[120,190]
    assert Connection.from_dict(c.to_dict())==c
    assert evaluate(c).checks
    assert evaluate(c).status=='ATENDE ÀS VERIFICAÇÕES REALIZADAS'
    assert evaluate(replace(c,gauge=10)).status=='GEOMETRIA INVÁLIDA'


def test_removed_variant_cannot_export_a_new_resistance_report():
    from lro.report import create_report
    c=replace(next(iter(presets().values())),plate_shape='between_flanges',opposite_stiffener=True)
    with pytest.raises(ValueError,match='não são avaliados'):
        create_report(c,evaluate(c))


def test_schema1_preserves_old_geometry_loads_and_normalizes_catalog(referencia):
    d=referencia.to_dict();d['schema_version']=1;d['app_version']='0.1.0'
    for key in ('plate_shape','root_width','corner_clip','flange_weld','opposite_stiffener','stiffener_t','stiffener_width','stiffener_weld','stiffener_steel','bolt_columns','gauge'):
        d['connection'].pop(key)
    d['connection']['beam']['source']='Descrição antiga do catálogo'
    d['connection']['project']='Exemplo antigo adaptado à V1'
    c=Connection.from_dict(d)
    assert (c.plate_top,c.V,c.N,c.beam.d,c.tp)==(referencia.plate_top,referencia.V,referencia.N,referencia.beam.d,referencia.tp)
    assert c.beam.source==referencia.beam.source
    assert c.project=='Exemplo de referência adaptado'


def test_import_cannot_treat_text_false_as_boolean_true(referencia):
    assert evaluate(replace(referencia,restrained="false")).status=="GEOMETRIA INVÁLIDA"
