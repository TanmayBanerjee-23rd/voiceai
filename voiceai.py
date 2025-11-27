import asyncio
import os
import sys
import re
import json
import urllib.request
import keyboard
import threading
import struct
from microphoneStream import MicrophoneStream, CHUNK
from speakerStream import SpeakerStream

from dotenv import load_dotenv

# Import Deepgram
from deepgram import DeepgramClient
from deepgram.core.events import EventType
from deepgram.extensions.types.sockets import ListenV2SocketClientResponse, SpeakV1SocketClientResponse, SpeakV1ControlMessage, ListenV2MediaMessage, SpeakV1TextMessage

from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

async def main():
    """Main demo function."""
    print("🚀 Deepgram Flux Agent Demo")
    print("=" * 40)

    try:
        # Initialize the Voice Agent
        deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
        if not deepgram_api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is not set")
        print(f"API Key found!")
        # Initialize Deepgram client
        client = DeepgramClient(
            api_key=deepgram_api_key
        )

        # Transcribe with Flux
        print("\n🎤 Transcribing with Flux...\n")
        transcript = ""
        transcript_done = asyncio.Event()

        def on_flux_message(message: ListenV2SocketClientResponse) -> None:
            nonlocal transcript
            if hasattr(message, 'type') and message.type == 'TurnInfo':
                if hasattr(message, 'event') and message.event == 'EndOfTurn':
                    if hasattr(message, 'transcript') and message.transcript:
                        transcript += " " + message.transcript.strip()
                        print("\n")
                        print("~" * 90)
                        print(f"\n✓ Current Transcript: '{transcript if transcript else 'Empty'}'\n")
                        print("Please let me know what you'd like to ask.")
                        print("Use below controls to manage recording:")
                        print("'Esc'       -> To stop recording and process your request.\n")
                        print("'Space Bar' -> To flush previous recording and re-record.")
                        transcript_done.set()
        
        # === Event Handlers ===
        def on_open(self, **kwargs):
            print("Deepgram connection OPENED!\n")

        def on_error(self, error, **kwargs):
            print(f"Error: {error}")

        def on_close(close_response, **kwargs):
            print(f"Deepgram connection CLOSED!\n")

        with client.listen.v2.connect(model="flux-general-en", encoding="linear16", sample_rate=16000) as connection:
                
            # Register event handlers
            connection.on(EventType.OPEN, on_open)
            connection.on(EventType.MESSAGE, on_flux_message)
            connection.on(EventType.ERROR, on_error)
            connection.on(EventType.CLOSE, on_close)

            threading.Thread(target=connection.start_listening, daemon=True).start()

            # === Stream from Mac Microphone ===
            try:
                print("Please let me know what you'd like to ask.")
                print("Use below controls to manage recording:")
                print("'Esc'       -> To stop recording and process your request.\n")
                print("'Space Bar' -> To flush previous recording and re-record.")
                with MicrophoneStream() as mic_stream:
                    while True:
                        data = mic_stream.read(CHUNK, exception_on_overflow=False)
                        connection.send_media(data)
                        if keyboard.is_pressed('esc'):
                            break
                        if keyboard.is_pressed('space'):
                            print("\n")
                            print("~" * 90)
                            print("Flushing previous recording. Please re-record your request.")
                            transcript = ""
                        await asyncio.sleep(0.01)  # Small delay to prevent CPU overload

            except KeyboardInterrupt:
                print("\nStopping Mic Stream Ingestion...")

            finally:
                print("Transcription completed.")

            # Wait for transcript
            await asyncio.wait_for(transcript_done.wait(), timeout=30.0)

        if not transcript:
            print("❌ It seems Transcription didn't succeed as no transcript was detected.")
            return

        # Generate Gemini response
        print("\n🤖 Generating Gemini response...")

        genaiClient = genai.Client()

        genai_response = genaiClient.models.generate_content(
            model="gemini-2.5-flash",
            contents=[transcript],
            config=types.GenerateContentConfig(
                system_instruction="""
                You are an highly intelligent and helpful voice assistant. 
                You respond to user queries in a concise and informative manner.
                You answer in a friendly and engaging manner.
                Your answer should be in maximum of 100 words.
                You do also categorize your generated response 
                into one of the following categories and Sub-Category:
                Category - Scientific Classification Systems - Sub-Categories such as Biology, Chemistry, Physics and Mathematics;
                Category - Philosophical/Existential Categories - Sub-Categories such as Mind, Matter, Ethics, 
                Metaphysics, Epistemology and Logic;
                Category - Practical/Everyday Categorizations - Sub-Categories such as Food & Cooking, 
                Travel & Geography, Fashion & Lifestyle, Home & Garden, Finance & Economics, 
                Relationships & Social Dynamics, Career & Professional Development, Hobbies & Interests,
                Technology & Computing, Arts & Literature, History & Culture, 
                General Knowledge, Entertainment & Media, Health & Wellness, 
                Environment & Nature, Education & Learning, Sports & Recreation.
                Provide the response in a JSON format with two fields: 'response', 'category' and 'sub-category'.
                The 'response' field contains your answer to the user's query.
                The 'category' field contains the category of the user's intent.
                The 'sub-category' field contains the sub-category of the user's intent.
                """,
                temperature=0.1
            )
        )

        def extract_json_from_fence(text: str):
            """
            Extract JSON object from a string that may contain Markdown code fences
            like ```json ... ``` or ``` ... ```. Returns a Python dict.
            """
            # Try to capture a fenced JSON block first (```json { ... } ``` or ``` { ... } ```)
            m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.S | re.I)
            if m:
                json_str = m.group(1)
            else:
            # Fallback: try to find the first JSON object in the text
                m2 = re.search(r'(\{(?:[^{}]|\{[^{}]*\})*\})', text, re.S)
                json_str = m2.group(1) if m2 else text.strip()

            # Parse JSON
            return json.loads(json_str)

        # Example: parse JSON out of the model genai_response (which may include fences)
        response_text = genai_response.text  # default to original text (genai_response.text is read-only)
        response_category = ""
        try:
            parsed = extract_json_from_fence(genai_response.text)
            # Use parsed values (safe defaults if keys missing)
            parsed_response_text = parsed.get("response", "")
            parsed_category = parsed.get("category", "")
            parsed_subcategory = parsed.get("sub-category", "")
            # Set our mutable variables instead of assigning to response.text``
            response_text = parsed_response_text or response_text
            response_text = response_text.replace('*', '')
            response_category = parsed_category or ""
            response_subcategory = parsed_subcategory or ""
        except Exception as e:
            print(f"Failed to parse fenced JSON: {e}")
            # Keep original text on failure (response_text already set)

        print("✓ Response: " + response_text)
        print("✓ Category: " + response_category)
        print("✓ Sub-Category: " + response_subcategory)

        # Generate TTS Response
        print("\n🔊 Generating TTS...")
        tts_audio = []
        tts_done = asyncio.Event()

        def on_tts_message(message: SpeakV1SocketClientResponse) -> None:
            if isinstance(message, bytes):
                tts_audio.append(message)
            elif hasattr(message, 'type') and message.type == 'Flushed':
                tts_done.set()

        with client.speak.v1.connect(model="aura-2-arcas-en", encoding="linear16", sample_rate=16000) as connection:
            connection.on(EventType.MESSAGE, on_tts_message)

            threading.Thread(target=connection.start_listening, daemon=True).start()

            connection.send_text(SpeakV1TextMessage(type="Speak", text=response_text))
            connection.send_control(SpeakV1ControlMessage(type="Flush"))

            # Wait for TTS completion
            await asyncio.wait_for(tts_done.wait(), timeout=15.0)

        # Save TTS audio
        if tts_audio:
            output_file = "audio/responses/agent_response.wav"
            combined_audio = b''.join(tts_audio)

            with SpeakerStream() as speaker_stream:
                speaker_stream.write(combined_audio)

            # Create simple WAV header
            wav_header = struct.pack(
                '<4sI4s4sIHHIIHH4sI',
                b'RIFF', 36 + len(combined_audio), b'WAVE', b'fmt ', 16, 1, 1,
                16000, 32000, 2, 16, b'data', len(combined_audio)
            )

            with open(output_file, 'wb') as f:
                f.write(wav_header + combined_audio)

            print(f"💾 Saved TTS audio: {output_file}")

        print("\n🎉 Demo complete!")

    except Exception as e:
      print(f"Error: {str(e)}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
