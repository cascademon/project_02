"""Offline regression checks against notebook definitions, never its demo cells."""
import ast
import json
import os
import re
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, TypedDict
from unittest.mock import Mock

import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from langchain_core.messages import HumanMessage, SystemMessage

ROOT = Path(__file__).parent
NOTEBOOK = Path(os.environ.get('LECTURE_NOTEBOOK', ROOT / 'lecture_agent.ipynb'))
BOOK = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
VALID_QUIZZES = {'quizzes':[
    {'question':f'문제 {i}', 'answer':'O' if i != 2 else 'X', 'explanation':f'근거 {i}'}
    for i in range(1,4)
]}

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setenv('LANGCHAIN_TRACING_V2', 'false')
    monkeypatch.setenv('LANGSMITH_TRACING', 'false')
    monkeypatch.setattr(socket.socket, 'connect', Mock(side_effect=AssertionError('Network disabled in offline tests')))

@pytest.fixture
def ns():
    scope = dict(globals())
    scope['State'] = dict
    for cell in BOOK['cells']:
        src = ''.join(cell['source'])
        if cell['cell_type'] != 'code' or src.lstrip().startswith(('!', '%')):
            continue
        tree = ast.parse(src)
        definitions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        exec(compile(ast.Module(body=definitions, type_ignores=[]), str(NOTEBOOK), 'exec'), scope)
    scope['llm'] = Mock()
    scope['llm'].bind.return_value = scope['llm']
    def reply(messages):
        content = json.dumps(VALID_QUIZZES,ensure_ascii=False) if 'JSON 객체만' in messages[0].content else '테스트 대본'
        return SimpleNamespace(content=content, response_metadata={'finish_reason':'stop'},
                               usage_metadata={'input_tokens':10,'output_tokens':20})
    scope['llm'].invoke.side_effect = reply
    scope['tavily_tool'] = Mock()
    scope['tavily_tool'].invoke.return_value = [{'title':'source','content':'context','url':'https://example.com'}]
    return scope

def test_python_cells_parse():
    for cell in BOOK['cells']:
        src = ''.join(cell['source'])
        if cell['cell_type'] == 'code' and not src.lstrip().startswith(('!', '%')):
            ast.parse(src)

def test_state_declares_search_context(ns):
    assert 'cur_search_context' in ns['State'].__annotations__

def test_scripts_accumulated_once(ns, tmp_path):
    state = dict(slide_idx=0, work_dir=str(tmp_path), cur_page_content='page', scripts=[],
                 page_contents=[], audios=[], videos=[], cur_audio='audio', cur_video='video')
    ns['node_generate_script'](state)
    ns['node_accumulate_and_step'](state)
    assert state['scripts'] == ['테스트 대본']
    assert state['slide_idx'] == 1

def test_previous_script_used(ns, tmp_path):
    state = dict(slide_idx=1, work_dir=str(tmp_path), scripts=['previous page'], cur_page_content='next page')
    ns['node_generate_script'](state)
    assert 'previous page' in ns['llm'].invoke.call_args.args[0][1].content

def test_empty_ppt_rejected(ns, tmp_path):
    ppt = tmp_path / 'empty.pptx'
    Presentation().save(ppt)
    with pytest.raises(ValueError):
        ns['node_parse_all']({'pptx_path':str(ppt), 'work_dir':str(tmp_path)})

@pytest.mark.parametrize('idx,expected', [(0,'CONTINUE'),(2,'DONE')])
def test_loop_boundary(ns, idx, expected):
    assert ns['router_continue_or_done']({'slide_idx':idx,'n_slides':2}) == expected

def test_search_failure_is_local_fallback(ns):
    ns['tavily_tool'].invoke.side_effect = RuntimeError('test failure')
    assert '오류' in ns['web_search_by_title']('topic')

def test_quiz_uses_summary_and_requests_answers(ns):
    state = ns['node_generate_quizzes']({'summary':'summary marker'})
    messages = ns['llm'].invoke.call_args.args[0]
    assert 'summary marker' in messages[1].content
    assert '3개' in messages[0].content and '정답' in messages[0].content
    assert len(state['quiz_items']) == 3
    assert state['quizzes'].count('</details>') == 3

def test_missing_upload(ns):
    class UIError(Exception): pass
    ns['gr'] = SimpleNamespace(Error=UIError)
    with pytest.raises(UIError):
        ns['run_pipeline_ui'](None, 'tone', 'alloy')

