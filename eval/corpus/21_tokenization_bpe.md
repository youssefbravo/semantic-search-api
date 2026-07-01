# Tokenization and Byte Pair Encoding

Before a language model can process text, the text must be turned into tokens, the
discrete units the model actually reads. How text is split into tokens affects both the
size of the model's vocabulary and how it copes with words it has never seen.

The naive options are both poor. Splitting on whole words gives a huge vocabulary and
breaks on any out-of-vocabulary word that was not seen in training. Splitting into
individual characters keeps the vocabulary tiny but makes sequences very long and forces
the model to relearn how characters combine into meaning.

Subword tokenization strikes the balance. It breaks text into subword units, so common
words stay whole while rare words are split into meaningful pieces. The word "tokenizer"
might become "token" and "izer", which lets the model represent a word it never saw by
composing parts it does know.

The dominant algorithm for building these units is byte pair encoding. Starting from
individual characters, it repeatedly finds the most frequent adjacent pair of symbols
and merges it into a new symbol, and it keeps doing this until the vocabulary reaches a
target size. Frequent sequences thus become single tokens while rare ones remain split.

The outcome is a vocabulary of fixed size that can represent any input, because in the
worst case a word falls back to its individual characters. This guarantee, that there
is no truly unknown input, is the main reason subword tokenization replaced word-level
schemes in modern models, including the embedding model used in this project.
