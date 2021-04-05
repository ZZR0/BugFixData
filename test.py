# chunk_list = []
# chunk = []
# line = ' DCNL '.join(chunk)
# chunk_list.append(line + '\n')
# print(chunk_list)


# import decamelize

# print(decamelize.convert("camel_case"))


# print('asd12 3 .'.isascii())
import pickle

def check_pkl(file):
    with open(file, 'rb') as f:
        data = pickle.load(f)
    return data

check_pkl('./bugfix/commit/commits.pkl')