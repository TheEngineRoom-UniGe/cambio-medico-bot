import spacy
from nameparser import HumanName

# python -m spacy download it_core_news_md
nlp = spacy.load("it_core_news_md")

def get_name_surname(phrase):
    if len(phrase.split(' ')) == 1:
        names = [{'nome': '', 'cognome': phrase}]
    else:
        doc = nlp(phrase)
        names = [e.text for e in doc.ents if e.label_ == 'PER']
        names = [HumanName(name) for name in names]
        names = [{'nome': name.first, 'cognome': name.last} for name in names]
    return names