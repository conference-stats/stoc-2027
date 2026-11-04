import argparse
import json
import re
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from recompute import ReportParser

ROOT = Path(__file__).resolve().parent


def regex(pattern):
    return re.compile(pattern, re.I)


AI = r"(?:generative[\s-]+(?:artificial\s+intelligence|AIs?)|gen[ -]?AIs?|artificial\s+intelligence|(?-i:AIs?)|LLMs?|large\s+language\s+models?)"
MODEL = r"(?:Chat[ -]?GPT(?:[ -]?\d[\w.\-]*)?|GPT(?:[ -]?\d[\w.\-]*)?|Claude|Gemini|DeepSeek|Copilot|Codex|OpenAI(?:'s)?|Anthropic(?:'s)?|WorkBuddy|Fable\s+\d|(?:GPT[ -]?)?Astra|(?:Claude\s+)?Opus\s+\d|(?:Claude\s+)?Sonnet\s+\d|Grok|Perplexity|NotebookLM|Qwen|Grammarly|DeepL|Kimi|Cursor|Le Chat)"
TOOL = rf"(?:{AI}|{MODEL})"
HEADING = regex(
    rf"^\s*(?:(?:appendix\s+)?(?:[A-Z](?:\.\d+)*|\d+(?:\.\d+)*)[.\s]+)?"
    rf"(?P<head>(?:(?:acknowledg(?:e)?ments?|methodology|proof\s+development)\s+(?:and|&)\s+)?(?:(?:use\s+of\s+)?(?:generative\s+)?AI-assisted\s+technologies|(?:statements?\s+(?:on|of)\s+|disclosure\s+of\s+)?(?:the\s+)?"
    rf"(?:{AI}\s+(?:use|usage|disclosure|methodolog(?:y|ies|ical)|assistance|statement|declaration|policy|"
    rf"acknowledg(?:e)?ments?|methodol?og\w*|storytime|involvement|contributions?|tools?)"
    rf"|(?:use|usage|disclosure|assistance|declaration|acknowledg(?:e)?ment)\s+(?:of|with|on)\s+{AI}"
    rf"|(?:use|usage|disclosure|assistance|declaration)\s+(?:of|with|on)\s+(?:the\s+)?{MODEL}"
    rf"|(?:acknowledg(?:e)?ments?\s+and\s+)?{AI}\s*[- ]\s*(?:assisted|generated)\s+(?:research|work|writing|content))"
    rf"(?:\s+(?:disclosure|statement|declaration|note|methodology|policy|and\s+LLMs?|and\s+disclosure|and\s+acknowledg(?:e)?ments?|"
    rf"in\s+(?:the\s+)?(?:research|preparation|writing|this\s+(?:work|paper|manuscript))))?"
    rf"(?:\s+tools?)?))(?P<tail>\s*[:.\u2014\u2013-]\s*.*|\s+(?-i:[A-Z]).*|\s*)$"
)
QUICK_HEADING = regex(r"\b(?:AIs?|LLMs?|artificial\s+intelligence|large\s+language|ChatGPT|GPT|Claude|Gemini)\b")
TOC = regex(r"\.{2,}\s*\d+\s*$|\s{4,}\d+\s*$")
STOP = regex(r"^\s*(?:(?:[A-Z](?:\.\d+)*|\d+(?:\.\d+)*)[.]?\s{2,})?(?:References|Bibliography|Acknowledg(?:e)?ments?|Appendices)\s*$|^\s*(?:[A-Z](?:\.\d+)*|\d+(?:\.\d+)*)[.]?\s{2,}[A-Z].{1,130}$")
SECTION_LIKE = regex(r"^\s*(?:\d+|[ivx]+)\s*$")
NO = regex(
    rf"\b(?:no|without)\s+(?:(?:the\s+)?(?:use|usage|assistance|aid|help)\s+of\s+|using\s+)?(?:any\s+)?{TOOL}\b"
    rf"|\b(?:not|never)\s+(?:make\s+use\s+of\s+|rely\s+on\s+|use[ds]?\s+|employ(?:ed)?\s+|consult(?:ed)?\s+|engag(?:e|ed)\s+with\s+)(?:any\s+)?{TOOL}\b"
    rf"|\b{TOOL}\b.{{0,90}}?\b(?:was|were|is|are|has|have)\s+(?:never|not)(?:\s+been)?\s+(?:used|employed|involved|utilized|consulted)\b"
    rf"|\b(?:did\s+not|didn['’]t|have\s+not|haven['’]t)\s+(?:use|consult|employ|utilize|rely\s+on)\s+.{{0,25}}?\b{TOOL}\b"
    rf"|\b(?:none\s+of\s+the\s+authors|neither\s+author)\s+(?:used|employed)\s+{TOOL}\b"
    rf"|\b{AI}\s+usage\s*[:–—-]\s*(?:none|n/?a)\b"
    rf"|\b(?:fully|entirely|solely)\s+(?:developed|written)\s+(?:and\s+(?:developed|written)\s+)?by\s+(?:the\s+)?human\s+authors\b"
)
FIRST = r"(?:we|(?-i:I)|the\s+(?:(?:first|second|third|last|corresponding)\s+)?(?:co-?)?authors?|one\s+of\s+the\s+authors?)"
USED = r"(?:used|use|acknowledge(?:s)?\s+using|(?:made|make|making)\s+(?:(?:substantial|extensive|limited)\s+)?use\s+of|employed|utili[sz]ed|leveraged|consulted|queried|prompted|asked|worked\s+with|experimented\s+with|interacted\s+with|relied\s+on|engaged\s+with|collaborated\s+with|turned\s+to|acknowledge(?:s)?\s+(?:having\s+)?(?:the\s+)?use\s+of)"
QUAL = r"(?:(?:a|an|the|various|both|multiple|several|many|different|state-of-the-art|commercial|frontier|some|of|variety|range|few|modern|commercially|available|language|foundation|leading|primarily|mostly|selectively|extensively|occasionally|initially|only|sparingly|limited|advanced|successfully|in|particular|also|briefly|carefully|lightly|frequently|often)\s+){0,8}"
OWN = r"(?:this|our|the)\s+(?:paper|manuscript|work|proofs?|results?|research|project|submission|draft|writing|presentation|study)"
DIRECT = regex(
    rf"\b{FIRST}\s+(?:(?:have|has|had|also|occasionally|only|then|primarily|extensively|initially|subsequently|experimentally|sometimes|did|in\s+particular|sparingly|further)\s+){{0,5}}{USED}\s+{QUAL}{TOOL}\b"
    rf"|\b(?:this|our|the)\s+(?:paper|manuscript|work|proofs?|results?|research|project|submission|draft|writing)\s+(?:was|were|has\s+been|have\s+been)\s+.{{0,80}}?\b(?:by|with)\s+(?:the\s+(?:help|assistance|aid)\s+of\s+)?{TOOL}\b"
    rf"|\b(?:we|I|authors?)\s+acknowledge(?:s)?\s+{TOOL}\b"
    rf"|\b{FIRST}\s+(?:received|sought|obtained|got)\s+(?:\w+\s+){{0,6}}(?:help|assistance|feedback|support|suggestions)\s+from\s+{TOOL}\b"
)
PASSIVE = regex(
    rf"\b{TOOL}\b.{{0,85}}?\b(?:was|were|is|are|has\s+been|have\s+been)\s+(?:(?:also|only|then|subsequently|further|extensively|primarily|occasionally|in\s+turn)\s+){{0,2}}(?:used|employed|utili[sz]ed|consulted|leveraged)\b"
    rf"|\b(?:with|using)\s+(?:(?:the\s+)?(?:help|aid|assistance|support|guidance)\s+of\s+{TOOL}|{AI}\s+(?:assistance|guidance|support|input))\b"
    rf"|\b(?:obtained|discovered|developed|generated|drafted|revised|written|written\s+up|produced|checked|proofread|edited|derived|implemented|verified|explored|simplified|suggested)\b.{{0,36}}?\b(?:by|using|with|via|from)\s+(?:both\s+)?{TOOL}\b"
    rf"|\b{MODEL}\b.{{0,40}}?\b(?:suggested|assisted|helped|generated|discovered|developed|improved|found|wrote|drafted|edited|proposed|produced|provided|proved|derived|identified|contributed)\b"
    rf"|\b(?:we|I)\s+(?:then\s+|also\s+)?(?:gave|supplied|fed|presented|provided|asked|taught)\s+(?:(?:a|the|our)\s+\w+\s+to\s+|the\s+)?{TOOL}\b"
    rf"|\b(?:interact\w*|brainstorm\w*|discuss\w*|collaborat\w*)\s+with\s+{TOOL}\b"
    rf"|\b{TOOL}\b.{{0,35}}?\b(?:helps?|completed|gave|did|performed|carried\s+out|participated|was\s+instrumental|played)\b"
    rf"|\b(?:our|the author(?:s|’s|'s)?)\s+use\s+of\s+{TOOL}\b"
)
TASK = regex(r"\b(?:proofread\w*|copy[ -]?edit\w*|typos?|typograph\w*|brainstorm\w*|literature|polish\w*|gramm\w*|manuscript|acknowledge\w*|writ(?:e|ing|ten)|research\s+(?:process|ideas?))\b")
AUTHOR_CONTEXT = regex(rf"\b{OWN}\b|\b(?:we|I|authors?)\b|\b(?:manuscript|proofread\w*|copy[ -]?edit\w*)\b")
STUDY_CONTEXT = regex(r"\b(?:benchmark|dataset|synthetic data|evaluat\w*|test(?:ing)?|experiment\w*|model outputs?|prompts?|performance|classification|training|test set|embedding\w*|inference|sampling|queries|accuracy)\b")
NO_SCOPE = regex(r"\b(?:for|to|in)\s+(?:the\s+)?(?:develop\w*|writ\w*|research\w*|draft\w*|produc\w*|generat\w*|construct\w*|formulat\w*|mak\w*|creat\w*|deriv\w*|proofs?)\b")
STRONG_NO = regex(r"\b(?:at any stage|for anything|whatsoever|any aspect|at all|in any way|throughout|any part|any purpose|never used)\b")
CONTRAST = regex(r"\b(?:but|however|although|except|nevertheless|yet|rather|only)\b")
TAG_PATTERNS = {
    "Editing and exposition": r"\b(?:proof[ -]?read\w*|copy[ -]?edit\w*|edit(?:ing|ed|s)?|typos?|typographic\w*|polish\w*|wording|linguistic\w*|language\s+(?:refinement|editing|quality)|gramm\w*|clarity|present(?:ation|ing)|exposition|styl(?:e|istic)|format(?:ting)?|typeset\w*|translat\w*|diagram\s+prepar\w*)\b",
    "Manuscript drafting": r"\b(?:draft(?:ed|ing)?|writ(?:e|ing|ten)|generat(?:e|ed|ing))\b.{0,42}\b(?:paper|manuscript|sections?|paragraphs?|text|prose|exposition)\b|\b(?:AI|LLM)[ -]generated\s+drafts?\b",
    "Literature search": r"\bliterature\b.{0,30}\b(?:search\w*|check\w*|review\w*|survey\w*)\b|\b(?:search\w*|find\w*|identif\w*|check\w*|discov\w*|locat\w*|review\w*)\b.{0,45}\b(?:literature|related\s+(?:papers?|work)|references|citations|prior\s+(?:work|results?))\b|\brelated\s+(?:papers?|work)\b.{0,30}\b(?:search\w*|identif\w*)\b",
    "Brainstorming and exploration": r"\b(?:brain[ -]?storm\w*|mathematical\s+exploration|theoretical\s+exploration|explor\w*\s+(?:possible\s+)?(?:ideas?|approaches?|strategies|directions?|variants|proof\s+(?:ideas|strategies))|suggest\w*\s+(?:possible\s+)?(?:ideas?|directions?|approaches?|strategies)|generat\w*\s+ideas?|proof\s+(?:ideas|strategies)|thinking\s+of\s+applications|bounc\w*\s+ideas|ideation)\b",
    "Verification and error checking": r"\b(?:verif\w*|validat\w*|debug\w*|sanity\s+check\w*|check\w*\s+(?:\w+\s+){0,5}(?:proofs?|arguments?|math\w*|correctness|consistency|errors?|details?|contents?|steps?|inconsistenc\w*)|error[ -]check\w*|find\w*\s+\w+\s+errors|correctness\s+check\w*|review\w*\s+(?:\w+\s+){0,3}(?:proofs?|arguments?|manuscript|paper))\b",
    "Calculations and examples": r"\b(?:calculat\w*|symbolic\s+comput\w*|algebraic\s+manipulat\w*|simplif\w*\s+expressions?|worked\s+examples?|numeric(?:al)?\s+comput\w*|counter[ -]?examples?|small\s+(?:examples?|instances?))\b",
    "Code and experiments": r"\b(?:code|coding|code[- ]generation|scripts?|implement(?:ing|ation|ed)|programming|computational\s+experiments?|simulat\w*|numerical\s+experiments?|software|Lean\s+formalization|formaliz\w*\s+(?:\w+\s+){0,3}Lean)\b",
    "Proof or result development": r"\b(?:develop\w*|generat\w*|draft\w*|discov\w*|obtain\w*|deriv\w*|writ\w*|prov(?:e|ed|ing)|establish\w*|simplif\w*|strengthen\w*|generaliz\w*|generaliz\w*|suggest\w*)\s+(?:(?:most|all|some|many|several|parts?)\s+of\s+)?(?:\w+\s+){0,4}(?:proofs?|results?|lemma(?:s|ta)?|theorems?|propositions?|lower\s+bounds?|upper\s+bounds?|constructions?)\b|\bproofs?\b.{0,45}\b(?:drafted|generated|developed|written|discovered|obtained|simplified)\b|\btechnical\s+(?:contributions?|development)\b",
}
TAG_RE = {name: regex(pattern) for name, pattern in TAG_PATTERNS.items()}
TOOL_RE = {
    "OpenAI": regex(r"\b(?:OpenAI|Chat[ -]?GPT|GPT(?=[ -]?\d)|Codex|Astra)\b|\bGPT(?=[ -]?\d)"),
    "Anthropic": regex(r"\b(?:Anthropic|Claude|Fable\s+\d|Opus\s+\d|Sonnet\s+\d)\b"),
    "Google": regex(r"\b(?:Gemini|NotebookLM|Google\s+(?:AI|Bard))\b"),
    "DeepSeek": regex(r"\bDeepSeek\b"),
    "GitHub / Microsoft Copilot": regex(r"\b(?:GitHub\s+|Microsoft\s+)?Copilot\b"),
    "Perplexity": regex(r"\bPerplexity(?:\s+AI)?\b"),
    "xAI": regex(r"\b(?:xAI|Grok)\b"),
    "Qwen": regex(r"\bQwen\b"),
    "Kimi": regex(r"\bKimi\b"),
    "Grammarly": regex(r"\bGrammarly\b"),
    "DeepL": regex(r"\bDeepL\b"),
    "Cursor": regex(r"\bCursor\b"),
    "Mistral": regex(r"\b(?:Mistral|Le Chat)\b"),
}
MODEL_RE = regex(
    r"\b(?:Chat[ -]?GPT|GPT)[ -]?\d+(?:\.\d+)*(?:[ -]+(?:Astra|Pro|Thinking|Extended|Instant|Codex|Sol|Terra|Luna|Mini|Nano|Turbo|High|XHigh|Ultra)){0,2}"
    r"|\bGPT[ -]?(?:o\d+(?:[ -]?mini)?|4o)\b|\b(?:OpenAI\s+)?o[134](?:[ -]?(?:mini|pro))\b"
    r"|\b(?:Claude\s+)?(?:Opus|Sonnet|Fable|Haiku)[ -]?\d+(?:\.\d+)*(?:[–-]\d+\.\d+)?"
    r"|\bClaude\s+\d+(?:\.\d+)*\s+(?:Opus|Sonnet|Fable|Haiku)\b|\bClaude\s+Code\b"
    r"|\bGemini[ -]?\d+(?:\.\d+)*(?:[ -]+(?:Pro|Flash|Ultra|Deep Think|Thinking)){0,2}"
    r"|\b(?:DeepSeek|Grok|Qwen|Kimi)[ -]?(?:[VRK][ -]?)?\d+(?:\.\d+)*\b|\b(?:ChatGPT\s+)?Astra\b"
)


