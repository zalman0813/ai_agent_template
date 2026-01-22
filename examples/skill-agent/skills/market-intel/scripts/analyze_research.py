#!/usr/bin/env python3
"""
Market Intelligence Analysis Script

Processes web search results to extract:
- Entities (companies, products, people)
- Sentiment analysis
- Topic clustering
- Key insights

Uses only Python standard library for simplicity.
"""

import json
import argparse
import re
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Any


# Entity extraction patterns (simple keyword-based)
COMPANY_INDICATORS = ['Inc', 'LLC', 'Corp', 'Ltd', 'Company', 'Technologies', 'Labs']
PRODUCT_KEYWORDS = ['AI', 'tool', 'platform', 'service', 'app', 'software', 'system']

# Sentiment keywords
POSITIVE_WORDS = [
    'excellent', 'great', 'amazing', 'outstanding', 'impressive', 'good',
    'better', 'best', 'love', 'fantastic', 'wonderful', 'superior',
    'innovative', 'powerful', 'efficient', 'easy', 'simple', 'fast',
    'reliable', 'accurate', 'helpful', 'useful', 'effective', 'quality'
]

NEGATIVE_WORDS = [
    'bad', 'poor', 'terrible', 'awful', 'horrible', 'worst', 'worse',
    'disappointing', 'frustrated', 'frustrating', 'slow', 'difficult',
    'hard', 'complex', 'expensive', 'costly', 'limited', 'lacking',
    'issues', 'problems', 'bugs', 'errors', 'fails', 'failed', 'broken'
]


def load_search_results(file_path: str) -> Dict[str, Any]:
    """Load search results from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        exit(1)


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Simple entity extraction using keyword matching.
    In production, would use NLP libraries like spaCy or NLTK.
    """
    entities = {
        'companies': [],
        'products': [],
        'people': []
    }

    # Find capitalized words (potential entities)
    words = text.split()

    # Extract companies (capitalized words with company indicators)
    for i, word in enumerate(words):
        if any(indicator in word for indicator in COMPANY_INDICATORS):
            # Get the word before the indicator
            if i > 0:
                company = words[i-1] + ' ' + word
                entities['companies'].append(company)
        elif word[0].isupper() and len(word) > 2:
            # Check if next word is also capitalized (potential company name)
            if i < len(words) - 1 and words[i+1][0].isupper():
                potential_company = word + ' ' + words[i+1]
                # Common tech companies pattern
                if any(kw in text.lower() for kw in ['github', 'google', 'microsoft', 'openai', 'anthropic']):
                    entities['companies'].append(potential_company)

    # Extract product names (capitalized words near product keywords)
    text_lower = text.lower()
    for keyword in PRODUCT_KEYWORDS:
        if keyword.lower() in text_lower:
            # Find capitalized words near this keyword
            pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
            matches = re.findall(pattern, text)
            entities['products'].extend(matches[:3])  # Limit to avoid noise

    # Remove duplicates while preserving order
    entities['companies'] = list(dict.fromkeys(entities['companies']))
    entities['products'] = list(dict.fromkeys(entities['products']))

    return entities


def analyze_sentiment(text: str) -> str:
    """
    Simple sentiment analysis using keyword matching.
    Returns: 'positive', 'negative', or 'neutral'
    """
    text_lower = text.lower()

    positive_count = sum(1 for word in POSITIVE_WORDS if word in text_lower)
    negative_count = sum(1 for word in NEGATIVE_WORDS if word in text_lower)

    if positive_count > negative_count:
        return 'positive'
    elif negative_count > positive_count:
        return 'negative'
    else:
        return 'neutral'


