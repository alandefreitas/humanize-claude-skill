"""
Labeled calibration samples for calibrate.py.

POS[criterion_id] = sentences (or paragraphs, for paragraph-scope criteria) where
the pattern IS present. NEG_SENTENCES / NEG_PARAGRAPHS = plain human writing where
none of the patterns is present (emails, technical prose, casual notes, talk lines).

Keep positives different from the examples quoted inside the question text where
possible, so the measurement is not just string matching.
"""

POS = {
    "undue_significance": [
        "The library stands as a testament to the community's commitment to open source.",
        "This release marks a pivotal moment that will shape the future of the ecosystem.",
        "Her work left an indelible mark on the field and reflects broader shifts in the industry.",
    ],
    "notability_inflation": [
        "He has been cited in The New York Times, Forbes and Wired, and is widely recognized as a leading expert.",
        "She maintains an active social media presence and is a renowned thought leader in her field.",
    ],
    "participle_tail": [
        "The team adopted the new tool in March, underscoring its commitment to quality.",
        "Sales rose by 12 percent last quarter, reflecting growing demand across the region.",
        "The committee approved the proposal, showcasing a new era of collaboration.",
    ],
    "promotional": [
        "Nestled in the heart of the old town, the cafe boasts a vibrant atmosphere and a rich culinary heritage.",
        "This groundbreaking framework delivers a stunning, world-class developer experience.",
    ],
    "vague_attribution": [
        "Experts argue that remote work improves productivity for most teams.",
        "Industry reports suggest that adoption will double within two years.",
        "Observers have noted that the company is losing ground to smaller rivals.",
    ],
    "ai_vocabulary": [
        "We need to delve into the intricate interplay between performance and maintainability.",
        "This comprehensive guide will help you navigate the nuanced landscape of modern tooling.",
        "The new API fosters a seamless and robust developer experience.",
    ],
    "copula_avoidance": [
        "The function serves as the main entry point of the program.",
        "The report represents a summary of last year's results.",
        "The park features three lakes and boasts a large bird population.",
    ],
    "negative_parallelism": [
        "It's not just a faster compiler, it's a new way of thinking about builds.",
        "Not only did the tests pass, but the build also got faster.",
        "The config lives in one file. One place to look, no hunting.",
    ],
    "rule_of_three": [
        "The new design is faster, cleaner and more reliable.",
        "We tested it on laptops, servers and phones, and it worked on each.",
    ],
    "false_range": [
        "The workshop covers everything from code reviews to team culture.",
        "Our customers range from startups to hospitals.",
    ],
    "passive_hidden_actor": [
        "It was decided that the launch would be postponed.",
        "Mistakes were made during the migration, and data was lost.",
        "The bug was fixed by the team on Friday.",
    ],
    "chatbot_artifact": [
        "I hope this helps! Let me know if you have any other questions.",
        "Certainly! Here is a summary of the key points you asked for.",
        "Would you like me to expand on any of these sections?",
    ],
    "knowledge_cutoff": [
        "As of my last update, the library had not released version 2.",
        "Based on the information available, specific details about the merger remain limited.",
    ],
    "sycophancy": [
        "Great question! You've touched on something really important.",
        "You're absolutely right, and that is an excellent point.",
    ],
    "filler_phrase": [
        "In order to run the tests, you need to install the dependencies first.",
        "Due to the fact that the server was down, we missed the deadline.",
        "It is important to note that the API has the ability to retry failed calls.",
    ],
    "stacked_hedging": [
        "This could potentially possibly cause issues in some cases.",
        "It might perhaps be somewhat beneficial, to some extent, for certain users.",
    ],
    "generic_conclusion": [
        "The future looks bright for the project and its growing community.",
        "This is a step in the right direction, and exciting times lie ahead.",
    ],
    "authority_trope": [
        "At its core, this is a question about trust.",
        "The real question is not whether to migrate, but when.",
        "At the end of the day, what really matters is the user.",
    ],
    "signposting": [
        "Let's dive in and explore how the scheduler works.",
        "Here's what you need to know before we break this down.",
        "In this article we will look at three ways to cache results.",
    ],
    "throat_clearing": [
        "Here's the thing: most teams never measure their build times.",
        "The truth is, nobody reads the documentation.",
        "Let me be clear, this was never about the money.",
    ],
    "emphasis_crutch": [
        "Make no mistake, this change will cost you. Full stop.",
        "Builds are slow. Let that sink in.",
    ],
    "business_jargon": [
        "Moving forward, we should double down on the platform and circle back next quarter.",
        "This is a game-changer, so let's lean into it and do a deep dive.",
    ],
    "meta_commentary": [
        "Plot twist: the slow part was never the database.",
        "In this section we'll walk you through the setup, as we'll see later.",
    ],
    "telling_not_showing": [
        "This is what good engineering actually looks like.",
        "This is genuinely hard, and it actually matters.",
    ],
    "vague_declarative": [
        "The reasons are structural and the implications are significant.",
        "The stakes are high and the consequences are real.",
    ],
    "rhetorical_setup": [
        "What if your builds took five seconds instead of five minutes?",
        "Think about it: every minute waiting is a minute not coding.",
    ],
    "false_agency": [
        "The data tells us that users prefer the dark theme.",
        "The numbers show a clear decline in churn since March.",
    ],
    "quotable_line": [
        "Speed is a feature. Slowness is a decision.",
        "Every abstraction is a promise you will one day have to keep.",
    ],
    "redundant_confirmation": [
        "Just to confirm, it is all done and everything is in order.",
        "I just wanted to reach out and let you know that I went ahead and sent the file.",
        "I have not attached the invoice yet.",
    ],
    "headless_statement": [
        "Six transforms, each written in JavaScript and Lua, ran over the corpus.",
        "Figures are the median of three runs.",
        "Present: X, Y and Z. Absent: A and B.",
    ],
    "filler_adverb": [
        "The code was completely refactored last week.",
        "This is basically how it works, and it is really quite simple.",
        "It is generally considered good practice to do this.",
    ],
    # paragraph scope
    "challenges_future": [
        "Despite its success, the project faces challenges, including limited funding and a shrinking contributor base. Looking ahead, the community remains optimistic about the road ahead.",
        "Despite these challenges, the team continues to grow. The future outlook remains positive as new opportunities emerge.",
    ],
    "elegant_variation": [
        "The protagonist leaves the city at dawn. The main character then meets a stranger on the road. By noon the central figure has lost everything, and the hero must start again.",
        "The compiler reads the file first. The translator then builds a tree, and the build tool emits the object code the toolchain needs.",
    ],
    "dramatic_fragments": [
        "Three words. That's it. Done. No more meetings. Ever.",
        "One test. One bug. One fix. Every single time.",
    ],
    "narrator_distance": [
        "Engineers often face a tension between speed and correctness. Organizations tend to reward the former, and individuals learn to adapt. Over time this shapes how teams make decisions.",
        "People in modern workplaces experience a constant stream of notifications. Workers find it hard to focus, and companies pay the price in lost output.",
    ],
    "ai_overall": [
        "In today's rapidly evolving digital landscape, it is crucial to leverage robust, scalable solutions that seamlessly enhance productivity.",
        "This comprehensive guide delves into the intricate tapestry of modern software development, highlighting key insights.",
        "By fostering a culture of innovation, organizations can unlock transformative outcomes and navigate complexity with confidence.",
    ],
    "ai_overall_paragraph": [
        "In today's rapidly evolving digital landscape, organizations must leverage robust solutions to stay competitive. By fostering a culture of innovation and embracing cutting-edge technologies, teams can unlock transformative outcomes. Ultimately, the key lies in navigating complexity with agility and resilience.",
        "Effective communication is crucial for success. It not only enhances collaboration but also fosters trust among team members. Moreover, it plays a pivotal role in driving innovation and ensuring alignment with organizational goals.",
    ],
}

