from concurrent.futures import ThreadPoolExecutor, as_completed
from motion import Component
import os
from openai import OpenAI

import requests
from rich import print


from dotenv import load_dotenv

load_dotenv()

oai_client = OpenAI()


GlobalSummaries = Component("GlobalSummaries")


@GlobalSummaries.init_state
def setup():
    return {
        "urls_summarized": [],
        "news_summary": "",
        "raw_news": [],
        "user_activity_summary": "",
        "user_activity": [],
    }


@GlobalSummaries.update("news")
def update_news_summary(state, props):
    # Get the urls to summarize
    new_items = props["urls_and_news_texts"]  # list of (url, (text, img_url)) tuples

    # Filter out the urls that have already been summarized
    new_texts = [text for url, text in new_items if url not in state["urls_summarized"]]

    news_htmls = "\n\n".join([f"<p>{text}</p>" for text in new_texts])
    news_img_urls = [
        img_url
        for url, (_, img_url) in new_items
        if img_url and url not in state["urls_summarized"]
    ]
    news_img_urls = news_img_urls[:8]

    # Try to download these news_img_urls to make sure they work
    valid_img_urls = []
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(requests.get, img_url): img_url for img_url in news_img_urls
        }
        for future in as_completed(futures):
            img_url = futures[future]
            try:
                response = future.result()
                if (
                    response.status_code == 200
                    and "image" in response.headers["Content-Type"]
                ):
                    print(f"Downloaded image at {img_url}")
                    valid_img_urls.append(img_url)
                else:
                    print(f"Invalid image content type or error status for {img_url}")
            except Exception as e:
                print(f"Failed to download image at {img_url}: {e}")
    news_img_urls = valid_img_urls

    old_summary = state["news_summary"]

    response = oai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a news summarizer. Please summarize the news related to fashion trends and what to wear.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Here is a summary of fashion trends:\n\n{old_summary}\n\nHere are the latest news articles and their images related to fashion trends and what to wear:\n\n{news_htmls}\n\nPlease generate a new summary (up to 5 sentences) that keeps the existing trends and includes trends from the latest news articles. Keep the trends focused on what to wear, not necessarily the news articles themselves.",
                    },
                    *[
                        {
                            "type": "image_url",
                            "image_url": {"url": img_url, "detail": "low"},
                        }
                        for img_url in news_img_urls
                    ],
                ],
            },
        ],
    )
    new_summary = response.choices[0].message.content
    print(
        f"Updated news summary from GPT-4o, including {len(news_img_urls)} images: {new_summary}"
    )

    # Update urls with the new urls
    urls = state["urls_summarized"] + [
        url for url, _ in new_items if url not in state["urls_summarized"]
    ]

    raw_news = state["raw_news"] + new_texts

    return {
        "urls_summarized": urls,
        "news_summary": new_summary,
        "raw_news": raw_news,
    }


@GlobalSummaries.update("user_activity")
def update_user_activity_summary(state, props):
    user_activity = props["user_activity"]
    timestamp = props["timestamp"]
    old_summary = state["user_activity_summary"]

    response = oai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a user activity summarizer. Please summarize the user activity.",
            },
            {
                "role": "user",
                "content": f"Here is a summary of user activity:\n\n{old_summary}\n\nHere is the latest user activity event:\n\n{user_activity}\n\nPlease update the summary to include the latest user activity event. The summary should be one paragraph of plain text prose (no bullets or formatting), and should include any trends or patterns in the user activity.",
            },
        ],
    )
    new_summary = response.choices[0].message.content

    return {
        "user_activity_summary": new_summary,
        "user_activity": state["user_activity"] + [(timestamp, user_activity)],
    }
