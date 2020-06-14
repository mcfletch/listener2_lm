#! /usr/bin/env python3
import argparse, os, gzip, io, bz2, tarfile, logging, subprocess
from collections import Counter
import progressbar
from listener import tokenizer

log = logging.getLogger(__name__)


def ds_tokenizer(line):
    """Default upstream tokenizer"""
    return line.lower().split()


def convert_and_filter_topk(
    input_txt,
    output_dir=None,
    top_k=50000,
    tokenizer=ds_tokenizer,
    stop_after=None,
    filter_function=None,
    context='default',
):
    """ Convert to lowercase, count word occurrences and save top-k words to a file """

    counter = Counter()
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(input_txt))

    data_lower = os.path.join(
        output_dir, "%(context)s-lower.txt.gz" % {'context': context,}
    )

    print("\nConverting to lowercase and counting word occurrences ...")
    lines = 0
    with io.TextIOWrapper(
        io.BufferedWriter(gzip.open(data_lower, "w+")), encoding="utf-8"
    ) as file_out:

        # Open the input file either from input.txt or input.txt.gz
        rest, file_extension = os.path.splitext(input_txt)
        if rest.endswith('.tar'):
            file_in = tarfile.open(input_txt, mode='r:gz')

            def iter_tar_lines():
                for member in file_in:
                    if not member.isfile():
                        continue
                    try:
                        for line in io.TextIOWrapper(
                            file_in.extractfile(member), encoding='utf-8',
                        ):
                            yield line
                    except UnicodeDecodeError as err:
                        log.warning("Encoding for %s is not utf-8", member.name)
                        continue

            line_iterator = iter_tar_lines()
        else:
            if file_extension == ".gz":
                file_in = io.TextIOWrapper(
                    io.BufferedReader(gzip.open(input_txt)), encoding="utf-8"
                )
            elif file_extension == ".bz2":
                file_in = io.TextIOWrapper(
                    io.BufferedReader(bz2.open(input_txt)), encoding="utf-8"
                )
            else:
                file_in = open(input_txt, encoding="utf-8")
            line_iterator = file_in

        for line in progressbar.progressbar(line_iterator):
            if filter_function and not filter_function(line):
                continue
            tokens = tokenizer(line)
            if tokens:
                counter.update(tokens)
            file_out.write(' '.join(tokens).lower() + '\n')
            lines += 1
            if stop_after and lines > stop_after:
                break
            elif not lines % 10000:
                print(line)
                print(' '.join(tokens))

        file_in.close()

    # Save top-k words
    print("\nSaving top {} words ...".format(top_k))
    top_counter = counter.most_common(top_k)
    vocab_str = "\n".join(word for word, count in top_counter)
    vocab_path = "{}-vocab-{}.txt".format(context, top_k)
    vocab_path = os.path.join(output_dir, vocab_path)
    with open(vocab_path, "w+") as file:
        file.write(vocab_str)

    print("\nCalculating word statistics ...")
    total_words = sum(counter.values())
    print("  Your text file has {} words in total".format(total_words))
    print("  It has {} unique words".format(len(counter)))
    top_words_sum = sum(count for word, count in top_counter)
    word_fraction = (top_words_sum / total_words) * 100
    print(
        "  Your top-{} words are {:.4f} percent of all words".format(
            top_k, word_fraction
        )
    )
    print('  Your most common word "{}" occurred {} times'.format(*top_counter[0]))
    last_word, last_count = top_counter[-1]
    print(
        '  The least common word in your top-k is "{}" with {} times'.format(
            last_word, last_count
        )
    )
    for i, (w, c) in enumerate(reversed(top_counter)):
        if c > last_count:
            print(
                '  The first word with {} occurrences is "{}" at place {}'.format(
                    c, w, len(top_counter) - 1 - i
                )
            )
            break

    return data_lower, vocab_str


def wikipedia_filter(line):
    if line == '---END.OF.DOCUMENT---':
        return None
    elif not line.strip():
        return None
    tokens = line.lower().split()
    if len(tokens) < 4:  # skip titles, empty lines, etc
        return None
    return line


