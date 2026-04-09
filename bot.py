import asyncio
import os

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMContextFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
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

    context = LLMContext(messages=[{"role": "system", "content": BOT_SYSTEM_PROMPT}])
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

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("WhatsApp call connected")
        await task.queue_frames([LLMContextFrame(context=context)])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("WhatsApp call ended")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)


async def bot(args: DailySessionArguments):
    await run_bot(args.webrtc_connection)
