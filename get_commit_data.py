import pymongo
from tqdm import tqdm
import datetime
import decamelize
import os

projects = ['jdt', 'platform', 'gerrit']
afters = ['2014-01-01', '2016-01-01', '2016-01-01']
befores = ['2017-01-01', '2019-01-01', '2019-01-01']

client = pymongo.MongoClient("mongodb://localhost:27017/")

def chunk2list(all_chunks):
    # one_chunks: [chunk [line] ]
    chunk_list = []
    for chunk in all_chunks:
        line = ' DCNL '.join(chunk)
        chunk_list.append(line + '\n')
    
    return chunk_list

def split_sentence(sentence):
    sentence = sentence.replace('.', ' . ').replace('_', ' ').replace('@', ' @ ')\
        .replace('-', ' - ').replace('~', ' ~ ').replace('%', ' % ').replace('^', ' ^ ')\
        .replace('&', ' & ').replace('*', ' * ').replace('(', ' ( ').replace(')', ' ) ')\
        .replace('+', ' + ').replace('=', ' = ').replace('{', ' { ').replace('}', ' } ')\
        .replace('|', ' | ').replace('\\', ' \ ').replace('[', ' [ ').replace(']', ' ] ')\
        .replace(':', ' : ').replace(';', ' ; ').replace(',', ' , ').replace('<', ' < ')\
        .replace('>', ' > ').replace('?', ' ? ').replace('/', ' / ')
    sentence = ' '.join(sentence.split())
    return sentence

def clean_sentence(sentence):
    if not sentence.isascii(): return ''
    sentence = split_sentence(sentence)
    sentence = sentence.split()
    sentence = [decamelize.convert(word) for word in sentence]
    sentence = ' '.join(sentence)
    sentence = sentence.replace('_', ' ')
    return sentence

def get_one(db, query):
    for elem in db.find(query):
        return elem
    return None

def process_data(chunks, labels, features, pref='train'):

    process_chunk, process_label, process_feature, int_label = [], [], [], []

    for chunk, label, feature in zip(chunks, labels, features):
        chunk = clean_sentence(chunk.strip())
        feature = list(map(str, feature))

        if chunk:
            process_chunk.append(chunk + '\n')
            process_label.append(label + '\n')
            process_feature.append(' '.join(feature) + '\n')
            int_label.append(label.split('----')[0] + '\n')

    with open('bugfix/project/{}/code.original_subtoken'.format(pref), 'w', encoding='utf-8') as f:
        f.writelines(process_chunk)
    with open('bugfix/project/{}/javadoc.original'.format(pref), 'w', encoding='utf-8') as f:
        f.writelines(process_label)
    with open('bugfix/project/{}/labels'.format(pref), 'w', encoding='utf-8') as f:
        f.writelines(int_label)
    with open('bugfix/project/{}/features.txt'.format(pref), 'w', encoding='utf-8') as f:
        f.writelines(process_feature)

def check_annotation(sentence):
    sentence = sentence.strip().strip('\t').strip(' ')
    if sentence.startswith('//') or sentence.startswith('/*') or sentence.startswith('*/') or sentence.startswith('*'):
        return True

    return False

def process_commits(ppcommits, k_feature_db):
    all_chunks, all_labels, all_features = [], [], []
    for commit in tqdm(ppcommits):
        commit_id = commit['_id']
        label = 1 if commit['bug_count'] > 0 else 0
        k_feature = get_one(k_feature_db, {'_id':commit_id})
        k_feature = [feature[1] for feature in k_feature.items()]
        for diff in commit['files_diff'].items():
            chunk = []
            file_name = diff[0]
            file_diff = diff[1]['b']
            for elem in file_diff.items():
                line = elem[0]
                code = elem[1]['code']
                if len(chunk) == 0 or int(chunk[-1][0]) == int(line)-1:
                    chunk.append((line, code))
                else:
                    new_chunk = []
                    for chunk_code in chunk:
                        if check_annotation(chunk_code[1]): continue
                        new_chunk.append(chunk_code)
                    if new_chunk:
                        line_num = new_chunk[0][0] if new_chunk else -1
                        new_chunk = [c[1] for c in new_chunk]
                        all_chunks.append(new_chunk)
                        all_labels.append('{}----{}----{}----{}----{}'.format(label, project, commit_id, file_name, line_num))
                        all_features.append(k_feature)
                        assert k_feature[0] == commit_id
                    chunk = [(line, code)]
    
    assert len(all_chunks) == len(all_labels) and len(all_chunks) == len(all_features)
    return all_chunks, all_labels, all_features

if __name__ == '__main__':
    train_chunks, test_chunks = [], [] # [chunk[line]]
    train_labels, test_labels = [], []
    train_features, test_features = [], []

    for project, after, before in zip(projects, afters, befores):
        pjdb = client[project]
        ppcommits_db = pjdb['preprocess_commit']
        k_feature_db = pjdb['k_feature']
        after = datetime.datetime.strptime(after,"%Y-%m-%d").timestamp()
        before = datetime.datetime.strptime(before,"%Y-%m-%d").timestamp()
        ppcommits_db.create_index('commit_date')

        ppcommits = list(ppcommits_db.find({"commit_date": {'$gte': after, '$lte': before}, 
                                            "median_issue": 0}).sort([('commit_date',1)]))
        idx = int(len(ppcommits) * 0.8)

        chunks, labels, features = process_commits(ppcommits[:idx], k_feature_db)
        train_chunks.extend(chunks)
        train_labels.extend(labels)
        train_features.extend(features)

        chunks, labels, features = process_commits(ppcommits[idx:], k_feature_db)
        test_chunks.extend(chunks)
        test_labels.extend(labels)
        test_features.extend(features)

    chunks_list = chunk2list(test_chunks)
    process_data(chunks_list, test_labels, test_features, pref='test')

    chunks_list = chunk2list(train_chunks)
    process_data(chunks_list, train_labels, train_features, pref='train')
    
    # os.system("scp bugfix/project/* cg@10.20.83.122:/data2/cg/BugFixData/bugfix/project/")
    # os.system("scp bugfix/project/* cg@10.20.83.122:/data2/cg/NeuralCodeSum/data/bugfix/project/")

    os.system("scp -r bugfix/project/* cg@10.20.83.122:/data2/cg/deep-code-search/data/bugfix/commit/")