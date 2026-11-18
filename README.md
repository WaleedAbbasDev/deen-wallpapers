# Deen Reminders: Islamic lock-screen wallpapers

A free web app plus an iPhone Shortcut that keep changing your lock screen to
reminders from the Quran, Sahih Hadith, Hazrat Ali (RA), Allama Iqbal and Rumi.

* GitHub hosts it for free and makes a fresh set of 200 wallpapers every 4 hours.
* The iPhone **Shortcuts** app puts a new one on your lock screen automatically.

---

## Part 1: Put it on GitHub (computer, about 10 minutes)

1. Go to **github.com** and create a free account.
2. Click **+** (top right) → **New repository**.
   * Name: `deen-wallpapers`
   * Choose **Public** (free hosting needs this)
   * Click **Create repository**.
3. On the new page click **uploading an existing file**.
4. Unzip `deen-wallpapers.zip` on your computer. Open the folder, select **everything inside it**
   (`app`, `generator`, `quotes.json`, `README.md`) and drag it into the GitHub page.
   Click **Commit changes**.
5. Add the automatic builder. Mac Finder hides folders whose names start with a dot,
   so add this file by hand:
   * Click **Add file** → **Create new file**.
   * In the name box type exactly: `.github/workflows/build.yml`
   * Open `build.yml` from the zip (it's in the folder `.github/workflows`; on a Mac press
     **Cmd + Shift + .** to show hidden folders), or copy it from the bottom of this page.
     Paste its contents in, then click **Commit changes**.
6. Turn on hosting: **Settings** → **Pages** → under *Source* choose **GitHub Actions**.
7. Go to the **Actions** tab → **Make new wallpapers** → **Run workflow**. Wait about 2 minutes
   for the green tick.
8. Your app is now live at:
   **`https://YOUR-GITHUB-NAME.github.io/deen-wallpapers/`**

## Part 2: On your iPhone

1. Open that address in **Safari** → **Share** → **Add to Home Screen**.
2. Open the app and go to the **Setup** tab. It walks you through making the Shortcut,
   and the address you need is already filled in for you.

Short version of the Shortcut:

| # | Action | Setting |
|---|--------|---------|
| 1 | Random Number | 1 to 200 |
| 2 | Text | `https://YOUR-GITHUB-NAME.github.io/deen-wallpapers/w/[Random Number].jpg` |
| 3 | Get Contents of URL | (uses the Text) |
| 4 | Set Wallpaper Photo | your current wallpaper, Show Preview **off** |

Then in **Automation**: *Time of Day → Run Immediately*, and/or *App → Instagram/TikTok/YouTube
→ Is Opened → Run Immediately*.

Your lock screen must be a normal **Photo** wallpaper, not "Photo Shuffle".

---

## Adding your own reminders

Open `quotes.json` on GitHub → pencil icon ✏️ → edit → **Commit changes**.
New wallpapers are built within a couple of minutes.

* **Quran:** add a reference to `quran_refs`, like `"2:255"` or `"94:5-6"`. The English text is added automatically.
* **Anything else:** copy an entry in `quotes` and change `text` and `ref`.
  `cat` can be `hadith`, `ali`, `iqbal`, `rumi` or `scholar`. For Iqbal you can add
  `"original"` with the Urdu lines.

Please only add quotes you have checked in a trusted book. Many sayings online under the names
of Hazrat Ali, Rumi and Shams Tabrizi are not really theirs.

## Sources

* **Quran:** Saheeh International English translation, downloaded at build time.
* **Hadith:** Sahih al-Bukhari and Sahih Muslim only, with hadith numbers.
* **Hazrat Ali (RA):** Nahj al-Balagha (saying numbers may differ by one or two between editions).
* **Iqbal:** Bang-e-Dra, Bal-e-Jibril, Zarb-e-Kalim. **Rumi:** Masnavi, Fihi Ma Fihi.
* The hadith, Ali, Iqbal and Rumi texts are English renderings of the meaning.

## If something stops

* No new wallpapers? Go to **Actions** → **Make new wallpapers** → **Enable workflow** / **Run workflow**.
  Your existing 200 wallpapers keep working regardless.
* Fonts: Crimson Text and DM Sans (SIL Open Font License, included).

```yaml
# .github/workflows/build.yml
name: Make new wallpapers

on:
  push:
    branches: [main]
  schedule:
    - cron: "23 */4 * * *"   # every 4 hours
  workflow_dispatch:          # lets you press "Run workflow" by hand

permissions:
  contents: read
  pages: write
  id-token: write
  actions: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Pillow
        run: pip install pillow

      - name: Make wallpapers
        run: python generator/make_wallpapers.py

      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

      # GitHub pauses scheduled jobs after 60 days without activity.
      # Re-enabling the workflow resets that timer, so it keeps running.
      - name: Keep the schedule alive
        continue-on-error: true
        env:
          GH_TOKEN: ${{ github.token }}
        run: gh api --method PUT "repos/${{ github.repository }}/actions/workflows/build.yml/enable"

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```
