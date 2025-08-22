# main.py - Multi-Model AI Analysis API
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import pipeline
import uvicorn
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Initialize FastAPI app
app = FastAPI(title="Multi-Model AI Analysis API", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for models (loaded once at startup)
models = {}

# Initialize all models at startup
print("Loading AI models...")

try:
    # Sentiment Analysis
    print("Loading sentiment analysis model...")
    models['sentiment'] = pipeline("sentiment-analysis",
                                   model="cardiffnlp/twitter-roberta-base-sentiment-latest")

    # Emotion Detection
    print("Loading emotion detection model...")
    models['emotion'] = pipeline("text-classification",
                                 model="j-hartmann/emotion-english-distilroberta-base")

    # Text Summarization
    print("Loading text summarization model...")
    models['summarization'] = pipeline("summarization",
                                       model="facebook/bart-large-cnn")

    # Language Detection
    print("Loading language detection model...")
    models['language'] = pipeline("text-classification",
                                  model="papluca/xlm-roberta-base-language-detection")

    print("All models loaded successfully!")

except Exception as e:
    print(f"Error loading models: {e}")
    # Load basic sentiment model as fallback
    models['sentiment'] = pipeline("sentiment-analysis")


# Input/Output Models
class TextInput(BaseModel):
    text: str
    max_length: Optional[int] = 150  # For summarization
    min_length: Optional[int] = 30  # For summarization


class SingleAnalysisResponse(BaseModel):
    analysis_type: str
    text: str
    result: Dict[str, Any]
    confidence: Optional[float] = None
    timestamp: str


class MultiAnalysisResponse(BaseModel):
    text: str
    analyses: Dict[str, Dict[str, Any]]
    timestamp: str


# Helper functions
def format_sentiment_result(result):
    """Format sentiment analysis result"""
    prediction = result[0]
    label_mapping = {
        "LABEL_0": "negative",
        "LABEL_1": "neutral",
        "LABEL_2": "positive"
    }
    sentiment = label_mapping.get(prediction["label"], prediction["label"].lower())
    return {
        "sentiment": sentiment,
        "confidence": round(prediction["score"], 3),
        "raw_label": prediction["label"]
    }


def format_emotion_result(result):
    """Format emotion detection result"""
    prediction = result[0]
    return {
        "emotion": prediction["label"].lower(),
        "confidence": round(prediction["score"], 3),
        "all_emotions": [
            {"emotion": r["label"].lower(), "confidence": round(r["score"], 3)}
            for r in result[:3]  # Top 3 emotions
        ]
    }


def format_language_result(result):
    """Format language detection result"""
    prediction = result[0]
    # Map language codes to full names
    language_names = {
        'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
        'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese',
        'ko': 'Korean', 'zh': 'Chinese', 'ar': 'Arabic', 'hi': 'Hindi'
    }
    detected_lang = prediction["label"]
    language_name = language_names.get(detected_lang, detected_lang)

    return {
        "language_code": detected_lang,
        "language_name": language_name,
        "confidence": round(prediction["score"], 3)
    }


def format_summarization_result(result, original_length):
    """Format text summarization result"""
    summary = result[0]['summary_text']
    return {
        "summary": summary,
        "original_length": original_length,
        "summary_length": len(summary),
        "compression_ratio": round(len(summary) / original_length, 2)
    }


# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Multi-Model AI Analysis API is running!",
        "available_models": list(models.keys()),
        "version": "2.0.0"
    }


@app.get("/models")
async def available_models():
    """Get list of available models and their descriptions"""
    model_descriptions = {
        "sentiment": "Analyzes positive, negative, or neutral sentiment in text",
        "emotion": "Detects specific emotions like joy, anger, sadness, fear, etc.",
        "summarization": "Creates concise summaries of longer text",
        "language": "Detects the language of the input text"
    }

    return {
        "available_models": {
            model: {
                "description": model_descriptions.get(model, "AI analysis model"),
                "loaded": model in models
            }
            for model in model_descriptions.keys()
        }
    }


