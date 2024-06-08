import sys

sys.path.append("//Users/shreyashankar/Documents/hacking/motion-fashion")

from collections import defaultdict
import streamlit as st
from fashion.globalsummaries import GlobalSummaries

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

url = "https://google.serper.dev/news"
scrape_url = "https://scrape.serper.dev"


def fetch_news(url):
    payload = json.dumps({"url": url})
    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json",
    }
    response = requests.post(scrape_url, headers=headers, data=payload)
    return response.json()["text"], response.json()["metadata"].get("og:image", "")


st.set_page_config(layout="wide")

st.subheader("Recent Activity")
st.write(
    "This page shows a real-time event loop that polls for a global summary of all users' preferences every 5 seconds. It also subscribes to Google News for the latest fashion news and updates a summary of recent news every 10 minutes."
)

# Initialize session state for last update time
if "global_last_update" not in st.session_state:
    st.session_state.global_last_update = time.time()
if "last_news_update" not in st.session_state:
    st.session_state.last_news_update = time.time()
if "first_time" not in st.session_state:
    st.session_state.first_time = True

news_placeholder = st.empty()
placeholder = st.empty()

# Poll for global summary every 5 seconds
while True:
    if (
        st.session_state.first_time
        or time.time() - st.session_state.last_news_update > 600
    ):
        st.session_state.last_news_update = time.time()

        # Use serper.dev to get the latest news

        payload = json.dumps(
            {
                "q": "fashion",
                "location": "Chile",
                "gl": "cl",
                "num": 20,
                "tbs": "qdr:h",
            }
        )
        headers = {
            "X-API-KEY": os.getenv("SERPER_API_KEY"),
            "Content-Type": "application/json",
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        data = response.json()

        urls = [item["link"] for item in data["news"]]
        titles = [item["title"] for item in data["news"]]
        dates = [item["date"] for item in data["news"]]

        # Now asynchronously fetch the news content
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_news, url) for url in urls]
            news = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    news.append(result)
                except Exception:
                    pass

        # Submit to global summaries
        with GlobalSummaries("production") as gs:
            gs.run(
                "news",
                props={"urls_and_news_texts": list(zip(urls, news))},
                ignore_cache=True,
            )

        news_placeholder.empty()
        with news_placeholder.container():
            with st.expander("#### Recent News ('fashion' in Chile)"):
                # Show the images that are not empty in a grid format
                cols = st.columns(3)  # Define a grid of 3 columns
                col_index = 0
                for title, url, date, (text, img_url) in zip(titles, urls, dates, news):
                    if img_url:
                        cols[col_index].image(img_url)  # Display smaller images
                        cols[col_index].write(f"({date}) [{title}]({url})")
                        col_index = (
                            col_index + 1
                        ) % 3  # Move to the next column, wrap around after 3

    if (
        st.session_state.first_time
        or time.time() - st.session_state.global_last_update > 5
    ):
        st.session_state.global_last_update = time.time()

        with GlobalSummaries("production") as gs:
            user_activity_summary = gs.read_state("user_activity_summary")
            all_user_activity = gs.read_state("user_activity")
            news_summary = gs.read_state("news_summary")

        placeholder.empty()
        with placeholder.container():
            # Show a summary
            st.write("**Recent News Summary**")
            st.success(news_summary)

            st.write("#### All user activity summary")
            st.warning(user_activity_summary)

            # Display the user activity list of (timestamp, user_activity) pairs
            # Sort by timestamp descending
            sorted_user_activity = sorted(
                all_user_activity, key=lambda x: x[0], reverse=True
            )
            for timestamp, user_activity in sorted_user_activity:
                # Format the timestamp
                timestamp = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(timestamp)
                )
                st.success(f"**{timestamp}**: {user_activity}")

    st.session_state.first_time = False
    time.sleep(3)