def test_snapshot_page_selection(ns, tmp_path, monkeypatch):
    ppt = tmp_path / 'input.pptx'
    ppt.touch()
    commands = []
    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        if cmd[0] == 'soffice':
            (tmp_path / 'input.pdf').touch()
        elif cmd[0] == 'pdftoppm':
            Path(cmd[-1] + '.png').touch()
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(subprocess, 'run', fake_run)
    out = ns['export_slide_as_png']({'pptx_path':str(ppt),'work_dir':str(tmp_path),'slide_idx':9})
    cmd = commands[-1]
    assert cmd[cmd.index('-f')+1] == '10'
    assert cmd[cmd.index('-l')+1] == '10'
    assert '-singlefile' in cmd
    assert Path(out['slide_image']).name == 'slide_010.png'

def test_empty_concat_rejected(ns, tmp_path):
    with pytest.raises(ValueError):
        ns['concat_videos_ffmpeg']([], str(tmp_path/'out.mp4'))

def test_concat_quote_and_order(ns, tmp_path, monkeypatch):
    videos = [tmp_path / "a'b.mp4", tmp_path / 'second.mp4']
    for video in videos: video.touch()
    monkeypatch.setattr(subprocess, 'check_call', Mock())
    output = str(tmp_path/'full.mp4')
    ns['concat_videos_ffmpeg']([str(v) for v in videos], output)
    lines = Path(output+'.txt').read_text(encoding='utf-8').splitlines()
    assert "'\\''" in lines[0]
    assert 'second.mp4' in lines[1]

def test_no_saved_secrets_or_outputs():
    for cell in BOOK['cells']:
        if cell['cell_type'] == 'code':
            assert not cell.get('outputs')
            source = ''.join(cell['source'])
            assert not re.search(r"print\(os\.environ\[.*API_KEY.*\]\[:", source)

def test_graph_search_survives_state_and_many_slides(ns, tmp_path):
    # Real LangGraph runtime; replace external API and media nodes only.
    seen = []
    def parse(state):
        state.update(slides=[{'title':f'page{i}'} for i in range(5)], n_slides=5, slide_idx=0,
                     scripts=[], page_contents=[], audios=[], videos=[])
        return state
    def gen_page(state):
        seen.append(state.get('cur_search_context'))
        state['cur_page_content'] = 'page'
        return state
    def tts(state):
        state['cur_audio'] = 'fake.mp3'
        return state
    def video(state):
        state['cur_video'] = 'fake.mp4'
        return state
    def concat(state):
        state['last_video'] = 'fake_full.mp4'
        return state
    ns.update(node_parse_all=parse, node_generate_page_content=gen_page,
              node_tts=tts, node_make_video=video, node_concat=concat)
    graph_src = next(''.join(c['source']) for c in BOOK['cells'] if 'builder = StateGraph(State)' in ''.join(c['source']))
    exec(graph_src, ns)
    result = ns['app'].invoke({'work_dir':str(tmp_path),'prompt':{}}, config={'recursion_limit':40})
    assert len(seen) == 5 and all(s and 'context' in s for s in seen)
    assert len(result['scripts']) == 5
    assert result['slide_idx'] == 5
    assert result['summary'] and result['quizzes']

def test_ui_uses_slide_dependent_recursion_budget():
    source = ''.join(BOOK['cells'][112]['source'])
    assert 'recursion_limit' in source
    assert 'uuid.uuid4()' in source

