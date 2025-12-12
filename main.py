import streamlit as st
import random
import pandas as pd
import json
import os
import hashlib

# --- Configuration ---
USERS_FILE = "users.json"
DATA_PREFIX = "data_"  # distinct files: data_username.json

st.set_page_config(page_title="Keyword & Tag Manager", layout="centered")

# --- Security & Auth Functions ---
def make_hashes(password):
    """Returns SHA-256 hash of the password."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    """Checks if password matches the hash."""
    if make_hashes(password) == hashed_text:
        return True
    return False

def load_users():
    """Loads the user credentials database."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_user(username, password):
    """Saves a new user to the credentials database."""
    users = load_users()
    users[username] = make_hashes(password)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def get_user_data_file(username):
    """Returns the filename for a specific user's data."""
    # Simple sanitization to prevent directory traversal
    safe_username = "".join([c for c in username if c.isalnum() or c in ('_', '-')])
    return f"{DATA_PREFIX}{safe_username}.json"

# --- Data Persistence Functions ---
def load_data(username):
    """Loads data specific to the logged-in user."""
    filename = get_user_data_file(username)
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_data(username):
    """Saves current session db to the user's specific file."""
    filename = get_user_data_file(username)
    with open(filename, 'w') as f:
        json.dump(st.session_state.db, f, indent=4)

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'db' not in st.session_state:
    st.session_state.db = []
if 'all_tags' not in st.session_state:
    st.session_state.all_tags = set()
if 'random_result' not in st.session_state:
    st.session_state.random_result = None

# --- Logic Functions ---
def login_user(username, password):
    users = load_users()
    if username in users and check_hashes(password, users[username]):
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.db = load_data(username)
        # Rebuild tags for this user
        tags = set()
        for entry in st.session_state.db:
            for tag in entry.get('Tags', []):
                tags.add(tag)
        st.session_state.all_tags = tags
        st.rerun()
    else:
        st.error("Incorrect Username or Password")

def register_user(username, password):
    users = load_users()
    if username in users:
        st.error("Username already exists.")
    else:
        save_user(username, password)
        st.success("Account created! Please log in.")

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.db = []
    st.session_state.all_tags = set()
    st.session_state.random_result = None
    st.rerun()

def add_entry(keyword, selected_tags, new_tags_input):
    if not keyword:
        st.error("Please enter a keyword.")
        return

    final_tags = list(selected_tags)
    
    # Process multiple comma-separated new tags
    if new_tags_input:
        new_tags = [t.strip() for t in new_tags_input.split(',') if t.strip()]
        for tag in new_tags:
            if tag not in final_tags:
                final_tags.append(tag)
                st.session_state.all_tags.add(tag)

    entry = {"Keyword": keyword, "Tags": final_tags}
    st.session_state.db.append(entry)
    save_data(st.session_state.username)
    st.success(f"Added '{keyword}'")

def update_entry(index, tags_to_add, new_tags_text, tags_to_remove):
    if 0 <= index < len(st.session_state.db):
        current_tags = st.session_state.db[index]['Tags']
        
        # Add new custom tags
        if new_tags_text:
            new_tags = [t.strip() for t in new_tags_text.split(',') if t.strip()]
            for tag in new_tags:
                if tag and tag not in current_tags:
                    current_tags.append(tag)
                    st.session_state.all_tags.add(tag)
        
        # Add existing
        for t in tags_to_add:
            if t not in current_tags:
                current_tags.append(t)
        
        # Remove
        for t in tags_to_remove:
            if t in current_tags:
                current_tags.remove(t)
                
        st.session_state.db[index]['Tags'] = current_tags
        save_data(st.session_state.username)
        st.toast("Entry updated!")

def delete_entry(index):
    if 0 <= index < len(st.session_state.db):
        removed = st.session_state.db.pop(index)
        save_data(st.session_state.username)
        st.toast(f"Deleted '{removed['Keyword']}'")
        st.session_state.random_result = None

