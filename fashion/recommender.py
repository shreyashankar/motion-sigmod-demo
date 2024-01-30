"""
TODOs:
* Add a "note" serve method that generates a note for why the user should purchase it. If there isn't enough data, rely on generic things like what's in style, etc.
* Add "user_feedback" update method that update the state with the liked and disliked items. Every 10 items, summarize the feedback.
* Streamlit sidebar that displays versions of the prompt in real-time
"""

from motion import Component
import os
from openai import AzureOpenAI
import instructor
from fashion.utils import (
    RecommendationPrompt,
    ItemListPrompt,
    SummaryPrompt,
    NotePrompt,
)

from rich import print


from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_API_VERSION"),
)
client = instructor.patch(client)


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
    }


@Fashion.serve("state")
def noop(state, props):
    return state


@Fashion.serve("note")
def note(state, props):
    recommendation = props["recommendation"]
    query = props["event"]
    gender = state["gender"]

    query_summary = state["query_summary"]
    if len(query_summary) > 0:
        query_summary = f" Here's a summary of my previous searches, which you can use to figure out my lifestyle and potential wardrobe preferences: {query_summary}."

    return client.chat.completions.create(
        model="gpt-35-turbo",
        response_model=NotePrompt,
        messages=[
            {
                "role": "system",
                "content": f"You are a professional stylist for {gender}.",
            },
            {
                "role": "user",
                "content": f"I am your client, a {state['occupation']} and {state['age']} years old.{query_summary} For `{query}`, you recommended the following item for me to buy: {recommendation}. Please write a short 2-3 sentence note for why I should buy this item, referencing only my occupation and preferences if they are relevant to the event. If you don't have enough information, describe why this item is in style or why it's a good fit for the event.",
            },
        ],
    ).note  # type: ignore


@Fashion.serve("recommend")
def recommend(state, props):
    # Construct prompt
    query = props["event"]
    gender = state["gender"]

    already_rec = state["previous_recommendations"].get(query.lower(), [])
    if len(already_rec) > 0:
        already_rec = ", ".join(already_rec)
        already_rec = f" Avoid recommending the following: {already_rec}."
    else:
        already_rec = ""
    query_summary = state["query_summary"]
    if len(query_summary) > 0:
        query_summary = f" Here's a summary of my previous searches, which you can use to figure out my lifestyle and potential wardrobe preferences: {query_summary}."

    return client.chat.completions.create(
        model="gpt-35-turbo",
        response_model=RecommendationPrompt,
        messages=[
            {
                "role": "system",
                "content": f"You are a professional stylist for {gender}.",
            },
            {
                "role": "user",
                "content": f"I am your client, a {state['occupation']} and {state['age']} years old.{query_summary} What {gender} apparel items should I buy to wear to {query}?{already_rec} Make sure your suggestions are appropriate for the dress code. Be highly specific for each item, including colors, cuts, and styles.",
            },
        ],
    )  # type: ignore


@Fashion.update("recommend")
def update_previous_recommendations(state, props):
    # Ask LLM to extract items from the serve_result
    llm_response = props.serve_result.model_dump()
    gender = state["gender"]
    query = props["event"]

    already_rec = state["previous_recommendations"].get(query.lower(), [])
    if len(already_rec) > 0:
        already_rec = ", ".join(already_rec)
        already_rec = f" You have also recommended {already_rec}."
    else:
        already_rec = ""

    items = client.chat.completions.create(
        model="gpt-4-2",
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
    return {"previous_recommendations": recs}


@Fashion.update("recommend")
def update_search_queries(state, props):
    # Maintain a summary of search queries
    query = props["event"]
    gender = state["gender"]
    queries = state["search_history"] + [query]
    summary = state["query_summary"]

    if len(queries) >= 3:
        summary = client.chat.completions.create(
            model="gpt-4-2",
            response_model=SummaryPrompt,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional stylist for {gender}. I've been asking you for recommendations for what to buy for various events.",
                },
                {
                    "role": "user",
                    "content": f"Here's my previous summary of events I've wanted to be styled for: {state['search_history']}\n\nI've made a new query, {query}. Please summarize my event styling request history in 3 sentences, describing my lifestyle and other information a stylist should consider when styling me in the future.",
                },
            ],
        ).summary

    return {"search_history": queries, "query_summary": summary}


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
