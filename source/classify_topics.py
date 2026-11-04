import argparse
import json
from pathlib import Path
from recompute import ReportParser
import re
import unicodedata


ROOT = Path(__file__).resolve().parent
AI_TOPIC = "Generative AI & Language Models"
UNCLASSIFIED = "Unclassified"

RULES = {
    "Graph Algorithms & Combinatorics": (
        r"graph algorithms?|graph theor\w+|graph color\w+|graph isomorph\w+|subgraph isomorph\w+|graph minor\w*|graph homomorph\w+|graph decompos\w+|graph sparsi\w+|spectral graph\w*|graph cut\w*|graph factor\w*|random graphs?|expander graphs?|expander decompos\w+|directed graphs?|dynamic graphs?|sparse graphs?|planar graphs?|bipartite graphs?|geometric graphs?|independent sets?|dominating sets?|maximum matchings?|perfect matchings?|graph matchings?|shortest paths?|minimum cuts?|maximum flows?|minimum cost flows?|network flows?|multicommodity flows?|vertex covers?|vertex connect\w+|edge connect\w+|all pairs shortest paths?|traveling salesperson|travelling salesman|traveling salesman|steiner trees?|steiner forests?|graph spanners?|hamiltonian cycles?|ramsey numbers?|ramsey theor\w+|extremal combinator\w+|erdos posa|tur[aá]n|hypergraphs?|treewidth|pathwidth|cycle finding|weisfeiler leman|graph property testing|graph reconstruction|pagerank|effective resistance|mincuts?|maximum spanning trees?|minimum spanning trees?|minimum k cut|k cuts?|edge color\w+|digraphs?|cactus decompos\w+|tangle structure trees?|ramanujan graphs?|ramanujan 2 lift|graph similarity|tree decompos\w+|graph rigidity|collective tree exploration|directed acyclic graphs?|dags?|graph labeling|graph labelling|freiman ruzsa|marton s conjecture|additive combinator\w+|percolated hypercube|graph percolation|cardinality matchings?|sparsest cuts?|maximum weight matchings?",
        r"graphs?|digraphs?|combinator\w+|vertices|edges|matchings?|diameters?|connectivity|chordal|matroids?|colorings?|graphical|cliques?|induced|connectivity|arboricity|pathfinding|conductance|girth|spectral|spanning trees?",
    ),
    "Complexity & Lower Bounds": (
        r"computational complexity|complexity theor\w+|complexity classes|circuit complexity|circuit lower bounds?|proof complexity|proof systems?|communication complexity|query complexity|query lower bounds?|oracle separation|fine grained complexity|fine grained hardness|parameterized complexity|complexity dichotom\w+|polynomial hierarchy|counting hierarchy|sum of squares|resolution proofs?|extended resolution|polynomial calculus|probabilistically checkable proofs?|interactive proofs?|proofs? of proximity|exponential time hypothesis|orthogonal vectors hypothesis|strong exponential time hypothesis|conditional hardness|np completeness|np complete|np hardness|np hard|inapproximability|fixed parameter tractab\w+|fixed parameter algorithms?|kernelization|branching algorithms?|time hierarchy|time space tradeoff\w*|pseudodeterministic|tfnp|ppad|pls complete|puma|oracles? relativiz\w*|space bounded|log space|bounded arithmetic|hardness magnification|kolmogorov complexity|formula complexity|decision trees?|catalytic (?:space|comput\w+|communicat\w+)|regular languages?|satisfiability problem|algebraic lower bounds?|counting hardness|complexity of finding|pspace|ptime|sharp p hardness|frege|resolution refutations?|pcps?|branching programs?|holant|de morgan formulas?|witness isolation|determinantal complexity|xor lemma|catalytic comput\w+|average case reductions?|deterministic time|space hierarchy|nonuniform complexity|time space hardness|np complete\w*|pspace complete\w*|property testing lower bounds?",
        r"lower bounds?|hardness|reductions?|completeness|complexity|space complexity|subexponential|relativiz\w+|arithmetization|nondetermin\w+|counting complexity|seth|eth|pcp|bqp hardness|circuit families|fpt|kernels?|k hitting set|d hitting set|parameteriz\w+|arithmetic circuits?",
    ),
    "Optimization & Approximation": (
        r"convex optimization|nonconvex optimization|non convex optimization|combinatorial optimization|integer programm\w+|linear programm\w+|semidefinite programm\w+|quadratic programm\w+|stochastic optimization|gradient descent|gradient methods?|first order methods?|second order methods?|first order oracle|proximal methods?|convex body chasing|online optimization|online algorithms?|online learning|competitive ratio\w*|primal dual|approximation algorithms?|approximation ratios?|approximation schemes?|submodular (?:minimization|maximization|optimization)|matroid (?:intersection|optimization)|bin packing|facility location|vehicle routing|job scheduling|machine scheduling|resource allocation|optimal transport|ellipsoid method|interior point methods?|sparse linear systems|linear system solvers?|numerical optimization|semidefinite relaxations?|variance reduction|online discrepancy|online matching|k means|k median|k center|sum of squared distances|dynamic programming|subset sum|set packing|steinitz|online vector balanc\w+|matrix spencer|convex bodies|k taxi|k server|quadratic optimization|discrepancy minimization|linear optimization|approximation scheme\w*|bilinear optimization|optimal tradeoffs? for optimization|maximum delays?|ptas|fptas|approximation scheme\w*|matrix discrepancy|matrix spencer|kadison singer|vector balanc\w+|online packing|min sum clustering|linear objective|solvers? for sparse systems|linear least squares|spectral outliers?|numerical linear algebra",
        r"convex|nonconvex|optimization|optimisation|approximat\w+|competitive|fractional|submodular|packing|covering|rounding|relaxations?|lagrangian|clustering|regret|scheduling|linear systems?|condition number\w*|solver\w*|gradient\w*|maximization|minimization",
    ),
    "Data Structures, Streaming & Sketching": (
        r"data structures?|cell probe|word ram|range searching|range queries|range search|orthogonal range|point location|nearest neighbou?rs?|similarity search|locality sensitive hashing|dynamic (?:connectivity|matching|algorithms?|shortest paths?|data structure\w*|graphs?)|fully dynamic|incremental (?:algorithm\w*|connectivity|shortest paths?)|decremental (?:algorithm\w*|connectivity|shortest paths?)|online query processing|range reporting|dictionary problem|predecessor search|succinct data structures?|streaming algorithms?|data streams?|graph streaming|turnstile streams?|linear sketches?|frequency moments?|sampling sketches?|sublinear space|sublinear time|massively parallel computation|semi streaming|graph sketch\w+|matrix sketch\w+|count sketch|caching|cache replacement|cache size|permutation streams?|shellsort|sorting algorithms?|priority queues?|online data structures?|sampling data structures?|stream processing|sketching",
        r"sketch(?:es|ing)?|streaming|dynamic|succinct|amortized|preprocessing|update time|query time|sublinear|queries|indexes|indexing|hashing|compression|range|estimating",
    ),
    "Learning, Statistics & AI": (
        r"machine learning|learning theor\w+|deep learning|statistical learning|reinforcement learning|imitation learning|active learning|online learning|pac learning|agnostic learning|supervised learning|unsupervised learning|semi supervised learning|distribution learning|learning distributions?|learnability|learning halfspaces?|learning sparse|learning parities|learning juntas?|sample complexity|distribution testing|distribution properties|property testing|mean estimation|covariance estimation|density estimation|robust statistics|statistical estimat\w+|linear regression|logistic regression|neural networks?|language models?|large language models?|large reasoning models?|generative models?|generative ai|diffusion models?|multi armed bandits?|contextual bandits?|multiagent learning|markov decision process\w*|generalization bounds?|distribution shift|hypothesis testing|statistical query|classification error|vc dimension|predictive models?|transfer learning|artificial intelligence|time series forecast\w+|relu networks?|prototypical networks?|gaussian mixture\w*|gaussian location mixtures?|softmax attention|kolmogorov arnold networks?|nonparametric|statistical verification|language generation|autoregressive learning|autoregressive distribution learning|monotonicity testing|metric testing|causal failure rank|learning halfspaces|causal discovery|omniprediction|first order regret|adaptive data analysis|distribution identity testing|tolerant testing|covariate shift|causal inference",
        r"learning|estimation|estimators?|prediction|classif\w+|regression|bandits?|neural|generalization|train(?:ing|ed)|dataset\w*|samples?|statistical|inference|classifiers?|distribution robust|halfspaces?|model accuracy|backpropagation|retrieval",
    ),
    "Cryptography & Security": (
        r"cryptograph\w+|zero knowledge|homomorphic encryption|fully homomorphic|pseudorandom functions?|pseudorandom permutations?|one way functions?|trapdoor functions?|public key|private key|secure computation|secure multiparty computation|multiparty computation|oblivious transfer|oblivious ram|secret sharing|functional encryption|attribute based encryption|indistinguishability obfuscation|random oracle|digital signatures?|signatures? schemes?|signature schemes?|proof of work|proof of stake|blockchains?|authenticated data structures?|verifiable computation|succinct arguments?|interactive arguments?|bulletproofs|snarks?|starks?|fiat shamir|proofs? of (?:knowledge|retrievability)|lattice based cryptography|learning with errors|decision diffie hellman|side channel|post quantum|commitment schemes?|hash functions?|security reductions?|cryptanalysis|witness encryption|generic group model|shortest vector problem|learning with physical rounding|ring lwe|module lwe|mlwe|pseudorandom correlation\w*|bilinear groups?|cryptographic hardness|public verifiability|cyber defen[cs]e|secret keys?|ciphers?|ciphertext security|key schedules?|key alternating|block cipher\w+",
        r"encryption|security|adversar\w+|ciphertexts?|plaintexts?|pseudorandom\w*|malicious|computational indistinguishability|commitments?|lwe|sis|secure|quantum secure|unforgeab\w+|cryptosystems?|zkp",
    ),
    "Privacy, Fairness & Robustness": (
        r"differential\w* privat\w+|privacy preserv\w+|privacy guarantees?|privacy loss|privacy filters?|privacy odometers?|privacy amplification|privacy auditing|data privacy|private data|private proofs?|synthetic data|private learning|private estimation|differential privacy|local privacy|shuffle model|pan privacy|learning with privacy|statistical fairness|algorithmic fairness|demographic parity|equalized odds|group fairness|individual fairness|fair classification|membership inference|robust statistics|robust estimation|adversarial examples?|adversarial robustness|certified robustness|replicable learning|replicable (?:algorithm\w*|estimation|mean)|replicability|distributionally robust|robust optimization|distribution robust|testing fairness|fairness of|private synthetic|privacy budget|privacy accounting|replicable mean estimation|fairness auditing|private graph",
        r"privacy|private|robust\w*|fairness|fairness constraints|replica\w+|sensitive data|anonymiz\w*|memorization|robustness|outliers?|data poisoning|data corruption",
    ),
    "Quantum Computing": (
        r"quantum|qubits?|hamiltonian complexity|local hamiltonian|commuting hamiltonian|hamiltonian simulation|bqp|qma|qip|qldpc|quantum ldpc|cnot|surface codes?|stabilizer codes?|stabilizer states?|toric codes?|logical qubits?|boson sampling|unitary designs?|unitary circuits?|bell inequalities|schrodinger|many body physics|fault tolerant computing|welded trees|color codes?|quantumly|hamiltonian property testing|unitary circuit\w*|quantum states?|pauli measurements?|ground state energ\w+|purity estimation|syk model|lindbladian|mixedness testing|cloning of mixed states|quantum advantage|heisenberg limit\w+",
        r"nonlocal games?|entangle\w+|hamiltonians?|isometries|unitary|stabilizers?|purifications?|contextuality|choi|fault tolerance|wave particle",
    ),
    "Coding & Information Theory": (
        r"coding theor\w+|information theor\w+|list decod\w+|list recover\w+|error correct\w+|error detect\w+|reed solomon|reed muller|low density parity check|ldpc|locally decodable|locally correctable|locally testable|erasure codes?|edit codes?|insertion deletion codes?|insdel|polar codes?|channel coding|codes? at capacity|rate distortion|shannon capacity|information complexity|data processing inequality|data processing inequalities|source coding|linear codes?|hamming codes?|coded computation|channel capacity|minimum distance decoding|minimum weight decoding|decoding algorithm|proximity gaps|min entropy|gilbert varshamov|list recovery|data compression|information transmission|error exponents?|channel resolvability|synchronization strings?|minimum weight decod\w+",
        r"codes?|coding|decoding|decodable|entropy|information|hamming|minimum distance|relative distance|capacity|decoders?|lccs?|ldcs?|correctable|testable|communication rate",
    ),
    "Economics, Games & Fair Division": (
        r"mechanism design|game theor\w+|algorithmic economics|computational economics|market equilibr\w+|competitive equilibr\w+|nash equilibr\w+|correlated equilibr\w+|fisher markets?|matching markets?|combinatorial auctions?|auctions?|fair division|fair allocation\w*|envy free\w*|efx|ef1|maximin share\w*|mms allocations?|nash welfare|social welfare|welfare maximization|incentive compatib\w+|revenue maximization|posted price\w*|prophet inequalities|prophet secretary|secretary problems?|strategic behavior|price of anarchy|price of stability|social choice|voting rules?|stable matching|school choice|preference aggregation|house allocation|utility maximization|economic mechanisms?|consumer utility|bayesian persuasion|optimal stopping|mean field games?|congestion games?|auction design|single parameter agents?|bilateral trade|dynamic pricing|posted pricing|prophet inequalit\w+|fictitious play|swap regret|stackelberg|stable matchings?|matching market\w*|fair and efficient allocation|bayesian mechanism|persuasion|strategic information|money burning|contract design|contract theor\w*|dynamic contracts?|procurement auctions?|information design",
        r"economic\w*|equilibr\w+|welfare|valuations?|agents?|bidders?|strategic|pricing|markets?|utility|auctions?|games?|indivisible goods|resource allocat\w+|envy|allocations?|truthful|incentives?|revenue",
    ),
    "Randomness, Probability & Sampling": (
        r"random walks?|markov chains?|mixing times?|rapid mixing|mcmc|markov chain monte carlo|monte carlo sampling|spectral independence|glauber dynamics|spin systems?|spin glasses?|sherrington kirkpatrick|ising models?|hard core models?|gibbs distributions?|gibbs sampling|partition functions?|sampling algorithms?|sampling from|sampling lower bounds?|hit and run|correlation decay|concentration inequalit\w+|probability theor\w+|stochastic processes|stochastic differential equations|derandomiz\w+|randomness extract\w+|extractors?|pseudorandom generators?|pseudorandomness|dispersers?|limited independence|random restrictions?|anti concentration|boolean functions?|spectral gaps?|strong spatial mixing|beyond worst case|random matrix theor\w+|random matrices|random graphs?|local lemma|random constraint satisfaction|log sobolev|gaussian sampling|probabilistic algorithms?|space bounded derandomization|spectral sparsification|correlated randomness|random lattice\w*|gaussian process\w*|multi access randomness|independence number|ramanujan lift\w*|explicit expander\w*|coupling argument\w*|free probability|random matrix discrepancy|semicircular operator\w*",
        r"randomness|sampling|probabilit\w+|stochastic|randomiz\w+|probabilistic|independence|concentration|spin|couplings?|distributional|pseudorandom\w*|random sources?|moments?|martingal\w+|fourier",
    ),
    "Distributed, Parallel & Network Algorithms": (
        r"distributed comput\w+|distributed algorithms?|distributed lower bounds?|parallel algorithms?|parallel computation|parallel complexity|massively parallel|congest model|congested clique|local model|distributed graph|message passing|network synchroniz\w+|byzantine agreement|byzantine fault tolerance|consensus protocols?|distributed consensus|radio networks?|network coding|network design|network routing|packet routing|load balancing|multiprocessor scheduling|shared memory|asynchronous networks?|message complexity|round complexity|round lower bounds?|local computation algorithms?|distributed estimation|minimum spanning tree in congest|round efficient|mpc algorithms?|mpc model|parallel rounds?|rounds of communication|gossip algorithms?|distributed training|wait free|renaming dichotomy|distributed memory|distributed model\w*|asynchronous consensus|minority dynamics|majority dynamics|binary consensus",
        r"distributed|parallel|decentralized|network\w*|consensus|broadcast\w*|leader election|processors?|rounds?|synchronous|asynchronous|fault tolerant|congest|pram|communication rounds?|message size",
    ),
    "Algebra, Number Theory & Symbolic Computing": (
        r"algebraic algorithms?|algebraic complexity|computational algebra|computational number theory|symbolic comput\w+|matrix multiplication|polynomial factor\w*|polynomial identity testing|polynomial interpolation|polynomial multiplication|polynomial satisfiability|sparse polynomials?|integer multiplication|integer factorization|arithmetic circuits?|algebraic circuits?|prime fields?|finite fields?|groebner bas\w+|groebner|commutative algebra|algebraic geometry|finite algebras?|group isomorph\w+|group theor\w+|permutation groups?|tensor rank|rank decomposition|tensor decompos\w+|permanent computation|computing permanents?|discrete logarithms?|monotone circuits?|partial homogenization|multivariate polynomial|polynomial systems?|lattice enumeration|coset differences?|sublattices?|modular forms?|algorithmic information|shortest vector|tensor pca|matrix completion|linear systems over finite fields?",
        r"algebra\w*|symbolic|polynomials?|finite fields?|matrices|matrix|tensor\w*|rank|modular|determinants?|number theor\w+|prime\w*|arithmetic|bilinear|linear algebra|factorization|commutative",
    ),
    "Geometry & Topology": (
        r"computational geometry|geometric algorithms?|euclidean geometry|discrete geometry|convex geometry|metric geometry|geometric combinatorics|geometric graphs?|geometric range search\w*|geometric intersection\w*|euclidean (?:k means|k median|distances?|spanners?|balls?|space)|voronoi|delaunay|computational topology|topological data analysis|persistent homology|homotopy|simplicial complex\w*|frechet distances?|hausdorff distances?|wasserstein distances?|polytope approximation|geometric discrepancy|low dimensional geometry|point location|convex hulls?|geometric packing|arrangements? of hyperplanes|curve simplification|planar subdivisions?|metric embeddings?|john ellipsoid|dimension reduction|nearest neighbor search|euclidean lattice\w*|lattice covering radius|tusnady|zonotope\w*|ellipsoid fitting|convex bodies|square tilings?|polyominoes?|point sets?|euclidean distances?",
        r"geomet\w+|topolog\w+|euclidean|polytop\w+|polygons?|convex bodies|metric spaces?|plane|planar|distances?|points?|curves?|grids?|spatial|high dimension\w*|arrangements?",
    ),
    "Logic, Automata & Formal Methods": (
        r"automata theor\w+|finite automata|weighted automata|pushdown automata|regular expressions?|regular languages?|formal languages?|context free grammars?|logic of|first order logic|second order logic|monadic second order|modal logic|fixed point logic|temporal logic|computable structure\w*|finite model theor\w+|model checking|automated theorem prov\w+|proof assistants?|proof formaliz\w+|program verification|formal verification|formal methods?|type theor\w+|logic programming|constraint satisfaction|constraint languages?|universal algebra|mal tsev|maltsev|smt solv\w+|satisfiability modulo theor\w+|datalog|computational logic|logical equivalence|formal theorem proving|countermodel\w*|language generation in the limit|computability theory|regular language\w*|proof reconfiguration",
        r"logic|grammars?|automata|logical|definability|expressive power|models? of computation|regularity|csp|sat solving|formaliz\w+|lean prover|lean proofs?",
    ),
    "Databases, Strings & Computational Biology": (
        r"database systems?|query evaluation|query answering|relational databases?|relational queries|conjunctive queries|query containment|schema mapping|query optimization|database theor\w+|joins? algorithms?|worst case optimal join\w*|fine grained (?:text|string)|string match\w+|pattern match\w+|string algorithms?|longest common subsequence|longest common substring|text indexing|suffix arrays?|suffix trees?|edit distance|string compression|sequence alignment|genome assembly|computational biology|bioinformat\w*|phylogen\w+|genomic\w*|protein folding|rna folding|dna sequencing|de bruijn graphs?|hypertree width|string generation|language generation in the limit|permutation pattern\w*|dynamic strings?|probabilistic databases?|document retrieval|data provenance|conjunctive query|shortest superstrings?|longest common subsequences?|superstring conjecture|edit correction",
        r"strings?|patterns?|sequences?|subsequences?|substrings?|databases?|queries|relational|words?|genomes?|sequences?|biological|suffix|k mers?|data management",
    ),
}


