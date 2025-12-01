# voiceAi

## Primary Language

**python**

## How to use the agent.

- Install all required packages using the below command ::

  `pip install -r requirements.txt`

- Create an .env file and add below environment variables ::

  ```
  DEEPGRAM_API_KEY="" // obtain an API key from deepgram.com

  GEMINI_API_KEY="" // obtain an API key from aistudio.google.com/api-keys
  ```

- Run the below command to run the agent ::

  `sudo python3 voiceai.py`

## Established at Inception

A voice agent which helps to clarify user queries and speaks it through device speaker.
Uses Deepgram for STT and TTS and google-genai for response generation.

## Establishment on second commit

The response is categorized and sub-categorized.

## Establishment on third commit

Retained the genai response in Pinecone Vector Database for semantic search based on category and subcategory of historical response records and future analysis purposes.
