import json
from collections import defaultdict

from IPython.terminal.shortcuts.auto_suggest import accept


def count_entities(text, entities):
    count = 0
    for entity in entities:
        count += text.lower().count(entity.lower())  # case-insensitive count
    return count


# tags = ["meta.description", "meta.twitter:description", "div", "li", "h2", "p", "nav", "h3",
#                         "h4", "h6", "h5", "dt", "option", "u", "ul", "bdi", "split-lines", "blockquote" #small
#                         "figcaption"] #30 instances?


if __name__ == '__main__':
    with open('united-dataset.json', 'r') as dataset:
        first_json = json.load(dataset)

    with open('valid_results.json', 'r') as statistics:
        tags = json.load(statistics)

    good = ["meta.description", "meta.twitter:description", "div", "li", "h2", "p", "nav", "h3"]

    stats = {}
    url_to_data = {item["URL"]: item for item in tags}
    for entry in first_json:
        accept = 0
        decline = 0
        alter = 0
        url, sample_text, entities = entry
        check = entities
        if url in url_to_data:
            data = url_to_data[url]
            for entity in entities:
                if count_entities(data.get('title', ''), [entity]):
                    if entity in check: check.remove(entity)

            for entity in entities:
                if data.get('h1', []):
                    for h1_text in data.get('h1', []):
                         if count_entities(h1_text, [entity]):
                             if entity in check: check.remove(entity)

            for text_item in data.get('text', []):
                tag = text_item.get('tag')
                if tag in good:
                    for entity in entities:
                        if count_entities(text_item.get('content', ''), [entity]):
                            if entity in check: check.remove(entity)


            if data.get('images', []):
                for image in data.get('images', []):
                    if image['alt']:
                        for entity in entities:
                            if count_entities(image.get('alt', ''), [entity]):
                                if entity in check: check.remove(entity)

            if len(check) != 0:
                stats[url] = check

    with open('statistics.json', 'w') as s:
        json.dump(stats, s ,indent=1)
    # print(json.dumps(stats, indent=1))