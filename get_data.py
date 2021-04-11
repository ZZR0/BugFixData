import subprocess
import os
import line_parser
from aggregator import aggregator
from tqdm import tqdm
import decamelize
import random
from astree import *

random.seed(2021)
diff_cmd = 'git diff {} {}'

def exec(cmd):
    pip = os.popen(cmd)
    output = pip.buffer.read().decode(encoding='utf8', errors="ignore")
    output = output.strip('\n').split('\n') if output else []
    return output

def split_diff_log(file_diff_log):
    files_log, file_log = [], []
    for line in file_diff_log:
        if line[:10] == 'diff --git':
            if file_log:
                files_log.append(file_log)
                file_log = []

        file_log.append(line)

    if file_log:
        files_log.append(file_log) 
    
    return files_log

def get_diff_chunk(bug_file, fix_file):
    file_diff_log = exec(diff_cmd.format(bug_file, fix_file))
    files_log = split_diff_log(file_diff_log)

    bug_chunks, fix_chunks = [], []

    for file_log in files_log:
        # try:
        files_diff = aggregator(line_parser.parse_lines(file_log))
        for file_diff in files_diff:
            for chunk in file_diff['chunks']:
                bug, fix = [], []
                for line in chunk['lines']:
                    code = line['line'].strip()
                    line_number = line['from_line_number']
                    elem = ({'file':bug_file, 'line':line_number}, code.replace('\r', '').replace('\n', ''))
                    is_code = not (code.startswith('*') or code.startswith('//') or code.startswith('/*'))
                    if line['action'] == 'delete':
                        if is_code:
                            bug.append(elem)
                    if line['action'] == 'add':
                        if is_code:
                            fix.append(elem)

                if len(bug) == 0 or len(fix) == 0: continue
                bug_chunks.append(bug)
                fix_chunks.append(fix)
        # except:
        #     pass
    
    return bug_chunks, fix_chunks


def parser_ast(code, ast):
    var_map = ast.variable
    ast_code = [var_map[word] if word in var_map else word for word in code.split()]

    return ' '.join(ast_code)


def extract_code_ast(chunk, ast_cache):
    file_path = chunk["file"].replace("buggy-version","buggy-ast")
    code = chunk["code"]

    if not file_path.endswith('.java'): return chunk["code"]

    try:
        ast = ast_cache.get(file_path)
        if not ast:
            ast = build_ast_from_file(file_path)
            ast = extract_Variable(ast)

            ast_cache.add(file_path, ast)
        
        return parser_ast(code, ast)
    except:
        print(f"Error In {file_path}")

    return chunk["code"]


def chunk2list(one_chunks):
    # one_chunks: [files [chunk [(num, line)] ] ]
    chunk_list = []
    lines_list = []
    ast_cache = Cache()
    for file_chunk in one_chunks:
        for chunk in file_chunk:
            line_nums = [line[0] for line in chunk]
            codes = [line[1] for line in chunk]
            line = ' DCNL '.join(codes)
            if line_nums:
                line_number = {'file':line_nums[0]['file'], 
                               'start_line': line_nums[0]['line'], 
                               'end_line': line_nums[-1]['line']}
                chunk = {"file":line_nums[0]['file'], "code":line}
                line_number["code_ast"] = extract_code_ast(chunk, ast_cache)
                line_number = str(line_number)
            else:
                line_number = ''
            chunk_list.append(line + '\n')
            lines_list.append(line_number + '\n')
    
    return chunk_list, lines_list


def process_one_bugfix(path):
    bug_path = path+'buggy-version/'
    fix_path = path+'fixed-version/'
    files = subprocess.check_output(['ls', bug_path])
    files = files.decode('utf-8').strip().split('\n')

    one_bug_chunks, one_fix_chunks = [], [] # [files [chunk [line] ] ]

    for file in files:
        bug_file = bug_path + file
        fix_file = fix_path + file
        bug_chunks, fix_chunks = get_diff_chunk(bug_file, fix_file)

        one_bug_chunks.append(bug_chunks)
        one_fix_chunks.append(fix_chunks)

    bug_chunks_list, bug_lines_list = chunk2list(one_bug_chunks)
    fix_chunks_list, fix_lines_list = chunk2list(one_fix_chunks)

    bug_output = path+'bug_chunk.txt'
    fix_output = path+'fix_chunk.txt'

    bug_locat_output = path+'bug_location.txt'
    fix_locat_output = path+'fix_location.txt'

    with open(bug_output, 'w', encoding='utf-8') as f:
        f.writelines(bug_chunks_list)
    with open(fix_output, 'w', encoding='utf-8') as f:
        f.writelines(fix_chunks_list)

    with open(bug_locat_output, 'w', encoding='utf-8') as f:
        f.writelines(bug_lines_list)
    with open(fix_locat_output, 'w', encoding='utf-8') as f:
        f.writelines(fix_lines_list)
    

def combine_data(pre_path, paths, bug_output, fix_output, bug_loca_output, fix_loca_output):
    bug_data, fix_data = [], []
    bug_loca_data, fix_loca_data = [], []

    for path in tqdm(paths):
        bug_file = './{}/{}/bug_chunk.txt'.format(pre_path, path)
        fix_file = './{}/{}/fix_chunk.txt'.format(pre_path, path)

        bug_loca = './{}/{}/bug_location.txt'.format(pre_path, path)
        fix_loca = './{}/{}/fix_location.txt'.format(pre_path, path)

        with open(bug_file, 'r', encoding='utf-8') as f:
            bug_lines = f.readlines()
            bug_data.extend(bug_lines)
        with open(fix_file, 'r', encoding='utf-8') as f:
            fix_lines = f.readlines()
            fix_data.extend(fix_lines)

        with open(bug_loca, 'r', encoding='utf-8') as f:
            bug_lines = f.readlines()
            bug_loca_data.extend(bug_lines)
        with open(fix_loca, 'r', encoding='utf-8') as f:
            fix_lines = f.readlines()
            fix_loca_data.extend(fix_lines)

    assert len(bug_data) == len(bug_loca_data)
    print(len(bug_data))
    with open(bug_output, 'a', encoding='utf-8') as f:
        f.writelines(bug_data)
    with open(fix_output, 'a', encoding='utf-8') as f:
        f.writelines(fix_data)

    with open(bug_loca_output, 'a', encoding='utf-8') as f:
        f.writelines(bug_loca_data)
    with open(fix_loca_output, 'a', encoding='utf-8') as f:
        f.writelines(fix_loca_data)

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
    if len(sentence.split()) < 10: return ''
    return sentence


if __name__ == "__main__":
    bug_file, fix_file = 'bug_chunk.txt', 'fix_chunk.txt'
    bug_loca_file, fix_loca_file = 'bug_location.txt', 'fix_location.txt'
    os.system('rm {} {}'.format(bug_file, fix_file))
    os.system('rm {} {}'.format(bug_loca_file, fix_loca_file))

    dataset_path = '../BugFixDataset/'
    pre_paths = ['Partation1', 'Partation2', 'Partation3', 'Partation4', 'Partation5']
    pre_paths = [dataset_path+path for path in pre_paths]
    for pre_path in pre_paths:
        file_paths = subprocess.check_output(['ls', pre_path])
        file_paths = file_paths.decode('utf-8').strip().split('\n')
        # file_paths = file_paths[:100]

        for path in tqdm(file_paths):
            process_one_bugfix('./{}/{}/'.format(pre_path, path))

        combine_data(pre_path, file_paths, bug_file, fix_file, bug_loca_file, fix_loca_file)
