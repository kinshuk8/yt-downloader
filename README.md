# YT Downloader

A small local app for downloading YouTube videos at the best quality available (up to 4K/8K), or as MP3 audio.

- Pick any resolution the video offers, or "Best available"
- Video as MP4, MKV or WebM
- MP3 at 128–320 kbps, with the cover art and title saved in the file
- Live progress, speed and time left
- Files are saved to `~/Downloads/YouTube/`

Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp), ffmpeg and Flask. Everything runs on your own Mac; nothing is uploaded anywhere.

## Mac app (recommended)

1. Open `YT-Downloader.dmg` and drag **YT Downloader** into **Applications**.
2. Open it from Launchpad, Spotlight or the Dock. It runs in its own window; close the window to quit.

Everything is bundled (ffmpeg, a JavaScript runtime for YouTube, yt-dlp), so no Homebrew or Terminal needed. yt-dlp updates itself in the background, and the update applies from the next launch. The current version is shown at the bottom of the window.

The app is not notarized by Apple, so on a Mac that downloaded the DMG from the internet, the first launch is blocked: right-click the app → **Open** → **Open** (or allow it in System Settings → Privacy & Security). Apple silicon Macs only.

### Building the DMG

```bash
./build-dmg.sh
```

Needs Homebrew; it installs anything missing and writes `dist/YT-Downloader.dmg`. Build files are kept in `~/.cache/yt-downloader-build`.

## Browser version (from source)

Runs the same app in your browser, straight from the code. Handy while changing it. Needs [Homebrew](https://brew.sh) and Python 3.

```bash
git clone https://github.com/kinshuk8/yt-downloader.git
cd yt-downloader
./launch.sh
```

Or double-click `start.command` in Finder. The first launch installs ffmpeg and the Python packages, so it takes a minute. Click **Quit** in the page when you're done.

## Troubleshooting

- **Downloads suddenly fail:** YouTube changes often. The app fetches yt-dlp fixes on launch and uses them from the next one, so reopen it once or twice.
- **4K/1440p video won't play in QuickTime:** YouTube only serves VP9/AV1 at those resolutions. Use VLC or IINA, or choose MKV.
- **Logs (browser version):** `server.log` in the project folder.

## Note

Only download videos you have the right to, such as your own uploads or Creative Commons content. YouTube's terms don't allow downloading most videos.
