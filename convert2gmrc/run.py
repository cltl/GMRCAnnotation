from glob import glob
import argparse
from joblib import Parallel, delayed
import shutil
import json
from sklearn.cluster import AgglomerativeClustering
import random
import pickle
import numpy as np
import av
from tqdm import tqdm
import cv2
import os
import coolname
import uuid
import shutil
DATABASE_DIR = './Datasets'
EXAMPLE_DIR = '../example_data'
DET_THRESHOLD = 0.90
COS_THRESHOLD = 0.80
INTERVAL_SEC = 2


def batch_paths(list_of_elements, n_jobs):
    batch_size = len(list_of_elements) // n_jobs
    batched = [
        list_of_elements[i*batch_size: (i+1)*batch_size] for i in range(n_jobs)]

    batched[-1] += list_of_elements[batch_size*n_jobs:]

    assert sorted(list_of_elements) == sorted(
        [bar for foo in batched for bar in foo])

    return batched


def loadN(path, interval_sec):
    """Load every Nth frame from the original video."""
    try:
        container = av.open(path)
    except (av.error.InvalidDataError, av.error.FileNotFoundError) as e:
        print(e)
        return None, None, None
    frames = {}
    fps = round(float(container.streams.video[0].average_rate))
    every_N = int(fps*interval_sec)

    for idx, frame in enumerate(container.decode(video=0)):
        if idx % every_N != 0:
            continue
        numpy_RGB = np.array(frame.to_image())
        frames[idx] = numpy_RGB
    container.close()
    duration_msec = (idx + 1) / fps * 1000

    return frames, duration_msec, fps


def get_existing_path(DATABASE_DIR, DATABASE, modality, DATASET, uttid,
                      extensions):
    candidates = [os.path.join(DATABASE_DIR, DATABASE, modality,
                               DATASET, uttid + extension)
                  for extension in extensions]

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def get_unique_faces(embeddings):

    if len(embeddings) == 1:
        labels_clustered = np.array([0])

    elif len(embeddings) == 0:
        return None

    else:
        ac = AgglomerativeClustering(n_clusters=None,
                                     affinity='cosine',
                                     linkage='average',
                                     distance_threshold=COS_THRESHOLD)

        clustering = ac.fit(embeddings)
        labels_clustered = clustering.labels_

    labels_unique = np.unique(labels_clustered)
    while True:
        names_unique = [coolname.generate_slug(2) for _ in labels_unique]
        if len(labels_unique) == len(names_unique):
            break

    label2name = {lbl: nm for lbl, nm in zip(labels_unique, names_unique)}
    face_names = [label2name[lbl] for lbl in labels_clustered]

    return face_names


