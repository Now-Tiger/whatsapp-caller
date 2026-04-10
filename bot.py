import asyncio
import os
import ssl
from typing import Union

import certifi
from dotenv import load_dotenv

# Ensure every HTTPS connection uses certifi's CA bundle.
# Required on macOS (python.org installer) where Python's OpenSSL does not
# automatically trust system Keychain certificates.
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMContextFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.runner.types import SmallWebRTCRunnerArguments
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecatcloud.agent import DailySessionArguments

from bot_prompt import BOT_SYSTEM_PROMPT

load_dotenv()


async def run_bot(webrtc_connection: SmallWebRTCConnection):
    try:
        logger.info(
            "Starting bot | LLM model={} | STT=Deepgram | TTS=Deepgram voice=aura-2-helena-en",
            os.environ.get("OPENROUTER_LLM_MODEL", "NOT SET"),
        )

        transport = SmallWebRTCTransport(
            webrtc_connection=webrtc_connection,
            params=TransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )

        stt = DeepgramSTTService(api_key=os.environ["DEEPGRAM_API_KEY"])

        llm = OpenAILLMService(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url=os.environ["OPENROUTER_BASE_URL"],
            settings=OpenAILLMService.Settings(model=os.environ["OPENROUTER_LLM_MODEL"]),
        )

        tts = DeepgramTTSService(
            api_key=os.environ["DEEPGRAM_API_KEY"],
            settings=DeepgramTTSService.Settings(voice="aura-2-helena-en"),
        )

        context = LLMContext(
            messages=[{"role": "system", "content": BOT_SYSTEM_PROMPT}]
        )
        context_aggregators = LLMContextAggregatorPair(context)

        pipeline = Pipeline(
            [
                transport.input(),
                stt,
                context_aggregators.user(),
                llm,
                tts,
                transport.output(),
                context_aggregators.assistant(),
            ]
        )

        task = PipelineTask(
            pipeline,
            params=PipelineParams(allow_interruptions=True),
        )

        logger.info("Pipeline ready — waiting for WebRTC connection")

        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            logger.info("WhatsApp call connected")
            await task.queue_frames([LLMContextFrame(context=context)])
            logger.info("Greeting context frame queued for call")

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            logger.info("WhatsApp call ended")
            await task.cancel()

        runner = PipelineRunner(handle_sigint=False)
        await runner.run(task)

    except Exception:
        logger.exception("Unhandled error in run_bot")
        raise


# Unified entrypoint for both local dev (SmallWebRTCRunnerArguments)
# and Pipecat Cloud (DailySessionArguments) — both expose webrtc_connection.
async def bot(args: Union[SmallWebRTCRunnerArguments, DailySessionArguments]):
    logger.info("bot() invoked — starting run_bot")
    await run_bot(args.webrtc_connection)


if __name__ == "__main__":
    import sys
    from pipecat.runner.run import main

    # Inject required flags so `uv run bot.py` is sufficient — the user
    # never has to remember to pass --whatsapp -t webrtc manually.
    if "--whatsapp" not in sys.argv:
        sys.argv += ["-t", "webrtc", "--whatsapp"]

    main()
