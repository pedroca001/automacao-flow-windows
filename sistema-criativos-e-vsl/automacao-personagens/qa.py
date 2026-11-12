"""QA posterior independente: arquivos, contato 2 fps e fala versus texto esperado."""
import argparse
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re
import subprocess
import time

from core import atomic, read, sha
from controller import probe
from flow_platform import process_options


def words(value):
    numbers = {'one':'1','two':'2','three':'3','four':'4','five':'5','six':'6','seven':'7','eight':'8','nine':'9','ten':'10'}
    return [numbers.get(token, token) for token in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", value.lower())]


def inspect(cid, scene, root):
    folder = root / 'qa'
    folder.mkdir(exist_ok=True)
    output = folder / (cid + '.json')
    previous = read(output, {})
    digest = sha(scene['file'])
    if previous.get('sha256') == digest and previous.get('qa_version') == 1:
        return previous
    info = probe(scene['file'])
    video = next(s for s in info['streams'] if s['codec_type'] == 'video')
    audio = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
    result = {'qa_version':1, 'sha256':digest, 'duration':float(info['format']['duration']),
              'resolution':[video['width'],video['height']], 'fps':video['r_frame_rate'],
              'has_audio':audio is not None, 'expected_spoken':scene.get('spoken'), 'issues':[],
              'visual_qa':'not_reviewed', 'voice_identity_qa':'not_reviewed'}
    subprocess.run(['ffmpeg','-v','error','-xerror','-threads','2','-i',scene['file'],'-f','null','-'],check=True,capture_output=True,timeout=90,**process_options())
    result['decode_ok']=True
    contact=folder/(cid+'-contato.jpg')
    subprocess.run(['ffmpeg','-v','error','-y','-i',scene['file'],'-vf','fps=2,scale=180:-2,tile=8x2','-frames:v','1',str(contact)],check=True,capture_output=True,timeout=30,**process_options())
    result['contact']=str(contact)
    if result['resolution']!=[720,1280] or abs(result['duration']-8)>.25:
        result['issues'].append('video_fora_do_formato')
    if audio is None:
        result['issues'].append('sem_faixa_de_audio')
    elif scene.get('spoken'):
        wav=folder/(cid+'.wav')
        stem=folder/(cid+'-whisper')
        subprocess.run(['ffmpeg','-v','error','-y','-i',scene['file'],'-vn','-ac','1','-ar','16000',str(wav)],check=True,capture_output=True,timeout=30,**process_options())
        model=Path(os.environ.get('WHISPER_MODEL',''))
        if not model.is_file():
            result['issues'].append('whisper_modelo_ausente')
        else:
            command=['whisper-cli','-m',str(model),'-f',str(wav),'-l','en','-t','2','-oj','-of',str(stem),'-nt','-np']
            done=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120,**process_options())
            if done.returncode or not stem.with_suffix('.json').exists():
                result['issues'].append('transcricao_indisponivel')
            else:
                transcript=read(stem.with_suffix('.json'))
                text=' '.join(segment.get('text','').strip() for segment in transcript.get('transcription',[])).strip()
                score=SequenceMatcher(None,words(scene['spoken']),words(text)).ratio()
                result.update(transcript=text,word_similarity=round(score,4))
                if score<.8:
                    result['issues'].append('fala_diverge_do_roteiro')
        wav.unlink(missing_ok=True)
    atomic(output,result)
    return result


def run(plan_path, watch=False):
    root=Path(plan_path).resolve().parent
    while True:
        state=read(root/'estado-personagens.json',{})
        results={}
        for cid,scene in state.get('scenes',{}).items():
            if scene['status']=='complete':
                results[cid]=inspect(cid,scene,root)
        summary={'checked':len(results),'issues':{cid:r['issues'] for cid,r in results.items() if r['issues']},
                 'results':results,'visual_qa':'not_reviewed','voice_identity_qa':'not_reviewed'}
        atomic(root/'QA-PERSONAGENS.json',summary)
        print(json.dumps({'checked':summary['checked'],'issues':summary['issues']},ensure_ascii=False),flush=True)
        if not watch or state.get('status') in ('complete','complete_with_discards','incomplete','stopped'):
            return 0
        time.sleep(15)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plano',required=True)
    parser.add_argument('--acompanhar',action='store_true')
    args=parser.parse_args()
    raise SystemExit(run(args.plano,args.acompanhar))
