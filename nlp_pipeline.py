import os
import re
import ftfy
import emoji
import spacy
import stopwordsiso
from huggingface_hub import InferenceClient
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

DetectorFactory.seed = 0
_nlp = None
_vader = None
_hf_client = None

EMOTION_LABELS = ["Happy", "Sad", "Stress", "Angry", "Fear", "Neutral"]
EMOTION_EMOJI = {
    "Happy": "\U0001F60A", "Sad": "\U0001F622", "Stress": "\U0001F62B",
    "Angry": "\U0001F621", "Fear": "\U0001F628", "Neutral": "\U0001F610",
}

GOEMOTIONS_TO_APP_LABEL = {
    "joy": "Happy", "amusement": "Happy", "excitement": "Happy",
    "love": "Happy", "gratitude": "Happy", "optimism": "Happy",
    "relief": "Happy", "pride": "Happy", "admiration": "Happy",
    "approval": "Happy", "caring": "Happy",
    "sadness": "Sad", "disappointment": "Sad", "grief": "Sad",
    "remorse": "Sad",
    "nervousness": "Stress", "embarrassment": "Stress",
    "confusion": "Stress",
    "anger": "Angry", "annoyance": "Angry", "disgust": "Angry",
    "disapproval": "Angry",
    "fear": "Fear",
    "neutral": "Neutral", "realization": "Neutral", "surprise": "Neutral",
    "curiosity": "Neutral", "desire": "Neutral",
}

LANGUAGE_NAMES = {
    "te": "Telugu", "kn": "Kannada", "en": "English", "ta": "Tamil",
    "hi": "Hindi", "ml": "Malayalam", "mr": "Marathi", "bn": "Bengali", "gu": "Gujarati",
    "fr": "French", "de": "German", "es": "Spanish", "pt": "Portuguese",
    "ar": "Arabic", "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "ru": "Russian",
}

def _get_stopwords(language_code: str) -> set:
    if stopwordsiso.has_lang(language_code):
        return stopwordsiso.stopwords(language_code)
    return set()

def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("xx_sent_ud_sm")
    return _nlp

def _get_vader():
    global _vader
    if _vader is None:
        _vader = SentimentIntensityAnalyzer()
    return _vader

def _get_hf_client():
    global _hf_client
    if _hf_client is None:
        hf_token = os.getenv("HF_TOKEN")
        _hf_client = InferenceClient(token=hf_token)
    return _hf_client

def _bert_emotion(text: str) -> dict:
    client = _get_hf_client()
    if not text.strip():
        text = "(empty feedback)"
    
    try:
        raw_predictions = client.text_classification(text, model="bhadresh-savani/bert-base-go-emotion")
    except Exception:
        raw_predictions = [{"label": "neutral", "score": 1.0}]
    
    app_scores = {label: 0.0 for label in EMOTION_LABELS}
    for pred in raw_predictions:
        goemotion_label = pred["label"].lower()
        app_label = GOEMOTIONS_TO_APP_LABEL.get(goemotion_label, "Neutral")
        app_scores[app_label] += pred["score"]
        
    total = sum(app_scores.values()) or 1.0
    app_scores = {label: round(score / total, 4) for label, score in app_scores.items()}
    final_emotion = max(app_scores, key=app_scores.get)
    confidence = app_scores[final_emotion]
    return {"emotion": final_emotion, "scores": app_scores, "confidence": confidence}

