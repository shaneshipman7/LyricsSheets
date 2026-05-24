import streamlit as st
import requests
import re
import urllib.parse
import random

st.set_page_config(page_title="Stage Master", page_icon="🎤", layout="wide")

# ====================== DEFAULT SONGS ======================
DEFAULT_SONGS = [
    "Estuve Joan Sebastian",
    "Tatuajes Joan Sebastian",
    "Eso y Más Joan Sebastian",
    "Aunque Me Duela El Alma Joan Sebastian",
    "Bohemian Rhapsody Queen",
    "Hotel California Eagles",
]

# ====================== CHORD TEMPLATES ======================
STAGE_CHORD_TEMPLATES = {
    "ESTUVE": ["G", "D", "A", "D", "G", "D", "Em", "Bm", "A", "D", "Em", "A", "D"],
    "ESO Y MÁS": ["D", "A", "G", "D", "Bm", "F#m", "G", "A", "D"],
    "TATUAJES": ["C", "G", "F", "C", "Am", "Em", "F", "G", "C"],
}

def search_songs(query: str, limit: int = 8):
    if len(query.strip()) < 3:
        return []
    try:
        res = requests.get(f"https://lrclib.net/api/search?q={urllib.parse.quote(query)}", timeout=5)
        if res.ok:
            results = res.json()[:limit]
            return [(item.get('name', ''), item.get('artistName', '')) for item in results]
    except:
        pass
    return []

def fetch_lyrics(query: str):
    try:
        res = requests.get(f"https://lrclib.net/api/search?q={urllib.parse.quote(query)}", timeout=10)
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

def add_chords_to_lyrics(lyrics_text: str, title: str, density: int = 5) -> str:
    lookup = title.upper().strip()
    templates = {
        "ESTUVE": {"chords": STAGE_CHORD_TEMPLATES["ESTUVE"], "density": 5},
        "ESO Y MÁS": {"chords": STAGE_CHORD_TEMPLATES["ESO Y MÁS"], "density": 4},
        "TATUAJES": {"chords": STAGE_CHORD_TEMPLATES["TATUAJES"], "density": 5},
    }
    template = templates.get(lookup, {"chords": ["G", "D", "Em", "C", "D"], "density": 5})
    active_chords = template["chords"]
    chord_density = density
    
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
                output.append(timestamp)
                continue

            words = lyric_part.split()
            built = []
            syllable_count = 0

            for word in words:
                built.append(word)
                syllables = len(re.findall(r'[aeiouáéíóú]', word.lower())) or 1
                syllable_count += syllables

                if syllable_count >= chord_density:
                    chord = active_chords[chord_index % len(active_chords)]
                    chord_index += 1
                    built.insert(-1, f"[{chord}]")
                    syllable_count = 0

            if not any('[' in x for x in built):
                chord = active_chords[chord_index % len(active_chords)]
                built.insert(0, f"[{chord}]")
                chord_index += 1

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
    
    if "query_input" not in st.session_state:
        st.session_state.query_input = ""
    
    # --- CHANGED: Clear flag handling intercepts before input is generated ---
    if st.session_state.get("clear_query", False):
        st.session_state.query_input = ""
        st.session_state.clear_query = False

    query = st.text_input(
        "Song Title & Artist", 
        value=st.session_state.query_input,
        key="query_input",
        placeholder="Type song title and artist...",
        help="Start typing to search"
    )
    
    # Better auto-select JavaScript
    st.components.v1.html("""
        <script>
            setTimeout(() => {
                const inputs = document.querySelectorAll('input[aria-label="Song Title & Artist"]');
                inputs.forEach(input => {
                    input.addEventListener('focus', function() {
                        this.select();
                    }, { once: true });
                });
            }, 800);
        </script>
    """, height=0)

    # Clear button
    if st.button("🗑️ Clear Search Box", use_container_width=False):
        st.session_state.clear_query = True
        st.rerun()

    suggestions = search_songs(query)
    
    if suggestions:
        st.markdown("**Suggestions:**")
        selected_option = st.selectbox(
            "Choose a song:",
            options=[f"{title} - {artist}" for title, artist in suggestions],
            key="song_select"
        )
        
        if st.button("🎵 Load Selected Song", type="primary", use_container_width=True):
            with st.spinner("Fetching lyrics..."):
                lyrics_raw, title, artist = fetch_lyrics(selected_option)
                if lyrics_raw:
                    processed = add_chords_to_lyrics(lyrics_raw, title)
                    st.session_state.processed = processed
                    st.session_state.original_lyrics = lyrics_raw
                    st.session_state.title = title
                    st.session_state.artist = artist
                    
                    # --- FIX: Set flag to clear input text box on next loop rerun ---
                    st.session_state.clear_query = True 
                    
                    st.success(f"✅ Loaded **{title}**")
                    st.rerun()
    else:
        if query.strip():
            if st.button("Fetch + Generate Chords", type="primary", use_container_width=True):
                with st.spinner("Fetching lyrics..."):
                    lyrics_raw, title, artist = fetch_lyrics(query)
                    if lyrics_raw:
                        processed = add_chords_to_lyrics(lyrics_raw, title)
                        st.session_state.processed = processed
                        st.session_state.original_lyrics = lyrics_raw
                        st.session_state.title = title
                        st.session_state.artist = artist
                        
                        # --- FIX: Set flag to clear input text box on next loop rerun ---
                        st.session_state.clear_query = True
                        
                        st.success(f"✅ Loaded **{title}**")
                        st.rerun()
                    else:
                        st.error("Lyrics not found. Try manual paste below.")

    st.subheader("Manual Paste")
    manual = st.text_area("Paste full lyrics or chord sheet", height=280)
    if st.button("Process Manual Input", use_container_width=True):
        if manual.strip():
            st.session_state.processed = manual
            st.session_state.original_lyrics = manual
            st.session_state.title = "CUSTOM"
            st.session_state.artist = "Artist"
            st.success("Manual sheet loaded!")

