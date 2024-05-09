# Spotify-IG

- Automatically upload Instagram stories when you listen to song on Spotify.

![](./ig.png)

## Instructions

1. Install Requirements

```bash
pip3 install -r requirements.txt
```

2. Install apt packages

```bash
sudo apt install mediainfo ffmpeg -y
```

3. Get [Spotify configurations](#getting-spotify-configurations-for-env) for [`.env`](#sample-of-env).

4. Fill your configuration [`.env`](#sample-of-env) file.

5. Run `python3 config.py`, you will automatically redirected to Spotify login page, if not, go to `https://accounts.spotify.com/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri=http://localhost:{PORT}&scope=user-read-playback-state%20user-read-currently-playing` and give authorisation to your spotify account, to fill out missing configurations.

6. Finally run the screipt with `python3 main.py`.

## Getting Spotify configurations for `.env`

1. Go to [this](https://developer.spotify.com/).

2. Login to your profile.

3. Create new app and set app name and description.

4. Redirect URI should be http://localhost:PORT, where you can use custom PORT number by adding it in [`.env`](#sample-of-env). Default PORT number is 3000. So it should look like `http://localhost:3000`.

5. Select Web API and Agree to the TOS and guidelines and save the app.

6. Go to your app's dashboard and head to settings tab.

7. Copy Client ID and Client Secret and fill it in [`.env`](#sample-of-env).

## Sample of .env

> Note: 2FA support for instagram is not yet implemented.

```bash
CLIENT_ID= #Get it from https://developer.spotify.com
CLIENT_SECRET= #Get it from https://developer.spotify.com
IG_USERNAME= #Your instagram username
IG_PASSWORD= #Your instagram password
```

> Note

- Songs are cached for 1 day and same song won't be uploaded again within 24 hours.