def extract_topics(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract common topics from search results.
    Uses keyword frequency analysis.
    """
    # Combine all text
    all_text = ' '.join([
        r.get('title', '') + ' ' + r.get('snippet', '')
        for r in results
    ])

    # Common stopwords to exclude
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
        'that', 'these', 'those', 'it', 'its', 'which', 'who', 'what', 'when'
    }

    # Extract words and count frequency
    words = re.findall(r'\b[a-z]{4,}\b', all_text.lower())
    word_freq = Counter([w for w in words if w not in stopwords])

    # Get top topics
    topics = []
    for word, count in word_freq.most_common(10):
        # Analyze sentiment for this topic
        topic_sentiment = 'neutral'
        # Find sentences with this word
        sentences = [r.get('snippet', '') for r in results if word in r.get('snippet', '').lower()]
        if sentences:
            sentiments = [analyze_sentiment(s) for s in sentences]
            sentiment_counts = Counter(sentiments)
            topic_sentiment = sentiment_counts.most_common(1)[0][0]

        topics.append({
            'topic': word,
            'mentions': count,
            'sentiment': topic_sentiment
        })

    return topics


def generate_insights(analysis: Dict[str, Any]) -> List[str]:
    """Generate human-readable insights from analysis."""
    insights = []

    # Entity insights
    if analysis['entities']['companies']:
        companies = analysis['entities']['companies'][:3]
        insights.append(f"Key companies mentioned: {', '.join(companies)}")

    if analysis['entities']['products']:
        products = analysis['entities']['products'][:3]
        insights.append(f"Notable products: {', '.join(products)}")

    # Sentiment insights
    sentiment = analysis['sentiment']
    total = sum(sentiment.values())
    if total > 0:
        pos_pct = int((sentiment['positive'] / total) * 100)
        if pos_pct > 60:
            insights.append(f"Overall sentiment is positive ({pos_pct}% positive mentions)")
        elif pos_pct < 40:
            insights.append(f"Overall sentiment is negative ({pos_pct}% positive mentions)")
        else:
            insights.append(f"Sentiment is mixed ({pos_pct}% positive mentions)")

    # Topic insights
    if analysis['top_topics']:
        top_topic = analysis['top_topics'][0]
        insights.append(f"Most discussed topic: '{top_topic['topic']}' ({top_topic['mentions']} mentions)")

    return insights


def analyze(search_results: Dict[str, Any]) -> Dict[str, Any]:
    """Main analysis function."""
    results = search_results.get('results', [])

    # Aggregate entities from all results
    all_entities = defaultdict(list)
    sentiment_counts = Counter()

    for result in results:
        text = result.get('title', '') + ' ' + result.get('snippet', '')

        # Extract entities
        entities = extract_entities(text)
        for entity_type, entity_list in entities.items():
            all_entities[entity_type].extend(entity_list)

        # Analyze sentiment
        sentiment = analyze_sentiment(text)
        sentiment_counts[sentiment] += 1

    # Remove duplicates from entities
    for entity_type in all_entities:
        all_entities[entity_type] = list(dict.fromkeys(all_entities[entity_type]))

    # Extract topics
    topics = extract_topics(results)

    # Build analysis result
    analysis = {
        'query': search_results.get('query', 'Unknown'),
        'analyzed_at': datetime.now().isoformat(),
        'sources_count': len(results),
        'entities': dict(all_entities),
        'sentiment': {
            'positive': sentiment_counts.get('positive', 0),
            'neutral': sentiment_counts.get('neutral', 0),
            'negative': sentiment_counts.get('negative', 0)
        },
        'top_topics': topics
    }

    # Generate insights
    analysis['insights'] = generate_insights(analysis)

    return analysis


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Analyze market intelligence from web search results'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Path to search results JSON file'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Path to output analysis JSON file'
    )

    args = parser.parse_args()

    # Load search results
    print(f"Loading search results from: {args.input}")
    search_results = load_search_results(args.input)

    # Perform analysis
    print("Analyzing data...")
    analysis = analyze(search_results)

    # Save results
    print(f"Saving analysis to: {args.output}")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n=== Analysis Complete ===")
    print(f"Sources analyzed: {analysis['sources_count']}")
    print(f"Companies found: {len(analysis['entities']['companies'])}")
    print(f"Products found: {len(analysis['entities']['products'])}")
    print(f"Topics identified: {len(analysis['top_topics'])}")
    print(f"\nKey insights:")
    for insight in analysis['insights']:
        print(f"  • {insight}")


if __name__ == '__main__':
    main()
