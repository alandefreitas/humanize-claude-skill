# The humanize rules

This file lists the rules behind the scanner. One of four components checks each rule, and the component is named in brackets at the end of the rule. A model criterion lives in `ai-tells/criteria.py`, where the jev server answers its question for every sentence or paragraph. A deterministic check lives in `ai-tells/ai_tells.py` (regex, no model). The vocabulary check lives in `simple-english/simple_english.py`. The editor's reading covers the rest, listed in section 5 of the report, because the model measured unreliable on it or because only a reader can see it. The skill acts on the report. This file is the source for the components. Edit this file when a rule changes, then edit the component that checks it.

Rule numbers follow the sources: A to E are Wikipedia's "Signs of AI writing" (patterns 1 to 29), F is from stop-slop plus personal additions, G to J are personal. The README explains where each rule came from.

## A. Content patterns

1. Undue significance. Claims of lasting importance or deeper meaning instead of what happened: *stands as a testament, pivotal, key role, indelible mark, marks a milestone, reflects broader trends, enduring legacy*. State what happened. [model `undue_significance`]
2. Notability inflation. Lists of media mentions, *leading expert, widely recognized, active social media presence*. Cite one specific source with context. [model `notability_inflation`]
3. Participle tails. An -ing phrase added at the end that gives opinion instead of a fact: *highlighting, underscoring, reflecting, symbolizing, showcasing, fostering, contributing to*. Cut it or make a real claim. [model `participle_tail`]
4. Promotional language. *boasts, vibrant, rich heritage, profound, nestled, in the heart of, groundbreaking, breathtaking, stunning, must-visit, renowned, world-class*. [model `promotional`]
5. Vague attribution. *experts argue, industry reports, observers have noted, some critics, many believe, studies show*. Name the person, study or date. [model `vague_attribution`]
6. Challenges and future prospects. The formula *despite its success, X faces challenges*, and general *looking ahead* final lines. Replace with concrete events. [model `challenges_future`, paragraph scope, unreliable for English, so reading]

## B. Language and grammar

7. AI vocabulary. *delve, crucial, pivotal, robust, seamless, leverage, landscape, tapestry, testament, underscore, enhance, foster, navigate, nuanced, comprehensive, transformative, intricate, meticulous, showcase, garner, interplay, moreover, furthermore, additionally* and the like. Replace with the plain word. [model `ai_vocabulary`. The vocabulary check catches the English list as off-list words, and the vale packs catch the es/pt lists]
8. Copula avoidance. *serves as, stands as, represents, boasts, features, offers, marks, acts as* where *is* or *has* would do. [model `copula_avoidance`, plus deterministic `copula_avoidance_literal` for *serves as* and *stands as*]
9. Negative parallelism. *not only X but Y*, *it's not just about X, it's Y*, and trailing negative fragments (*..., no guessing*). State the point. [model `negative_parallelism`]
10. Rule of three. Three adjectives, nouns or clauses for the sound where two carry the meaning. Use two. [model `rule_of_three`, unreliable, so reading]
11. Elegant variation. Cycling through different words for one thing (*protagonist, main character, central figure*). Pick one term and use it every time. [model `elegant_variation`, paragraph scope, unreliable, so reading]
12. False ranges. *from X to Y* where X and Y are not points on a scale. [model `false_range`]
13. Passive voice. Not a tell by itself. Change to active when the sentence names the actor (*the bug was fixed by the team*). Change it too when the writer knows the actor but hides it (*it was decided that*), or when the passive avoids blame (*mistakes were made*). Keep the passive when the actor is unknown or does not matter, or when the thing acted on is the topic (*templates are instantiated at compile time*). Keep it when the field writes it that way (*memory is allocated on the heap*). It also stays when active voice would be longer or harder to read, or when the format does not allow first person (double-blind reviews). The test: if the active form loses information, adds words or breaks a convention of the field, keep the passive. [deterministic `passive_agent_named` (clear case for a change) and `passive_voice` (a case for this test). The model failed both the judgment question and the plain passive question, see the README]

## C. Style patterns

14. Em dashes. Replace every em or en dash used as punctuation with a full stop (first choice), a comma, or parentheses when the clauses are too tightly coupled to split. Never with a semicolon, which is the same tell in a different mark. [deterministic `em_dash`]
14b. Semicolons in prose. Remove every one. Full stop first, comma when the clauses are tightly coupled. Keep only inside a list whose items contain commas, and inside real code. [deterministic `semicolon`, vale `humanize-local.SemicolonOveruse`]
15. Mechanical bold. Strip bold used for emphasis in running text. Keep it only when the emphasis itself carries meaning, which is rare. [deterministic `mechanical_bold`, two or more bold pieces in one block]
16. Bold inline headers. *Bold term + colon + explanation* lists. Convert to prose or to a flat list. [deterministic `bold_inline_header`]
17. Title Case Headings. Use sentence case. [deterministic `title_case_heading`]
18. Emoji in headings or bullets. Strip. [deterministic `emoji`]
19. Curly quotes. Replace with straight quotes. [deterministic `curly_quotes`]