with col2:
    if "processed" in st.session_state:
        lyrics = st.session_state.processed
        title = st.session_state.get("title", "SONG")
        artist = st.session_state.get("artist", "")

        font_size = st.slider("Font Size (Stage View)", 14, 32, 22)
        chord_density = st.slider("Chord Density (Lower = More Chords)", 3, 8, 5)
        show_timestamps = st.checkbox("Show Timestamps", value=False)
        show_trans = st.checkbox("Show Spanish → English Translation", True)

        st.markdown(f"### {title.upper()}")
        st.markdown(f"**{artist}**")

        if st.button("🔄 Re-apply Chords with New Density", use_container_width=True):
            if "original_lyrics" in st.session_state:
                lyrics_raw = st.session_state.original_lyrics
                new_processed = add_chords_to_lyrics(lyrics_raw, title, density=chord_density)
                st.session_state.processed = new_processed
                st.rerun()

        # Translation caching
        if "translations" not in st.session_state:
            st.session_state.translations = {}
        translations = st.session_state.translations

        if show_trans and detect_spanish(lyrics):
            with st.spinner("Translating..."):
                lines = lyrics.split("\n")
                for line in lines[:15]:
                    clean = re.sub(r'\[\d{2}:\d{2}.*?\]|\[[A-G].*?\]', '', line).strip()
                    if clean and len(clean) > 5 and clean not in translations:
                        try:
                            r = requests.get(
                                f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(clean)}&langpair=es|en",
                                timeout=4
                            )
                            if r.ok:
                                translations[clean] = r.json()['responseData']['translatedText']
                        except:
                            pass

        # Display lyrics
        for line in lyrics.split("\n"):
            if not line.strip():
                st.markdown("---")
                continue

            time_match = re.match(r'^\[(\d{2}:\d{2})\]', line)
            timestamp = time_match.group(0) if time_match else ""
            content = line[len(timestamp):].strip() if timestamp else line.strip()

            parts = re.split(r'(\[[^\]]+\])', content)
            display_html = ""
            for part in parts:
                if part.startswith('[') and part.endswith(']'):
                    chord = part[1:-1]
                    display_html += f"<span style='color:#ff4d4d; font-weight:bold; font-size:{font_size+4}px; margin-right:12px;'>{chord}</span>"
                elif part.strip():
                    display_html += f"<span style='font-size:{font_size}px; font-family:monospace; white-space:pre;'>{part}</span>"

            if display_html:
                ts_html = f"<span style='color:#888; font-size:{font_size-2}px; margin-right:12px;'>{timestamp}</span>" if show_timestamps and timestamp else ""
                st.markdown(f"<div style='margin-bottom:14px; line-height:1.7;'>{ts_html}{display_html}</div>", unsafe_allow_html=True)
                
                clean_key = re.sub(r'\[[^\]]+\]', '', line).strip()
                if clean_key in translations:
                    st.markdown(f"<div style='color:#666; font-style:italic; font-size:{font_size-3}px; margin-bottom:8px; margin-left:20px;'>→ {translations[clean_key]}</div>", unsafe_allow_html=True)

        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button("📥 Download .txt", lyrics, f"{title} - {artist}.txt", "text/plain")
        
        with col_b:
            if st.button("🖨️ Print / Save as PDF", use_container_width=True):
                printable_html = f"""
                <html>
                <head>
                    <title>{title} - {artist}</title>
                    <style>
                        @media print {{
                            body {{ font-family: monospace; padding: 40px; max-width: 900px; margin: auto; line-height: 1.8; }}
                            .chord {{ color: #ff4d4d; font-weight: bold; }}
                            h1 {{ text-align: center; }}
                            h2 {{ text-align: center; color: #555; }}
                            hr {{ margin: 25px 0; }}
                        }}
                    </style>
                </head>
                <body>
                    <h1>{title.upper()}</h1>
                    <h2>{artist}</h2>
                    <hr>
                """
                for line in lyrics.split("\n"):
                    if not line.strip():
                        printable_html += "<br><br>"
                        continue
                    time_match = re.match(r'^\[(\d{2}:\d{2})\]', line)
                    timestamp = time_match.group(0) if time_match else ""
                    content = line[len(timestamp):].strip() if timestamp else line.strip()
                    content_html = re.sub(r'\[([A-G]#?m?)\]', r'<span class="chord">[\1]</span>', content)
                    ts_display = f"{timestamp} " if show_timestamps else ""
                    printable_html += f'<div style="margin:16px 0;">{ts_display}{content_html}</div>'
                printable_html += "</body></html>"

                st.components.v1.html(
                    f"""<script>
                        var win = window.open('', '_blank');
                        win.document.write(`{printable_html}`);
                        win.document.close();
                        setTimeout(() => win.print(), 600);
                    </script>""", 
                    height=0
                )
                st.success("✅ Clean print window opened!")
    else:
        st.info("👈 Search a song or paste lyrics on the left panel")