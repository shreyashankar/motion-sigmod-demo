from pydantic import BaseModel, Field
from typing import Optional, List


# Define pydantic model
class RecommendationPrompt(BaseModel):
    shoes: str = Field(
        ..., description="Detailed description of shoes to buy for the event."
    )
    upper_body_garments: str = Field(
        ..., description="Detailed description of shirt or top to buy for the event."
    )
    lower_body_garments: str = Field(
        ...,
        description="Detailed description of pants or lower-body garment to buy for the event.",
    )
    outerwear: str = Field(
        ...,
        description="Detailed description of jacket or coat or sweater to buy for the event.",
    )
    bags: str = Field(
        ..., description="Detailed description of bag to buy for the event."
    )


class ItemListPrompt(BaseModel):
    recommendations: List[str] = Field(
        ...,
        description="List of items extracted from the dictionary of recommendations.",
    )


class SummaryPrompt(BaseModel):
    summary: str = Field(
        ...,
        description="Summary of the my preferences, lifestyle, and events I attend.",
    )


class EventSuggestionPrompt(BaseModel):
    event: str = Field(
        ...,
        description="An event I might like to attend based on my preferences and lifestyle.",
    )


class NotePrompt(BaseModel):
    note: str = Field(
        ...,
        description="Short note for why I should buy this item.",
    )
