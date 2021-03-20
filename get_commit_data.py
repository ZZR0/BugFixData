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

def process_data(chunks, labels):

    process_chunk, process_label, int_label = [], [], []

    for chunk, label in zip(chunks, labels):
        chunk = clean_sentence(chunk.strip())

        if chunk:
            process_chunk.append(chunk + '\n')
            process_label.append(label + '\n')
            int_label.append(label.split('----')[0] + '\n')

    with open('bugfix/project/code.original_subtoken', 'w', encoding='utf-8') as f:
        f.writelines(process_chunk)
    with open('bugfix/project/javadoc.original', 'w', encoding='utf-8') as f:
        f.writelines(process_label)
    with open('bugfix/project/labels', 'w', encoding='utf-8') as f:
        f.writelines(int_label)

def check_annotation(sentence):
    sentence = sentence.strip().strip('\t').strip(' ')
    if sentence.startswith('//') or sentence.startswith('/*') or sentence.startswith('*/') or sentence.startswith('*'):
        return True

    return False

if __name__ == '__main__':
    all_chunks = [] # [chunk[line]]
    all_labels = []
    for project, after, before in zip(projects, afters, befores):
        pjdb = client[project]
        ppcommits_db = pjdb['preprocess_commit']
        after = datetime.datetime.strptime(after,"%Y-%m-%d").timestamp()
        before = datetime.datetime.strptime(before,"%Y-%m-%d").timestamp()
        ppcommits_db.create_index('commit_date')

        ppcommits = list(ppcommits_db.find({"commit_date": {'$gte': after, '$lte': before}, 
                                            "median_issue": 0}).sort([('commit_date',1)]))
        idx = int(len(ppcommits) * 0.8)
        ppcommits = ppcommits[idx:]

        for commit in tqdm(ppcommits):
            commit_id = commit['_id']
            label = 1 if commit['bug_count'] > 0 else 0
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
                        chunk = [code[1] for code in chunk]
                        new_chunk = []
                        for code in chunk:
                            if check_annotation(code): continue
                            new_chunk.append(code)
                        if new_chunk:
                            all_chunks.append(new_chunk)
                            all_labels.append('{}----{}----{}'.format(label, project, commit_id))
                        chunk = [(line, code)]

        chunks_list = chunk2list(all_chunks)
        process_data(chunks_list, all_labels)
    
    # os.system("scp bugfix/project/* cg@10.20.83.122:/data2/cg/BugFixData/bugfix/project/")
    # os.system("scp bugfix/project/* cg@10.20.83.122:/data2/cg/NeuralCodeSum/data/bugfix/project/")
    os.system("scp bugfix/project/* cg@10.20.83.122:/data2/cg/deep-code-search/data/bugfix/commit/")