def clean(text):
    return unicodedata.normalize("NFKC", text).translate(str.maketrans({"\u00ad": "", "‑": "-", "−": "-", "‒": "-", "’": "'", "‘": "'"}))


def flatten(lines):
    text = "\n".join(lines)
    text = re.sub(r"(?<=[a-z])[-]\n\s*(?=[a-z])", "", text)
    text = re.sub(r"(?i)Chat[-]\n\s*GPT", "ChatGPT", text)
    return " ".join(text.split())


def collect_headings(pages):
    for p, lines in enumerate(pages):
        for i, line in enumerate(lines):
            if len(line.strip()) > 330 or not QUICK_HEADING.search(line) or TOC.search(line):
                continue
            match = HEADING.match(line)
            if not match:
                continue
            heading = match["head"]
            lead = match["tail"].lstrip(" :.—–-")
            content = [lead] if lead else []
            done = False
            length = len(lead)
            for j, other_lines in enumerate(pages[p:p + 3]):
                if done:
                    break
                for following in (other_lines[i + 1:] if j == 0 else other_lines):
                    if TOC.search(following) and re.search(r"\.{2,}", following):
                        done = True
                        break
                    if STOP.match(following) or (QUICK_HEADING.search(following) and HEADING.match(following)) or regex(r"^\s*(?:Acknowledg(?:e)?ments?|References|Bibliography)\s*[.:]").match(following):
                        done = True
                        break
                    if not SECTION_LIKE.match(following):
                        content.append(following)
                        length += len(following)
                    if length > 3200:
                        done = True
                        break
            excerpt = flatten(content)
            if excerpt and not regex(r"^\d+\s+(?:[A-Z]\s+|\d+(?:\.\d+)*\s+)").match(excerpt):
                yield p + 1, heading, excerpt


