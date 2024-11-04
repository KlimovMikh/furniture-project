import spacy, json

if __name__ == '__main__':
    nlp = spacy.load("backup_models/custom_ner_model_transferred")

    # with open('datasets/united-dataset.json') as json_file:
    #     dataset = json.load(json_file)

    with open('datasets/united-dataset.json') as dataset_file:
        dataset = json.load(dataset_file)

    dataset = [item for item in dataset if len(item[2]) < 2]





    # data_dict = {item[0]: item[1:] for item in check}
    # data = dataset['https://loft-theme-demo-nashville.myshopify.com/products/black-chair']

    predictions = []

    for data in dataset:
        url = data[0]
        test_text = data[1]
        correct = data[2]

        doc = nlp(test_text)

        labels = []

        for ent in doc.ents:
            labels.append(ent.text)

        # if labels != correct:
        predictions.append({'url' : url, 'correct' : correct, 'predictions' : labels})

        # print(url, '\n')
        # for ent in doc.ents:
        #     print(ent.text, ent.label_)

    with open("predict.json", "w") as outfile:
        json.dump(predictions, outfile, indent=1)