import os
import json
import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageOps
from PIL.ImageFont import truetype
from datetime import datetime
from config import MAX_AUDIO
from calendar import month_name
from asyncio.subprocess import create_subprocess_exec, PIPE


def format_time(milliseconds):
    minutes, seconds = divmod(int(milliseconds / 1000), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        ((f"{hours:02d}:") if hours else "")
        + ((f"{minutes:02d}:" if minutes else "00:"))
        + ((f"{seconds:02d}") if seconds else "00")
    )
    if not tmp:
        return "00"

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
        "-i",
        video_path,
        "-i",
        audio_path,
        "-shortest",
        "-c:v",
        "libx265",
        "-c:a",
        "aac",
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
    # print(output, err)
    return output, err


async def createVideo(DATA):
    imageGif, trackName, audioFile = await createImage(DATA)
    if not audioFile:
        mpPath = f"{trackName}.mp4"
        proc = await create_subprocess_exec(
            "ffmpeg",
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


def add_corners(im, rad):
    circle = Image.new("L", (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2 - 1, rad * 2 - 1), fill=255)
    alpha = Image.new("L", im.size, 255)
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    im.putalpha(alpha)
    return im


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
        thumbActual = add_corners(thumbActual, 20)
        # create a second Image from thumbnail for background!
        enhancer = ImageEnhance.Brightness(thumbActual)
        # thumbOverlay = Image.new("RGBA", thumb.size, "white")
        # thumb.paste(thumbOverlay, (0,0))
        # thumbActual.filter(ImageFilter.BoxBlur(10))
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
        dateString = (
            f"{month_name[now.month]} {now.day}, {now.hour:02d}:{now.minute:02d} {tag}"
        )
        draw.text((img.width - 30, img.height - 50), dateString, font=font, anchor="rs")

        # Add spotify icon
        spotify = Image.open("assets/spotify.png").resize((100, 100))
        img.paste(spotify, (20, img.height - spotify.height - 20), mask=spotify)

        # add play-slider
        h = 1400
        w = img.width - 80

        diff = (img.width - thumbActual.width) // 2
        draw.rounded_rectangle(
            (diff, h, thumbActual.width + diff, h + 10),
            radius=5,
            fill="white",
        )
        diff = (((thumbActual.width) // Aduration) * (frame)) + diff
        draw.ellipse((diff - 25, h - 25 + 2.5, diff + 25, h + 25 + 2.5), fill="#6fd1c6")

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
            f"00:{frame:02d}",
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
