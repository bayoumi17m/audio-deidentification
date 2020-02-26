"""Audio Redaction taking in audio file, transcript, and NER."""

from pydub import AudioSegment


def audio_redaction(audio_path, asr_output, ner_output):
    """Redact audio files such that the sound is negligible at all PII/PHI.

    [Extended Summary]

    :param audio_path: Path to the audio file to be redacted
    :type audio_path: str
    :param asr_output: Dictionary output after AWS transcribe
    :type asr_output: dict
    :param ner_output: Output of the NER model using BERT
    :type ner_output: dict
    :return: redacted asr_output and audio file
    :rtype: typing.Tuple[dict, AudioSegment]
    """
    audio = AudioSegment.from_wav(audio_path)
    timestamped_tokens = asr_output["results"]["items"]
    redacted_asr = {
        "jobName": asr_output["jobName"],
        "accountId": asr_output["accountId"],
        "status": "COMPLETED",
    }

    asr_results = {}
    transcript = ""
    items = []

    for ner_step, asr_step in zip(ner_output, timestamped_tokens):
        if "-" in ner_step["tag"]:
            start_ms = int(float(asr_step["start_time"]) * 1000)
            end_ms = int(float(asr_step["end_time"]) * 1000)
            audio = (
                audio[:start_ms]
                + (AudioSegment.silent(duration=end_ms - start_ms))
                + audio[end_ms + 1 :]
            )
        else:
            if asr_step["type"] == "pronunciation":
                transcript += " " + asr_step["alternatives"][0]["content"]
            else:
                transcript += asr_step["alternatives"][0]["content"]
            items.append(asr_step)

    asr_results["transcripts"] = [{"transcript": transcript}]
    asr_results["items"] = items
    redacted_asr["results"] = asr_results

    return (redacted_asr, audio)
