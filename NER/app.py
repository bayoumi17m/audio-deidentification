"""NER Web application"""

from bert import Ner
from flask import Flask, jsonify, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

model = Ner("out_large")


@app.route("/predict", methods=["POST"])
def predict():
    text = request.json["text"]
    try:
        out = model.predict(text)
        return jsonify({"result": out})
    except Exception as e:
        print(e)
        return jsonify({"result": "Model Failed"})


if __name__ == "__main__":
    app.run("0.0.0.0", port=8000)