NEG_SENTENCES = [
    "I booked the hotel like you suggested, and the receipt is attached.",
    "The flight lands at 6 p.m. on Friday, so I will take a taxi to the venue.",
    "Can you send me the invoice number when you get a chance?",
    "The build takes about four minutes on my laptop and nine on CI.",
    "We moved the config to a single file so new people can find it.",
    "Templates are instantiated at compile time, so the error shows up before you run anything.",
    "I'll be in Buzios from the 10th to the 14th for the committee meeting.",
    "My landlord still has not returned the deposit, so I filed the complaint on Monday.",
    "The function returns a pointer to the first element, or null if the vector is empty.",
    "Thanks for the review. I fixed the two typos and pushed again.",
    "Dinner is at eight. Bring the wine you mentioned.",
    "The test fails on Windows because the path separator is different.",
    "I read the paper twice and still do not understand section four.",
    "Our team has three people in Panama and two in Brazil.",
    "The car needs new tyres before the trip, so I booked the shop for Tuesday.",
    "Memory is allocated lazily, which is why the first call is slower.",
    "She asked me to review the slides by Thursday, and I said yes.",
    "The price went up from 40 to 55 dollars this year.",
    "If the server is down, the client retries three times and then gives up.",
    "I did not like the ending, but the first half of the book was good.",
    "The deadline for the abstract is March 3, so I will send you a draft next week.",
    "He pushed directly to main again, so the deploy broke for an hour.",
    "We use clang on macOS and gcc on Linux, and both builds are green.",
    "The doctor said the knee is fine and I can go back to the gym next week.",
    "I need the form signed by Friday or the bank will close the request.",
    "The talk is 45 minutes with 15 for questions.",
    "Our apartment is on the tenth floor and faces the sea.",
    "The parser handles comments by skipping to the end of the line.",
    "Please bring your passport and the printed ticket.",
    "I measured it three times and got 2.1, 2.3 and 2.2 seconds.",
    # technical documentation register
    "Optional extras: foo[serve] (HTTP server), foo[mcp] (MCP server), foo[onnx] (ONNX Runtime).",
    "Python 3.10 or newer is required.",
    "The same call works in any of the supported languages.",
    "Details are in the Fine-tuning section below.",
    "Pass max_len=8192 for long documents, since the default limit cuts them off.",
    "From the command line, run the tool with --preset triage to answer a ready-made question set.",
    "The router detects the script and language and sends non-English text to the multilingual checkpoint.",
    "Short inputs give identical answers with the larger limit, and speed follows the input's real length.",
    "Install it with pip, or with uv in a virtual environment.",
    "A NaN metric, limit or tolerance can no longer pass a gate.",
    "Step-by-step setup for each platform and troubleshooting are in the installation section.",
    "The export declares its dynamic dimensions in a form every supported torch version accepts.",
]

NEG_PARAGRAPHS = [
    "I booked the hotel like you suggested. The receipt is attached. The flight lands at 6 p.m. on Friday, so I will take a taxi to the venue and should be there by eight.",
    "The parser reads one line at a time. When it finds a comment marker it skips to the end of the line. Strings are handled separately because they can contain the marker.",
    "My landlord has not returned the deposit yet. I sent the written notice on Monday and kept a copy. If I hear nothing by the 15th, I will file the complaint with the housing office.",
    "The build takes about four minutes on my laptop and nine on CI. Most of the time goes into the two template-heavy files. Splitting them cut the CI run to six minutes.",
    "We have three people in Panama and two in Brazil, so meetings happen at 10 a.m. Panama time. That is 12 in Brasilia, which works for everyone except on Fridays.",
    "I read the paper twice. The method in section three is clear, but I do not follow the proof in section four. I wrote to the author and will send you her answer.",
]


def for_lang(lang):
    """(POS, NEG_SENTENCES, NEG_PARAGRAPHS) for a language; es/pt live in samples_langs.py."""
    if lang == "en":
        return POS, NEG_SENTENCES, NEG_PARAGRAPHS
    import samples_langs
    return samples_langs.SETS[lang]
