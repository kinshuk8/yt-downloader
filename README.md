# YT Downloader

A small local app for downloading YouTube videos at the best quality available (up to 4K/8K), or as MP3 audio.

- Pick any resolution the video offers, or "Best available"
- Video as MP4, MKV or WebM
- MP3 at 128–320 kbps, with the cover art and title saved in the file
- Live progress, speed and time left
- Files are saved to `~/Downloads/YouTube/`

Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp), ffmpeg and Flask. Everything runs on your own Mac; nothing is uploaded anywhere.

## Setup (macOS, once)

You need [Homebrew](https://brew.sh) and Python 3 (`brew install python`).

```bash
git clone https://github.com/kinshuk8/yt-downloader.git
cd yt-downloader
./make-app.sh
```

This puts **YT Downloader.app** in `~/Applications`.

## Run

Open **YT Downloader** from Spotlight (⌘Space), Launchpad or your Dock. The app opens in your browser. The first launch installs ffmpeg and the Python packages, so it takes a minute.

Click **Quit** in the page when you're done.

To launch without building the app, you can also double-click `start.command` in Finder, or run `./launch.sh`.

> Keep the cloned folder where it is: the app runs the code from there. If you move the folder, run `./make-app.sh` again.

## Troubleshooting

- **Downloads suddenly fail:** YouTube changes often. Each launch updates yt-dlp, so quit and reopen the app.
- **4K/1440p video won't play in QuickTime:** YouTube only serves VP9/AV1 at those resolutions. Use VLC or IINA, or choose MKV.
- **Logs:** `server.log` in the project folder.

## Note

Only download videos you have the right to, such as your own uploads or Creative Commons content. YouTube's terms don't allow downloading most videos.
