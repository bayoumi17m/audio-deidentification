import tempfile
import json

from flask import Flask, request, make_response
from flask_cors import CORS
import connexion
import boto3
from botocore.exceptions import ClientError

from ASR.run_aws_transcribe import transcribe_job
from NER.bert import Ner
from REDACT.audio_redact import audio_redaction

# application = connexion.App(__name__)
app = Flask(__name__) # application.app
app.config.from_pyfile("./config.cfg")
CORS(app)

AWS_ACCESS_KEY_ID = app.config["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = app.config["AWS_SECRET_ACCESS_KEY"]

model = Ner("NER/out_large")

s3_client = boto3.client('s3', aws_access_key_id = AWS_ACCESS_KEY_ID, aws_secret_access_key = AWS_SECRET_ACCESS_KEY)


def correct_contraction_tokens(tokens):
    """
    """
    idx_to_pop = []
    contractive_endings = ["'m", "'ve", "'re", "'s", "'ll", "n't"]
    num_tokens = len(tokens)
    for i in range(1,num_tokens):
        if tokens[i]["word"] in contractive_endings:
            tokens[i-1]["word"] = tokens[i-1]["word"]+tokens[i]["word"]
            idx_to_pop.append(i - len(idx_to_pop))
    
    for i in idx_to_pop:
        tokens.pop(i)
    
    return tokens



def redact_text_and_audio(job_name, input_bucket_name, input_s3_path, output_bucket_name):
    """redact_text_and_audio removes PII from the text (placeholder) and audio.

    :param job_name: Unique name of the redaction job. Should be unique per
        call to client. That is, call 1 and call 2 to person A will have
        different job_names and all calls to person A and person B won't have
        the same job_name
    :type job_name: str
    :param input_bucket_name: Name of the S3 bucket the file is stored in.
    :type input_bucket_name: str
    :param input_s3_path: Path within the S3 bucket. E.g. 'samples/call_1.wav'
        The string should not start with a '/'.
    :type input_s3_path: str
    :param output_bucket_name: Name of the S3 bucket to store the output in.
    :type output_bucket_name: str
    """
    output_asr_file = job_name + "_redacted.json"
    output_audio_file = job_name + "_redacted.wav"

    job_uri = 'https://s3.amazonaws.com/{}/{}'.format(input_bucket_name, input_s3_path)

    # Run AWS Transcribe job
    data = transcribe_job(job_name, job_uri, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

    if data["status"] == "FAILED":
        return "Error- The transcribe job failed. Please check the output in console"
    
    # Predict whether a word is PII / PHI
    preds = model.predict_long(data["results"]["transcripts"][0]["transcript"])

    # Output of preds splits contractions and so we must combine them again
    # before performing the redaction
    corrected_preds = correct_contraction_tokens(preds)

    # Redact Audio + Text and output it
    with tempfile.NamedTemporaryFile(suffix = ".wav") as f:
        s3_client.download_fileobj(input_bucket_name,input_s3_path,f)
        (redacted_asr, redacted_audio) = audio_redaction(f.name, data, corrected_preds)
    redacted_audio.export(job_name + "_redacted.wav")
    with open(job_name + "_redacted.json", "w") as fp:
        json.dump(redacted_asr, fp)

    # Upload files to AWS S3 Bucket
    try:
        s3_client.upload_file(output_asr_file, output_bucket_name, job_name + "/" + output_asr_file)
    except ClientError as e:
        return "Error- " + e.msg
    
    try:
        s3_client.upload_file(output_audio_file, output_bucket_name, job_name + "/" + output_audio_file)
    except ClientError as e:
        return e.msg

    return "Success- You should see the results in the console"


@app.route("/redaction", methods=["POST"])
def redaction():
    job_name = request.json["job_name"]
    input_bucket_name = request.json["input_bucket_name"]
    input_s3_path = request.json["input_s3_path"]
    output_bucket_name = request.json["output_bucket_name"]

    response = redact_text_and_audio(job_name, input_bucket_name, input_s3_path, output_bucket_name)
    if response[:6] == "Error-":
        return make_response(response, 500, {"Content-Type": "text/plain"})
    else:
        return make_response(response, 200, {"Content-Type": "text/plain"})


# application.add_api("openapi/spec.yaml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)