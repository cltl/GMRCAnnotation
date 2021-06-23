from typing import Iterable

import logging
import spacy
import time
import uuid

from emissor.persistence import ScenarioStorage
from emissor.processing.api import SignalProcessor
from emissor.representation.annotation import AnnotationType, Token, NER
from emissor.representation.container import Index, AtomicRuler
from emissor.representation.scenario import Modality, TextSignal, Mention, Annotation, Scenario, Signal

logger = logging.getLogger(__name__)


nlp = spacy.load('en_core_web_sm')


SPACY_ID = "SpaCY"


class MMSRMeldNERProcessor(SignalProcessor):
    def process(self, scenario: Scenario, modality: Modality, signals: Iterable[Signal], storage: ScenarioStorage):
        if modality is not Modality.TEXT:
            return

        logger.info("Add tokenization and NER annotations to %s", scenario.id)
        for signal in signals:
            # TODO: check if annotations already exist
            self.add_ner_annotation(signal)

        storage.save_signals(scenario.id, Modality.TEXT, signals)

    def add_ner_annotation(self, signal: TextSignal):
        utterance = ''.join(signal.seq)

        doc = nlp(utterance)

        offsets, tokens = zip(*[(Index(signal.id, token.idx, token.idx+len(token)), Token.for_string(token.text))
                                for token in doc])

        ents = [NER.for_string(ent.label_) for ent in doc.ents]
        entity_text = [ent.text for ent in doc.ents]
        segments = [token.ruler for token in tokens if token.value in entity_text]

        annotations = [Annotation(AnnotationType.TOKEN.name.lower(), token, SPACY_ID, int(time.time()))
                       for token in tokens]
        ner_annotations = [Annotation(AnnotationType.NER.name.lower(), ent, SPACY_ID, int(time.time()))
                           for ent in ents]

        signal.mentions.extend([Mention(str(uuid.uuid4()), [offset], [annotation])
                                for offset, annotation in zip(offsets, annotations)])
        signal.mentions.extend([Mention(str(uuid.uuid4()), [segment], [annotation])
                                for segment, annotation in zip(segments, ner_annotations)])

        return signal