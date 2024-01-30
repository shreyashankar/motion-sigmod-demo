import streamlit as st
from fashion.recommender import Fashion

from dotenv import load_dotenv
import os
import time
import motion

load_dotenv()

import requests
import json

SERPER_URL = "https://google.serper.dev/images"
NUM_RESULTS = 4

st.set_page_config(layout="wide")


@st.cache_resource
def load_instance():
    f = Fashion()
    return f


col2, col1 = st.columns(2)


def fetch_results(query):
    f = load_instance()

    start_time = time.time()
    recs = f.run(
        "recommend", props={"event": query}, ignore_cache=True, force_refresh=True
    )
    generation_time = time.time() - start_time

    # Load up each recommendation
    for _, value in recs.model_dump().items():
        # Generate a note very fast
        note = f.run(
            "note",
            props={"recommendation": value, "event": query},
            ignore_cache=True,
            force_refresh=True,
        )

        payload = json.dumps({"q": f"womenswear {value}"})

        headers = {
            "X-API-KEY": os.getenv("SERPER_API_KEY"),
            "Content-Type": "application/json",
        }

        response = requests.request("POST", SERPER_URL, headers=headers, data=payload)
        yield generation_time, note, response.json()
    #     all_results.extend(response.json()["images"])

    # return all_results


# Initialize session state for page number
if "page_number" not in st.session_state:
    st.session_state.page_number = 1

col2.subheader("Demo Application")

# Input for query string
query = col2.text_input("What event do you want to be styled for?")

# Check if a query was entered
if query:
    i = 0
    # Fetch images for the selected page
    for generation_time, note, results in fetch_results(query):
        img_results = results["images"][:NUM_RESULTS]
        # st.subheader(results["searchParameters"]["q"].replace("menswear", "").strip())

        if i == 0:
            col2.caption(f"Generated in {generation_time} seconds")

        col2.caption(note)
        # Display results in a grid
        row1 = col2.columns(len(img_results))
        for elem, result in zip(row1, img_results):
            elem.image(result["imageUrl"], use_column_width="always")
            elem.write(result["title"])

        i += 1

    # Display results
    # if results:
    #     st.write(results)
    # else:
    #     st.write("No results to display")

    # Next Page button
    if col2.button("Next Page"):
        st.session_state.page_number += 1


# Initialize session state for last update time
if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()
if "last_diff" not in st.session_state:
    st.session_state.last_diff = time.time()
if "old_state" not in st.session_state:
    st.session_state.old_state = None

# Placeholder for dynamic content in col1
header_placeholder = col1.empty()
description_placeholder = col1.empty()
time_placeholder = col1.empty()
state_placeholder = col1.empty()
# Main loop to refresh content
while True:
    # Check if 5 seconds have passed
    if time.time() - st.session_state.last_update > 5:
        # Load instance and fetch state
        f = load_instance()
        state = f.run("state", props={}, ignore_cache=True, force_refresh=True)

        if (
            st.session_state.old_state is not None
            and st.session_state.old_state != state
        ):
            st.session_state.last_diff = time.time()

        st.session_state.old_state = state

        header_placeholder.subheader("Prompt Sub-Parts")
        description_placeholder.write(
            "Each sub-part of the prompt gets updated separately. Some are the results of LLM calls (e.g., `previous_recommendations` is an extracted list of short items from the notes on the left, and `search_query_summary` is an LLM-generated summary of previous search queries)."
        )
        time_placeholder.caption(
            f"Last updated {time.time() - st.session_state.last_diff} seconds ago"
        )
        state_placeholder.write(state)

        # Update last refresh time
        st.session_state.last_update = time.time()

    time.sleep(1)  # Short sleep to prevent maxing out the CPU
