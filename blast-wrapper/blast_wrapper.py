#!/usr/bin/python3

"""
Required: BLAST+ installed in $PATH

Usage:

## Simplest:
$ python blast_wrapper.py -q query.faa -df database.faa
or if you already have an established database:
$ python blast_warpper.py -q query.faa -db blast+_database

## Moderate:
$ python blast_wrapper.py -b blastn -q query.fna -o output -df database.fna \
                          -e 1e-10 -n 5

## Control freak:
$ python blast_wrapper.py -b blastn -q query.fna -o output -df database.fna \
                          -e 1e-10 -n 5 -ms 3 --no_qseq

*Any change to output format by -f option may lead to errors when parsing output results.
"""

import os
import sys
import argparse
from collections import defaultdict

__author__ = "Heyu Lin"
__contact__ = "heyu.lin(AT)student.unimelb.edu.au"

parser = argparse.ArgumentParser()
parser.add_argument('-q', '--query', metavar='query_fasta', dest='q',
                    type=str, required=True)
parser.add_argument('-o', '--output', metavar='output', dest='o',
                    type=str)
parser.add_argument('-df', '--database_fasta', metavar='database_fasta',
                    dest='df', type=str,
                    help='fasta file to be used as database')
parser.add_argument('-db', '--database', metavar='database',
                    dest='db', type=str,
                    help='blast database which has already been made')
parser.add_argument('-e', '--evalue', metavar='max_e-value', dest='e',
                    type=float, default=1e-5,
                    help='threshod e-value for blast (default=1e-5)')
parser.add_argument('-ms', '--max_target_seqs', metavar='num_sequences',
                    dest='ms', type=int, default=1,
                    help='specify the max_number of target seqs for hits per query (default=1)')
parser.add_argument('-n', '--num_threads', metavar='num_cpu',
                    dest='n', type=int, default=3,
                    help='specify the number of threads used by blast (default=3)')
parser.add_argument('-b', '--blast_program', metavar='blast+ program',
                    dest='b', type=str, default='blastp',
                    help='specify the blast program (default=blastp)')
parser.add_argument('-id', '--identity', metavar='identity_threshold',
                    dest='idt', type=float, default=0,
                    help='specify the threshold of identity (default=0)')
parser.add_argument('-qc', '--qcov', metavar='coverage_threshold',
                    dest='qc', type=float, default=0,
                    help='specify the threshold of query coverage (default=0)')
parser.add_argument('--no_qseq', metavar='hide qseq column',
                    dest='nq', nargs="?", const=True, default=False,
                    help='no query sequences will be showed if this argument is added')
# You're not going to like to change this default output format.
# Any change to this outfmt argument may lead to exceptions for query coverage calculation
parser.add_argument('-f', '--outfmt', metavar='output_format*',
                    dest='f', type=str,
                    default='"6 qseqid sseqid pident length mismatch gapopen ' \
                    + 'qstart qend sstart send qlen slen evalue bitscore"',
                    help='outfmt defined by blast+, it is dangerous to change the default value')
args = parser.parse_args()


def input_type(b):
    '''
    return blast database type (prot or nucl)
    '''
    if b == 'blastp' or b == 'blastx':
        tp = 'prot'
        return tp
    elif b == 'blastn' or b == 'tblastn':
        tp = 'nucl'
        return tp
    else:
        sys.exit("Error: -b argument should only be 'blastp/blastn/blastx/tblastn'!")


def database_exist(db):
    prot_databases = db + '.phr'
    nucl_databases = db + '.nhr'
    if os.path.exists(prot_databases) or os.path.exists(nucl_databases):
        return True


def run_mkblastdb(fi, fo, tp):
    '''
    fi: input fasta file
    fo: output database name
    tp: prot or nucl
    '''
    cmd_para = [
                'makeblastdb',
                '-in', fi,
                "-dbtype", tp,
                "-parse_seqids",
                "-out", fo
                ]
    cmd = ' '.join(cmd_para)
    try:
        print("\n", 'Make Blast Database'.center(50, '*'))
        print(cmd, "\n")
        os.system(cmd)
    except Exception as e:
        raise e