def test_real_ffmpeg_render_and_concat(ns, tmp_path, monkeypatch):
    import imageio_ffmpeg
    import wave
    from PIL import Image
    executable = imageio_ffmpeg.get_ffmpeg_exe()
    audio = tmp_path / 'tone.wav'
    with wave.open(str(audio), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes(b'\x00\x00' * 8000)
    image = tmp_path / 'slide.png'
    Image.new('RGB', (320,180), 'white').save(image)
    ns['ffprobe_duration'] = lambda path: 0.5
    original_call = subprocess.check_call
    def call(cmd):
        assert cmd[0] == 'ffmpeg'
        return original_call([executable] + cmd[1:], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    monkeypatch.setattr(subprocess, 'check_call', call)
    clips = [tmp_path / "one's.mp4", tmp_path / 'two.mp4']
    for clip in clips:
        ns['render_mp4'](str(image),str(audio),str(clip),width=320,height=180)
    output = tmp_path / 'joined.mp4'
    ns['concat_videos_ffmpeg']([str(c) for c in clips], str(output))
    decoded = subprocess.run([executable,'-v','error','-i',str(output),'-f','null','-'], capture_output=True)
    assert decoded.returncode == 0 and output.stat().st_size > 1000

def test_search_query_includes_slide_body(ns):
    slide = {'title':'머신러닝의 개념 변화', 'texts':['시간에 따라 데이터 분포가 변하여 예측 성능이 달라집니다.']}
    ns['node_tool_search']({'slides':[slide], 'slide_idx':0})
    query = ns['tavily_tool'].invoke.call_args.args[0]['query']
    assert '데이터 분포' in query
    assert len(query) <= 381

def test_search_query_table_fallback(ns):
    assert '데이터 분포' in ns['build_slide_query']({'title':'변화','tables':[[['데이터 분포','시간']]]})

def test_script_prompt_keeps_original_source(ns, tmp_path):
    state = {'slide_idx':0,'work_dir':str(tmp_path),'scripts':[],
             'slides':[{'title':'개념 변화','texts':['데이터 분포 변화']}],
             'cur_page_content':'잘못된 역사 설명'}
    ns['node_generate_script'](state)
    prompt = ns['llm'].invoke.call_args.args[0][1].content
    assert '데이터 분포 변화' in prompt
    assert '주제 판단의 최우선 근거' in prompt
    assert '짧게 작성' in prompt

@pytest.mark.parametrize('reason', ['length','content_filter'])
def test_incomplete_completion_rejected(ns, reason):
    ns['llm'].invoke.side_effect = None
    ns['llm'].invoke.return_value = SimpleNamespace(content='partial',response_metadata={'finish_reason':reason})
    state = {}
    with pytest.raises(ValueError):
        ns['invoke_checked_llm'](state,'test',[SystemMessage(content='test')],100)
    assert state['generation_meta']['test']['finish_reason'] == reason

@pytest.mark.parametrize('content', ['', '  ', []])
def test_empty_or_unsupported_response_rejected(ns, content):
    ns['llm'].invoke.side_effect = None
    ns['llm'].invoke.return_value = SimpleNamespace(content=content,response_metadata={'finish_reason':'stop'})
    with pytest.raises(ValueError):
        ns['invoke_checked_llm']({},'test',[],100)

@pytest.mark.parametrize('value', [
    '{"quizzes":[', '{"quizzes":[]}', '{"quizzes":null}',
    json.dumps({'quizzes':VALID_QUIZZES['quizzes'][:2]}),
    json.dumps({'quizzes':[{'question':'q','answer':'maybe','explanation':'e'}]*3}),
    json.dumps({'quizzes':[{'question':'q','answer':'O','explanation':'e'}]*3}),
    json.dumps({'quizzes':[{'question':'q','answer':'O','explanation':''}]*3}),
])
def test_malformed_quiz_rejected(ns, value):
    with pytest.raises(ValueError): ns['parse_quizzes'](value)

def test_quiz_rendering_escapes_model_html(ns):
    items = [dict(item) for item in VALID_QUIZZES['quizzes']]
    items[0]['question'] = '<script>alert(1)</script>'
    items[0]['explanation'] = '</details><img src=x onerror=alert(1)>'
    rendered = ns['render_quizzes'](items)
    assert '<script>' not in rendered and '<img ' not in rendered
    assert rendered.count('<details>') == rendered.count('</details>') == 3

def test_quiz_error_clears_previous_result(ns):
    state = {'summary':'', 'quizzes':'old quiz', 'quiz_items':['old']}
    with pytest.raises(ValueError): ns['node_generate_quizzes'](state)
    assert 'quizzes' not in state and 'quiz_items' not in state

def test_usage_is_recorded(ns):
    state = {}
    ns['invoke_checked_llm'](state,'test',[SystemMessage(content='test')],900)
    assert state['generation_meta']['test'] == {'finish_reason':'stop','input_tokens':10,'output_tokens':20}
    ns['llm'].bind.assert_called_with(max_tokens=900)

def test_generation_rules_preserve_uncertainty_and_first_slide(ns):
    ns['invoke_checked_llm']({'slide_idx':0},'script',[SystemMessage(content='대본 작성')],1400)
    prompt = ns['llm'].invoke.call_args.args[0][0].content
    assert '확실성 수준을 유지' in prompt
    assert '권위 표현을 사용하지 않는다' in prompt
    assert '존재하지 않는 앞선 설명' in prompt

def test_first_slide_rule_not_applied_to_later_slide(ns):
    ns['invoke_checked_llm']({'slide_idx':1},'script',[SystemMessage(content='대본 작성')],1400)
    assert '첫 슬라이드다' not in ns['llm'].invoke.call_args.args[0][0].content

def test_libreoffice_profile_is_outside_long_work_directory():
    source = ''.join(BOOK['cells'][33]['source'])
    assert 'tempfile.mkdtemp(prefix="lecture-lo-")' in source
    assert 'profile_dir = work_dir' not in source