def collect_inline(pages):
    for p, lines in enumerate(pages, start=1):
        for chunk in re.split(r"\n\s*\n", "\n".join(lines)):
            words = flatten(chunk.splitlines())
            if not words or not MODEL_MENTION.search(words):
                continue
            for match in re.finditer(rf"\b{TOOL}\b", words, re.I):
                left = max(0, match.start() - 115)
                right = min(len(words), match.end() + 190)
                excerpt = words[left:right]
                if DIRECT.search(excerpt) and (TASK.search(excerpt) or not STUDY_CONTEXT.search(excerpt)):
                    relevant = [clause for clause in clauses(words) if DIRECT.search(clause)]
                    if relevant:
                        excerpt = " ".join(relevant[:3])[:1100]
                    yield p, "", excerpt
                    break
                if NO.search(excerpt) and AUTHOR_CONTEXT.search(excerpt) and TASK.search(excerpt):
                    yield p, "", excerpt
                    break
                if (PASSIVE.search(excerpt) or EDIT_EXCEPTION.search(excerpt)) and AUTHOR_CONTEXT.search(excerpt) and TASK.search(excerpt):
                    yield p, "", excerpt
                    break


def clauses(text):
    return re.split(r"(?<=[.!?;])\s+(?=[A-Z])|\s+(?:but|however|except that|although|while|whereas)\s+", text, flags=re.I)