# --- Main App Interface ---
def main_app():
    st.sidebar.markdown(f"👤 Logged in as: **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        logout()

    st.title("🗂️ Keyword Manager")

    tab_manage, tab_random = st.tabs(["📝 Manage Data", "🎲 Random Retrieve"])

    # === TAB 1: MANAGE DATA ===
    with tab_manage:
        with st.expander("➕ Add New Entry", expanded=False):
            with st.form("add_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    new_kw = st.text_input("Keyword", placeholder="e.g. Machine Learning")
                with c2:
                    tag_opts = sorted(list(st.session_state.all_tags))
                    sel_tags = st.multiselect("Existing Tags", options=tag_opts)
                    new_tags_in = st.text_input("New Tags (Comma-separated)", placeholder="urgent, study")
                
                if st.form_submit_button("Save"):
                    add_entry(new_kw, sel_tags, new_tags_in)
                    st.rerun()

        st.divider()

        st.subheader("Current Database")
        if st.session_state.db:
            # Show Table
            df = pd.DataFrame(st.session_state.db)
            df_display = df.copy()
            df_display['Tags'] = df_display['Tags'].apply(lambda x: ', '.join(x))
            st.dataframe(df_display, use_container_width=True)
            
            st.write("### Edit Entry")
            edit_opts = range(len(st.session_state.db))
            selected_idx = st.selectbox(
                "Select an entry to modify:", 
                options=edit_opts, 
                format_func=lambda x: f"{x+1}. {st.session_state.db[x]['Keyword']}"
            )

            if selected_idx is not None:
                entry_data = st.session_state.db[selected_idx]
                with st.container(border=True):
                    st.markdown(f"**Selected:** `{entry_data['Keyword']}`")
                    st.caption(f"Current Tags: {', '.join(entry_data['Tags'])}")
                    
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        st.caption("Add Tags")
                        avail = [t for t in st.session_state.all_tags if t not in entry_data['Tags']]
                        add_exist = st.multiselect("Pick tags", sorted(avail), key="edit_add")
                        add_new = st.text_input("Create tags (comma-separated)", key="edit_new")
                    with ec2:
                        st.caption("Remove Tags")
                        rem_tags = st.multiselect("Select tags to remove", entry_data['Tags'], key="edit_rem")
                    
                    b1, b2 = st.columns([1, 4])
                    with b1:
                        if st.button("Update", type="primary"):
                            update_entry(selected_idx, add_exist, add_new, rem_tags)
                            st.rerun()
                    with b2:
                        if st.button("🗑️ Delete"):
                            delete_entry(selected_idx)
                            st.rerun()
        else:
            st.info("No data found for this account.")

    # === TAB 2: RANDOM RETRIEVE ===
    with tab_random:
        st.header("Random Picker")
        if st.button("🎲 Pick Random Keyword", type="primary", use_container_width=True):
            if not st.session_state.db:
                st.warning("Database is empty.")
            else:
                st.session_state.random_result = random.choice(st.session_state.db)

        if st.session_state.random_result:
            res = st.session_state.random_result
            st.markdown("---")
            st.subheader(res['Keyword'])
            if res['Tags']:
                html_tags = ""
                colors = ["#e0f2f1", "#e3f2fd", "#f3e5f5", "#fbe9e7", "#fff3e0"]
                text_colors = ["#00695c", "#1565c0", "#6a1b9a", "#d84315", "#ef6c00"]
                for i, tag in enumerate(res['Tags']):
                    bg = colors[i % len(colors)]
                    tx = text_colors[i % len(colors)]
                    html_tags += f'<span style="background-color:{bg}; color:{tx}; padding:5px 10px; border-radius:15px; margin:0 5px; display:inline-block;">#{tag}</span>'
                st.markdown(html_tags, unsafe_allow_html=True)
            else:
                st.caption("No tags assigned")
            st.markdown("---")

# --- Login Interface ---
def login_page():
    st.title("🔐 Login")
    
    tabs = st.tabs(["Login", "Sign Up"])
    
    with tabs[0]:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            if submit:
                login_user(username, password)
                
    with tabs[1]:
        st.header("Create New Account")
        with st.form("register_form"):
            new_user = st.text_input("New Username")
            new_pass = st.text_input("New Password", type="password")
            submit_reg = st.form_submit_button("Sign Up")
            if submit_reg:
                if new_user and new_pass:
                    register_user(new_user, new_pass)
                else:
                    st.warning("Please fill in both fields")

# --- Flow Control ---
if st.session_state.logged_in:
    main_app()
else:
    login_page()
