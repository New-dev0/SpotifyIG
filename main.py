import asyncio, os
from config import *
from decouple import RepositoryEnv
from aiohttp import ClientSession
from aiohttp.client_exceptions import ContentTypeError
from create import createVideo
from instagrapi import Client
from datetime import datetime
from instagrapi.types import StoryLink

iclient = Client()
if os.path.exists(SETTINGS_PATH):
    iclient.load_settings(SETTINGS_PATH)
else:
    iclient.login(IG_USERNAME, IG_PASSWORD)
    iclient.dump_settings(SETTINGS_PATH)


def publishToInstagram(path, track_url):
    iclient.video_upload_to_story(
        path,
        links=[
            StoryLink(webUri=track_url),
            StoryLink(webUri="https://github.com/New-dev0/SpotifyIG"),
        ],
    )


dailyCache = {}


async def main():
    data = RepositoryEnv(".env").data
    access_token = data.get("ACCESS_TOKEN")
    refresh_token = data.get("REFRESH_TOKEN")
    sleepTime = 5
    currentlyPlaying = None

    oauth = {"Authorization": f"Bearer {access_token}"}

    while True:
        async with ClientSession() as session:
            response = await session.get(
                "https://api.spotify.com/v1/me/player/currently-playing", headers=oauth
            )
            status_code = response.status

            if status_code == 401:
                data = {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                }
                res = await session.post(
                    "https://accounts.spotify.com/api/token", data=data
                )
                response = await res.json()
                data = {
                    "ACCESS_TOKEN": response["access_token"],
                }
                if response.get("refresh_token"):
                    data["REFRESH_TOKEN"] = response["refresh_token"]
                updateConfig(data)
                return await main()
            try:
                videoInfo = await response.json()
                if videoInfo.get("item"):
                    uri = videoInfo["item"]["uri"]
                    trackUrl = videoInfo["item"]["external_urls"]["spotify"]

                    if currentlyPlaying and currentlyPlaying == uri:
                        print("Already playing!")
                        await asyncio.sleep(sleepTime)
                        continue

                    if dailyCache.get(uri) and (
                        (datetime.now() - dailyCache[uri]).days < 1
                    ):
                        print("Already in cache!")
                        await asyncio.sleep(sleepTime)
                        continue

                    if (
                        videoInfo.get("is_playing")
                        and videoInfo.get("progress_ms", 0) > 10000
                    ) and videoInfo.get("item").get("preview_url"):
                        sleep_time = 15
                        currentlyPlaying = uri

                        videoPath, hasAudio = await createVideo(videoInfo)
                        # print(trackUrl, videoPath)
                        dailyCache[uri] = datetime.now()
                        await publishToInstagram(videoPath, trackUrl)
                        os.remove(videoPath)
                        thumbPath = f"{videoPath}.jpg"
                        if os.path.exists(thumbPath):
                            os.remove(thumbPath)
                    else:
                        sleep_time = 15

                else:
                    sleepTime = 15
            except ContentTypeError:
                # Not Playing state
                sleepTime = 15
            except Exception as er:
                print(er)
            await asyncio.sleep(sleepTime)


print("Started Script!")
asyncio.run(main())