def process_employee_feedback(text: str) -> dict:
    nlp = _get_nlp()
    vader = _get_vader()
    normalized_text = ftfy.fix_text(text)
    
    try:
        language = detect(normalized_text)
    except Exception:
        language = "unknown"
    detected_language = LANGUAGE_NAMES.get(language, "Other / Unknown")
    
    emoji_list = [ch for ch in normalized_text if ch in emoji.EMOJI_DATA]
    cleaned_text = re.sub(r"https?://\S+|www\.\S+", " ", normalized_text)
    cleaned_text = re.sub(r"\S+@\S+", " ", cleaned_text)
    cleaned_text = re.sub(r"@\w+|#\w+", " ", cleaned_text)
    cleaned_text = emoji.replace_emoji(cleaned_text, replace="")
    cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()
    
    doc = nlp(cleaned_text)
    sentences = [s.text.strip() for s in doc.sents if s.text.strip()]
    original_tokens = [t.text for t in doc if not t.is_space]
    clean_tokens = [t.text for t in doc if not t.is_punct and not t.is_space and not t.like_num]
    
    selected_stopwords = _get_stopwords(language)
    filtered_tokens = [t for t in clean_tokens if t.lower() not in selected_stopwords]
    final_preprocessed_text = " ".join(filtered_tokens)
    
    try:
        translated_text = GoogleTranslator(source="auto", target="en").translate(final_preprocessed_text)
    except Exception as error:
        translated_text = f"Translation failed: {error}"
        
    english_doc = nlp(translated_text)
    lemmas = [t.lemma_ if t.lemma_ else t.text for t in english_doc if not t.is_space]
    lemmatized_text = " ".join(lemmas)
    
    sentiment_scores = vader.polarity_scores(translated_text)
    compound_score = sentiment_scores["compound"]
    
    if compound_score >= 0.05:
        final_sentiment = "Positive \U0001F60A"
    elif compound_score <= -0.05:
        final_sentiment = "Negative \U0001F614"
    else:
        final_sentiment = "Neutral \U0001F610"
        
    bert_result = _bert_emotion(translated_text)
    emotion_scores = bert_result["scores"]
    final_emotion_label = bert_result["emotion"]
    final_emotion = f"{final_emotion_label} {EMOTION_EMOJI.get(final_emotion_label, '')}"
    emotion_confidence = bert_result["confidence"]
    
    return {
        "language_code": language,
        "detected_language": detected_language,
        "normalized_text": normalized_text,
        "cleaned_text": cleaned_text,
        "sentences": sentences,
        "original_tokens": original_tokens,
        "filtered_tokens": filtered_tokens,
        "emoji_list": emoji_list,
        "final_preprocessed_text": final_preprocessed_text,
        "translated_text": translated_text,
        "lemmatized_text": lemmatized_text,
        "sentiment_scores": sentiment_scores,
        "final_sentiment": final_sentiment,
        "emotion_scores": emotion_scores,
        "final_emotion": final_emotion,
        "emotion_confidence": emotion_confidence,
    }

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "want to die", "self harm",
    "self-harm", "hurt myself", "not worth living", "no reason to live",
]

CRISIS_MESSAGE = (
    "I'm really glad you reached out, and I want to make sure you get support "
    "beyond what I can offer here. If you're in immediate danger, please contact "
    "your local emergency number right now. You can also reach a crisis line: "
    "in India, AASRA is available at +91-9820466726 (24/7). If you're outside "
    "India, please look up a local crisis helpline or talk to a trusted person "
    "or your HR/EAP contact. You don't have to go through this alone."
)

WELLNESS_SYSTEM_PROMPT = (
    "You are a supportive workplace wellness assistant for employees. "
    "Your role is to listen, validate feelings, and offer general, gentle "
    "coping suggestions (like breathing exercises, taking a short break, "
    "or talking to a trusted colleague or manager). "
    "You are NOT a therapist or doctor: never diagnose any condition, never "
    "claim expertise you don't have, and never give medical or medication "
    "advice. If the employee describes something serious (ongoing crisis, "
    "self-harm, harming others), gently encourage them to contact a mental "
    "health professional, their HR/EAP program, or a crisis helpline. "
    "Keep replies short (2-4 sentences), warm, and non-judgmental. "
    "Avoid clinical labels and avoid being preachy or repetitive."
)

def _contains_crisis_language(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in CRISIS_KEYWORDS)

def wellness_chat_reply(message: str, history: list[dict] | None = None) -> dict:
    if _contains_crisis_language(message):
        return {"reply": CRISIS_MESSAGE, "flagged": True}
    
    client = _get_hf_client()
    messages = [{"role": "system", "content": WELLNESS_SYSTEM_PROMPT}]
    for turn in (history or []):
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": message})
    
    try:
        response = client.chat_completion(
            messages=messages, 
            model="Qwen/Qwen2.5-0.5B-Instruct", 
            max_tokens=150
        )
        reply = response.choices[0].message.content.strip()
    except Exception:
        reply = "I'm here and listening — could you tell me a bit more about how you're feeling?"
        
    return {"reply": reply, "flagged": False}