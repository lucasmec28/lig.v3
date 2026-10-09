from pathlib import Path
from streamlit.testing.v1 import AppTest

APP=Path(__file__).resolve().parents[1]/'app.py'


def test_ui_load_change_and_export():
    at=AppTest.from_file(str(APP),default_timeout=30).run()
    assert not at.exception
    assert any(x.value=='ATENDE ÀS VERIFICAÇÕES REALIZADAS' for x in at.success)
    assert sum('Não é verificada a interação fora do plano' in x.value for x in at.caption)==1
    assert 'support_edge_distance' not in [x.key for x in at.number_input]
    name=next(x for x in at.selectbox(key='example').options if 'CS600' in x)
    at.selectbox(key='example').set_value(name)
    next(x for x in at.button if x.label=='Usar este exemplo').click().run()
    assert not at.exception
    assert any('ATENDE AO ESCOPO' in x.value for x in at.success)
    next(x for x in at.button if x.label=='Gerar memória Word').click().run()
    assert not at.exception
    initial_report=at.session_state['report']
    assert initial_report[2][:2]==b'PK'
    assert len(initial_report[2])>15000
    at.number_input(key='pitch').set_value(20.).run()
    assert not at.exception
    assert any('GEOMETRIA INVÁLIDA' in x.value for x in at.error)
    assert next(x for x in at.button if x.label=='Gerar memória Word').disabled
    # Relatório antigo não pode continuar disponível após alteração das entradas.
    assert not any(getattr(x,'label','')=='Baixar memória .docx' for x in at.get('download_button'))


def test_profile_change_applies_visible_material_default():
    at=AppTest.from_file(str(APP),default_timeout=30).run()
    at.selectbox(key='support_name').set_value('CS 600 x 281').run()
    assert not at.exception
    assert at.selectbox(key='support_steel').value=='ASTM A36'
    at.selectbox(key='kind').set_value('column_flange').run()
    assert not at.exception


def test_saved_project_import_callback():
    import json
    from lro.examples import presets
    sample=list(presets().values())[1]
    at=AppTest.from_file(str(APP),default_timeout=30).run()
    at.get('file_uploader')[0].upload('projeto.json',json.dumps(sample.to_dict()).encode(),'application/json').run()
    next(x for x in at.button if x.label=='Abrir arquivo').click().run()
    assert not at.exception
    assert at.text_input(key='project').value==sample.project
    assert at.number_input(key='V_kgf').value==sample.V/9.80665


def test_plate_position_visible_manual_and_invalid():
    at=AppTest.from_file(str(APP),default_timeout=30).run()
    z=at.number_input(key='plate_top').value
    assert at.number_input(key='plate_top').disabled
    at.checkbox(key='center_plate').uncheck().run()
    assert not at.number_input(key='plate_top').disabled
    assert at.number_input(key='plate_top').value==z
    at.number_input(key='plate_top').set_value(40.).run()
    assert not at.exception
    assert at.number_input(key='plate_top').value==40
    at.number_input(key='plate_top').set_value(-1.).run()
    assert any('GEOMETRIA INVÁLIDA' in x.value for x in at.error)


def test_removed_full_depth_import_cannot_be_reinterpreted():
    import json
    from dataclasses import replace
    from lro.examples import presets
    legacy=replace(next(iter(presets().values())),plate_shape='between_flanges')
    at=AppTest.from_file(str(APP),default_timeout=30).run()
    assert not any(x.key in ('plate_shape','restrained','opposite_stiffener','support_joint_weld') for x in [*at.selectbox,*at.checkbox,*at.number_input])
    at.get('file_uploader')[0].upload('antigo.json',json.dumps(legacy.to_dict()).encode(),'application/json').run()
    next(x for x in at.button if x.label=='Abrir arquivo').click().run()
    assert not at.exception
    assert any('variante retirada' in x.value for x in at.error)
    assert at.session_state['plate_shape']=='rectangular'


def test_usi_options_follow_product_type():
    at=AppTest.from_file(str(APP),default_timeout=30).run()
    assert 'USI-CIVIL 300' in at.selectbox(key='plate_steel').options
    assert 'USI-CIVIL 350' not in at.selectbox(key='beam_steel').options
    at.selectbox(key='support_name').set_value('CS 600 x 281').run()
    assert 'USI-CIVIL 350' in at.selectbox(key='support_steel').options
