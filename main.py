import streamlit as st
import random
import pandas as pd
import json
import os

# --- Configuration ---
DATA_FILE = "keywords_data.json"
st.set_page_config(page_title="Keyword & Tag Manager", layout="centered")


# --- Helper Functions for Persistence ---
def load_data():
    """Loads data from the local JSON file."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []  # Return empty if file is corrupted
    return []


def save_data():
    """Saves the current session state database to the local JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(st.session_state.db, f, indent=4)


# --- Session State Initialization ---
if 'db' not in st.session_state:
    st.session_state.db = load_data()

# Rebuild the set of unique tags from the loaded database
# This ensures we have all tags even after a restart
current_all_tags = set()
for entry in st.session_state.db:
    for tag in entry.get('Tags', []):
        current_all_tags.add(tag)
st.session_state.all_tags = current_all_tags

if 'random_result' not in st.session_state:
    st.session_state.random_result = None


# --- Action Functions ---
def add_entry(keyword, selected_tags, new_tags_input):
    if not keyword:
        st.error("Please enter a keyword.")
        return

    # Process tags
    final_tags = list(selected_tags)

    # Process multiple comma-separated new tags
    if new_tags_input:
        new_tags = [t.strip() for t in new_tags_input.split(',') if t.strip()]
        for tag in new_tags:
            if tag not in final_tags:
                final_tags.append(tag)
                st.session_state.all_tags.add(tag)

    # Add to DB
    entry = {"Keyword": keyword, "Tags": final_tags}
    st.session_state.db.append(entry)

    # Save to disk
    save_data()
    st.success(f"Added '{keyword}' with {len(final_tags)} tags")


def update_entry(index, tags_to_add, new_tags_text, tags_to_remove):
    if 0 <= index < len(st.session_state.db):
        current_tags = st.session_state.db[index]['Tags']

        # Add new custom tags (comma separated)
        if new_tags_text:
            new_tags = [t.strip() for t in new_tags_text.split(',') if t.strip()]
            for tag in new_tags:
                if tag and tag not in current_tags:
                    current_tags.append(tag)
                    st.session_state.all_tags.add(tag)

        # Add selected existing tags
        for t in tags_to_add:
            if t not in current_tags:
                current_tags.append(t)

        # Remove selected tags
        for t in tags_to_remove:
            if t in current_tags:
                current_tags.remove(t)

        st.session_state.db[index]['Tags'] = current_tags
        save_data()  # Save to disk
        st.toast("Entry updated successfully!")


def delete_entry(index):
    if 0 <= index < len(st.session_state.db):
        removed = st.session_state.db.pop(index)
        save_data()  # Save to disk
        st.toast(f"Deleted '{removed['Keyword']}'")
        st.session_state.random_result = None


def get_random_entry():
    if not st.session_state.db:
        st.warning("Database is empty.")
        return None
    return random.choice(st.session_state.db)


# --- UI Layout ---
st.title("🗂️ Keyword Manager")

# Simplified Tabs
tab_manage, tab_random = st.tabs(["📝 Manage Data", "🎲 Random Retrieve"])

# === TAB 1: MANAGE DATA ===
with tab_manage:
    # 1. ADD SECTION (Collapsible)
    with st.expander("➕ Add New Entry", expanded=False):
        with st.form("add_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                new_kw = st.text_input("Keyword", placeholder="e.g. Machine Learning")
            with c2:
                # Get latest tags for the dropdown
                tag_opts = sorted(list(st.session_state.all_tags))
                sel_tags = st.multiselect("Existing Tags", options=tag_opts)
                new_tags_in = st.text_input("New Tags (Comma-separated)", placeholder="e.g. urgent, study, important")

            if st.form_submit_button("Save"):
                add_entry(new_kw, sel_tags, new_tags_in)
                st.rerun()

    st.divider()

    # 2. EDIT/DELETE SECTION
    st.subheader("Current Database")

    if st.session_state.db:
        # Show Table
        df = pd.DataFrame(st.session_state.db)
        # Convert tags list to string for better display in dataframe
        df_display = df.copy()
        df_display['Tags'] = df_display['Tags'].apply(lambda x: ', '.join(x))
        st.dataframe(df_display, use_container_width=True)

        st.write("### Edit Entry")
        # Selector for editing
        edit_opts = range(len(st.session_state.db))
        selected_idx = st.selectbox(
            "Select an entry to modify:",
            options=edit_opts,
            format_func=lambda x: f"{x + 1}. {st.session_state.db[x]['Keyword']}"
        )

        if selected_idx is not None:
            entry_data = st.session_state.db[selected_idx]

            # Edit Container
            with st.container(border=True):
                st.markdown(f"**Selected:** `{entry_data['Keyword']}`")
                st.caption(f"Current Tags: {', '.join(entry_data['Tags'])}")

                ec1, ec2 = st.columns(2)
                with ec1:
                    st.caption("Add Tags")
                    # Calculate available tags to add
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
        st.info("No data yet. Open the 'Add New Entry' section above to get started.")

# === TAB 2: RANDOM RETRIEVE ===
with tab_random:
    st.header("Random Picker")

    if st.button("🎲 Pick Random Keyword", type="primary", use_container_width=True):
        st.session_state.random_result = get_random_entry()

    if st.session_state.random_result:
        res = st.session_state.random_result

        st.markdown("---")
        st.subheader(res['Keyword'])

        if res['Tags']:
            # Render tags nicely
            html_tags = ""
            colors = ["#e0f2f1", "#e3f2fd", "#f3e5f5", "#fbe9e7", "#fff3e0"]
            text_colors = ["#00695c", "#1565c0", "#6a1b9a", "#d84315", "#ef6c00"]

            for i, tag in enumerate(res['Tags']):
                bg = colors[i % len(colors)]
                tx = text_colors[i % len(colors)]
                html_tags += f'''
                <span style="background-color:{bg}; color:{tx}; 
                padding:5px 10px; border-radius:15px; margin:0 5px; 
                display:inline-block; font-weight:500;">#{tag}</span>
                '''
            st.markdown(html_tags, unsafe_allow_html=True)
        else:
            st.caption("No tags assigned")
        st.markdown("---")