def wikipedia():
    convert_and_filter_topk(
        '/var/datasets/text/WestburyLab.Wikipedia.Corpus.txt.bz2',
        tokenizer=create_dictation_tokenizer(),
        filter_function=wikipedia_filter,
    )


def upstream():
    convert_and_filter_topk(
        '/var/datasets/text/librispeech-lm-norm.txt.gz', tokenizer=ds_tokenizer,
    )


def raw_python_corpus():
    convert_and_filter_topk(
        '/var/datasets/text/python-corpus.tar.gz',
        tokenizer=create_dictation_tokenizer(code=True),
        filter_function=None,
    )


def create_dictation_tokenizer(code=False):
    """Create a tokenizer for dictation inputs"""

    dictionary = tokenizer.default_dictionary()
    tokenizer = tokenizer.Tokenizer(dictionary, run_together_guessing=code)
    return tokenizer


def build_lm(args, data_lower, vocab_str):
    print("\nCreating ARPA file ...")
    lm_path = os.path.join(args.output_dir, "lm.arpa")
    subargs = [
        os.path.join(args.kenlm_bins, "lmplz"),
        "--order",
        str(args.arpa_order),
        "--temp_prefix",
        args.output_dir,
        "--memory",
        args.max_arpa_memory,
        "--text",
        data_lower,
        "--arpa",
        lm_path,
        "--prune",
        *args.arpa_prune.split("|"),
    ]
    if args.discount_fallback:
        subargs += ["--discount_fallback"]
    subprocess.check_call(subargs)

    # Filter LM using vocabulary of top-k words
    print("\nFiltering ARPA file using vocabulary of top-k words ...")
    filtered_path = os.path.join(args.output_dir, "lm_filtered.arpa")
    subprocess.run(
        [
            os.path.join(args.kenlm_bins, "filter"),
            "single",
            "model:{}".format(lm_path),
            filtered_path,
        ],
        input=vocab_str.encode("utf-8"),
        check=True,
    )

    # Quantize and produce trie binary.
    print("\nBuilding lm.binary ...")
    binary_path = os.path.join(args.output_dir, "lm.binary")
    subprocess.check_call(
        [
            os.path.join(args.kenlm_bins, "build_binary"),
            "-a",
            str(args.binary_a_bits),
            "-q",
            str(args.binary_q_bits),
            "-v",
            args.binary_type,
            filtered_path,
            binary_path,
        ]
    )


def main():
    from listener import defaults

    parser = argparse.ArgumentParser(
        description="Generate contextual language models for Listener"
    )
    parser.add_argument(
        '-c',
        '--context',
        help="Which context to process",
        choices=['code', 'wikipedia', 'upstream',],
        default='code',
    )

    parser.add_argument(
        "--output_dir",
        help="Directory path for the output",
        type=str,
        required=True,
        default='/var/datasets/text',
    )
    parser.add_argument(
        "--top_k",
        help="Use top_k most frequent words for the vocab.txt file. These will be used to filter the ARPA file.",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--kenlm_bins",
        help="File path to the KENLM binaries lmplz, filter and build_binary",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--arpa_order",
        help="Order of k-grams in ARPA-file generation",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--max_arpa_memory",
        help="Maximum allowed memory usage for ARPA-file generation",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--arpa_prune",
        help="ARPA pruning parameters. Separate values with '|'",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--binary_a_bits",
        help="Build binary quantization value a in bits",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--binary_q_bits",
        help="Build binary quantization value q in bits",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--binary_type",
        help="Build binary data structure type",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--discount_fallback",
        help="To try when such message is returned by kenlm: 'Could not calculate Kneser-Ney discounts [...] rerun with --discount_fallback'",
        action="store_true",
    )

    args = parser.parse_args()

    data_lower, vocab_str = convert_and_filter_topk(args)
    build_lm(args, data_lower, vocab_str)

    # Delete intermediate files
    # os.remove(os.path.join(args.output_dir, "lower.txt.gz"))
    # os.remove(os.path.join(args.output_dir, "lm.arpa"))
    # os.remove(os.path.join(args.output_dir, "lm_filtered.arpa"))
