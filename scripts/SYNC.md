# Sync resume from Google Doc

Source of truth: Google Doc **Resume 2026**  
Doc id: `1Ja6F7E2iyhQQhrioG0xFzrvjMW2p9hMKF-GRm9uS7Nk`

## Re-sync procedure (“sync my resume”)

1. **Export Markdown** from the Google Drive connector:
   - `read_file` with `fileId=1Ja6F7E2iyhQQhrioG0xFzrvjMW2p9hMKF-GRm9uS7Nk`
   - Save the returned Markdown to `data/resume.md` in this repo.

2. **Regenerate the HTML page**:
   ```bash
   python3 scripts/sync_resume.py data/resume.md -o resume.html
   ```
   The script strips street address, phone, and full mailing-address lines.
   It keeps name, title, “Scotts Valley, CA”, email, and LinkedIn/GitHub links.

3. **Export PDF** (optional but usual):
   - `export_file` with the same `fileId` and `format=pdf`
   - Decode the base64 payload to `resume.pdf`
   - Note: the PDF is the Doc as written and **includes address and phone**.

4. Commit and push to `main` so GitHub Pages publishes:
   - Live resume: https://andyperlitch.github.io/andyperlitch.com/resume.html
