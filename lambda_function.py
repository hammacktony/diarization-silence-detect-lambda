import logging
import os
import re
import subprocess
from contextlib import contextmanager
from typing import Any, List, Tuple

import boto3


class FFmpegError(Exception):
    """ FFMPEG Exception Class """


# FFMPEG Command -> This comes from the Lambda layer.
FFMPEG_CMD = "/opt/python/ffmpeg"

# Default config values in case nothing is passed
DEFAULT_DURATION = 0.3  # Units: seconds
DEFAULT_TOLERANCE = -36  # UNits: decibels

# Compile regexs for search ffmpeg output
SILENCE_START_RE = re.compile(" silence_start: (?P<start>[0-9]+(\.?[0-9]*))$")
SILENCE_END_RE = re.compile(" silence_end: (?P<end>[0-9]+(\.?[0-9]*)) ")
TOTAL_DURATION_RE = re.compile(
    "size=[^ ]+ time=(?P<hours>[0-9]{2}):(?P<minutes>[0-9]{2}):(?P<seconds>[0-9\.]{5}) bitrate="
)


def _popen(cmd_line: List[str], *args, **kwargs) -> subprocess.Popen:
    """ Wrapper for ffmpeg command """
    return subprocess.Popen(cmd_line, *args, **kwargs)


def detect_silence(input_file: str, noise_tolerance: int, noise_duration: float) -> str:
    """ Run ffmpeg command to detect silence """
    p = _popen(
        [
            FFMPEG_CMD,
            "-i",
            input_file,
            "-filter_complex",
            f"[0]silencedetect=d={noise_duration}:n={noise_tolerance}dB[s0]",
            "-map",
            "[s0]",
            "-f",
            "null",
            "-",
            "-nostats",
        ],
        stderr=subprocess.PIPE,
    )

    output = p.communicate()[1].decode("utf-8")
    if p.returncode != 0:
        logging.error(output)
        raise FFmpegError("FFMPEG Error. Check logs")

    return output


def has_audio(
    input_file: str, noise_tolerance: int = DEFAULT_TOLERANCE, noise_duration: float = DEFAULT_DURATION,
) -> Tuple[List[Tuple[float, float]], bool]:
    """ Checks to see if clip has audio """

    # Call ffmpeg and detect silence in file
    output = detect_silence(input_file, noise_tolerance, noise_duration)

    noise_detected = True  # Denotes if the entire segment was all silence, or if there was audio
    start_time, end_time = 0.0, None

    # Chunks start when silence ends, and chunks end when silence starts.
    chunk_starts = []
    chunk_ends = []
    for line in output.splitlines():
        silence_start_match = SILENCE_START_RE.search(line)
        silence_end_match = SILENCE_END_RE.search(line)
        total_duration_match = TOTAL_DURATION_RE.search(line)
        if silence_start_match:
            chunk_ends.append(float(silence_start_match.group("start")))
            if len(chunk_starts) == 0:
                # Started with non-silence.
                chunk_starts.append(start_time or 0.0)
        elif silence_end_match:
            chunk_starts.append(float(silence_end_match.group("end")))
        elif total_duration_match:
            hours = int(total_duration_match.group("hours"))
            minutes = int(total_duration_match.group("minutes"))
            seconds = float(total_duration_match.group("seconds"))
            end_time = hours * 3600 + minutes * 60 + seconds

    if len(chunk_starts) == 0:
        # No silence found.
        chunk_starts.append(start_time)

    if len(chunk_starts) > len(chunk_ends) > 0:
        # Finished with non-silence.
        chunk_ends.append(end_time or 10000000.0)
    else:
        # Happens when silence never stopped
        noise_detected = False

    return list(zip(chunk_starts, chunk_ends)), noise_detected


@contextmanager
def s3_object(bucket_name: str, key_name: str):
    """ Context manager for handling the s3 file.

    It downloads the data to a temp. Then, it yields the filename via
    the contextmanager protocol. Finally, it deletes this temp file.
    """
    file_name = f"/tmp/{key_name.split('/')[-1]}"
    s3_client = boto3.client("s3")
    s3_client.download_file(bucket_name, key_name, file_name)
    yield file_name
    os.remove(file_name)


def lambda_handler(event, context):
    """ Lambda handler """
    resp = {"success": False, "noise_detected": False, "errors": None}

    try:
        bucket_name = event["body"]["bucket_name"]
        key_name = event["body"]["key_name"]
        noise_tolerance = event["body"]["noise_tolerance"]
        noise_duration = event["body"]["noise_duration"]

        with s3_object(bucket_name, key_name) as input_file:
            _, noise_detected = has_audio(input_file, noise_tolerance, noise_duration)

        resp["noise_detected"] = noise_detected
        resp["success"] = True
    except Exception as e:
        resp["error"] = f"{type(e)}: {str(e)}"

    return {"statusCode": 200, "data": resp}