def compile_terms(group):
    return [re.compile(r"(?<!\w)(?:" + term + r")(?!\w)") for term in re.split(r"\|(?![^()]*\))", group)]


COMPILED = {topic: (compile_terms(high), compile_terms(context)) for topic, (high, context) in RULES.items()}
AI_TERMS = re.compile(
    r"(?<!\w)(?:large (?:language|reasoning) models?|language models?|llms?|"
    r"generative ai|foundation models?|chatgpt|(?:gpt|llama|claude|gemini|deepseek) [23456](?:\w+)?|"
    r"diffusion models?|softmax attention|transformer attention|self attention in transformers?|transformer (?:architectures?|models?|networks?|layers?)|"
    r"generative pre trained transformers?)(?!\w)"
)
ABSTRACT_START = re.compile(r"^\s*a\s*b\s*s\s*t\s*r\s*a\s*c\s*t(?:\s*[:.\-—]\s*|\s{2,}|\s*$)", re.I)
INTRO = re.compile(r"^\s*(?:1[.:]?|i[.:])?\s*introduction\s*[:.]?\s*$", re.I)
STOP = re.compile(
    r"^\s*(?:1[.:]?\s+|i[.:]?\s+)?(?:introduction|contents|table of contents|keywords?|"
    r"ccs concepts|classification|subject classification|references|acknowledg\w+|ai methodology|ai disclosure|ai statement|ai use statement|use of ai|use of generative ai|"
    r"generative ai disclosure|preliminaries|background|overview)\b",
    re.I,
)
DISCLOSURE_SENTENCE = re.compile(
    r"(?:\bwe (?:used|use|employed|consulted|asked)\b|\b(?:authors?|manuscript|paper|writing|proofs?)\b.{0,30}\b(?:assisted|edited|generated)\b)"
    r".{0,95}\b(?:polish\w*|proofread\w*|copy edit\w*|grammar|editing|writing|brainstorm\w*|typesett\w*|improv\w* the exposition)\b"
    r"|\b(?:proofs?|arguments?|derivations?|ideas?|lemmas?|manuscript|results?|theorems?|constructions?|algorithms?)\b.{0,28}\b"
    r"(?:obtained|produced|discovered|found|generated|derived|written)\s+by\b",
    re.I,
)


