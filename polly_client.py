"""Amazon Polly Client module for Text-to-Speech (TTS) synthesis.

Turns text notes into lifelike audio streams using AWS Polly.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger("polly_client")


class PollyManager:
    """Manager for Amazon Polly Text-to-Speech operations."""

    def __init__(
        self,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self._polly_client = None

    def _get_client(self):
        """Get or initialize the boto3 Polly client."""
        if self._polly_client:
            return self._polly_client

        try:
            if self.aws_access_key_id and self.aws_secret_access_key:
                self._polly_client = boto3.client(
                    "polly",
                    region_name=self.region_name,
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                )
            else:
                # Fallback to default AWS credential chain (~/.aws/credentials or IAM role)
                self._polly_client = boto3.client("polly", region_name=self.region_name)

            return self._polly_client
        except Exception as e:
            logger.error(f"Failed to initialize AWS Polly client: {e}")
            return None

    def synthesize_to_file(
        self,
        text: str,
        output_file_path: str,
        voice_id: str = "Lupe",
        engine: str = "neural",
        output_format: str = "mp3",
    ) -> Optional[str]:
        """Synthesize text into an audio file using Amazon Polly.

        Available Spanish voices (Neural/Standard):
        - Lupe (US / Spanish - Neural)
        - Mia (Mexican / Spanish - Neural)
        - Lucia (Spain / Spanish - Neural)
        - Enrique (Spain / Spanish - Standard)

        Returns the absolute file path if successful.
        """
        client = self._get_client()
        if not client:
            logger.error("Polly client is not available. Check AWS credentials.")
            return None

        try:
            logger.info(f"Synthesizing speech with Polly (Voice: {voice_id}, Engine: {engine})...")
            response = client.synthesize_speech(
                Text=text,
                OutputFormat=output_format,
                VoiceId=voice_id,
                Engine=engine,
            )

            if "AudioStream" in response:
                out_path = Path(output_file_path)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "wb") as file:
                    file.write(response["AudioStream"].read())
                logger.info(f"Audio file generated at: {out_path}")
                return str(out_path.resolve())
            else:
                logger.error("No AudioStream in Polly response.")
                return None

        except (BotoCoreError, ClientError) as error:
            logger.error(f"Amazon Polly synthesis failed: {error}")
            return None

    def synthesize_bytes(
        self,
        text: str,
        voice_id: str = "Lupe",
        engine: str = "neural",
        output_format: str = "mp3",
    ) -> Optional[bytes]:
        """Synthesize text into raw audio bytes using Amazon Polly."""
        client = self._get_client()
        if not client:
            logger.error("Polly client is not available.")
            return None

        try:
            logger.info(f"Synthesizing speech bytes with Polly (Voice: {voice_id}, Engine: {engine})...")
            response = client.synthesize_speech(
                Text=text,
                OutputFormat=output_format,
                VoiceId=voice_id,
                Engine=engine,
            )
            if "AudioStream" in response:
                return response["AudioStream"].read()
            return None
        except (BotoCoreError, ClientError) as error:
            logger.error(f"Amazon Polly synthesis bytes failed: {error}")
            return None


# Global instance
polly_manager = PollyManager()