def run_blast(q, o, db, e, f, n, b):
    '''
    q: query
    o: output
    db: database
    e: evalue
    f: outfmt
    n: num_threads
    b: blast program
    '''
    cmd_para = [
                b,
                '-query', q,
                '-out', o,
                '-db', db,
                '-evalue', str(e),
                '-outfmt', f,
                '-num_threads', str(n)
                ]
    cmd = ' '.join(cmd_para)
    try:
        print("\n", 'BLAST Searching'.center(50, '*'))
        print(cmd, "\n")
        os.system(cmd)
    except Exception as e:
        raise e


def creat_dict(fa):
    with open(fa, 'r') as f:
        dict = defaultdict(str)
        name = ''
        for line in f:
            if line.startswith('>'):
                name = line[1:-1].split()[0]
                continue
            dict[name] += line.strip()
        return dict


def blast_Parser(fi, fo, header, idt, qc, ms, *dict):
    '''
    fi: blast output (format as defined in this script)
    fo: final output
    dict: dictionary created from query fasta (used to extract hit sequences)
    '''
    seq_dict = {}  # initialize a dict to index query sequences
    if dict:
        seq_dict = dict[0]

    with open(fi) as input, open(fo, 'w') as output:
        output.write("\t".join(header) + "\n")
        times = 0  # initialize the hit number
        quer_last = ''  # initialize the hit sequence
        for line in input.readlines():
            items = line.strip().split("\t")
            quer = items[0]
            if quer == quer_last:
                times += 1
                if times > ms:
                    continue
            else:
                quer_last = quer
                times = 1
            qstart, qend, qlen = map(float, (items[6], items[7], items[10]))
            qcov = 100 * (qend - qstart) / qlen
            ident = float(items[2])
            if ident < idt or qcov < qc:
                continue
            items.append(str(round(qcov, 1)))
            if seq_dict:
                qid = items[0]
                items.append(seq_dict[qid])
            output.write("\t".join(items) + "\n")


def review_output(file):
    with open(file, 'r+') as fi:
        if len(fi.readlines()) == 1:
            fi.seek(0)
            fi.truncate()

def main():
    tp = input_type(args.b)

    if not args.o:
        args.o = os.path.basename(args.q) + '_blast.out'

    # Make blast database
    if args.df:
        database_file = os.path.join(os.getcwd(), args.df) + '.db'
        if not database_exist(database_file):
            print("Starting to make blast database...")
            run_mkblastdb(args.df, database_file, tp)
        args.db = database_file
        print('DB: ', args.db)

    # Storing temporary blast result
    tempt_output = str(args.o) + '_blast.tmp'

    # => Run blast program
    run_blast(args.q, tempt_output, args.db, args.e, args.f, args.n, args.b)

    # Creat dict from query fasta, in order to extract sequencs later
    dict = creat_dict(args.q)

    # Parse blast output
    header = [
                'qid', 'sid', 'ident%', 'aln_len', 'miss',
                'gap', 'qstart', 'qend', 'sstart', 'send',
                'qlen', 'slen', 'evalue', 'bitscore', 'qcov%', 'qseq'
            ]
    # If the --no_qseq option was specified, there would be no qseq column.
    if args.nq:
        header.remove('qseq')
        blast_Parser(tempt_output, args.o, header, args.idt, args.qc, args.ms)
    else:
        blast_Parser(tempt_output, args.o, header, args.idt, args.qc, args.ms, dict)
    # Remove temp file
    os.remove(tempt_output)

    # Clear the lonely header line if no hit was found
    review_output(args.o)

    print("\n", 'OUTPUT'.center(50, '*'))
    print("Output File: {0}".format(args.o))


if __name__ == '__main__':
    main()
