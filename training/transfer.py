import json
import random
import spacy
from spacy.training.example import Example
from sklearn.metrics import recall_score, f1_score, precision_score, accuracy_score
from spacy.training import offsets_to_biluo_tags
from spacy.tokens import Doc
from spacy.util import minibatch, compounding

from main import convert_to_spacy_format, split_data, extract_entities, evaluate_ner_model, remove_misaligned_entities

n_iter = 1000

if __name__ == "__main__":
    with open('datasets/united-dataset.json', 'r') as f:
        data = json.load(f)

    data = [item for item in data if len(item[2]) < 2]

    training_data = convert_to_spacy_format(data)
    train_data, valid_data = split_data(training_data)

    # Create a blank spaCy model
    # spacy.require_gpu()
    nlp = spacy.load("custom_ner_model_small_sentences")
    # nlp = spacy.load("en_core_web_trf")

    ner = nlp.get_pipe("ner")
    aligned_train_data = remove_misaligned_entities(nlp, train_data)
    aligned_valid_data = remove_misaligned_entities(nlp, valid_data)
    print(len(aligned_train_data))

    with open('valid_data.json', 'w') as valid:
        json.dump(aligned_valid_data, valid, indent=1)

    # # Add the labels
    # for _, annotations in aligned_train_data:
    #     for ent in annotations.get("entities"):
    #         ner.add_label(ent[2])

    # Disable other pipelines during training
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
    with nlp.disable_pipes(*other_pipes):  # Only train NER
        # optimizer = nlp.begin_training()
        optimizer = nlp.resume_training()
        decay_rate = 0.9
        # optimizer.learn_rate = 0.01
        # optimizer.clip_gradients(5.0)
        for itn in range(n_iter):
            random.shuffle(aligned_train_data)
            losses = {}
            if itn != 0 and itn % 10 == 0:
                optimizer.learn_rate *= decay_rate
                print("LEARNING RATE: ", optimizer.learn_rate)
            for text, annotations in aligned_train_data:
                doc = nlp.make_doc(text)
                example = Example.from_dict(doc, annotations)
                nlp.update([example], losses=losses, drop=0.5, sgd=optimizer)
            print(f"Iteration {itn}, Losses: {losses}")

            accuracy, precision, recall, f1 = evaluate_ner_model(nlp, aligned_valid_data)
            print(
                f"Validation after iteration {itn}: Accuracy={accuracy:.5f} Precision={precision:.5f},"
                f" Recall={recall:.5f}, F1-Score={f1:.5f}")
            if f1 > 0.8:
                break

            accuracy, precision, recall, f1 = evaluate_ner_model(nlp, aligned_train_data)
            print(
                f"Training after iteration {itn}: Accuracy={accuracy:.5f} Precision={precision:.5f},"
                f" Recall={recall:.5f}, F1-Score={f1:.5f}")


    # Train the model
    # ner_model = train_spacy_model(train_data, n_iter=50)
    nlp.to_disk("custom_ner_model_transferred")

    # Evaluate the NER model on the validation data
    # accuracy, precision, recall, f1 = evaluate_ner_model(nlp, aligned_valid_data)
    #
    # print(f"Accuracy: {accuracy:.2f}")
    # print(f"Precision: {precision:.2f}")
    # print(f"Recall: {recall:.2f}")
    # print(f"F1-Score: {f1:.2f}")
