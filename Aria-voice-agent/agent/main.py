import asyncio
import json
import os
import requests
import re
from typing import List, Any, Dict, Set
from livekit import rtc
from livekit.agents import JobContext, WorkerOptions, cli, JobProcess
from livekit.agents.llm import (
    ChatContext,
    ChatMessage,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.agents.log import logger
from livekit.plugins import deepgram, silero, cartesia, google
from dotenv import load_dotenv

load_dotenv()

# Bad language filter
BAD_WORDS: Set[str] = {
    "profanity", "obscenity", "swear", "curse", "explicit",
    # Add actual profane words to filter in a real implementation
}

class EnhancedVoicePipelineAgent(VoicePipelineAgent):
    """Enhanced agent with additional capabilities like content filtering and context awareness"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sample HR policies, IT support, and event information loaded from public resources
        self.company_context = {
            "hr_policies": {
                "pto": "Employees receive a specified number of paid time off days annually, typically accrued monthly.",
                "work_hours": "Standard work hours are typically 9 AM to 5 PM, with flexible working arrangements possible.",
                "remote_work": "A hybrid work model may allow for a combination of in-office and remote work days.",
                "benefits": "Common employee benefits include health, dental, and vision insurance, along with retirement plans.",
                "parental_leave": "Many organizations offer paid parental leave for a set period, commonly up to 12 weeks."
            },
            "it_support": {
                "helpdesk_hours": "IT support is generally available during business hours, often Monday to Friday.",
                "password_reset": "Employees can request password resets through the designated employee portal.",
                "equipment_requests": "Requests for new equipment typically require managerial approval."
            },
            "upcoming_events": [
                {"name": "Company Picnic", "date": "TBD", "location": "Local Park"},
                {"name": "Quarterly Town Hall", "date": "TBD", "location": "Main Auditorium"},
                {"name": "Training & Development Session", "date": "TBD", "location": "Training Center"}
            ]
        }

    async def filter_response(self, text: str) -> str:
        """Filter out bad language and special characters"""
        # Remove asterisks
        text = text.replace('*', '')

        # Filter bad words (simplified implementation)
        for word in BAD_WORDS:
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            text = pattern.sub("[inappropriate language removed]", text)

        return text

    async def say(self, text: str, allow_interruptions: bool = False):
        """Override say method to apply filters"""
        filtered_text = await self.filter_response(text)
        return await super().say(filtered_text, allow_interruptions)

def prewarm(proc: JobProcess):
    # Preload models when process starts to speed up the first interaction
    proc.userdata["vad"] = silero.VAD.load()

    # Fetch Cartesia voices
    headers = {
        "X-API-Key": os.getenv("CARTESIA_API_KEY", ""),
        "Cartesia-Version": "2024-08-01",
        "Content-Type": "application/json",
    }
    response = requests.get("https://api.cartesia.ai/voices", headers=headers)
    if response.status_code == 200:
        proc.userdata["cartesia_voices"] = response.json()
    else:
        logger.warning(f"Failed to fetch Cartesia voices: {response.status_code}")

async def entrypoint(ctx: JobContext):
    # Create a comprehensive system prompt for an HR and organizational assistant
    hr_system_prompt = """
    You are an advanced HR and organizational assistant designed to provide helpful, accurate, 
    and concise information to employees. Your areas of expertise include:
    
    1. **HR Policies and Procedures**: Information on paid time off (PTO), benefits, work hours, remote work arrangements, parental leave, and other relevant policies.
    2. **IT Support**: Assistance with password resets, equipment requests, software licenses, and general IT inquiries.
    3. **Company Events**: Information about upcoming company events, town halls, and training sessions.
    4. **Office Logistics**: Guidance on meeting room bookings, parking arrangements, and other facility-related inquiries.
    5. **Onboarding Information**: Support for new employees regarding orientation, training, and resources available.

    When responding:
    - Be professional, friendly, and conversational.
    - Provide concise and relevant information.
    - Avoid using asterisks (*) or special formatting in your responses.
    - If you don't know the answer, acknowledge it and offer to connect the employee with the appropriate department.
    - Adapt your tone to be helpful and supportive.
    - Keep your responses brief and to the point while maintaining a natural conversational style.
    - Prioritize clarity and accuracy in your answers.
    
    Remember that you are interfacing through voice, so maintain a natural speaking style without any text formatting.
    """

    initial_ctx = ChatContext(
        messages=[
            ChatMessage(
                role="system",
                content=hr_system_prompt,
            )
        ]
    )
    cartesia_voices: List[dict[str, Any]] = ctx.proc.userdata["cartesia_voices"]

    tts = cartesia.TTS(
        model="sonic-2",
    )

    # Use LiveKit's official Google plugin for Gemini with optimized parameters
    llm = google.LLM(
        model="gemini-2.0-flash-exp",  # Use experimental model for better performance
        temperature=0.3,  # Lower temperature for more precise answers
        top_p=0.9,
        max_output_tokens=1024,  # Limit token length for faster responses
        api_key=os.getenv("GOOGLE_API_KEY", "")
    )

    # Use our enhanced agent class instead of the basic VoicePipelineAgent
    agent = EnhancedVoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(model="nova-2"),  # Use nova-2 for better transcription
        llm=llm,
        tts=tts,
        chat_ctx=initial_ctx,
    )

    is_user_speaking = False
    is_agent_speaking = False

    @ctx.room.on("participant_attributes_changed")
    def on_participant_attributes_changed(
        changed_attributes: dict[str, str], participant: rtc.Participant
    ):
        # Check for attribute changes from the user itself
        if participant.kind != rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD:
            return

        if "voice" in changed_attributes:
            voice_id = participant.attributes.get("voice")
            logger.info(
                f"Participant {participant.identity} requested voice change: {voice_id}"
            )
            if not voice_id:
                return

            voice_data = next(
                (voice for voice in cartesia_voices if voice["id"] == voice_id), None
            )
            if not voice_data:
                logger.warning(f"Voice {voice_id} not found")
                return
            if "embedding" in voice_data:
                language = "en"
                if "language" in voice_data and voice_data["language"] != "en":
                    language = voice_data["language"]
                tts._opts.voice = voice_data["embedding"]
                tts._opts.language = language
                # Allow user to confirm voice change as long as no one is speaking
                if not (is_agent_speaking or is_user_speaking):
                    asyncio.create_task(
                        agent.say("How do I sound now?", allow_interruptions=True)
                    )

    await ctx.connect()

    @agent.on("agent_started_speaking")
    def agent_started_speaking():
        nonlocal is_agent_speaking
        is_agent_speaking = True

    @agent.on("agent_stopped_speaking")
    def agent_stopped_speaking():
        nonlocal is_agent_speaking
        is_agent_speaking = False

    @agent.on("user_started_speaking")
    def user_started_speaking():
        nonlocal is_user_speaking
        is_user_speaking = True

    @agent.on("user_stopped_speaking")
    def user_stopped_speaking():
        nonlocal is_user_speaking
        is_user_speaking = False

    # Set voice listing as attribute for UI
    voices = []
    for voice in cartesia_voices:
        voices.append(
            {
                "id": voice["id"],
                "name": voice["name"],
            }
        )
    voices.sort(key=lambda x: x["name"])
    await ctx.room.local_participant.set_attributes({"voices": json.dumps(voices)})

    agent.start(ctx.room)
    await agent.say("Hello! I'm your HR and organizational assistant. How can I help you today with HR policies, IT support, or company information?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