EDIT_EXCEPTION = regex(r"\b(?:apart\s+from|except\s+for|other\s+than|with\s+the\s+exception\s+of)\b[^.!?;]{0,100}\b(?:AI|LLMs?|ChatGPT)\b[^.!?;]{0,50}\b(?:language\s+editing|proofread\w*|copy[ -]?edit\w*|editing|typographic\w*)\b")
SUBSTANTIVE_WORDING = regex(r"\b(?:was|were|is|are|been)\s+(?:directly\s+)?(?:developed|proved|discovered|obtained|drafted|constructed|generated)\b[^!?;]{0,135}\b(?:ChatGPT|GPT[ -]?\d|Astra|Claude|Gemini|Fable|AI\s+tools|LLMs?)\b")


def status_of(evidence, headed):
    if not evidence:
        return "unclear"
    if EDIT_EXCEPTION.search(evidence):
        return "use"
    found_no = False
    for clause in clauses(evidence):
        if NO.search(clause) and (headed or not regex(r"\b(?:model|algorithm|uses?)\s+no\s+(?:AI|LLM)\b").search(clause)):
            found_no = True
            if regex(r"\b(?:substantially|extensively|materially)\b").search(clause):
                found_no = False
            continue
        if DIRECT.search(clause) or PASSIVE.search(clause) or (headed and SUBSTANTIVE_WORDING.search(clause)):
            return "use"
        if headed and re.search(rf"\b{TOOL}\b", clause, re.I) and regex(r"\b(?:assist\w*|collaborat\w*|suppl\w*|AI-generated|model\s+pilot|model\s+played|input\s+from\s+AI|with\s+GPT|with\s+ChatGPT|(?:conversations?|discussions?)\s+with|with\s+Claude|used\s+for|used\s+throughout|interactions?\s+with)\b").search(clause):
            return "use"
        if headed and regex(r"^(?:None|N/?A|Not applicable)\.?$").fullmatch(clause):
            found_no = True
    if found_no:
        if headed and re.search(rf"\b{TOOL}\b", evidence, re.I) and regex(r"\b(?:also|only|then|thus|instead|subsequently|however)\b").search(evidence) and regex(r"\b(?:assist\w*|help\w*|prompt\w*|gave|tool\b|editing|proofreading|drafted)\b").search(evidence):
            return "unclear"
        return "no_use"
    if headed and (re.search(rf"\b{TOOL}\b", evidence, re.I) and TASK.search(evidence)):
        return "unclear"
    return "unclear"