## D. Communication patterns

20. Chatbot artifacts. *I hope this helps, Certainly!, Of course!, Would you like me to, Let me know if, Here is a summary, Feel free to ask*. Instructions that tell the reader what to run are not a chatbot artifact. [model `chatbot_artifact`]
21. Knowledge-cutoff disclaimers. *as of my last update, based on available information, while specific details are limited*. Replace with the fact or leave it out. [model `knowledge_cutoff`]
22. Sycophancy. *Great question!, You're absolutely right, That's an excellent point*. [model `sycophancy`]

## E. Filler and hedging

23. Filler phrases. *in order to* (to), *due to the fact that* (because), *at this point in time* (now), *has the ability to* (can), *it is important to note that* (cut). Also *in terms of*, *for the purpose of*, and the es/pt equivalents. [deterministic `filler_phrase_literal`. The model criterion `filler_phrase` is unreliable]
24. Stacked hedging. *could potentially possibly might*. One hedge at most, usually none. [model `stacked_hedging`]
25. Generic positive conclusions. *the future looks bright, exciting times lie ahead, a step in the right direction*. End on a concrete fact. [model `generic_conclusion`]
26. Hyphenated word pairs. *cross-functional, data-driven, decision-making, well-known, high-quality, real-time, long-term, end-to-end* and similar. Humans are not consistent about the hyphen, AI always adds it. Drop the hyphen on common pairs. [deterministic `hyphen_pair`, English]
27. Authority tropes. *the real question is, at its core, in reality, what really matters, fundamentally, the deeper issue, the heart of the matter*. [model `authority_trope`, unreliable, so reading]
28. Signposting. *let's dive in, let's explore, let's break this down, here's what you need to know, without further ado*. Just do the thing. A plain pointer (*see section 4*) is fine. [model `signposting`, unreliable, so reading]
29. Heading restatement. A one-line paragraph after a heading that repeats the heading. Cut it. [deterministic `heading_restatement`]

## F. Additions

