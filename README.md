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

3. Fill your configuration `.env` file


> Note
- Songs are cached for 1day and same song cant be uploaded again within 24 hours.