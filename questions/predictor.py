import pickle


class QuestionPredictor():

    def __init__(self):
        self.model = pickle.load(open("questions/saved_models/linear_svc_1_0.pkl", "rb"))
        self.vectorizer = pickle.load(open("questions/saved_models/tfidf_vectorizer_1_0.pkl", "rb"))

    def predict_related_faq_ids(self, questions):
        texts = []
        for question in questions:
            texts.append(question.title + " " + question.text)
        features = self.vectorizer.transform(texts)
        labels = self.model.predict(features)
        return labels.tolist()
