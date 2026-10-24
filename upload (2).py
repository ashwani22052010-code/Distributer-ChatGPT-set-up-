#!/usr/bin/env python3
"""videos/*.mp4  ->  YouTube channel par PRIVATE upload (sirf Python standard library).

Secrets (GitHub me): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Title/description (optional): scripts/<video-ka-naam>.yt
    Line 1  = title
    tags: horror, ai, funny        (optional line)
    baaki sab = description
"""
import http.client, json, os, sys, time, urllib.parse, urllib.request
from pathlib import Path

TOKEN_URL = os.environ.get("YT_TOKEN_URL", "https://oauth2.googleapis.com/token")
UPLOAD_URL = os.environ.get("YT_UPLOAD_URL", "https://www.googleapis.com/upload/youtube/v3/videos")
CHUNK = 16 * 1024 * 1024          # 256 KiB ka multiple hona zaroori hai


def env_clean(name):
    raw = os.environ.get(name, "")
    return raw, raw.strip().strip('"').strip("'").strip()


def diagnose():
    """Secrets ki value nahi, sirf unka 'shape' dikhata hai (safe)."""
    ci_raw, ci = env_clean("YT_CLIENT_ID")
    cs_raw, cs = env_clean("YT_CLIENT_SECRET")
    rt_raw, rt = env_clean("YT_REFRESH_TOKEN")
    ok = lambda b: "OK" if b else "GALAT"
    print("   --- secrets check ---")
    print(f"   YT_CLIENT_ID     : {len(ci)} akshar, '.apps.googleusercontent.com' par khatam: {ok(ci.endswith('.apps.googleusercontent.com'))}, extra space/quote tha: {ci_raw != ci}")
    print(f"   YT_CLIENT_SECRET : {len(cs)} akshar, 'GOCSPX-' se shuru: {ok(cs.startswith('GOCSPX-'))}, extra space/quote tha: {cs_raw != cs}")
    print(f"   YT_REFRESH_TOKEN : {len(rt)} akshar, '1//' se shuru: {ok(rt.startswith('1//'))}, extra space/quote tha: {rt_raw != rt}")


def access_token():
    data = urllib.parse.urlencode({
        "client_id": env_clean("YT_CLIENT_ID")[1], "client_secret": env_clean("YT_CLIENT_SECRET")[1],
        "refresh_token": env_clean("YT_REFRESH_TOKEN")[1], "grant_type": "refresh_token"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=data), timeout=60) as r:
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        print(f"Login (token) fail: {e.code} {e.read()[:300]!r}")
        diagnose()
        sys.exit("invalid_grant = token is client ke saath nahi bana ya expire/galat hai. "
                 "Teeno secrets ek hi client ke hone chahiye; token OAuth Playground me 'Use your own OAuth credentials' "
                 "ke saath nikalna hai.")


def request(url, method, body=None, headers=None):
    u = urllib.parse.urlparse(url)
    C = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
    c = C(u.netloc, timeout=600)
    c.request(method, u.path + ("?" + u.query if u.query else ""), body=body, headers=headers or {})
    r = c.getresponse()
    data = r.read()
    out = (r.status, r.getheader("Location"), r.getheader("Range"), data)
    c.close()
    return out


def read_meta(stem, scripts_dir):
    base = stem[:-7] if stem.endswith("_shorts") else stem
    title, desc, tags = base.replace("_", " ").replace("-", " ").strip().title(), "", []
    f = Path(scripts_dir) / f"{base}.yt"
    if f.exists():
        lines = f.read_text(encoding="utf-8-sig").splitlines()
        body = []
        for i, ln in enumerate(lines):
            if i == 0 and ln.strip():
                title = ln.strip()
            elif ln.lower().startswith("tags:"):
                tags = [t.strip() for t in ln[5:].split(",") if t.strip()]
            else:
                body.append(ln)
        desc = "\n".join(body).strip()
    if stem.endswith("_shorts"):
        title += " #Shorts"
    return {"snippet": {"title": title[:100], "description": desc[:4900], "tags": tags, "categoryId": "24"},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}}


def resume_pos(loc, size, tok):
    st, _, rng, _ = request(loc, "PUT", b"", {"Authorization": f"Bearer {tok}", "Content-Length": "0",
                                              "Content-Range": f"bytes */{size}"})
    if st in (200, 201):
        return size
    return int(rng.split("-")[1]) + 1 if rng else 0


def upload(tok, path, meta):
    size = path.stat().st_size
    st, loc, _, d = request(UPLOAD_URL + "?uploadType=resumable&part=snippet,status", "POST",
                            json.dumps(meta).encode(),
                            {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                             "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"})
    if st != 200 or not loc:
        raise RuntimeError(f"upload session fail: {st} {d[:600]!r}")
    pos, fails = 0, 0
    with open(path, "rb") as f:
        while True:
            f.seek(pos)
            chunk = f.read(CHUNK)
            end = pos + len(chunk) - 1
            try:
                st, _, rng, d = request(loc, "PUT", chunk, {"Authorization": f"Bearer {tok}",
                                        "Content-Length": str(len(chunk)), "Content-Range": f"bytes {pos}-{end}/{size}"})
            except OSError as e:
                st, d = 599, repr(e).encode()
            if st in (200, 201):
                return json.loads(d)
            if st == 308:
                pos, fails = (int(rng.split("-")[1]) + 1 if rng else pos), 0
                print(f"   {pos / size * 100:5.1f}% uploaded", flush=True)
            elif st >= 500 or st == 429:
                fails += 1
                if fails > 6:
                    raise RuntimeError(f"upload beech me fail: {st} {d[:400]!r}")
                time.sleep(min(60, 2 ** fails))
                pos = resume_pos(loc, size, tok)
            else:
                raise RuntimeError(f"upload fail: {st} {d[:600]!r}")


def main():
    vdir = Path(sys.argv[1] if len(sys.argv) > 1 else "videos")
    sdir = sys.argv[2] if len(sys.argv) > 2 else "scripts"
    files = sorted(vdir.glob("*.mp4"))
    if not files:
        sys.exit("Koi mp4 nahi mili")
    tok = access_token()
    bad = 0
    for p in files:
        meta = read_meta(p.stem, sdir)
        print(f"==> {p.name}  ({p.stat().st_size/1e6:.0f} MB)  title: {meta['snippet']['title']}", flush=True)
        try:
            r = upload(tok, p, meta)
            print(f"   OK (private): https://youtu.be/{r['id']}")
        except Exception as e:                      # ek fail ho to baaki chalte rahein
            bad += 1
            print(f"   FAIL: {e}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