def normalize(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char)).casefold()
    text = re.sub(r"\\(?:text|mathrm|mathsf|operatorname|emph|textsc|textbf)\b", " ", text)
    text = re.sub(r"[-‐‑‒–—]\s*\n\s*(?=[a-z])", "", text)
    return re.sub(r"[\W_]+", " ", text, flags=re.UNICODE).strip()


def front_text(path):
    if not path.is_file():
        return "", "Title only"
    with path.open(encoding="utf-8", errors="replace") as stream:
        first_pages = stream.read(45_000).split("\f")[:3]
    lines = "\n\f\n".join(first_pages).split("\n")
    numbered = re.compile(r"^\s*(\d{1,3})[ \t]{3,}(?=\S)")
    markers = [int(mark[1]) for line in lines[:35] if (mark := numbered.match(line))]
    adjacent_markers = sum(right == left + 1 for left, right in zip(markers, markers[1:]))
    if adjacent_markers >= 4:
        lines = [numbered.sub("", line) for line in lines]
    for i, line in enumerate(lines):
        label = ABSTRACT_START.match(line)
        if not label or i > 155:
            continue
        collected = [line[label.end():]]
        blank_lines = 0
        word_count = len(collected[0].split())
        for next_line in lines[i + 1 :]:
            stripped = next_line.strip()
            if STOP.match(next_line) or (stripped.startswith(("* ", "∗", "†", "‡")) and word_count >= 25):
                break
            if stripped.isdigit() or next_line == "\f":
                if word_count >= 35:
                    break
                continue
            if stripped:
                if blank_lines >= 3 and word_count >= 35:
                    break
                blank_lines = 0
            else:
                blank_lines += 1
            collected.append(next_line)
            word_count += len(stripped.split())
            if word_count > 385:
                break
        abstract = "\n".join(collected).strip()
        if len(abstract.split()) >= 12 and re.search(r"[.!?](?:\s|$)", abstract):
            return abstract, "Title + abstract"
    for i, line in enumerate(lines[:145]):
        if not INTRO.fullmatch(line):
            continue
        collected = []
        for next_line in lines[i + 1 :]:
            if STOP.match(next_line) or next_line == "\f":
                break
            collected.append(next_line)
            if len(" ".join(collected).split()) > 210:
                break
        opening = "\n".join(collected).strip()
        if len(opening.split()) >= 40:
            return opening, "Title + opening text"
    return "", "Title only"