HUMAN_CLAUSE = regex(
    r"^\s*(?:the\s+(?:human\s+)?authors?|we|I|he|she)\s+(?:(?:carefully|subsequently|also|then|finally|independently|manually|personally|have|has|had|extensively)\s+){0,5}"
    r"(?:verif\w*|check\w*|review\w*|take\s+responsibility|assume\s+responsibility|are\s+(?:fully\s+)?responsible|wrote|rewrote|reworked|reconstruct\w*)\b"
    r"|\b(?:take|takes|assume|assumes|retain|retains)\s+(?:full\s+)?responsibility\b"
)
PROOF_EXCLUSION = regex(r"\b(?:select\w*|chose|choos\w*|checking|verification|proofread\w*|verifying)\b")
MODEL_MENTION = regex(rf"\b{TOOL}\b")


def author_use_clauses(text):
    return [
        clause for clause in clauses(text)
        if not NO.search(clause) and not (HUMAN_CLAUSE.search(clause) and not (DIRECT.search(clause) or PASSIVE.search(clause)))
    ]
def describe_use(text):
    parts = author_use_clauses(text)
    tags = [
        name for name, pattern in TAG_RE.items()
        if any(pattern.search(clause)
               and not (name == "Proof or result development" and PROOF_EXCLUSION.search(clause)
                        and not regex(r"\b(?:and\s+(?:develop|draft|generat|discover|writ|simplif|obtain)|assist\w*\s+(?:in|with)\s+(?:develop|draft|generat|discover|writ|simplif|obtain))").search(clause))
               and not regex(r"\b(?:independently|entirely\s+by|solely|without\s+AI|by\s+the\s+authors\s+alone|due\s+to\s+the\s+authors)\b").search(clause)
               for clause in parts)
    ]
    tools = [tool for tool, pattern in TOOL_RE.items() if pattern.search(text)]
    models = set()
    for match in MODEL_RE.finditer(text):
        model = re.sub(r"^chat[ -]?gpt[ -]?(?=\d)", "GPT-", match[0], flags=re.I)
        model = re.sub(r"^gpt[ -]?(?=\d)", "GPT-", model, flags=re.I)
        model = re.sub(r"^gpt-4\s+o$", "GPT-4o", model, flags=re.I)
        model = re.sub(r"(?<=\d)-(?=[A-Za-z])", " ", model)
        model = re.sub(r"\s+", " ", model).title().replace("Gpt", "GPT")
        model = re.sub(r"^((?:Opus|Sonnet|Fable|Haiku) )", r"Claude \1", model)
        models.add(model)
    if "Astra" in models and any(m.endswith(" Astra") for m in models):
        models.remove("Astra")
    if not tags and EDIT_EXCEPTION.search(text):
        tags = ["Editing and exposition"]
    return tags or ["Other or unspecified"], tools, sorted(models)



