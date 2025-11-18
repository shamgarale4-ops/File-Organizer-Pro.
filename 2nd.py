import streamlit as st
import os
import pathlib
import shutil
import time
import platform
import subprocess
import pandas as pd
import stat

# ==========================================
# 1. PAGE CONFIG & STYLING
# ==========================================
st.set_page_config(page_title="File Organizer Pro", page_icon="📂", layout="wide")

if 'current_path' not in st.session_state:
    st.session_state['current_path'] = ""
if 'start_path' not in st.session_state:
    st.session_state['start_path'] = ""
if 'preview_file' not in st.session_state:
    st.session_state['preview_file'] = None
if 'notepad_content' not in st.session_state:
    st.session_state['notepad_content'] = ""

# --- CSS STYLING ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #1e1e2f 0%, #252540 100%); }
    h1, h2, h3, h4, h5, h6, p, span, div { color: #e0e0e0; }
    
    .stTextInput > div > div, .stSelectbox > div > div {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
        color: white !important;
    }
    input, .stSelectbox [data-baseweb="select"] span { color: white !important; }
    
    [data-testid="stSidebar"] { background-color: #161625; border-right: 1px solid rgba(255,255,255,0.1); }
    
    .stButton > button {
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        font-weight: 500 !important;
    }
    .stButton > button:hover {
        background-color: rgba(255, 255, 255, 0.15) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
        color: #ffffff !important;
    }

    button[kind="primary"] {
        position: fixed !important;
        bottom: 40px !important;
        right: 40px !important;
        z-index: 9999 !important;
        width: auto !important;
        padding: 15px 40px !important;
        border-radius: 50px !important;
        font-size: 1.2rem !important;
        font-weight: bold !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5) !important;
        background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%) !important;
        color: white !important;
        border: 2px solid rgba(255,255,255,0.2) !important;
        transition: transform 0.2s ease !important;
    }
    button[kind="primary"]:hover {
        transform: scale(1.05) translateY(-5px) !important;
    }

    button[key^="del_"] { color: #ff6b6b !important; border-color: rgba(255, 107, 107, 0.3) !important; }
    button[key^="perm_del_"] { color: #ff4d4d !important; font-weight: bold !important; }
    
    .hero-title {
        font-size: 3rem; font-weight: 800;
        background: -webkit-linear-gradient(#fff, #aaa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent; margin: 0;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
FILE_CATEGORIES = {
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico", ".webp"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Code": [".py", ".java", ".cpp", ".c", ".js", ".html", ".css", ".php", ".sql", ".json", ".xml"],
    "Executables": [".exe", ".msi", ".apk", ".deb", ".dmg"]
}
CATEGORY_ICONS = {"Documents": "📄", "Images": "🖼️", "Videos": "🎥", "Audio": "🎵", "Archives": "📦", "Code": "💻", "Executables": "⚙️"}

TRASH_FOLDER_NAME = ".File_Organizer_Trash"

def get_category(file_extension):
    for category, extensions in FILE_CATEGORIES.items():
        if file_extension.lower() in extensions: return category
    return "Others"

def get_icon(name, is_folder=False):
    if is_folder: return "📁"
    ext = pathlib.Path(name).suffix.lower()
    if ext in FILE_CATEGORIES["Images"]: return "🖼️"
    if ext in FILE_CATEGORIES["Videos"]: return "🎥"
    if ext in FILE_CATEGORIES["Audio"]: return "🎵"
    if ext in FILE_CATEGORIES["Documents"]: return "📄"
    if ext in FILE_CATEGORIES["Code"]: return "💻"
    return "📝"

def get_unique_filename(directory, filename):
    if not os.path.exists(os.path.join(directory, filename)): return filename
    name, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(os.path.join(directory, f"{name}_{counter}{ext}")): counter += 1
    return f"{name}_{counter}{ext}"

def open_file_in_os(filepath):
    try:
        if platform.system() == 'Windows': os.startfile(filepath)
        elif platform.system() == 'Darwin': subprocess.call(('open', filepath))
        else: subprocess.call(('xdg-open', filepath))
    except Exception as e: st.error(f"Error: {e}")

def get_disk_usage(path):
    try:
        total, used, free = shutil.disk_usage(path)
        return total // (2**30), used // (2**30), free // (2**30)
    except: return 0, 0, 0

# --- ROBUST TRASH FUNCTIONS ---

def remove_readonly(func, path, excinfo):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception: pass

def init_trash(root_path):
    trash_path = os.path.join(root_path, TRASH_FOLDER_NAME)
    if not os.path.exists(trash_path):
        try:
            os.makedirs(trash_path)
            if platform.system() == "Windows":
                subprocess.check_call(["attrib", "+h", trash_path])
        except: pass
    return trash_path

def move_to_trash(item_path, root_path):
    trash_path = init_trash(root_path)
    item_name = os.path.basename(item_path)
    dest_name = get_unique_filename(trash_path, item_name)
    try:
        shutil.move(item_path, os.path.join(trash_path, dest_name))
        return True
    except PermissionError:
        try:
            os.chmod(item_path, stat.S_IWRITE)
            shutil.move(item_path, os.path.join(trash_path, dest_name))
            return True
        except: return False
    except Exception: return False

def restore_from_trash(item_name, root_path):
    trash_path = os.path.join(root_path, TRASH_FOLDER_NAME)
    source = os.path.join(trash_path, item_name)
    dest = get_unique_filename(root_path, item_name)
    try:
        shutil.move(source, os.path.join(root_path, dest))
        return True
    except: return False

def delete_permanently(item_name, root_path):
    trash_path = os.path.join(root_path, TRASH_FOLDER_NAME)
    target = os.path.join(trash_path, item_name)
    try:
        if os.path.isfile(target): os.remove(target)
        elif os.path.isdir(target): shutil.rmtree(target, onerror=remove_readonly)
        return True
    except: return False

def auto_clean_trash(root_path):
    trash_path = os.path.join(root_path, TRASH_FOLDER_NAME)
    if not os.path.exists(trash_path): return
    cutoff = time.time() - (30 * 86400)
    for item in os.listdir(trash_path):
        item_path = os.path.join(trash_path, item)
        try:
            if os.path.getmtime(item_path) < cutoff:
                if os.path.isfile(item_path): os.remove(item_path)
                elif os.path.isdir(item_path): shutil.rmtree(item_path, onerror=remove_readonly)
        except: pass

# --- NAV ACTIONS ---
def set_start_path():
    raw = st.session_state.get('path_input', '')
    clean = raw.strip('"').strip("'")
    if os.path.isdir(clean):
        st.session_state['current_path'] = clean
        st.session_state['start_path'] = clean
        st.session_state['preview_file'] = None
        auto_clean_trash(clean)
    elif clean: st.warning(f"Path not found: {clean}")

def change_dir(new_path):
    st.session_state['current_path'] = new_path
    st.session_state['preview_file'] = None

def go_up():
    curr = st.session_state.get('current_path', '')
    if curr:
        parent = os.path.dirname(curr)
        if parent and os.path.isdir(parent):
            st.session_state['current_path'] = parent
            st.session_state['preview_file'] = None

def go_home():
    st.session_state['current_path'] = st.session_state.get('start_path', '')
    st.session_state['preview_file'] = None

def set_preview(filepath):
    st.session_state['preview_file'] = filepath

# ==========================================
# 3. SIDEBAR
# ==========================================
with st.sidebar:
    st.title("⚙️ Dashboard")
    if st.session_state.get('current_path'):
        total, used, free = get_disk_usage(st.session_state.get('current_path'))
        st.caption(f"💾 Storage ({free} GB Free)")
        st.progress(used / total if total > 0 else 0)
    
    with st.expander("📝 Notepad", expanded=False):
        note_text = st.text_area("Write notes:", value=st.session_state['notepad_content'], height=150)
        st.session_state['notepad_content'] = note_text
        if st.button("💾 Save Note", use_container_width=True):
            current = st.session_state.get('current_path', '')
            if current and os.path.isdir(current):
                try:
                    with open(os.path.join(current, "notes.txt"), "a", encoding="utf-8") as f:
                        f.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n{note_text}\n")
                    st.success("Saved!")
                    st.session_state['notepad_content'] = ""
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
    
    root = st.session_state.get('start_path')
    if root:
        trash_dir = os.path.join(root, TRASH_FOLDER_NAME)
        trash_count = 0
        if os.path.exists(trash_dir):
            try: trash_count = len(os.listdir(trash_dir))
            except: pass
        
        with st.expander(f"🗑️ Trash ({trash_count})", expanded=False):
            st.caption("Files deleted automatically after 30 days.")
            if trash_count > 0:
                if st.button("🔥 Empty Trash Now", use_container_width=True):
                    try:
                        shutil.rmtree(trash_dir, onerror=remove_readonly)
                        init_trash(root)
                        st.toast("Trash Emptied!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
                
                st.divider()
                try:
                    for item in os.listdir(trash_dir):
                        c_name, c_rest, c_del = st.columns([3, 1, 1])
                        with c_name: st.text(item)
                        with c_rest:
                            if st.button("♻️", key=f"rst_{item}", help="Restore"):
                                restore_from_trash(item, root)
                                st.toast("Restored!")
                                time.sleep(0.5)
                                st.rerun()
                        with c_del:
                            if st.button("❌", key=f"perm_del_{item}", help="Delete Permanently"):
                                delete_permanently(item, root)
                                st.toast("Deleted Permanently")
                                time.sleep(0.5)
                                st.rerun()
                except: pass
            else:
                st.info("Trash is empty.")

    st.divider()
    st.subheader("Rules")
    with st.expander("View Extensions"):
        for cat, exts in FILE_CATEGORIES.items():
            st.markdown(f"**{CATEGORY_ICONS.get(cat,'📁')} {cat}**")
            st.caption(", ".join(exts))
    st.caption("File Organizer Pro v6.3")

# ==========================================
# 4. MAIN INTERFACE
# ==========================================

if not st.session_state.get('current_path'):
    st.markdown('<p class="hero-title">File Organizer Pro</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#a6a6c3; font-size:1.2rem;">Tidy up your digital chaos in seconds.</p>', unsafe_allow_html=True)
    st.write("") 
    st.text_input("📂 Paste your folder path here:", key='path_input', on_change=set_start_path)
    st.write("") 
    c1, c2, c3 = st.columns(3)
    with c1: st.info("**⚡ Instant Sort**\n\nCategorize files into Images, Docs, and Videos.")
    with c2: st.info("**👁️ Quick Preview**\n\nView images and play videos directly.")
    with c3: st.info("**🗑️ Smart Trash**\n\nSafely delete files with 30-day auto-recovery.")

else:
    c1, c2 = st.columns([5, 1])
    with c1: st.title("📂 File Explorer")
    with c2:
        if st.button("Close Folder", help="Go back"):
            st.session_state['current_path'] = ""
            st.session_state['start_path'] = ""
            st.rerun()

    current_path = st.session_state.get('current_path', '')
    start_path = st.session_state.get('start_path', '')
    
    if current_path and os.path.isdir(current_path):
        
        all_files_map = {}
        if start_path:
            for root_dir, dirs, filenames in os.walk(start_path):
                if TRASH_FOLDER_NAME in root_dir: continue
                for filename in filenames:
                    full_path = os.path.join(root_dir, filename)
                    rel_path = os.path.relpath(full_path, start_path)
                    all_files_map[rel_path] = full_path

        search_selection = st.selectbox(
            "🔍 Global Search (Recursive)", 
            options=list(all_files_map.keys()), 
            index=None, 
            placeholder="Type to search files in any subfolder..."
        )
        
        st.divider()

        if search_selection:
            st.success(f"Found: {search_selection}")
            selected_full_path = all_files_map[search_selection]
            c_res, c_prev = st.columns([1.5, 1])
            with c_res:
                st.markdown("### Selected File Actions")
                st.write(f"**Path:** `{selected_full_path}`")
                c1, c2, c3 = st.columns(3)
                with c1: 
                    if st.button("↗️ Open Externally", use_container_width=True): open_file_in_os(selected_full_path)
                with c2:
                    if st.button("👁️ Load Preview", use_container_width=True): set_preview(selected_full_path)
                with c3:
                    if st.button("🗑️ Delete File", use_container_width=True):
                        move_to_trash(selected_full_path, start_path)
                        st.toast("Moved to Trash")
                        time.sleep(1)
                        st.rerun()
            with c_prev:
                pv_path = selected_full_path
                ext = pathlib.Path(pv_path).suffix.lower()
                if ext in FILE_CATEGORIES["Images"]: st.image(pv_path)
                elif ext in FILE_CATEGORIES["Videos"]: st.video(pv_path)
                elif ext in FILE_CATEGORIES["Audio"]: st.audio(pv_path)
                elif ext in [".txt", ".py", ".c", ".json", ".xml"]:
                    try: 
                        with open(pv_path, "r", encoding="utf-8") as f:
                            st.code(f.read(), language=None)
                    except: st.info("Text preview unavailable")
            st.divider()
        
        st.markdown(f"""
        <div style="background-color: rgba(255,255,255,0.08); padding: 15px; border-radius: 10px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.1);">
            <span style="color: #b0b0b0; font-weight: 600; margin-right: 10px;">📂 Location:</span>
            <span style="color: #4fd1c5; font-family: monospace; font-size: 1rem;">{current_path}</span>
        </div>
        """, unsafe_allow_html=True)
        
        if current_path != start_path:
            b1, b2, b3 = st.columns([1, 1, 8])
            with b1: st.button("⬅️ Back", on_click=go_up)
            with b2: st.button("🏠 Home", on_click=go_home)
            st.divider()
        
        try:
            all_items = os.listdir(current_path)
            files = [f for f in all_items if os.path.isfile(os.path.join(current_path, f))]
            folders = [f for f in all_items if os.path.isdir(os.path.join(current_path, f)) and f != TRASH_FOLDER_NAME]
            
            if folders:
                st.subheader(f"📂 Folders ({len(folders)})")
                for i, folder in enumerate(folders):
                    new_path = os.path.join(current_path, folder)
                    st.button(f"📁 {folder}", key=f"dir_{i}", on_click=change_dir, args=(new_path,), use_container_width=True)
                st.write("")

            if files:
                st.divider()
                st.subheader(f"📄 Files ({len(files)})")
                
                with st.container(height=400):
                    for f in files:
                        fpath = os.path.join(current_path, f)
                        r1, r2, r3, r4 = st.columns([4, 1, 1, 1])
                        with r1: st.write(f"{get_icon(f)} **{f}**")
                        with r2: st.button("👁️", key=f"pv_{f}", on_click=set_preview, args=(fpath,), help="Preview")
                        with r3: 
                            if st.button("↗️", key=f"op_{f}", help="Open"): open_file_in_os(fpath)
                        with r4:
                            if st.button("🗑️", key=f"del_{f}", help="Delete"):
                                move_to_trash(fpath, start_path)
                                st.toast("Moved to Trash")
                                time.sleep(0.5)
                                st.rerun()
                        st.divider()
                
                st.subheader("Preview")
                pv_path = st.session_state.get('preview_file')
                if pv_path and os.path.exists(pv_path):
                    fname = os.path.basename(pv_path)
                    ext = pathlib.Path(fname).suffix.lower()
                    st.caption(f"Viewing: {fname}")
                    if ext in FILE_CATEGORIES["Images"]: st.image(pv_path)
                    elif ext in FILE_CATEGORIES["Videos"]: st.video(pv_path)
                    elif ext in FILE_CATEGORIES["Audio"]: st.audio(pv_path)
                    elif ext in [".txt", ".py", ".c", ".json", ".xml", ".md"]:
                        try: 
                            with open(pv_path, "r", encoding="utf-8") as f:
                                st.code(f.read(), language=None)
                        except: st.error("Cannot read text.")
                    else: st.info("No preview available.")
                else: st.info("Select a file (👁️) to preview.")

            elif not folders:
                st.warning("This folder is empty.")
                if current_path != start_path: st.button("⬅️ Go Back", on_click=go_up)
            
            if st.button("🚀 Organize Now", type="primary"):
                stats = {"moved": 0, "size": 0, "folders": set(), "cats": {}}
                all_files_to_move = []
                for root_dir, dirs, filenames in os.walk(current_path, topdown=False):
                    if TRASH_FOLDER_NAME in root_dir: continue 
                    for file in filenames:
                        if file == "notes.txt": continue
                        all_files_to_move.append(os.path.join(root_dir, file))
                
                prog = st.progress(0)
                total_files = len(all_files_to_move)
                
                if total_files > 0:
                    for i, src in enumerate(all_files_to_move):
                        filename = os.path.basename(src)
                        cat = get_category(pathlib.Path(filename).suffix)
                        dest_dir = os.path.join(start_path, cat)
                        
                        if os.path.dirname(src) == dest_dir: continue
                            
                        if not os.path.exists(dest_dir):
                            os.makedirs(dest_dir)
                            stats["folders"].add(cat)
                        
                        dest_name = get_unique_filename(dest_dir, filename)
                        try:
                            shutil.move(src, os.path.join(dest_dir, dest_name))
                            stats["moved"] += 1
                            stats["size"] += os.path.getsize(os.path.join(dest_dir, dest_name))
                            stats["cats"][cat] = stats["cats"].get(cat, 0) + 1
                        except: pass
                        prog.progress((i + 1) / total_files)

                generated_folders = set(FILE_CATEGORIES.keys())
                for root_dir, dirs, filenames in os.walk(current_path, topdown=False):
                    if root_dir == current_path: continue 
                    if TRASH_FOLDER_NAME in root_dir: continue
                    
                    if not os.listdir(root_dir):
                        folder_name = os.path.basename(root_dir)
                        if folder_name in generated_folders:
                            move_to_trash(root_dir, start_path)
                
                prog.empty()
                st.toast(f"Organized {stats['moved']} files!", icon="✅")
                st.success(f"Moved {stats['moved']} files to Main Root. Cleaned empty category folders.")
                
                if stats["cats"]:
                    chart_data = pd.DataFrame(list(stats["cats"].items()), columns=["Category", "Count"])
                    st.bar_chart(chart_data.set_index("Category"))
                
                st.session_state['preview_file'] = None
                time.sleep(1.5)
                st.rerun()
            
            st.write("")
            st.write("")
            st.write("")

        except Exception as e: st.error(f"Access Error: {e}")
