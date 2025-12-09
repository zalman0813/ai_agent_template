"""Content processing tools for text analysis.

These tools guide the LLM agent to process and analyze text content
in structured ways. The actual processing is done by the agent's model.
"""

from langchain_core.tools import tool


@tool
def extract_keywords(text: str) -> str:
    """
    Extract key terms and named entities from text.

    Args:
        text: The text content to analyze

    Returns:
        JSON string with keywords and entities:
        {"keywords": ["term1", "term2", ...], "entities": ["entity1", "entity2", ...]}

    Instructions for processing:
    - Keywords: Important terms, concepts, technologies mentioned
    - Entities: Named entities like companies, products, people, locations
    - Limit to top 10 keywords and top 5 entities
    - Return as valid JSON format
    """
    # This tool guides the agent on how to process the text
    # The actual extraction is performed by the LLM
    return (
        "Please extract keywords and entities from the following text "
        f"and return as JSON:\n\n{text}"
    )


@tool
def summarize(text: str, max_sentences: int = 3) -> str:
    """
    Summarize long text into key points.

    Args:
        text: The text content to summarize
        max_sentences: Maximum number of sentences in the summary (default: 3)

    Returns:
        A concise summary of the main points

    Instructions for processing:
    - Focus on the most important information
    - Keep the summary concise and informative
    - Preserve key facts and conclusions
    - Use bullet points if there are multiple distinct points
    """
    return f"Please summarize the following text in {max_sentences} sentences or less:\n\n{text}"


@tool
def analyze_sentiment(text: str) -> str:
    """
    Analyze sentiment and classify content.

    Args:
        text: The text content to analyze

    Returns:
        JSON string with sentiment analysis:
        {
            "sentiment": "positive/negative/neutral/mixed",
            "confidence": 0.0-1.0,
            "category": "news/opinion/technical/promotional/other",
            "key_themes": ["theme1", "theme2"]
        }

    Instructions for processing:
    - Sentiment: Overall emotional tone of the content
    - Confidence: How confident you are in the assessment (0.0 to 1.0)
    - Category: The type/genre of content
    - Key themes: Main topics or themes discussed (max 3)
    - Return as valid JSON format
    """
    return (
        "Please analyze the sentiment and classify the following text, "
        f"return as JSON:\n\n{text}"
    )


# Export all tools for easy import
content_tools = [extract_keywords, summarize, analyze_sentiment]