EXTENT = r"(?:most\s+of\s+(?:the\s+)?(?:proofs?|results?|paper)|all\s+(?:of\s+(?:the\s+)?)?(?:proofs?|(?:the\s+)?sections?)|(?:a|the)\s+(?:(?:full|complete|entire|first)\s+(?:paper|manuscript)|(?:full|complete|entire)\s+draft(?!\s+proof)|first\s+draft\s+of\s+(?:the\s+)?(?:paper|manuscript))|(?:a|the)\s+draft\s+(?:paper|manuscript)|substantial\s+portions?\s+of\s+(?:the\s+)?(?:draft|manuscript|paper)|(?:core|main|central|primary)\s+(?:result|proof|theorem|construction)s?)"
ARTIFACT = rf"(?:proofs?(?:\s+sketch(?:es)?)?|theorems?|lemmas?|propositions?|(?:lower|upper)\s+bounds?|results?|constructions?|drafts?\s+(?:paper|manuscript)|(?:first|initial)\s+(?:manuscript|paper)\s+drafts?|(?:portions?|parts?|sections?)\s+of\s+(?:the\s+)?(?:paper|manuscript)|{EXTENT})"
GENERATION = r"(?:generat\w*|draft\w*|produc\w*|discover\w*|deriv\w*|obtain\w*|prov(?:e|es|ed|ing)|complet\w*|writ(?:e|es|ing|ten)|wrote|came\s+up\s+with|develop\w*)"
MODEL_ACTS = regex(
    rf"\b{TOOL}\b[^.!?;]{{0,60}}?\b{GENERATION}\s+(?:\w+\s+){{0,5}}{ARTIFACT}\b"
    rf"|\b{ARTIFACT}\b[^.!?;]{{0,44}}?\b(?:was|were|have\s+been|has\s+been)\s+{GENERATION}\s+(?:with|using|by|via)\s+(?:both\s+)?(?:the\s+(?:help|aid|assistance)\s+of\s+)?{TOOL}\b"
    rf"|\b{TOOL}\b[^.!?;]{{0,40}}?\b(?:used|help(?:ed|s)?|assist\w*|instrumental)\s+(?:us\s+|in\s+|with\s+|to\s+|for\s+){{0,3}}{GENERATION}\s+(?:\w+\s+){{0,5}}{ARTIFACT}\b"
    rf"|\b(?:these\s+(?:tools|models)|(?:the|this|same)\s+(?:tool|model|AI|system)|it)\s+(?:also\s+|then\s+)?{GENERATION}\s+(?:\w+\s+){{0,5}}{ARTIFACT}\b"
)
SCOPE_GAP = regex(r"\b(?:only|primarily|limited\s+to)\s+(?:for\s+)?(?:writing|presentation|proofreading|editing|language)\b")
EXPLICIT_RESEARCH = regex(
    r"\b(?:mechanism\s+and\s+proof\s+development|mathematical\s+(?:contributions?|assistance|development)|"
    r"develop\w*\s+(?:through|with|via)\s+conversations?|proof\s+details|details\s+of\s+the\s+proof|"
    r"(?:assist\w*|help\w*)\s+(?:us\s+)?(?:with|in)\s+(?:\w+\s+){0,4}(?:proofs?|analys[ie]s|extensions?|algorithms?|constructions?)|"
    r"(?:identif\w*|suggest\w*|find\w*)\s+(?:\w+\s+){0,4}(?:function|argument|proof|construction|algorithm)|"
    r"develop\w*\s+(?:\w+\s+){0,4}(?:arguments?|frameworks?)|construct\w*\s+(?:\w+\s+){0,4}(?:proofs?|arguments?|circuits?))\b"
)
GENERATION_LIMIT = regex(
    r"\b(?:asked|prompted|queried|instructed)\b.{0,45}\b(?:to\s+try|to\s+prove)\b"
    r"|\b(?:proof\s+(?:idea|sketch|strategy)|formaliz\w*\s+of\s+(?:our|the)\s+main\s+result|verification\s+of\s+(?:our|the))\b"
    r"|\b(?:suggest\w*\s+(?:\w+\s+){0,3}(?:argument|idea|strategy)|without\s+success)\b"
)
UNKNOWN_SCOPE = regex(r"\b(?:some\s+(?:assistance|help)|used\s+extensively|during\s+(?:the\s+)?(?:development|preparation|research)|in\s+developing\s+this\s+paper)\b")


