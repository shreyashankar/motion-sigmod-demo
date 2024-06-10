"""
TODOs:
* Add a "note" serve method that generates a note for why the user should purchase it. If there isn't enough data, rely on generic things like what's in style, etc.
* Streamlit sidebar that displays versions of the prompt in real-time
"""

import time
from motion import Component
import os
from openai import OpenAI
import instructor
from fashion.utils import (
    RecommendationPrompt,
    ItemListPrompt,
    SummaryPrompt,
    NotePrompt,
    EventSuggestionPrompt,
)
from fashion.globalsummaries import GlobalSummaries

from rich import print


from dotenv import load_dotenv

load_dotenv()

oai_client = OpenAI()
client = instructor.from_openai(OpenAI())


Fashion = Component("Fashion")


@Fashion.init_state
def setup(
    gender: str = "womenswear", occupation: str = "computer programmer", age: str = "26"
):
    return {
        "previous_recommendations": {},
        "query_summary": "",
        # "disliked_items": [],
        # "liked_items": [],
        "search_history": [],
        "gender": gender,
        "occupation": occupation,
        "age": age,
        "raw_user_feedback": [],
        "raw_previous_recommendations": [],
    }


@Fashion.serve("note")
def note(state, props):
    recommendation = props["recommendation"]
    query = props["event"]
    gender = state["gender"]
    use_summaries = props.get("use_summaries", True)

    if use_summaries:
        query_summary = state["query_summary"]
        if len(query_summary) > 0:
            query_summary = f" Here's a summary of my previous searches, which you can use to figure out my lifestyle and potential wardrobe preferences: {query_summary}."

        # Get the trends
        with GlobalSummaries("production", disable_update_task=True) as gs:
            news_summary = gs.read_state("news_summary")

        return client.chat.completions.create(
            model="gpt-4o",
            response_model=NotePrompt,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional stylist for {gender}. Here are the latest fashion trends: {news_summary}",
                },
                {
                    "role": "user",
                    "content": f"I am your client, a {state['occupation']} and {state['age']} years old.{query_summary} For `{query}`, you recommended the following item for me to buy: {recommendation}. Please write a short 1 sentence note for why I should buy this item, referencing my occupation, style summary, fashion trends, and preferences if they are relevant to the event. If you don't have enough information, describe why this item is in style or why it's a good fit for the event.",
                },
            ],
        ).note  # type: ignore

    else:
        # Just dump all context into the prompt
        raw_previous_recs = state["raw_previous_recommendations"]
        raw_user_feedback = state["raw_user_feedback"]

        # Get the trends
        with GlobalSummaries("production", disable_update_task=True) as gs:
            raw_news = gs.read_state("raw_news")

        return client.chat.completions.create(
            model="gpt-4o",
            response_model=NotePrompt,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional stylist for {gender}. In the past, you have recommended the following items for me to buy: {raw_previous_recs}. I've also provided feedback on the following items: {raw_user_feedback}. Here are the latest fashion trends: {raw_news}",
                },
                {
                    "role": "user",
                    "content": f"I am your client, a {state['occupation']} and {state['age']} years old. For `{query}`, you recommended the following item for me to buy: {recommendation}. Please write a short 1 sentence note for why I should buy this item, referencing my occupation, style summary, and preferences if they are relevant to the event. If you don't have enough information, describe why this item is in style or why it's a good fit for the event.",
                },
            ],
        ).note


@Fashion.serve("recommend")
def recommend(state, props):
    # Construct prompt
    query = props["event"]
    gender = state["gender"]
    use_summaries = props.get("use_summaries", True)
    print(f"Use summaries: {use_summaries}")

    if use_summaries:
        already_rec = state["previous_recommendations"].get(query.lower(), [])
        if len(already_rec) > 0:
            already_rec = ", ".join(already_rec)
            already_rec = (
                f" Avoid recommending anything similar to the following: {already_rec}."
            )
        else:
            already_rec = ""
        query_summary = state["query_summary"]
        if len(query_summary) > 0:
            query_summary = f" Here's a summary of my previous searches, which you can use to figure out my lifestyle and potential wardrobe preferences: {query_summary}."

        # Get the trends
        with GlobalSummaries("production", disable_update_task=True) as gs:
            news_summary = gs.read_state("news_summary")

        return client.chat.completions.create(
            model="gpt-4o",
            response_model=RecommendationPrompt,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional stylist for {gender}. Here are the latest fashion trends: {news_summary}",
                },
                {
                    "role": "user",
                    "content": f"I am your client, a {state['occupation']} and {state['age']} years old.{query_summary} What {gender} apparel items should I buy to wear to {query}?{already_rec} Make sure your suggestions are appropriate for the event. Be highly specific for each item, including colors, cuts, and styles. Each item should be ~5 words long.",
                },
            ],
        )  # type: ignore

    else:
        # Just dump all context into the prompt
        raw_previous_recs = state["raw_previous_recommendations"]
        raw_user_feedback = state["raw_user_feedback"]

        # Get the trends
        with GlobalSummaries("production", disable_update_task=True) as gs:
            raw_news = gs.read_state("raw_news")

        already_rec = raw_previous_recs
        if len(already_rec) > 0:
            already_rec = ", ".join(already_rec)
            already_rec = (
                f" Avoid recommending anything similar to the following: {already_rec}."
            )
        else:
            already_rec = ""

        return client.chat.completions.create(
            model="gpt-4o",
            response_model=RecommendationPrompt,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional stylist for {gender}. Here are the latest fashion trends: {raw_news}",
                },
                {
                    "role": "user",
                    "content": f"I am your client, a {state['occupation']} and {state['age']} years old. I've provided feedback on the following items: {raw_user_feedback}. What {gender} apparel items should I buy to wear to {query}?{already_rec} Make sure your suggestions are appropriate for the event. Be highly specific for each item, including colors, cuts, and styles. Each item should be ~5 words long.",
                },
            ],
        )  # type: ignore