class DataBase():
    def __init__(self, DATABASE_DIR, DATABASE):
        with open(os.path.join(DATABASE_DIR, DATABASE,
                               'labels.json'), 'r') as stream:
            self.labels = json.load(stream)

        self.DATABASE = DATABASE
        self.DATASETS = list(self.labels.keys())

        utterance_ordered_path = os.path.join(DATABASE_DIR, self.DATABASE,
                                              'utterance-ordered.json')

        if os.path.isfile(utterance_ordered_path):
            with open(utterance_ordered_path, 'r') as stream:
                self.diauttids = json.load(stream)
        else:
            self.diauttids = {DATASET: {uttid: [uttid]
                                        for uttid, label in uttid_label.items()}
                              for DATASET, uttid_label in self.labels.items()}

        self.videopaths = {DATASET:
                           {uttid: get_existing_path(
                               DATABASE_DIR, self.DATABASE, 'raw-videos',
                               DATASET, uttid, ['.mp4', '.avi'])
                               for diaid, uttids in diauttid.items()
                               for uttid in uttids}
                           for DATASET, diauttid in self.diauttids.items()}

        self.facepaths = {DATASET:
                          {uttid: get_existing_path(
                              DATABASE_DIR, self.DATABASE, 'faces',
                              DATASET, uttid, ['.pkl'])
                           for diaid, uttids in diauttid.items()
                           for uttid in uttids}
                          for DATASET, diauttid in self.diauttids.items()}

        self.audiopaths = {DATASET:
                           {uttid: get_existing_path(
                               DATABASE_DIR, self.DATABASE, 'raw-audios',
                               DATASET, uttid, ['.wav', '.mp3'])
                               for diaid, uttids in diauttid.items()
                               for uttid in uttids}
                           for DATASET, diauttid in self.diauttids.items()}

        self.textpaths = {DATASET:
                          {uttid: get_existing_path(
                              DATABASE_DIR, self.DATABASE, 'raw-texts',
                              DATASET, uttid, ['.json'])
                           for diaid, uttids in diauttid.items()
                           for uttid in uttids}
                          for DATASET, diauttid in self.diauttids.items()}

    def process_dia(self, DATASET, diaid, interval_sec=INTERVAL_SEC):
        """Dialogue (session) level.

        Note that a dialogue (session) contains at least one utterance.

        """
        self.chat_gmrc = []
        self.image_gmrc = []

        self.face_recognition_dia(DATASET, diaid, interval_sec)

        starttime_msec = 0
        for uttid in self.diauttids[DATASET][diaid]:

            self.load_images_utt(DATASET, uttid, interval_sec)
            emotion = self.load_labeled_emotion(DATASET, uttid)
            if self.faces is not None:
                self.annotate_write_frames(
                    starttime_msec, DATASET, diaid, uttid, emotion)

            self.load_text(DATASET, uttid)
            if self.text is not None:
                self.chat_gmrc.append(
                    [self.text['Speaker'], self.text['Utterance'],
                     starttime_msec])

            # in case loading the video was not successful, we just add one
            # second (1000ms).
            if self.duration_msec is None:
                self.duration_msec = 1000

            starttime_msec += self.duration_msec

        if len(self.image_gmrc) != 0:
            self.write_image_gmrc(EXAMPLE_DIR, DATASET, diaid)

        if len(self.chat_gmrc) != 0:
            self.write_chat_gmrc(EXAMPLE_DIR, DATASET, diaid)

    def annotate_write_frames(self, starttime_msec, DATASET, diaid, uttid,
                              emotion):
        for idx, frame in self.frames.items():
            frame_time = int(starttime_msec + round(idx*1000/self.fps))
            numpy_BGR = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            os.makedirs(os.path.join(
                EXAMPLE_DIR, self.DATABASE, DATASET, diaid, 'image'),
                exist_ok=True)
            save_path = os.path.join(
                EXAMPLE_DIR, self.DATABASE, DATASET, diaid,
                'image', uttid + f'_frame{str(idx)}_{str(frame_time)}.jpg')
            cv2.imwrite(save_path, numpy_BGR)

            frame_info = {}
            frame_info['files'] = [os.path.join(
                'image', os.path.basename(save_path))]
            container_id = str(uuid.uuid4())
            frame_info['id'] = container_id
            frame_info['mentions'] = []

            frame_info['modality'] = 'image'
            frame_info['ruler'] = {'bounds': [0, 0, numpy_BGR.shape[1],
                                              numpy_BGR.shape[0]],
                                   'container_id': container_id,
                                   'type': 'MultiIndex'}
            frame_info['time'] = {'container_id': container_id,
                                  'start': frame_time,
                                  'end': frame_time + round(1000/self.fps),
                                  'type': 'TemporalRuler'}
            frame_info['type'] = 'ImageSignal'

            for k, feat in enumerate(self.faces[idx]):
                # age / gender estimation is too poor.
                age = feat['age']
                gender = 'male' if feat['gender'] == 1 else 'female'
                bbox = [int(num) for num in feat['bbox'].tolist()]
                faceprob = round(feat['det_score'], 3)
                name = self.face_names_dia[uttid][idx][k]

                annotations = []
                if k == 0:
                    annotations.append({'source': 'human',
                                        'timestamp': frame_time,
                                        'type': 'emotion',
                                        'value': emotion})

                annotations.append({'source': 'machine',
                                    'timestamp': frame_time,
                                    'type': 'person',
                                    'value': {'name': name,
                                              'age': age,
                                              'gender': gender,
                                              'faceprob': faceprob}})

                mention_id = str(uuid.uuid4())
                segment = [{'bounds': bbox,
                            'container_id': container_id,
                            'type': 'MultiIndex'}]
                frame_info['mentions'].append({'annotations': annotations,
                                               'id': mention_id,
                                               'segment': segment})
            self.image_gmrc.append(frame_info)

    def write_image_gmrc(self, SAVE_AT, DATASET, diaid):
        os.makedirs(os.path.join(
            SAVE_AT, self.DATABASE, DATASET, diaid, 'image'), exist_ok=True)

        with open(os.path.join(SAVE_AT, self.DATABASE, DATASET, diaid,
                               'image.json'), 'w') as stream:
            json.dump(self.image_gmrc, stream)

    def write_chat_gmrc(self, SAVE_AT, DATASET, diaid):
        os.makedirs(os.path.join(SAVE_AT, self.DATABASE, DATASET, diaid, 'text'),
                    exist_ok=True)
        with open(os.path.join(SAVE_AT, self.DATABASE, DATASET,
                               diaid, 'text', f"{diaid}.csv"), 'w') as stream:
            stream.write('speaker,utterance,time\n')

            for line in self.chat_gmrc:
                speaker, utterance, starttime_msec = line
                stream.write(speaker)
                stream.write(',')
                stream.write(f"\"{utterance}\"")
                stream.write(',')
                stream.write(str(starttime_msec))
                stream.write('\n')

    def face_recognition_dia(self, DATASET, diaid, interval_sec):
        embs_dia = {}
        for uttid in self.diauttids[DATASET][diaid]:
            videopath = self.videopaths[DATASET][uttid]
            facepath = self.facepaths[DATASET][uttid]

            frames, duration_msec, fps = loadN(videopath, interval_sec)

            if frames is None:
                continue

            with open(facepath, 'rb') as stream:
                faces = pickle.load(stream)
            faces = {idx: faces[idx] for idx in list(frames.keys())}

            embs_utt = {idx: [fc['normed_embedding']
                              for fc in face if fc['det_score'] > DET_THRESHOLD]
                        for idx, face in faces.items()}
            embs_dia[uttid] = embs_utt

        embs_unpacked = [emb for uttid, embs_utt in embs_dia.items()
                         for idx, embs in embs_utt.items() for emb in embs]
        unique_faces = get_unique_faces(embs_unpacked)

        count = 0
        self.face_names_dia = {}
        for uttid, embs_utt in embs_dia.items():
            self.face_names_dia[uttid] = {}
            for idx, embs in embs_utt.items():
                self.face_names_dia[uttid][idx] = []
                for emb in embs:
                    self.face_names_dia[uttid][idx].append(unique_faces[count])
                    count += 1

    def load_images_utt(self, DATASET, uttid, interval_sec):
        """Utterance level. This is the most atomic level."""
        videopath = self.videopaths[DATASET][uttid]
        self.frames, self.duration_msec, self.fps = None, None, None
        if videopath is not None:
            self.frames, self.duration_msec, self.fps = loadN(
                videopath, interval_sec)

        self.faces = None
        if self.frames is not None:
            facepath = self.facepaths[DATASET][uttid]
            if videopath is not None and facepath is not None:
                with open(facepath, 'rb') as stream:
                    faces = pickle.load(stream)
                self.faces = {idx: faces[idx]
                              for idx in list(self.frames.keys())}
                assert len(self.frames) == len(self.faces)

                self.faces = {idx: [fc for fc in face if fc['det_score']
                                    > DET_THRESHOLD]
                              for idx, face in self.faces.items()}

    def load_labeled_emotion(self, DATASET, uttid):
        """Utterance level. This is the most atomic level."""
        label = self.labels[DATASET][uttid]

        return label

    def load_text(self, DATASET, uttid):
        """Utterance level. This is the most atomic level."""
        textpath = self.textpaths[DATASET][uttid]
        self.text = None
        if textpath is not None:
            with open(textpath, 'r') as stream:
                self.text = json.load(stream)

    def load_audio(self, DATASET, uttid):
        """Utterance level. This is the most atomic level."""
        raise NotImplementedError("TODO!")