def depth_of(text, tags):
    parts = author_use_clauses(text)
    for part in parts:
        if MODEL_ACTS.search(part) and not (PROOF_EXCLUSION.search(part) or SCOPE_GAP.search(part) or GENERATION_LIMIT.search(part)):
            if regex(rf"\b{EXTENT}\b").search(part):
                return "Extensive generation"
    if any(MODEL_ACTS.search(part) and not PROOF_EXCLUSION.search(part) and not SCOPE_GAP.search(part) and not GENERATION_LIMIT.search(part) for part in parts):
        return "Substantive generation"
    if any(EXPLICIT_RESEARCH.search(part) for part in parts):
        return "Research contribution"
    if set(tags).intersection({"Brainstorming and exploration", "Calculations and examples", "Code and experiments", "Proof or result development", "Manuscript drafting"}):
        return "Research contribution"
    if set(tags).intersection({"Literature search", "Verification and error checking"}):
        return "Support and checking"
    if tags == ["Editing and exposition"] and not UNKNOWN_SCOPE.search(text):
        return "Editing only"
    return "Scope unspecified"


def page_lines(page):
    lines = page.splitlines()
    numbered = regex(r"^\s{0,12}\d{1,5}\s{1,8}(?=\S)")
    nonblank = sum(bool(line.strip()) for line in lines)
    if nonblank > 8 and sum(bool(numbered.match(line)) for line in lines) >= nonblank * .55:
        return [numbered.sub("", line, count=1) for line in lines]
    return lines