@app.post("/analyze/sentiment", response_model=SingleAnalysisResponse)
async def analyze_sentiment(input_data: TextInput):
    """Analyze sentiment of text"""
    if 'sentiment' not in models:
        raise HTTPException(status_code=503, detail="Sentiment model not available")

    try:
        result = models['sentiment'](input_data.text)
        formatted_result = format_sentiment_result(result)

        return SingleAnalysisResponse(
            analysis_type="sentiment",
            text=input_data.text,
            result=formatted_result,
            confidence=formatted_result["confidence"],
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")


@app.post("/analyze/emotion", response_model=SingleAnalysisResponse)
async def analyze_emotion(input_data: TextInput):
    """Detect emotions in text"""
    if 'emotion' not in models:
        raise HTTPException(status_code=503, detail="Emotion model not available")

    try:
        result = models['emotion'](input_data.text)
        formatted_result = format_emotion_result(result)

        return SingleAnalysisResponse(
            analysis_type="emotion",
            text=input_data.text,
            result=formatted_result,
            confidence=formatted_result["confidence"],
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emotion analysis failed: {str(e)}")


@app.post("/analyze/language", response_model=SingleAnalysisResponse)
async def analyze_language(input_data: TextInput):
    """Detect language of text"""
    if 'language' not in models:
        raise HTTPException(status_code=503, detail="Language model not available")

    try:
        result = models['language'](input_data.text)
        formatted_result = format_language_result(result)

        return SingleAnalysisResponse(
            analysis_type="language",
            text=input_data.text,
            result=formatted_result,
            confidence=formatted_result["confidence"],
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Language detection failed: {str(e)}")


@app.post("/analyze/summarize", response_model=SingleAnalysisResponse)
async def summarize_text(input_data: TextInput):
    """Summarize long text"""
    if 'summarization' not in models:
        raise HTTPException(status_code=503, detail="Summarization model not available")

    # Validate text length for summarization
    if len(input_data.text.split()) < 20:
        raise HTTPException(status_code=400, detail="Text too short for summarization (minimum 20 words)")

    try:
        result = models['summarization'](
            input_data.text,
            max_length=input_data.max_length,
            min_length=input_data.min_length,
            do_sample=False
        )
        formatted_result = format_summarization_result(result, len(input_data.text))

        return SingleAnalysisResponse(
            analysis_type="summarization",
            text=input_data.text,
            result=formatted_result,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


@app.post("/analyze/all", response_model=MultiAnalysisResponse)
async def analyze_all(input_data: TextInput):
    """Run all available analyses on the text"""
    if not input_data.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    analyses = {}

    # Run all available analyses
    try:
        # Sentiment
        if 'sentiment' in models:
            sentiment_result = models['sentiment'](input_data.text)
            analyses['sentiment'] = format_sentiment_result(sentiment_result)

        # Emotion
        if 'emotion' in models:
            emotion_result = models['emotion'](input_data.text)
            analyses['emotion'] = format_emotion_result(emotion_result)

        # Language
        if 'language' in models:
            language_result = models['language'](input_data.text)
            analyses['language'] = format_language_result(language_result)

        # Summarization (only if text is long enough)
        if 'summarization' in models and len(input_data.text.split()) >= 20:
            try:
                summary_result = models['summarization'](
                    input_data.text,
                    max_length=input_data.max_length,
                    min_length=input_data.min_length,
                    do_sample=False
                )
                analyses['summarization'] = format_summarization_result(summary_result, len(input_data.text))
            except:
                analyses['summarization'] = {"error": "Text may be too short or contain unsupported content"}

        return MultiAnalysisResponse(
            text=input_data.text,
            analyses=analyses,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-analysis failed: {str(e)}")


# Legacy endpoint for backward compatibility
@app.post("/analyze")
async def analyze_legacy(input_data: TextInput):
    """Legacy sentiment analysis endpoint"""
    return await analyze_sentiment(input_data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
