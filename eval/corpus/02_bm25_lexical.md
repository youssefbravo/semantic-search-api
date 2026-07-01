# BM25 and Lexical Retrieval

Lexical retrieval ranks documents by the words they share with the query. It is the
foundation of classic search engines and remains a strong baseline that is hard to
beat on queries containing rare or exact terms such as product codes, error
identifiers, or proper names.

BM25, short for Best Matching 25, is the most widely used lexical ranking function.
It scores a document for a query by summing a weight for each query term that the
document contains. Each term's weight combines two ideas: how often the term appears
in the document, and how rare the term is across the whole collection.

The first idea is term frequency. A document that mentions a query term many times
is more likely to be about that term. Crucially, BM25 applies term-frequency
saturation, so the tenth occurrence of a word adds far less to the score than the
second. This prevents long or keyword-stuffed documents from dominating purely by
repetition.

The second idea is inverse document frequency. A term that appears in almost every
document, such as "the", carries little discriminating power, whereas a term that
appears in only a handful of documents is highly informative. Inverse document
frequency gives rare query terms a much larger weight than common ones.

BM25 also performs document length normalization, controlled by a parameter
conventionally written as b. Without it, longer documents would score higher simply
because they contain more words and therefore more chances to match. Length
normalization discounts a document's score in proportion to how much longer it is
than the average document in the collection.

The main limitation of lexical retrieval is the vocabulary mismatch problem. Because
BM25 matches surface words, a query for "car" will not retrieve a document that only
mentions "automobile", even though they mean the same thing. This is precisely the
weakness that dense semantic retrieval was designed to address.