def classify(text):
    result = dict(status="no_statement", tags=[], tools=[], models=[], page=None, note="")
    if not text or not re.search(r"(?:[A-Za-z]{3,}\W+){12}", text):
        return dict(result, status="unavailable")
    pages = [page_lines(page) for page in clean(text).split("\f")]
    candidates = [
        (status_of(excerpt, True), page, heading, excerpt)
        for page, heading, excerpt in collect_headings(pages)
    ]
    if not candidates or not any(status == "use" for status, *_ in candidates):
        candidates += [
            (status_of(excerpt, False), page, heading, excerpt)
            for page, heading, excerpt in collect_inline(pages)
        ]
    if not candidates:
        return result
    priority = {"use": 2, "no_use": 1, "unclear": 0}
    selected = max(candidates, key=lambda x: (priority[x[0]], bool(x[2]), -x[1]))
    status, page, heading, excerpt = selected
    if status == "unclear" and not heading:
        return result
    result.update(status=status, page=page, heading=heading)
    if status == "use":
        tags, tools, models = describe_use(excerpt)
        result.update(tags=tags, tools=tools, models=models, depth=depth_of(excerpt, tags))
    if status == "no_use":
        result["note"] = "The manuscript explicitly states that the authors did not use AI within the scope they describe."
    if status == "unclear":
        result["note"] = "The manuscript has a possible disclosure that could not be classified confidently."
    return result, excerpt


def classify_file(path):
    return classify(path.read_text(encoding="utf-8", errors="replace") if path.is_file() else "")


def main():
    parser = argparse.ArgumentParser(description="Screen extracted manuscript text for author-reported AI use.")
    parser.add_argument("--report", type=Path, default=ROOT.parent / "stats.html")
    parser.add_argument("--index", type=Path, help="Use a JSON index of paper IDs instead of the report.")
    parser.add_argument("--text-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.index:
        papers = json.loads(args.index.read_text(encoding="utf-8"))
    else:
        report = ReportParser()
        report.feed(args.report.read_text(encoding="utf-8"))
        papers = json.loads(report.payloads["data"])

    keys = [str(paper["id"]) for paper in papers]
    if len(keys) != len(set(keys)):
        raise ValueError("Paper IDs must be unique")
    results = {}
    paths = [args.text_dir / f"{key}.txt" for key in keys]
    with ProcessPoolExecutor(max_workers=4) as workers:
        for key, outcome in zip(keys, workers.map(classify_file, paths, chunksize=12)):
            if isinstance(outcome, tuple):
                outcome = outcome[0]
            if outcome["status"] == "use" and not outcome.get("depth"):
                outcome["depth"] = "Scope unspecified"
            results[key] = outcome
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
