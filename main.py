# main.py - Sentiment Analysis API
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import pipeline
import uvicorn

# Initialize FastAPI app
app = FastAPI(title="Sentiment Analysis API", version="1.0.0")

# Add CORS middleware so frontend can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the pre-trained sentiment analysis model
# This happens when the server starts up
print("Loading sentiment analysis model...")
sentiment_analyzer = pipeline("sentiment-analysis",
                              model="cardiffnlp/twitter-roberta-base-sentiment-latest")
print("Model loaded successfully!")


# Define the input data structure
class TextInput(BaseModel):
    text: str


# Define the response data structure
class SentimentResponse(BaseModel):
    text: str
    sentiment: str
    confidence: float


# Health check endpoint
@app.get("/")
async def root():
    return {"message": "Sentiment Analysis API is running!"}


# Main prediction endpoint
@app.post("/analyze", response_model=SentimentResponse)
async def analyze_sentiment(input_data: TextInput):
    try:
        # Validate input
        if not input_data.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        # Run the sentiment analysis
        result = sentiment_analyzer(input_data.text)

        # The model returns a list, we take the first result
        prediction = result[0]

        # Map the model's labels to user-friendly names
        label_mapping = {
            "LABEL_0": "negative",
            "LABEL_1": "neutral",
            "LABEL_2": "positive"
        }

        sentiment = label_mapping.get(prediction["label"], prediction["label"].lower())
        confidence = round(prediction["score"], 3)

        return SentimentResponse(
            text=input_data.text,
            sentiment=sentiment,
            confidence=confidence
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# For production deployment
import os

# Run the server (for development)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)