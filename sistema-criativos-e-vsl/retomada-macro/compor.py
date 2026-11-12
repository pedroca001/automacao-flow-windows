from pathlib import Path
import hashlib
import json
import os
import subprocess


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], text=True, timeout=30))


def compose(files, output, work, receipt_path=None):
    output, work = Path(output), Path(work)
    assert len(files) in (4, 5)
    count, seconds = len(files), len(files) * 8
    if output.exists():
        raise RuntimeError('Entrega já existe; não sobrescrever: ' + str(output))
    work.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.parent / (output.stem + '.temporario.mp4')
    infos = [probe(file) for file in files]
    videos = [next(s for s in info['streams'] if s['codec_type'] == 'video') for info in infos]
    keys = ('codec_name', 'width', 'height', 'pix_fmt', 'r_frame_rate', 'time_base')
    compatible = all(all(v.get(k) == videos[0].get(k) for k in keys) for v in videos)
    copy_video = compatible and videos[0]['codec_name'] == 'h264' and videos[0]['r_frame_rate'] == '24/1'
    command = ['ffmpeg', '-v', 'error', '-y']
    if copy_video:
        manifest = work / (output.stem + '.concat.txt')
        manifest.write_text(''.join("file '" + Path(file).resolve().as_posix().replace("'", "'\\''") + "'\nduration 8\n" for file in files))
        command += ['-f', 'concat', '-safe', '0', '-i', str(manifest)]
    filters, streams = [], []
    for i, file in enumerate(files):
        info = infos[i]
        assert abs(float(info['format']['duration']) - 8) < .25
        command += ['-i', str(file)]
        index = i + 1 if copy_video else i
        if not copy_video:
            filters.append(f'[{index}:v]trim=duration=8,setpts=PTS-STARTPTS,fps=24,setsar=1[v{i}]')
        if any(s['codec_type'] == 'audio' for s in info['streams']):
            filters.append(f'[{index}:a]aresample=48000,apad,atrim=duration=8,asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo[a{i}]')
        else:
            filters.append(f'anullsrc=r=48000:cl=stereo,atrim=duration=8[a{i}]')
        streams += [f'[a{i}]' if copy_video else f'[v{i}][a{i}]']
    filters.append(''.join(streams) + (f'concat=n={count}:v=0:a=1[a]' if copy_video else f'concat=n={count}:v=1:a=1[v][a]'))
    command += ['-filter_complex', ';'.join(filters), '-map', '0:v:0' if copy_video else '[v]', '-map', '[a]']
    command += ['-c:v', 'copy'] if copy_video else ['-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p']
    command += ['-c:a', 'aac', '-b:a', '160k', '-t', str(seconds), '-movflags', '+faststart', str(temporary)]
    subprocess.run(command, check=True, capture_output=True, timeout=240)
    info = probe(temporary)
    assert abs(float(info['format']['duration']) - seconds) < .1
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(temporary), '-f', 'null', '-'], check=True, capture_output=True, timeout=120)
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt = {'file': str(output), 'sha256': hashlib.sha256(temporary.read_bytes()).hexdigest(), 'seconds': seconds}
    if receipt_path:
        path = Path(receipt_path)
        pending = path.with_suffix('.tmp')
        with pending.open('w') as stream:
            json.dump(receipt, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pending, path)
    # Windows rename não substitui destinos existentes e funciona em unidades
    # montadas sem suporte a hard links. Temporário e entrega no mesmo volume.
    if os.name == 'nt':
        os.rename(temporary, output)
    else:
        os.link(temporary, output)
        temporary.unlink()
    return receipt
