import re, json, random

# Example text
text = """
<tag_name>This is the first sentence in the first tag! Here is another sentence?</tag_name>
<tag_name>Another tag, with more text. And yet another sentence!</tag_name>
<tag_name>More content in a different tag. Is this the last sentence?</tag_name>
"""


def extract_sentences_by_tag(text):
    pattern = r"<(?P<tag>\w+)>(?P<content>.*?)<\/\1>"
    matches = re.finditer(pattern, text, re.DOTALL)
    extracted_data = []

    for match in matches:
        tag = match.group('tag')
        content = match.group('content').strip()
        sentences = [sentence.strip() for sentence in content.split('\n') if sentence.strip()]
        extracted_data.append({
            'tag': tag,
            'sentences': sentences
        })
        # if tag == 'img':
        #     print(sentences)

    return extracted_data


def filter_sentences(data, entities):
    # Iterate over each entity
    result = []
    check = set()

    # index = 0

    for entity in entities:
        entity_lower = entity.lower()
        for item in data:
            filtered_sentences = []
            # Collect all sentences that contain the entity (case-insensitive)
            entity_sentences = [sentence for sentence in item['sentences'] if entity_lower in sentence.lower()]

            # print(len(entity_sentences))

            if entity_sentences:
                # Keep the first sentence with the entity
                for i in range(len(entity_sentences)):
                    if len(entity_sentences[i]) < 512:
                        if entity_sentences[i] not in check:
                            check.add(entity_sentences[i])
                            filtered_sentences.append(entity_sentences[i])
                            # index += 1
                            break

                if len(filtered_sentences) > 0:
                    result.append({'tag' : item['tag'], 'sentences' : filtered_sentences})

        # if len(result) < 4:
        #     index = 4 - len(result)
        #     random_add = []
        #     for item in data:
        #         for sentence in item['sentences']:
        #             if 512 > len(sentence) > 4 and sentence not in check and item['tag'] != 'img':
        #                 random_add.append({'tag' : item['tag'], 'sentences' : [sentence]})
        #
        #                 index -= 1
        #                 if index <= 0:
        #                     break
        #         if index <= 0:
        #             break
        #     # print(random_add)
        #     result.extend(random_add)
    return result

def checker(data, entities):
    check = False
    for entity in entities:
        entity_lower = entity.lower()
        for item in data:
            for sentence in item['sentences']:
                if entity_lower in sentence.lower():
                    check = True
                    break
            if check: break
        if not check:
            print(entity)
    return not check






if __name__ == "__main__":

    num_sentences_to_extract = 2
    with open('united-dataset.json', 'r') as input_file:
        data = json.load(input_file)

    result = []
    for item in data:
        paragraphs = []
        extracted = extract_sentences_by_tag(item[1])
        entities = item[2]
        filtered = filter_sentences(extracted, entities)


        for content in filtered:
            paragraphs.append("<" + content['tag'] + "> " + " ".join(content['sentences']) + " </" + content['tag'] + ">")

        result.append([item[0], "\n".join(paragraphs), entities])

    with open('dirtyhook.json', 'r') as dirty:
        hook = json.load(dirty)

    for url, text in hook.items():
        for item in result:
            if item[0] == url:
                item[1] = text


    with open('sentence-dataset.json', 'w') as output_file:
        json.dump(result, output_file, indent=1)









    # Regular expression to match content inside <tag_name>...</tag_name>





# if __name__ == '__main__':
#     # Example usage: Extract 2 sentences for each entity from each tag
#     num_sentences_to_extract = 2
#     with open('united-dataset.json', 'r') as input_file:
#         data = json.load(input_file)
#
#     for temp in data:
#         print(extract_sentences_for_entities(temp[1], temp[2], num_sentences_to_extract))




    # with open('sentence-dataset.json', 'w') as output_file:
    #     json.dump(result, output_file, indent=1)



# # Iterate through the tags and their content
#     for tag, content in matches:
#         # Adjusted regular expression to account for . ! ? and <
#         sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!|<)\s', content)
#         for entity in entities:
#             # Find sentences that contain the entity
#             matching_sentences = []
#             for sentence in sentences:
#                 if len(sentence) < 512:
#                     if entity in sentence:
#                         if sentence.strip() not in check:
#                             matching_sentences.append(sentence)
#                             check.add(sentence.strip())
#                             # tags.add(tag)
#
#             # Limit the number of sentences to the given number
#             limited_sentences = matching_sentences[:num_sentences]
#
#             # Store the sentences under the corresponding entity for this tag
#             if limited_sentences:
#                 tag_entity_sentences[tag] = "<"+tag+">"+" ".join(limited_sentences)+"</"+tag+">"