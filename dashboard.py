from collections import defaultdict
import streamlit as st
from fashion.recommender import Fashion

import asyncio
import aiohttp
from dotenv import load_dotenv
import os
import time
import motion

from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

import requests
import json

SERPER_URL = "https://google.serper.dev/images"
NUM_RESULTS = 1

st.set_page_config(layout="wide")


@st.cache_resource
def load_instance(user_id, gender, occupation, age):
    f = Fashion(
        user_id,
        init_state_params={"gender": gender, "occupation": occupation, "age": age},
    )
    return f


tab2, tab1 = st.tabs(["Demo App", "Developer Dashboard"])


def send_feedback(
    query, user_id, gender, occupation, age, all_rec_text, action, feedback
):
    f = load_instance(user_id, gender, occupation, age)

    # Send feedback
    f.run(
        "user_feedback",
        props={
            "outfit": all_rec_text,
            "action": action,
            "feedback": feedback,
            "event": query,
        },
    )

    # Close the instance
    f.shutdown()


def fetch_results(query, user_id, gender, occupation, age):
    f = load_instance(user_id, gender, occupation, age)

    recs = f.run(
        "recommend", props={"event": query}, ignore_cache=True, force_refresh=True
    )

    with ThreadPoolExecutor() as executor:
        futures = []
        for _, value in recs.model_dump().items():
            futures.append(executor.submit(process_recommendation, f, value, query))

        for future in as_completed(futures):
            yield future.result()

    # Close the instance
    f.shutdown()


def process_recommendation(f, value, query):
    note = f.run(
        "note",
        props={"recommendation": value, "event": query},
        ignore_cache=True,
        force_refresh=True,
    )

    return value, note


async def fetch_all_images(recommendations, gender):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_images(session, value, gender) for value in recommendations]
        return await asyncio.gather(*tasks)


async def fetch_images(session, value, gender):
    payload = json.dumps({"q": f"{value} for {gender} to buy"})

    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json",
    }

    async with session.post(SERPER_URL, headers=headers, data=payload) as response:
        return await response.json()


with tab2:
    # Display user info form if not already submitted
    if st.session_state.get("user_info") is None:
        st.subheader("Enter Your Information")
        with st.form(key="user_info_form"):
            user_id = st.text_input("User ID", "test_user_1234")
            gender = st.selectbox("Gender", ["Male", "Female", "Non-binary"])
            occupation = st.text_input(
                "Occupation", "Researcher, computer scientist, dog dad"
            )
            age = st.slider("How old are you?", 15, 100, 30)
            submitted = st.form_submit_button("Submit")
            if submitted:
                st.session_state.user_info = {
                    "user_id": user_id,
                    "gender": gender,
                    "occupation": occupation,
                    "age": age,
                }
                f = load_instance(user_id, gender, occupation, age)
                f.shutdown()
                st.rerun()  # Reload the page to proceed with the main app

    else:
        # Initialize session state for page number
        if "page_number" not in st.session_state:
            st.session_state.page_number = 1

        st.subheader("Demo Application")

        # Input for query string
        query = st.text_input(
            "What event do you want to be styled for?",
        )

        # Check if a query was entered
        if query:
            i = 0
            placeholder_latency = st.empty()
            placeholder_buttons = st.columns([0.1, 0.15, 0.65, 0.1])
            columns_of_products = st.columns(5)

            # Get user info
            user_id = st.session_state.user_info["user_id"]
            gender = st.session_state.user_info["gender"]
            occupation = st.session_state.user_info["occupation"]
            age = st.session_state.user_info["age"]

            all_rec_text = []
            start_time = time.time()

            # Fetch images for the selected page
            for rec_text, note in fetch_results(
                query, user_id, gender, occupation, age
            ):
                if i == 0:
                    generation_time = time.time() - start_time
                    placeholder_latency.caption(
                        f"Generated in {generation_time} seconds"
                    )
                    love_button = placeholder_buttons[0].button(
                        "Love ❤️", key=f"like_{i}"
                    )
                    with placeholder_buttons[1].popover("Don't like 👎"):
                        dislike_feedback = st.text_input(
                            "Why don't you like this?", key=f"dislike_{i}"
                        )

                    # Next Page button
                    if placeholder_buttons[3].button("Next Page"):
                        st.session_state.page_number += 1

                # Fetch images
                columns_of_products[i].write(f"**{rec_text}**")
                columns_of_products[i].write(f"_{note}_")

                all_rec_text.append(rec_text)
                i += 1

            # Render images
            i = 0
            all_images = asyncio.run(fetch_all_images(all_rec_text, gender))
            for image_results in all_images:
                img_results = image_results["images"][:NUM_RESULTS]
                columns_of_products[i].image(
                    img_results[0]["imageUrl"], use_column_width="always"
                )
                i += 1

            # If user clicks on love button, trigger a new flow
            if love_button:
                send_feedback(
                    query,
                    user_id,
                    gender,
                    occupation,
                    age,
                    all_rec_text,
                    action="love",
                    feedback="",
                )

            if dislike_feedback:
                print(f"Sending Dislike feedback: {dislike_feedback}")
                send_feedback(
                    query,
                    user_id,
                    gender,
                    occupation,
                    age,
                    all_rec_text,
                    action="dislike",
                    feedback=dislike_feedback,
                )
                # Reset dislike feedback
                dislike_feedback = None