@Fashion.serve("random_event")
def random_event(state, props):
    query_summary = state["query_summary"]
    if len(query_summary) > 0:
        query_summary = f"Based on my style profile: {query_summary}"
    else:
        query_summary = "Based on my profile"

    response = oai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant.",
            },
            {
                "role": "user",
                "content": f"{query_summary}, suggest a specific type of event that might interest me, totally different from previous events that I've attended (e.g., hiking in Japan, a Beatles concert, dinner in Paris, brunch in Central Park in Manhattan, skiing in the Alps, a workout class in all lululemon). Don't suggest wine tasting in Napa Valley. Your answer should be a short phrase (~8 words).",
            },
        ],
    )

    return response.choices[0].message.content


@Fashion.update("recommend")
def update_previous_recommendations(state, props):
    # Ask LLM to extract items from the serve_result
    llm_response = props.serve_result.model_dump()
    gender = state["gender"]
    query = props["event"]
    raw_previous_recommendations = state["raw_previous_recommendations"] + [
        str(llm_response)
    ]

    already_rec = state["previous_recommendations"].get(query.lower(), [])
    if len(already_rec) > 0:
        already_rec = ", ".join(already_rec)
        already_rec = f" You have also recommended {already_rec}."
    else:
        already_rec = ""

    items = client.chat.completions.create(
        model="gpt-4o",
        response_model=ItemListPrompt,
        messages=[
            {
                "role": "system",
                "content": f"You are a professional stylist for {gender}.",
            },
            {
                "role": "user",
                "content": f"You recommended the following items for `{query}`: {str(llm_response)}.{already_rec} From these recommendations, generate a list of at most 5 items you've recommended, with each item being no more than 3 words long.",
            },
        ],
    )  # type: ignore

    recs = state["previous_recommendations"]
    recs[query.lower()] = items.recommendations
    return {
        "previous_recommendations": recs,
        "raw_previous_recommendations": raw_previous_recommendations,
    }


@Fashion.update("recommend")
def update_search_queries(state, props):
    # Maintain a summary of search queries
    query = props["event"]
    gender = state["gender"]
    queries = state["search_history"] + [query]
    summary = state["query_summary"]

    print(f"Creating a summary for user {state.instance_id}")

    if len(queries) >= 2:
        summary = (
            oai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional stylist for {gender}. I've been asking you for recommendations for what to buy for various events.",
                    },
                    {
                        "role": "user",
                        "content": f"Here's my previous list of events I've wanted to be styled for: {state['search_history']}\n\nHere's the previous summary of my style: {summary}\n\nI've made a new query, {query}. Please generate a new style summary with all of the above information. Keep your summary at 3 sentences, describing my lifestyle, preferences, and other information a stylist should consider when styling me in the future (e.g., hard dislikes, dress codes, styles, etc). Common styles to choose from are casual, retro, classic & elegant, goth, edgy, boho, hipster, etc. Your summary should not include any filler text or flowery language.",
                    },
                ],
            )
            .choices[0]
            .message.content
        )

    with GlobalSummaries("production") as gs:
        gs.run(
            "user_activity",
            props={
                "user_activity": f"User {state.instance_id} searched for {query}",
                "timestamp": time.time(),
            },
            flush_update=True,
            ignore_cache=True,
        )

    return {"search_history": queries, "query_summary": summary}


@Fashion.update("user_feedback")
def update_feedback(state, props):
    feedback = props.get("feedback", "")
    feedback_str = f"(Feedback: {feedback})" if len(feedback) > 0 else ""
    action = props["action"]  # Love or dislike
    outfit = props["outfit"]
    event = props["event"]
    gender = state["gender"]
    raw_user_feedback = state["raw_user_feedback"] + [str(props)]

    # Merge this into the style summary
    summary = (
        oai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional stylist for {gender}. I've been asking you for recommendations for what to buy for various events.",
                },
                {
                    "role": "user",
                    "content": f"Here's the previous summary of my style: {state['query_summary']}\n\nI've provided the following feedback, I said I {action} the outfit `{outfit}` for the event `{event}` {feedback_str}. Please incorporate this feedback into my style summary, keeping it at 3 sentences, describing my lifestyle, preferences, and other information a stylist should consider when styling me in the future (e.g., hard dislikes, dress codes, styles, etc). Your summary should not include any filler text or flowery language.",
                },
            ],
        )
        .choices[0]
        .message.content
    )

    with GlobalSummaries("production") as gs:
        gs.run(
            "user_activity",
            props={
                "user_activity": f"User {state.instance_id} gave feedback {feedback} of type {action} for outfit {outfit}",
                "timestamp": time.time(),
            },
            flush_update=True,
            ignore_cache=True,
        )

    return {"query_summary": summary, "raw_user_feedback": raw_user_feedback}


if __name__ == "__main__":
    f = Fashion(
        init_state_params={
            "gender": "menswear",
            "occupation": "student",
            "age": "25",
        }
    )
    print(f.run("recommend", props={"event": "a birthday party"}, flush_update=True))

    # Read state
    print(f.read_state("previous_recommendations"))

    # Try again
    print(
        f.run(
            "recommend",
            props={"event": "a birthday party"},
            ignore_cache=True,
            flush_update=True,
        )
    )

    # Read state
    print(f.read_state("previous_recommendations"))
