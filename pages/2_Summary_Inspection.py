from collections import defaultdict
import streamlit as st

import asyncio
import aiohttp
from dotenv import load_dotenv
import os
import time
import motion
import difflib

from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

import requests
import json


st.set_page_config(layout="wide")

st.subheader("Inspect Incrementally-Maintained Summaries Used in Prompts")
st.write(
    "Each sub-part of the prompt gets updated separately. Some are the results of LLM calls (e.g., `previous_recommendations` is an extracted list of short items from the notes on the left, and `search_query_summary` is an LLM-generated summary of previous search queries)."
)

# Initialize session state for last update time
if "global_last_update" not in st.session_state:
    st.session_state.global_last_update = time.time()
if "last_update" not in st.session_state:
    st.session_state.last_update = defaultdict(time.time)
if "last_diff" not in st.session_state:
    st.session_state.last_diff = defaultdict(time.time)
if "old_state" not in st.session_state:
    st.session_state.old_state = defaultdict(None)
if "query_summary_diff" not in st.session_state:
    st.session_state.query_summary_diff = defaultdict(str)
if "selected_index" not in st.session_state:
    st.session_state.selected_index = 0
if "first_time" not in st.session_state:
    st.session_state.first_time = True

# Display the summary trends
global_state = motion.inspect_state("GlobalSummaries__production")
st.write("**Latest News Summary** (In Every User's Prompt)")
st.success(global_state["news_summary"])

# Show a dropdown list of all the states in st.session_state.old_state
sorted_keys = sorted(
    st.session_state.old_state.keys(),
    key=lambda x: st.session_state.last_diff[x],
    reverse=True,
)
options = [
    f"{key} (updated {(time.time() - st.session_state.last_diff[key]):.2f} seconds ago)"
    for key in sorted_keys
]
instance_prettified = st.selectbox(
    "Select a user_id to inspect user-specific sub-parts",
    options,
    index=st.session_state.selected_index,
    key="instance_prettified",
    on_change=lambda: setattr(
        st.session_state,
        "selected_index",
        options.index(st.session_state["instance_prettified"]),
    ),
)
if instance_prettified:
    # Parse the selected instance
    selected_instance = options[st.session_state.selected_index]
    instance_to_show = selected_instance.split("(")[0].strip()

    st.caption(
        f"User_id {instance_to_show} last updated {time.time() - st.session_state.last_diff[instance_to_show]} seconds ago"
    )

    # Display the user's style summary in a styled box
    if st.session_state.old_state[instance_to_show] is not None:
        st.markdown(f"**{instance_to_show}'s Style Summary:**")
        st.warning(st.session_state.old_state[instance_to_show]["query_summary"])

    if st.session_state.query_summary_diff[instance_to_show]:
        st.markdown(f"**Diff:**")
        st.error(st.session_state.query_summary_diff[instance_to_show])

    with st.expander("Show all prompt sub-parts"):
        st.write(st.session_state.old_state[instance_to_show])

# Main loop to refresh content
while True:
    # List all instances of the Fashion component
    instances = motion.get_instances("Fashion")

    # Check if 2 seconds have passed
    if (
        st.session_state.first_time
        or time.time() - st.session_state.global_last_update > 2
    ):
        is_changed = False
        st.session_state.first_time = False

        for instance in instances:

            state = motion.inspect_state(f"Fashion__{instance}")

            # Load instance and fetch state
            gender = state["gender"]
            occupation = state["occupation"]
            age = state["age"]

            if instance not in st.session_state.old_state:
                st.session_state.old_state[instance] = None
                st.session_state.last_diff[instance] = time.time()
                st.session_state.last_update[instance] = time.time()

            if (
                st.session_state.old_state[instance] is not None
                and st.session_state.old_state[instance] != state
            ):
                st.session_state.last_diff[instance] = time.time()

            if (
                st.session_state.old_state[instance] is None
                or st.session_state.old_state[instance] != state
            ):
                if st.session_state.old_state[instance] is not None:
                    # Compute diff for query_summary
                    diff = difflib.ndiff(
                        st.session_state.old_state[instance][
                            "query_summary"
                        ].splitlines(),
                        state["query_summary"].splitlines(),
                    )
                    st.session_state.query_summary_diff[instance] = "\n".join(diff)
                else:
                    st.session_state.query_summary_diff[instance] = (
                        "No previous summary stored."
                    )

                st.session_state.old_state[instance] = state
                is_changed = True

            # Update last refresh time
            st.session_state.last_update[instance] = time.time()

        # Write global last update time
        st.session_state.global_last_update = time.time()

        # If something was refreshed, rerun the page
        if is_changed:
            st.rerun()

    time.sleep(1)  # Short sleep to prevent maxing out the CPU
