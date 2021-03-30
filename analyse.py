import os
import pickle

import pymongo
import json


client = pymongo.MongoClient("mongodb://localhost:27017/")


def update_large_elem(db, elem):
    try:
        result = db.update(
            {'_id': elem['_id']}, elem, check_keys=False, upsert=True)
    except:
        # DocumentTooLarge
        result = db.delete_many({'_id': elem['_id']})
            
    return result


def update_commit(commit):
    _id = commit['_id']
    project = commit['project']

    for chunk in commit['chunks']:
        sims = []
        for sim in chunk['sims']:
            value = float(sim[1])
            sim = json.loads(sim[0].strip().replace("'", '"'))
            sim['value'] = value
            sims.append(sim)
        chunk['sims'] = sims

    pjdb = client[project]
    simdb = pjdb['sim_feature']
    
    update_large_elem(simdb, commit)

def main():
    # cmd = 'scp cg@10.20.83.122:/data2/cg/deep-code-search/data/bugfix/commit/{}/commits.pkl bugfix/project/{}/'
    # os.system(cmd.format('train', 'train'))
    # os.system(cmd.format('test', 'test'))

    with open('./bugfix/project/train/commits.pkl', 'rb') as f:
        commits = pickle.load(f)
    
    for commit in commits.items():
        commit = commit[1]
        update_commit(commit)

    with open('./bugfix/project/test/commits.pkl', 'rb') as f:
        commits = pickle.load(f)
    
    for commit in commits.items():
        commit = commit[1]
        update_commit(commit)


if __name__ == "__main__":
    main()