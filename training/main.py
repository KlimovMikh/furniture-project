import json
import random
import spacy
from spacy.training.example import Example
from sklearn.metrics import recall_score, f1_score, precision_score, accuracy_score
from spacy.training import offsets_to_biluo_tags
from spacy.tokens import Doc
from spacy.util import minibatch, compounding

Doc.set_extension("paragraph_type", default=None)

def add_paragraph_type(doc, paragraph_type):
    """Add a paragraph type to the doc."""
    doc._.paragraph_type = paragraph_type
    return doc


def convert_with_paragraph_info(dataset, paragraph_info):
    """Convert the dataset to spaCy format, adding paragraph type as a feature."""
    training_data = []
    for i, item in enumerate(dataset):
        text = item[1].lower()
        entities = []
        for entity in item[2]:
            start_idx = text.find(entity.lower())
            if start_idx != -1:
                end_idx = start_idx + len(entity)
                entity_label = "ORG" if entity == "Loft" else "PRODUCT"
                entities.append((start_idx, end_idx, entity_label))

        # Add paragraph information as metadata
        doc = nlp.make_doc(text)
        doc = add_paragraph_type(doc, paragraph_info[i])  # Assuming you have paragraph_info list

        training_data.append((doc.text, {"entities": entities, "paragraph_type": doc._.paragraph_type}))
    return training_data

def convert_to_spacy_format(dataset):
    training_data = []
    for item in dataset:
        text = item[1].lower()
        entities = []
        for entity in item[2]:
            entity_lower = entity.lower()
            start_idx = text.find(entity_lower)
            if start_idx != -1:
                end_idx = start_idx + len(entity)
                # You can map entity types based on your preference, here I'm using ORG for company names, PRODUCT for items.
                entity_label = "PRODUCT"
                entities.append((start_idx, end_idx, entity_label))
        training_data.append((text, {"entities": entities}))
    return training_data

def split_data(data, split_ratio=0.7):
    random.shuffle(data)
    split_index = int(len(data) * split_ratio)
    return data[:split_index], data[split_index:]

# def train_spacy_model(train_data, n_iter=20):
#
#     return nlp

def extract_entities(doc):
    """Helper function to extract entities from a spaCy Doc object."""
    return [(ent.start_char, ent.end_char, ent.label_) for ent in doc.ents]

def evaluate_ner_model(nlp, data):
    y_true = []
    y_pred = []

    for text, annotations in data:
        # Process the text through the NER model
        doc = nlp(text)
        predicted_ents = extract_entities(doc)
        true_ents = annotations['entities']

        # Create sets of entities for comparison
        true_entities_set = set(true_ents)
        predicted_entities_set = set(predicted_ents)

        # Calculate True Positives (TP), False Positives (FP), and False Negatives (FN)
        for entity in predicted_entities_set:
            if entity in true_entities_set:
                y_true.append(1)  # True positive
                y_pred.append(1)
            else:
                y_true.append(0)  # False positive
                y_pred.append(1)

        for entity in true_entities_set:
            if entity not in predicted_entities_set:
                y_true.append(1)  # False negative
                y_pred.append(0)

    # Calculate precision, recall, and F1 score
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, average='binary')
    recall = recall_score(y_true, y_pred, average='binary')
    f1 = f1_score(y_true, y_pred, average='binary')

    return accuracy, precision, recall, f1

def remove_misaligned_entities(nlp, data):
    aligned_data = []
    for text, annotations in data:
        doc = nlp.make_doc(text)
        entities = annotations["entities"]
        try:
            biluo_tags = offsets_to_biluo_tags(doc, entities)
            if '-' not in biluo_tags:  # Only keep aligned examples
                aligned_data.append((text, annotations))
        except Exception as e:
            print(f"Error processing text: {text}\nError: {e}")
    return aligned_data

n_iter = 1000

if __name__ == '__main__':
    with open('datasets/sentence-dataset.json', 'r') as f:
        data = json.load(f)

    data = [item for item in data if len(item[2]) < 2]

    training_data = convert_to_spacy_format(data)
    train_data, valid_data = split_data(training_data)

    # Create a blank spaCy model
    # spacy.require_gpu()
    nlp = spacy.blank("en")
    # nlp = spacy.load("en_core_web_trf")

    nlp.add_pipe("ner")
    aligned_train_data = remove_misaligned_entities(nlp, train_data)
    aligned_valid_data = remove_misaligned_entities(nlp, valid_data)
    print(len(aligned_train_data))

    with open('valid_data.json', 'w') as valid:
        json.dump(aligned_valid_data, valid, indent=1)

    # Create the NER pipeline component
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner")
    else:
        ner = nlp.get_pipe("ner")

    # Add the labels
    for _, annotations in aligned_train_data:
        for ent in annotations.get("entities"):
            ner.add_label(ent[2])

    # Disable other pipelines during training
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
    with nlp.disable_pipes(*other_pipes):  # Only train NER
        # optimizer = nlp.begin_training()
        optimizer = nlp.begin_training()
        decay_rate = 0.9
        # optimizer.learn_rate = 0.01
        # optimizer.clip_gradients(5.0)
        for itn in range(n_iter):
            random.shuffle(aligned_train_data)
            losses = {}
            if itn != 0 and itn % 40 == 0:
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
            if f1 > 0.9:
                break

            accuracy, precision, recall, f1 = evaluate_ner_model(nlp, aligned_train_data)
            print(
                f"Training after iteration {itn}: Accuracy={accuracy:.5f} Precision={precision:.5f},"
                f" Recall={recall:.5f}, F1-Score={f1:.5f}")


    # Train the model
    # ner_model = train_spacy_model(train_data, n_iter=50)
    nlp.to_disk("custom_ner_model_small_sentences")

    # Evaluate the NER model on the validation data
    # accuracy, precision, recall, f1 = evaluate_ner_model(nlp, aligned_valid_data)
    #
    # print(f"Accuracy: {accuracy:.2f}")
    # print(f"Precision: {precision:.2f}")
    # print(f"Recall: {recall:.2f}")
    # print(f"F1-Score: {f1:.2f}")



