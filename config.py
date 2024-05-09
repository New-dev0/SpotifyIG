import asyncio
from decouple import config, RepositoryEnv
from aiohttp import ClientSession

CLIENT_ID = config("CLIENT_ID", default="")
CLIENT_SECRET = config("CLIENT_SECRET", default="")
INITIAL_TOKEN = config("INITIAL_TOKEN", default="")
MAX_AUDIO = config("MAX_AUDIO", default=30, cast=int)
PORT = config("PORT", default=3000, cast=int)

IG_USERNAME = config("IG_USERNAME", default="")
IG_PASSWORD = config("IG_PASSWORD", default="")
SETTINGS_PATH = config("SETTINGS_PATH", default="./settings.json")


def updateConfig(keyValueDict):
    from decouple import RepositoryEnv

    env = RepositoryEnv(".env")
    env.data.update(keyValueDict)

    with open(".env", "w") as f:
        for x, y in env.data.items():
            f.write(f"{x}={y}\n")


if not INITIAL_TOKEN:
    from aiohttp import web
    from aiohttp.web_app import Application

    async def save_code(request):
        INITIAL_TOKEN = request.rel_url.query["code"]
        updateConfig({"INITIAL_TOKEN": INITIAL_TOKEN})

        request.app["future"].set_result({"message": "You can close this tab now!"})

    async def getInitialToken():
        url = f"https://accounts.spotify.com/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri=http://localhost:{PORT}&scope=user-read-playback-state%20user-read-currently-playing"
        print(f"Redirecting to {url}")
        try:
            import webbrowser

            webbrowser.open_new(url)
        except Exception as er:
            print(er)

        app = Application()
        runner = web.AppRunner(app)
        loop = asyncio.get_running_loop()
        running = loop.create_future()
        app["future"] = running
        app.add_routes([web.get("/", save_code)])

        await runner.setup()
        site = web.TCPSite(runner, host="localhost", port=PORT)
        await site.start()
        try:
            await running
        except IndexError:
            pass

    asyncio.run(getInitialToken())


async def getClientToken():
    INITIAL_TOKEN = RepositoryEnv(".env").data.get("INITIAL_TOKEN")

    async with ClientSession() as session:
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": f"http://localhost:{PORT}",
            "code": INITIAL_TOKEN,
        }
        async with session.post(
            "https://accounts.spotify.com/api/token", data=data
        ) as post_response:
            response = await post_response.json()
            print(response)
            updateConfig(
                {
                    "ACCESS_TOKEN": response["access_token"],
                    "REFRESH_TOKEN": response["refresh_token"],
                }
            )


if not config("ACCESS_TOKEN", default=""):
    asyncio.run(getClientToken())
