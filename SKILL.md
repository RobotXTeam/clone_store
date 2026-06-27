---
name: CloneStore
description: "A resilient downloader for HuggingFace and GitHub repositories, capable of handling proxy disconnects, LFS files, and seamless background resume. Use this when you need to download a model or repo robustly."
---

# CloneStore

Use this skill whenever you need to reliably download a HuggingFace model or a GitHub repository, especially large models that frequently drop connections due to proxy instability. 

## Features
- Bypasses HuggingFace official client limitations by using a custom byte-range HTTP loop with `Content-Length` validation to prevent file truncation.
- Infinite retries on proxy drops, automatically resuming from `.incomplete` files.
- Operates in either interactive mode or headless background mode (`--worker`).

## Usage

This skill packages the `clone_store.py` script. Run the script interactively if you are interacting with the user and want to guide them through the download:
```bash
python3 clone_store.py
```
It will prompt for the HuggingFace/GitHub URL and optionally an Access Token.

### Headless/Worker Mode
If you want to spawn a background worker yourself to download specific files without interaction:
```bash
nohup python3 clone_store.py --worker --mode hf --repo_id <repo_id> --files <comma_separated_files> >> download.log 2>&1 < /dev/null &
```
- `--mode`: `hf` for HuggingFace, `github` for GitHub
- `--repo_id`: The identifier (e.g. `deepreinforce-ai/Ornith-1.0-35B`)
- `--files`: Comma-separated list of files to download
- Make sure to use `</dev/null` if running via SSH to prevent hanging!

### Tracking Progress
If the worker is running in the background, you can monitor its logs:
```bash
tail -n 20 download.log
```
Or check the total downloaded size in the target directory:
```bash
watch -n 2 du -sh <target_dir>
```