F1. Throat-clearing openers. *Here's the thing, the truth is, let me be clear, it turns out, I'm going to be honest, the uncomfortable truth is, can we talk about*. [model `throat_clearing`, unreliable, so reading]
F2. Emphasis crutches. *Full stop., Period., Let that sink in., Make no mistake, This matters because, Read that again*. [model `emphasis_crutch`]
F3. Business jargon. *navigate, unpack, lean into, game-changer, double down, deep dive, take a step back, moving forward, circle back, on the same page, synergy, low-hanging fruit*. [model `business_jargon`]
F4. Meta-commentary. *Hint:, Plot twist:, Spoiler:, you already know this but, let me walk you through, in this section we'll, as we'll see, I want to explore*. [model `meta_commentary`]
F5. Telling instead of showing. *This is genuinely hard, this is what leadership actually looks like, this actually matters*. Show the evidence. [model `telling_not_showing`]
F6. Vague declaratives. *The reasons are structural, the implications are significant, the stakes are high*. Name the reason, implication or stake. [model `vague_declarative`]
F7. Rhetorical setups. *What if, Think about it, Consider this, Imagine, Picture this, Sound familiar?* [model `rhetorical_setup`]
F8. Dramatic fragments. *Three words. That's it. Done.* Complete sentences unless the fragment has a clear purpose. [model `dramatic_fragments`, paragraph scope]
F9. False agency. *The data tells us, the numbers show, the results suggest*. Name the interpreter. [model `false_agency`]
F10. Narrator at a distance. General ideas and general people where talking to the reader as *you* with concrete details fits better. [model `narrator_distance`, paragraph scope, unreliable, so reading]
F11. Wh- and So- openers. Sentences starting with *What, Why, How, So*. Turn it into a statement. [deterministic `wh_so_opener`, English]
F12. Quotable lines. Sentences written to sound good in a quote rather than to inform. One per piece is fine, a pattern is a tell. [model `quotable_line`]
F13. Equal-length runs. Three or more sentences in a row of similar length (within 20%, eight words or more). Vary on purpose. [deterministic `rhythm_equal_length`]
F14. Hard-wrapped prose. Paragraphs with line breaks at a fixed column. The breaks survive a copy into forms, slides and mail programs. Prose paragraphs are one line in the source, with one blank line between paragraphs. Keep line breaks in real code, lists, tables and poetry. Unwrap prose even inside a code fence (a speaker introduction pasted as a code block). Test: if joining the lines gives normal prose, the breaks are not real. [deterministic `hard_wrap`]
F15. Redundant confirmations and empty connectives. Any clause that adds nothing once the reader has the rest of the text. That covers empty confirmations (*it is all done, it's all set, just to confirm, as mentioned, as you know*). Filler verbs of intention (*I went ahead and, I took the liberty of, I just wanted to, I am writing to*) fall under it too, as does repeating what a later line shows. Connecting words with no contrast (*that said, with that in mind*) are the same tell. Announcing something you did not do (*I have not attached X*) is the same tell, and saying nothing is the fix. The delete test: delete the clause in your head. If the reader loses no fact, instruction or needed detail, cut it. [model `redundant_confirmation` with paragraph context, unreliable, so reading. The report prints the delete test in section 5]
F16. Headless statements. A sentence that opens with a noun phrase or a count and never says what it describes (*Six transforms ran over the corpus. Figures are the median of three runs. Present: X, Y.*). A statement names its subject and frames it (*The table below shows..., This section compares...*). Colon-led label lists are the same tell in list form. Test it two ways. Ask whether it would work unchanged as a table caption. Ask whether the reader can tell if it describes what follows, what came before, or a general fact. [model `headless_statement` with paragraph context, unreliable, so reading]

## G. Adverbs

Flag an adverb only when it adds no meaning (intensifier, hedge, filler), above all when it sits with passive voice or an unclear subject. The filler list: *really, just, literally, genuinely, honestly, simply, actually, basically, deeply, truly, fundamentally, inherently, inevitably, interestingly, importantly, crucially, completely, generally, essentially* (as a hedge), *quite, rather, fairly, very*. Keep adverbs that change the technical meaning: *lazily, atomically, explicitly, deliberately, incrementally, recursively, mutually, occasionally, primarily, rarely*. The test: if removing the adverb changes the technical meaning, keep it. If it loses only emphasis or hedging, cut it. *The code was completely refactored* becomes *I refactored the code*, and *memory is allocated lazily* stays. [model `filler_adverb`]

## H. Spoken delivery (talks, `--spoken`)

Sentences of at most 20 words. Contractions (*don't, it's, we're*). No semicolons and no em dashes, a listener never hears them. Active voice unless the actor is unknown or does not matter. Vary sentence length on purpose. Put a five-word sentence next to a fifteen-word one. Key idea first, because a listener has no way to go back. No bullet lists in prose passages. Read it out loud and replace any word that does not roll off the tongue. [deterministic sentence length switches to 20/30 words. Section 5 prints the rest for reading]

## I. Sentence length

Average 15 to 25 words, varied on purpose. Flag at 35 words: most such sentences are two ideas joined by *and* or *because*, or one idea wrapped in hedging. Hard limit 50: split. Short sentences are fine and break the pattern. This rule targets the single 45-word sentence, not the contrast between an 8-word and a 25-word one. [deterministic `sentence_long` and `sentence_too_long`. The vocabulary check also lists 35+ word sentences]

## J. Core vocabulary

Only words on a core list pass: the New General Service List (2,818 headwords, about 92% of everyday English) for English, the 3,000 most frequent lemmas (OpenSubtitles) for Spanish and Portuguese. The checker accepts inflections, irregular forms, contractions, names and acronyms on its own. Replace every off-list word with a core word (*leverage* to *use*, *approximately* to *about*, *sufficient* to *enough*, *demonstrate* to *show*, *purchase* to *buy*, *obtain* to *get*, *require* to *need*, *numerous* to *many*). Or keep it with a one-line reason. A technical term whose plain wording would be wrong or much longer (*allocator, deductible*) counts, and so does the ordinary name of the thing (*passport, landlord*). A proper noun the checker did not know passes too, as does the exact word where the core word would change the meaning (*estimate* vs *guess*). Do not replace one hard word with a long phrase, and do not keep a word because it sounds better. The targets are an off-list count of zero once every kept word has its reason, and an in-list share at or above 95% for messages and general prose. Technical documents may sit lower with a one-line reason. Rule J covers the English lists in B7 and F3 and catches the long tail they miss. [vocabulary check. Use `--top 1000` for readers new to the language or for spoken delivery, `--allow` for one-off terms, and `simple-english/allowlist.txt` for terms used across many documents]