# Initialize session state for last update time
if "global_last_update" not in st.session_state:
    st.session_state.global_last_update = time.time()
if "last_update" not in st.session_state:
    st.session_state.last_update = defaultdict(time.time)
if "last_diff" not in st.session_state:
    st.session_state.last_diff = defaultdict(time.time)
if "old_state" not in st.session_state:
    st.session_state.old_state = defaultdict(None)
if "already_refreshed" not in st.session_state:
    st.session_state.already_refreshed = False

# Placeholder for dynamic content in tab1
with tab1:
    st.subheader("Prompt Sub-Parts")
    st.write(
        "Each sub-part of the prompt gets updated separately. Some are the results of LLM calls (e.g., `previous_recommendations` is an extracted list of short items from the notes on the left, and `search_query_summary` is an LLM-generated summary of previous search queries)."
    )

    # Show a refresh button
    if st.button("Refresh"):
        st.rerun()

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
    instance_to_show = st.selectbox("Select a user_id to inspect", options)
    if instance_to_show:
        # Parse the selected instance
        instance_to_show = instance_to_show.split("(")[0].strip()

        st.caption(
            f"User_id {instance_to_show} last updated {time.time() - st.session_state.last_diff[instance_to_show]} seconds ago"
        )

        # Display the user's style summary in a styled box
        st.markdown(
            f"""
            <div style="
                background-color: #ffffe0;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #d0d0d0;
                margin-bottom: 20px;
                ">
                <strong>{instance_to_show}'s Style Summary:</strong><br>
                {st.session_state.old_state[instance_to_show]["query_summary"]}
            </div>
        """,
            unsafe_allow_html=True,
        )

        with st.expander("Show all prompt sub-parts"):
            st.write(st.session_state.old_state[instance_to_show])

    # Main loop to refresh content
    while True:
        # List all instances of the Fashion component
        instances = motion.get_instances("Fashion")

        # Check if 5 seconds have passed
        if time.time() - st.session_state.global_last_update > 5:

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
                    # st.caption(
                    #     f"User_id {instance} last updated {time.time() - st.session_state.last_diff[instance]} seconds ago"
                    # )
                    # st.write(state)

                    st.session_state.old_state[instance] = state

                # Update last refresh time
                st.session_state.last_update[instance] = time.time()

            # Write global last update time
            st.session_state.global_last_update = time.time()

            # If something was refreshed, rerun the page
            if not st.session_state.already_refreshed:
                st.session_state.already_refreshed = True
                st.rerun()

        time.sleep(1)  # Short sleep to prevent maxing out the CPU
