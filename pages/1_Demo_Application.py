import sys

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

# SERPER_URL = "https://google.serper.dev/images"
SERPER_URL = "https://google.serper.dev/shopping"
NUM_RESULTS = 4

st.set_page_config(layout="wide")


@st.cache_resource
def load_instance(user_id, gender, occupation, age):
    f = Fashion(
        user_id,
        init_state_params={"gender": gender, "occupation": occupation, "age": age},
    )
    return f


def get_random_event(user_id, gender, occupation, age):
    f = load_instance(user_id, gender, occupation, age)
    return f.run("random_event", ignore_cache=True)


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


def fetch_results(query, user_id, gender, occupation, age, use_motion):
    f = load_instance(user_id, gender, occupation, age)

    recs = f.run(
        "recommend",
        props={"event": query, "use_summaries": use_motion},
        ignore_cache=True,
        # force_refresh=True,
    )

    with ThreadPoolExecutor() as executor:
        futures = []
        for _, value in recs.model_dump().items():
            futures.append(executor.submit(process_recommendation, f, value, query))

        for future in as_completed(futures):
            yield future.result()


def process_recommendation(f, value, query):
    note = f.run(
        "note",
        props={"recommendation": value, "event": query, "use_summaries": use_motion},
        ignore_cache=True,
        # force_refresh=True,
    )
    return value, note


async def fetch_all_images(recommendations, gender):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_images(session, value, gender) for value in recommendations]
        return await asyncio.gather(*tasks)


async def fetch_images(session, value, gender):
    payload = json.dumps({"q": f"{value} for {gender}"})

    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json",
    }

    async with session.post(SERPER_URL, headers=headers, data=payload) as response:
        return await response.json()


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
            load_instance(user_id, gender, occupation, age)
            st.rerun()  # Reload the page to proceed with the main app

else:
    # Initialize session state for page number
    if "page_number" not in st.session_state:
        st.session_state.page_number = 1
    if "dislike_feedback" not in st.session_state:
        st.session_state.dislike_feedback = ""

    st.subheader("Get Outfit Recommendations")

    use_motion = st.toggle("Use Motion", value=True)
    if use_motion:
        st.success(
            "You are using Motion! Over time, your queries should be faster (since there are fewer tokens in the prompts) and more accurate 🚀"
        )
    else:
        st.warning(
            "You are using LLMs with RAG, where context is fetched from the database and injected directly into the prompt. Over time, your queries may be more repetitive, less accurate, and slower 😢"
        )

    # Input for query string with an alternative button to pick an event
    if "random_event_query" not in st.session_state:
        st.session_state.random_event_query = ""

    query = st.text_input(
        "What event do you want to be styled for?", st.session_state.random_event_query
    )

    refresh = st.button("Or refresh with a random event I might like")
    if refresh:
        st.session_state.random_event_query = get_random_event(
            **st.session_state.user_info
        )
        query = st.session_state.random_event_query
        st.rerun()

    # Check if a query was entered
    if query:
        st.session_state.query = query
        with st.spinner("Querying LLM..."):
            i = 0
            placeholder_latency = st.empty()
            placeholder_buttons = st.columns([0.2, 0.3, 0.3, 0.2])
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
                query, user_id, gender, occupation, age, use_motion
            ):
                if i == 0:
                    generation_time = time.time() - start_time
                    placeholder_latency.caption(
                        f"Generated in {generation_time} seconds"
                    )
                    love_button = placeholder_buttons[0].button(
                        "Love these ideas ❤️", key=f"like_{i}"
                    )
                    with placeholder_buttons[1].popover("Don't like this outfit 👎"):
                        dislike_feedback = st.text_input(
                            "Why don't you like this?",
                            key=f"dislike_feedback_ti",
                            value=st.session_state.dislike_feedback,
                            on_change=lambda: setattr(
                                st.session_state,
                                "dislike_feedback",
                                st.session_state[f"dislike_feedback_ti"],
                            ),
                        )

                # Fetch images
                columns_of_products[i].write(f"**{rec_text}**")
                columns_of_products[i].write(f"_{note}_")

                all_rec_text.append(rec_text)
                i += 1

        # Render images
        i = 0
        all_images = asyncio.run(fetch_all_images(all_rec_text, gender))
        for image_results in all_images:
            for j in range(NUM_RESULTS):
                img_results = image_results["shopping"][j]
                item_and_title = columns_of_products[i].columns([0.4, 0.5])

                item_and_title[0].image(
                    img_results["imageUrl"]  # , use_column_width="always"
                )
                item_and_title[1].write(
                    f"[{img_results['source']}]({img_results['link']})"
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

        if st.session_state["dislike_feedback"]:
            send_feedback(
                query,
                user_id,
                gender,
                occupation,
                age,
                all_rec_text,
                action="dislike",
                feedback=st.session_state["dislike_feedback"],
            )
            st.session_state["dislike_feedback"] = ""
