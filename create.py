import os
import json
import requests
from PIL import Image, ImageDraw, ImageChops, ImageEnhance, ImageOps
from PIL.ImageFont import truetype
from PIL.ImageFilter import GaussianBlur
from PIL import ImageFilter
from datetime import datetime, date
from config import MAX_AUDIO
from calendar import month_name
from asyncio.subprocess import create_subprocess_exec, PIPE


def format_time(milliseconds):
    minutes, seconds = divmod(int(milliseconds / 1000), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    tmp = (
        ((str(weeks) + "w:") if weeks else "")
        + ((str(days) + "d:") if days else "")
        + ((str(hours) + "h:") if hours else "")
        + ((str(minutes) + "m:") if minutes else "")
        + ((str(seconds) + "s") if seconds else "")
    )
    if not tmp:
        return "0s"

    if tmp.endswith(":"):
        return tmp[:-1]
    return tmp


async def getFileDuration(audioPath):
    proc = await create_subprocess_exec(
        "mediainfo", audioPath, f"--output=JSON", stderr=PIPE, stdout=PIPE
    )
    await proc.wait()
    output = await proc.stdout.read()
    err = await proc.stderr.read()
    fileInfo = json.loads(output)
    return fileInfo["media"]["track"][0]["Duration"]


async def mergeAudioVideo(video_path, audio_path, output_path):
    commands = [
        "ffmpeg",
        "-stream_loop",
        "-1",
        "-i",
        video_path,
        "-i",
        audio_path,
        "-shortest",
        "-c:v",
        "libx265",
        "-crf",
        "26",
        "-c:a",
        "aac",
        "-q:a",
        "4",
        output_path,
        "-y",
    ]
    proc = await create_subprocess_exec(
        *commands,
        stderr=PIPE,
        stdout=PIPE,
    )
    await proc.wait()
    output = await proc.stdout.read()
    err = await proc.stderr.read()
    print(output, err)
    return output, err


async def createVideo(DATA):
    imageGif, trackName, audioFile = await createImage(DATA)
    if not audioFile:
        mpPath = f"{trackName}.mp4"
        proc = await create_subprocess_exec(
            "ffmpeg",
            "-stream_loop",
            "2",
            "-i",
            imageGif,
            "-movflags",
            "faststart",
            "-pix_fmt",
            "yuv420p",
            mpPath,
            "-y",
        )
        await proc.wait()
        os.remove(imageGif)
        return mpPath, False
    outputPath = f"{trackName}-merged.mp4"
    print("Merging Audio and Video...")
    out, err = await mergeAudioVideo(imageGif, audioFile, outputPath)
    os.remove(audioFile)
    os.remove(imageGif)
    return outputPath, True


async def createImage(DATA):
    print("Creating Video GIF...")
    item = DATA["item"]
    name = item["name"]
    audioFile = None

    if url := item.get("preview_url"):
        audioFile = f"{name}.mp4"
        with open(audioFile, "wb") as f:
            f.write(requests.get(url).content)
    if audioFile:
        duration = float(await getFileDuration(audioFile))
    else:
        duration = 1
    maxDuration = int(duration) if MAX_AUDIO > duration else MAX_AUDIO
    Aduration = int(item["duration_ms"]) / 1000
    now = datetime.now()
    imageBox = []

    for frame in range(0, maxDuration):
        img = Image.new("RGBA", (1080, 1920), color="white")

        with open("thumb.png", "wb") as f:
            f.write(requests.get(DATA["item"]["album"]["images"][0]["url"]).content)

        thumbActual = Image.open("thumb.png")
        # create a second Image from thumbnail for background!
        enhancer = ImageEnhance.Brightness(thumbActual)
        # thumbOverlay = Image.new("RGBA", thumb.size, "white")
        # thumb.paste(thumbOverlay, (0,0))
        # thumb.filter(ImageFilter.BoxBlur(10))
        thumb = enhancer.enhance(0.4).resize((img.height, img.height))
        # img = ImageChops.multiply(img, thumbOverlay)
        # thumb.show()
        img.paste(thumb, (-img.width // 2, 0))
        draw = ImageDraw.Draw(img)
        font = truetype("assets/fonts/BebasNeue-Regular.ttf", size=60)

        # add Heading texts.
        draw.text((40, 100), "Listening to", fill="white", font=font)
        font = truetype("assets/fonts/BebasNeue-Regular.ttf", size=100)
        draw.text((40, 162), DATA["item"]["name"], fill="white", font=font)

        # resize thumbnail and get position
        thumbActual = thumbActual.resize((img.width - 100,) * 2)
        w = (img.width // 2) - (thumbActual.width // 2)
        h = 280
        # wrap: Play button over middle thumbnail
        playButton = Image.open("assets/play.png")
        thumbActual.paste(
            playButton,
            (
                (thumbActual.width // 2) - (playButton.width // 2),
                (thumbActual.height // 2) - (playButton.height // 2),
            ),
            mask=playButton,
        )
        thumbActual = ImageOps.expand(thumbActual, border=5, fill="white")
        img.paste(thumbActual, (w, h))

        # add Date to bottom right
        font = truetype("assets/fonts/BebasNeue-Regular.ttf", size=60)
        tag = "AM" if now.hour < 12 else "PM"
        dateString = f"{month_name[now.month]} {now.day}, {now.hour}:{now.minute} {tag}"
        draw.text((img.width - 30, img.height - 50), dateString, font=font, anchor="rs")

        # Add spotify icon
        # spotify = Image.open("assets/spotify.png").resize((100, 100))
        # img.paste(spotify, (img.width - spotify.width - 20, img.height - spotify.height - 20), mask=spotify)

        # add play-slider
        h = 1400
        w = img.width - 80

        diff = (img.width - thumbActual.width) // 2
        draw.line((diff, h, thumbActual.width + diff, h), fill="white", width=15)
        diff = (((thumbActual.width) // Aduration) * (frame)) + diff
        draw.ellipse((diff - 25, h - 25, diff + 25, h + 25), fill="#6fd1c6")

        # add playing time
        draw.text(
            (img.width - 30, h + 68),
            format_time(item["duration_ms"]),
            fill="white",
            font=font,
            anchor="rs",
        )
        draw.text(
            (30, h + 25),
            f"0:{frame}",
            fill="white",
            font=font,
        )

        imageBox.append(img)

    imageBox[0].save(
        f"{name}.gif",
        save_all=True,
        append_images=imageBox[1:],
        duration=1000,
        loop=100,
    )
    return f"{name}.gif", name, audioFile
