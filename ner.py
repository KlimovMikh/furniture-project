import spacy, json, re

def clean_string(input_string):
    # Step 1: Remove Unicode characters of the form \u...
    # cleaned_string = re.sub(r'\\u[0-9a-fA-F]{4}', ' ', input_string)

    # cleaned_string = re.sub(r'\\\w+', '', input_string)

    # Step 2: Replace multiple spaces with a single space
    cleaned_string = re.sub(r'\s+', ' ', input_string)

    cleaned_string.replace(" | ", " ")
    # cleaned_string.replace("\u00d8", "")

    # Step 3: Strip leading and trailing spaces
    return cleaned_string.strip()

def extract_text(data):
    # Initialize a list to hold the transformed data
    transformed_data = []
    for item in data:
        # Check if the 'error' field is empty
        if item.get('error') == '':
            url = item.get('URL', '')
            content_parts = []

            title = item.get('title', '')
            if title:
                title = clean_string(title)
                content_parts.append('<title> ' + title + ' </title>')

            h1_headings = item.get('h1', [])
            if h1_headings:
                for h1 in h1_headings:
                    h1 = clean_string(h1)
                    content_parts.append('<h1> ' + h1 + ' </h1>')

            text_elements = item.get('text', [])
            for text in text_elements:
                tag = text.get('tag', '')

                tags = ["meta.description", "meta.twitter:description", "div", "li", "h2", "p", "nav", "h3"]
                # "h4", "h6", "h5", "dt", "option", "u", "ul", "bdi", "split-lines", "blockquote" #small
                # "figcaption"] #30 instances?

                if tag in tags:
                    content = text.get('content', '')
                    if tag and content:
                        content = clean_string(content)
                        content_parts.append('<' + tag + '> ' + content + ' </' + tag + '>')

            image_elements = item.get('images', [])
            if image_elements:
                for image in image_elements:
                    alt = image.get('alt', '')
                    if alt:
                        alt = clean_string(alt)
                        content_parts.append('<img> ' + alt + ' </img>')

            # Combine the content parts into a single string, separating each with two newlines
            content_str = '\n'.join(content_parts)

            # Append the transformed item to the list
            transformed_data.append({
                'URL': url,
                'content': content_str
            })

    # Convert the transformed data back into JSON format

    return transformed_data



if __name__ == "__main__":
    with open("valid_results.json", "r") as f:
        data = json.load(f)

    processed = extract_text(data)
    test_text = processed[0]["content"]
    nlp = spacy.load("custom_ner_model_transferred")
    doc = nlp(test_text)
    labels = []
    for ent in doc.ents:
        labels.append(ent.text)

    # Output final JSON to stdout
    print(json.dumps(labels))