def matches(patterns, text):
    return {match.group(0) for pattern in patterns if (match := pattern.search(text))}


def domain_score(topic, title, front, abstract_weight):
    specific, context = COMPILED[topic]
    title_specific, front_specific = matches(specific, title), matches(specific, front)
    title_context, front_context = matches(context, title), matches(context, front)
    title_context = {term for term in title_context if not any(term in phrase for phrase in title_specific)}
    front_context = {term for term in front_context if not any(term in phrase for phrase in front_specific)}
    score = (
        (6.4 + 1.5 * min(2, len(title_specific) - 1) if title_specific else 0)
        + (3.5 + 1.55 * min(3, len(front_specific) - 1) if front_specific else 0) * abstract_weight
        + min(3, len(title_context)) * 1.45
        + min(4, len(front_context)) * 0.5 * abstract_weight
    )
    evidence = sorted(title_specific, key=lambda x: (-len(x), x))[:2]
    evidence += sorted(front_specific - set(evidence), key=lambda x: (-len(x), x))[:2]
    if not evidence:
        evidence = sorted(title_context | front_context, key=lambda x: (-len(x), x))[:3]
    return score, evidence


def generative_topic(title, front_text_value, basis):
    title_matches = list(AI_TERMS.finditer(title))
    for hit in title_matches:
        if re.match(r"(?:gpt|chatgpt|llama|claude|gemini|deepseek)\b", hit.group()) and re.search(
            r"\b(?:with|using|assisted by|via) $", title[:hit.start()]
        ):
            continue
        return hit.group()
    raw_front = re.sub(r"\s+", " ", front_text_value)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", raw_front)
    clean = normalize(" ".join(sentence for sentence in sentences if not DISCLOSURE_SENTENCE.search(sentence)))
    found = list(AI_TERMS.finditer(clean))
    if not found:
        return None
    if len(found) >= 2 and (basis == "Title + abstract" or len(found) >= 3):
        return found[0].group()
    hit = found[0]
    left = clean[max(0, hit.start() - 100):hit.start()]
    right = clean[hit.end():hit.end() + 75]
    if basis == "Title + abstract" and (
        re.search(r"\b(?:study|analy[sz]e|understand|evaluate|train|compress|test|learning|interpret|simulate|"
                  r"model|modeling|modelling|theory of|attribution for|algorithm for|analysis of|performance of)\b.{0,54}$", left)
        or re.match(r"\s*(?:as|that|with|in|under|to)\s+(?:oracles?|classifiers?|learn\w+|compute|solv\w+|"
                    r"represent\w+|predict\w+|generate\w+|reason\w+|train\w+|attribut\w+)", right)
    ):
        return hit.group()
    return None


