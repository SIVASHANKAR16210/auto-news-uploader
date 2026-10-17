# Auto News Video Uploader (free / GitHub Actions)

This repository runs on GitHub Actions and automatically:
- fetches top headlines (Google News RSS by default),
- generates a short original narration,
- builds a slideshow-style video (slides + TTS),
- uploads the video to your YouTube channel.

Important:
- This is original content generated from public news topics.
- It does not re-upload other creators' videos.
- YouTube still requires compliance with copyright and monetization rules.

Setup:
1. Add GitHub secrets:
   - YT_CLIENT_ID
   - YT_CLIENT_SECRET
   - YT_REFRESH_TOKEN
   - YT_PRIVACY_STATUS
   - GOOGLE_NEWS_RSS

2. Run Actions:
   - Actions → Auto News Video Uploader → Run workflow

3. Result:
   - Video gets created and uploaded to YouTube automatically

Notes:
- Default video privacy is private
- Edit the cron in `.github/workflows/auto_youtube_news.yml` to change the schedule
- For more quality, use licensed stock images later
