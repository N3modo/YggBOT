import discord
import asyncio
import pytube
import os

from discord.ext import commands

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)
current_queue = []
currently_playing = 0

is_playlist = lambda x: "list=" in x


def extract_audio_url(video):
    return video.streams.filter(only_audio=True).first().url


# Function to download audio from YouTube
def get_audio(url):
    try:
        if is_playlist(url):
            return pytube.Playlist(url).videos
        else:
            return [pytube.YouTube(url)]
    except pytube.exceptions.PytubeError as e:
        print(f"Error extracting audio stream: {e}")


def reschedule_play(exception, voice_client):
    global current_queue, currently_playing
    if exception:
        print("Reschedule exception: ", exception)
        return
    if currently_playing >= len(current_queue):
        return
    currently_playing += 1
    schedule_play(voice_client)


def schedule_play(voice_client):
    global current_queue, currently_playing
    audio_url = extract_audio_url(current_queue[currently_playing])
    audio_source = discord.FFmpegPCMAudio(audio_url, before_options=" -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 1")
    voice_client.play(audio_source, after=lambda e: reschedule_play(e, voice_client))


@bot.event
async def on_ready():
    print(f'{bot.user.name} is connected to Discord!')

@bot.command(name='join')
async def join_channel(ctx):
    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel!")
        return
    voice_channel = ctx.author.voice.channel
    voice_client = ctx.voice_client
    if voice_client is not None:
        await voice_client.move_to(voice_channel)
    else:
        await voice_channel.connect()

@bot.command(name='leave')
async def leave_channel(ctx):
    voice_client = ctx.voice_client
    if voice_client is not None:
        await voice_client.disconnect()

@bot.command(name='play')
async def play_music(ctx, *, url):
    global current_queue, currently_playing
    voice_client = ctx.voice_client
    if voice_client is None:
        await ctx.invoke(bot.get_command('join'))
        voice_client = ctx.voice_client

    last_queue_len = len(current_queue)
    current_queue += get_audio(url)

    if not voice_client.is_playing():
        currently_playing = last_queue_len
        schedule_play(voice_client)

@bot.command(name='pause')
async def pause_music(ctx):
    voice_client = ctx.voice_client
    if voice_client is not None and voice_client.is_playing():
        voice_client.pause()

@bot.command(name='resume')
async def resume_music(ctx):
    voice_client = ctx.voice_client
    if voice_client is not None and voice_client.is_paused():
        voice_client.resume()

@bot.command(name='stop')
async def stop_music(ctx):
    voice_client = ctx.voice_client
    if voice_client is not None and voice_client.is_playing():
        voice_client.stop()

# Function to remove the temporary audio file
def remove_audio_file(audio_file):
    try:
        os.remove(audio_file)
    except OSError as e:
        print(f"Error removing audio file: {e}")