def classify(title, path):
    front_raw, basis = front_text(path)
    title = normalize(title)
    front = normalize(front_raw)
    abstract_weight = 0.7 if basis == "Title + opening text" else 1.0
    domain = {topic: domain_score(topic, title, front, abstract_weight) for topic in COMPILED}
    ai_term = generative_topic(title, front_raw, basis)
    if ai_term:
        score, evidence = domain["Learning, Statistics & AI"]
        domain["Learning, Statistics & AI"] = (max(score, 6.3 if AI_TERMS.search(title) else 4.3), evidence or [ai_term])
    ranked = sorted(domain.items(), key=lambda entry: (-entry[1][0], entry[0]))
    best = ranked[0][1][0]
    primary = ranked[0][0] if best >= 3.85 else UNCLASSIFIED
    tags = [topic for topic, (score, _) in ranked if topic == primary or score >= max(4.65, 0.56 * best)][:4]
    if ai_term:
        tags.append(AI_TOPIC)
    evidence = [f"{topic} · {', '.join(domain[topic][1])}" for topic in tags if topic in domain and domain[topic][1]]
    if ai_term:
        evidence.append(f"{AI_TOPIC} · {ai_term}")
    return {"primary": primary, "tags": tags, "ai_topic": bool(ai_term), "evidence": evidence, "basis": basis}


def read_index(args):
    if args.index:
        return json.loads(args.index.read_text(encoding="utf-8"))
    parser = ReportParser()
    parser.feed(args.report.read_text(encoding="utf-8"))
    return json.loads(parser.payloads["data"])


def main():
    parser = argparse.ArgumentParser(description="Reproduce the topic labels from paper titles and extracted text.")
    parser.add_argument("--report", type=Path, default=ROOT.parent / "stats.html")
    parser.add_argument("--index", type=Path, help="Use a JSON index of paper IDs and titles instead of the report.")
    parser.add_argument("--text-dir", type=Path, required=True, help="Directory of ID-based text files from pdftotext -layout.")
    args = parser.parse_args()
    index = read_index(args)
    metadata = {str(paper["id"]): paper for paper in index}
    if len(metadata) != len(index):
        raise ValueError("Paper IDs must be unique")
    labels = {identifier: classify(paper["title"], args.text_dir / f"{identifier}.txt")
              for identifier, paper in metadata.items()}
    print(json.dumps(labels, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
