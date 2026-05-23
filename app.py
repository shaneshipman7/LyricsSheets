import streamlit as st
import requests
import re
import urllib.parse

st.set_page_config(page_title="Stage Master", page_icon="🎤", layout="wide")

# ====================== CHORD TEMPLATES ======================
STAGE_CHORD_TEMPLATES = {
    "ESTUVE": ["G", "D", "A", "D", "G", "D", "Em", "Bm", "A", "D", "Em", "A", "D"],
    "ESO Y MÁS": ["D", "A", "G", "D", "Bm", "F#m", "G", "A", "D"],
    "TATUAJES": ["C", "G", "F", "C", "Am", "Em", "F", "G", "C"],
}

def fetch_lyrics(query: str):
    try:
        res = requests.get(
            f"https://lrclib.net/api/search?q={urllib.parse.quote(query)}",
            timeout=10
        )
        if res.ok and res.json():
            top = res.json()[0]
            return (
                top.get('syncedLyrics') or top.get('plainLyrics', ''),
                top.get('name', query.split()[0]),
                top.get('artistName', 'Artist')
            )
    except:
        pass
    return "", "Unknown", "Unknown"

def add_chords_to_lyrics(lyrics_text: str, title: str) -> str:
    lookup = title.upper().strip()
    active_chords = STAGE_CHORD_TEMPLATES.get(lookup, ["G", "D", "Em", "C", "D"])
    
    output = []
    chord_index = 0
    raw_lines = lyrics_text.replace('\r\n', '\n').split('\n')

    for line in raw_lines:
        line = line.strip()
        if not line:
            output.append("")
            continue

        time_match = re.match(r'^\[(\d{2}):(\d{2})(?:\.\d{2,3})?\](.*)', line)
        if time_match:
            timestamp = f"[{time_match.group(1)}:{time_match.group(2)}]"
            lyric_part = time_match.group(3).strip()
            if not lyric_part:
                continue

            words = lyric_part.split()
            built = []
            for i, word in enumerate(words):
                if i % 3 == 0:
                    chord = active_chords[chord_index % len(active_chords)]
                    chord_index += 1
                    built.append(f"[{chord}] {word}")
                else:
                    built.append(word)
            output.append(f"{timestamp} {' '.join(built)}")
        else:
            output.append(line)
    
    return "\n".join(output)

def detect_spanish(text: str) -> bool:
    indicators = ["que", "con", "una", "para", "amor", "corazon", "quiero", "estoy"]
    return sum(1 for w in indicators if re.search(rf"\b{w}\b", text, re.I)) >= 2

# ====================== UI ======================
st.title("🎤 Stage Master")
st.markdown("**Live Performance Chord Sheets with Spanish Translation**")

col1, col2 = st.columns([1, 1.8])

with col1:
    st.subheader("Search Song")
    query = st.text_input("Song Title & Artist", "Estuve Joan Sebastian", key="query")
    
    if st.button("Fetch + Generate Chords", type="primary", use_container_width=True):
        with st.spinner("Fetching lyrics..."):
            lyrics_raw, title, artist = fetch_lyrics(query)
            if lyrics_raw:
                processed = add_chords_to_lyrics(lyrics_raw, title)
                st.session_state.processed = processed
                st.session_state.title = title
                st.session_state.artist = artist
                st.success(f"✅ Loaded **{title}**")
            else:
                st.error("Lyrics not found. Try manual paste below.")

    st.subheader("Manual Paste")
    manual = st.text_area("Paste full lyrics or chord sheet", height=280)
    if st.button("Process Manual Input", use_container_width=True):
        if manual.strip():
            st.session_state.processed = manual
            st.session_state.title = "CUSTOM"
            st.session_state.artist = "Artist"
            st.success("Manual sheet loaded!")

with col2:
    if "processed" in st.session_state:
        lyrics = st.session_state.processed
        title = st.session_state.get("title", "SONG")
        artist = st.session_state.get("artist", "")

        font_size = st.slider("Font Size (Stage View)", 14, 32, 19)
        show_trans = st.checkbox("Show Spanish → English Translation", True)

        st.markdown(f"### {title.upper()}")
        st.markdown(f"**{artist}**")

        translations = {}
        if show_trans and detect_spanish(lyrics):
            with st.spinner("Translating..."):
                lines = lyrics.split("\n")
                for line in lines[:15]:
                    clean = re.sub(r'\[\d{2}:\d{2}.*?\]|\[[A-G].*?\]', '', line).strip()
                    if clean and len(clean) > 5:
                        try:
                            r = requests.get(
                                f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(clean)}&langpair=es|en",
                                timeout=4
                            )
                            if r.ok:
                                translations[clean] = r.json()['responseData']['translatedText']
                        except:
                            pass

        # Render with chords above lyrics
        for line in lyrics.split("\n"):
            if not line.strip():
                st.markdown("---")
                continue

            clean_line = re.sub(r'^\[\d{2}:\d{2}.*?\]\s*', '', line)
            chords = re.findall(r'\[([^\]]+)\]', clean_line)
            lyric_text = re.sub(r'\[[^\]]+\]', '', clean_line).strip()

            if chords:
                st.markdown(f"**{' '.join(chords)}**", unsafe_allow_html=True)
            
            if lyric_text:
                st.markdown(f"<div style='font-size:{font_size}px; font-family:monospace; margin: 4px 0;'>{lyric_text}</div>", unsafe_allow_html=True)
                
                clean_key = re.sub(r'\[[^\]]+\]', '', line).strip()
                if clean_key in translations:
                    st.markdown(f"<div style='color:#666; font-style:italic; font-size:{font_size-3}px;'>→ {translations[clean_key]}</div>", unsafe_allow_html=True)

        # Download buttons
        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button("📥 Download .txt", lyrics, f"{title} - {artist}.txt", "text/plain")
        with col_b:
            if st.button("🖨️ Print / PDF"):
                st.info("Press Ctrl+P → Save as PDF")
    else:
        st.info("👈 Search a song or paste lyrics on the left panel")