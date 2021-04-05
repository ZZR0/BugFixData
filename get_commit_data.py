import pymongo
from tqdm import tqdm
import datetime
import decamelize
import os
import pickle

projects = ['jdt', 'platform', 'gerrit']
afters = ['2014-01-01', '2016-01-01', '2016-01-01']
befores = ['2017-01-01', '2019-01-01', '2019-01-01']

client = pymongo.MongoClient("mongodb://localhost:27017/")

def chunk2list(all_chunks):
    # one_chunks: [chunk [line] ]
    chunk_list = []
    for chunk in all_chunks:
        line = str(chunk)
        chunk_list.append(line + '\n')
    
    return chunk_list

def chunk2str(chunk):
    # chunk: [line] 
    return ' DCNL '.join(chunk)

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

def process_data(chunks):

    process_chunk = []

    for chunk in chunks:
        code = chunk['code']
        code = clean_sentence(code)

        if code:
            process_chunk.append(chunk)

    with open('bugfix/commit/commits.pkl', 'wb') as f:
        pickle.dump(process_chunk, f)


def check_annotation(sentence):
    sentence = sentence.strip().strip('\t').strip(' ')
    if sentence.startswith('//') or sentence.startswith('/*') or sentence.startswith('*/') or sentence.startswith('*'):
        return True

    return False

def process_commits(ppcommits):
    all_chunks = []
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
                    new_chunk = []
                    for chunk_code in chunk:
                        if check_annotation(chunk_code[1]): continue
                        new_chunk.append(chunk_code)
                    if new_chunk:
                        start_line = new_chunk[0][0] if new_chunk else -1
                        end_line = new_chunk[-1][0] if new_chunk else -1
                        new_chunk = [c[1] for c in new_chunk]
                        new_chunk = chunk2str(new_chunk)
                        all_chunks.append({'_id': commit_id,
                                           'project': project,
                                           'label': label,
                                           'file': file_name,
                                           'start_line': start_line,
                                           'end_line': end_line,
                                           'code': new_chunk
                                           })

                    chunk = [(line, code)]
    
    return all_chunks

if __name__ == '__main__':
    all_chunks = [] # [chunk[line]]

    for project, after, before in zip(projects, afters, befores):
        pjdb = client[project]
        ppcommits_db = pjdb['preprocess_commit']
        after = datetime.datetime.strptime(after,"%Y-%m-%d").timestamp()
        before = datetime.datetime.strptime(before,"%Y-%m-%d").timestamp()
        ppcommits_db.create_index('commit_date')

        ppcommits = list(ppcommits_db.find({"commit_date": {'$gte': after, '$lte': before}, 
                                            "median_issue": 0}).sort([('commit_date',1)]))

        chunks = process_commits(ppcommits)
        all_chunks.extend(chunks)

    process_data(all_chunks)
    
    os.system("scp -r bugfix/commit/* cg@10.20.83.122:/data2/cg/deep-code-search/data/bugfix/commit/")