def run(DATASET, diaids, db):
    for diaid in tqdm(diaids):
        db.process_dia(DATASET, diaid)


parser = argparse.ArgumentParser(description='run.py')
parser.add_argument('--num-jobs', default=1, help='number of jobs')
args = parser.parse_args()
n_jobs = int(args.num_jobs)
print(f"n_jobs: {n_jobs}")

DATABASES = glob(os.path.join(DATABASE_DIR, '*/labels.json'))
DATABASES = [DB.split('/')[-2] for DB in DATABASES]
print(f"In total there are {len(DATABASES)} datasets found: {DATABASES}")

for DATABASE in tqdm(DATABASES):
    db = DataBase(DATABASE_DIR, DATABASE)

    for DATASET in tqdm(db.DATASETS):
        diaids = [diaid for diaid in list(db.diauttids[DATASET].keys())]
        random.shuffle(diaids)

        n_jobs_ = min(len(diaids), n_jobs)

        diaids_batched = batch_paths(diaids, n_jobs_)

        dbs = [DataBase(DATABASE_DIR, DATABASE) for i in range(n_jobs_)]
        Parallel(n_jobs=n_jobs_)(delayed(run)(DATASET, diaids, db)
                                 for diaids, db
                                 in tqdm(zip(diaids_batched, dbs)))

    shutil.rmtree(os.path.join(DATABASE_DIR, DATABASE), ignore_errors=True)
