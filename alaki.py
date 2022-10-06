import asyncio
from io import BytesIO
import subprocess
from ffmpeg import FFmpeg


player = FFmpeg(
    'ffplay'
).option(
    'autoexit'
).option(
    'nodisp'
).option(
    'hide_banner'
).input(
    r'h:\1.mp3',
    options={'loop': 1}
)

@player.on('start')
def on_start(arguments):
    print('Arguments:', arguments)

@player.on('stderr')
def on_stderr(line):
    print('stderr:', line)

@player.on('progress')
def on_progress(progress):
    print('progress:', progress)

@player.on('progress')
def time_to_terminate(progress):
    # Gracefully terminate when more than 200 frames are processed
    if progress.frame > 200:
        player.terminate()

@player.on('completed')
def on_completed():
    print('Completed')

@player.on('terminated')
def on_terminated():
    print('Terminated')

@player.on('error')
def on_error(code):
    print('Error:', code)

asyncio.run(player.execute())