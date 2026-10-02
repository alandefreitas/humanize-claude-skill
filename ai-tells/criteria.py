"""
Criteria for ai_tells.py: one entry per AI-writing pattern that the jev
server (laya-serve, /v1/systemone) evaluates on every piece of text.

Every entry:
  id        short stable name, used in reports and --criteria
  rule      the rule letter/number in ../RULES.md
  scope     "sentence" or "paragraph" (what unit of text the question is asked over)
  context   sentence-scope only: also show the model the surrounding paragraph
  type      "noul" (calibrated P(yes)) or "score" (ordered levels in `levels`)
  q         the question, keyed by language. "en" is required; "es"/"pt" are used
            when the input is in that language, otherwise "en" is used over the
            foreign text (the multilingual checkpoint reads both).
  threshold optional per-criterion flag threshold (overrides --threshold).
            Set from calibrate.py measurements; see README.md.
  plain_neg_only
            calibrate against plain human negatives only, not against other
            criteria's positives. For broad patterns (AI vocabulary, filler
            adverbs) that legitimately co-occur with the other tells.

Field names inside backticks (`sentence`, `paragraph`) match the keys of the
state dict the script sends, which is how laya presets phrase questions.
"""

CRITERIA = [
    # ---------------- A. Content patterns ----------------
    dict(id="undue_significance", rule="A1", scope="sentence", type="noul",
         q=dict(en="Does `sentence` claim lasting importance or symbolic meaning instead of stating what happened (stands as a testament, pivotal, key role, indelible mark, marks a milestone, reflects broader trends, enduring legacy)?",
                es="¿`sentence` afirma una importancia duradera o un significado simbólico en vez de decir qué pasó (es un testimonio de, fundamental, papel clave, deja una huella imborrable, marca un hito, refleja tendencias más amplias, legado perdurable)?",
                pt="`sentence` afirma uma importância duradoura ou um significado simbólico em vez de dizer o que aconteceu (é um testemunho de, fundamental, papel-chave, deixa uma marca indelével, marca um marco, reflete tendências mais amplas, legado duradouro)?")),
    dict(id="notability_inflation", rule="A2", scope="sentence", type="noul",
         q=dict(en="Does `sentence` inflate someone's importance by listing media mentions or calling them a leading expert, widely recognized, or having an active social media presence?")),
    dict(id="participle_tail", rule="A3", scope="sentence", type="noul",
         q=dict(en="Does `sentence` end with a tacked-on -ing phrase that adds commentary instead of a fact (highlighting, underscoring, reflecting, symbolizing, showcasing, fostering, contributing to, emphasizing)?",
                es="¿`sentence` termina con una frase de gerundio añadida que agrega comentario en vez de un hecho (destacando, subrayando, reflejando, simbolizando, mostrando, fomentando, contribuyendo a, enfatizando)?",
                pt="`sentence` termina com uma frase de gerúndio acrescentada que adiciona comentário em vez de um fato (destacando, ressaltando, refletindo, simbolizando, mostrando, fomentando, contribuindo para, enfatizando)?")),
    dict(id="promotional", rule="A4", scope="sentence", type="noul",
         q=dict(en="Does `sentence` use promotional or brochure language (boasts, vibrant, rich heritage, profound, nestled, in the heart of, groundbreaking, breathtaking, stunning, must-visit, renowned, world-class)?",
                es="¿`sentence` usa lenguaje promocional o de folleto (presume de, vibrante, rica herencia, profundo, enclavado, en el corazón de, revolucionario, impresionante, imperdible, renombrado, de clase mundial)?",
                pt="`sentence` usa linguagem promocional ou de folheto (ostenta, vibrante, rica herança, profundo, aninhado, no coração de, revolucionário, de tirar o fôlego, imperdível, renomado, de classe mundial)?")),
    dict(id="vague_attribution", rule="A5", scope="sentence", type="noul",
         q=dict(en="Does `sentence` attribute a claim to unnamed authorities instead of a specific person, study or date (experts argue, industry reports, observers have noted, some critics, many believe, studies show, it is widely accepted)?",
                es="¿`sentence` atribuye una afirmación a autoridades sin nombre en vez de a una persona, estudio o fecha concretos (los expertos afirman, informes del sector, observadores han señalado, algunos críticos, muchos creen, estudios muestran, es ampliamente aceptado)?",
                pt="`sentence` atribui uma afirmação a autoridades sem nome em vez de a uma pessoa, estudo ou data específicos (especialistas afirmam, relatórios do setor, observadores notaram, alguns críticos, muitos acreditam, estudos mostram, é amplamente aceito)?")),
    dict(id="challenges_future", rule="A6", scope="paragraph", type="noul",
         q=dict(en="Does `paragraph` follow the formula 'despite its success, X faces challenges' or close with a generic 'future outlook' / 'looking ahead' instead of concrete events?")),

    # ---------------- B. Language and grammar ----------------
    dict(id="ai_vocabulary", rule="B7", scope="sentence", type="noul", plain_neg_only=True,
         q=dict(en="Does `sentence` use words typical of AI-generated text (delve, crucial, pivotal, robust, seamless, leverage, landscape, tapestry, testament, underscore, enhance, foster, navigate, nuanced, comprehensive, transformative, intricate, meticulous, showcase, garner, interplay, moreover, furthermore, additionally)?",
                es="¿`sentence` usa palabras típicas de texto generado por IA (sumergirse, crucial, fundamental, robusto, fluido, aprovechar, potenciar, panorama, entramado, testimonio, subrayar, mejorar, fomentar, navegar, matizado, integral, transformador, intrincado, meticuloso, además, asimismo, cabe destacar)?",
                pt="`sentence` usa palavras típicas de texto gerado por IA (mergulhar, crucial, fundamental, robusto, fluido, alavancar, potencializar, cenário, panorama, tapeçaria, testemunho, ressaltar, aprimorar, fomentar, navegar, nuançado, abrangente, transformador, intrincado, meticuloso, além disso, ademais, vale destacar)?")),
    dict(id="copula_avoidance", rule="B8", scope="sentence", type="noul",
         q=dict(en="Does `sentence` use a fancy verb where 'is' or 'has' would do (serves as, stands as, represents, boasts, features, offers, marks, acts as)?",
                es="¿`sentence` usa un verbo rebuscado donde bastaría 'es' o 'tiene' (sirve como, se erige como, representa, cuenta con, ofrece, marca, actúa como, constituye)?",
                pt="`sentence` usa um verbo rebuscado onde bastaria 'é' ou 'tem' (serve como, se ergue como, representa, conta com, oferece, marca, atua como, constitui)?")),
    dict(id="negative_parallelism", rule="B9", scope="sentence", type="noul",
         q=dict(en="Does `sentence` use a 'not only X but Y', 'not X but Y', 'it's not just about X, it's Y' contrast, or a trailing negated fragment (..., no guessing; ..., no wasted motion)?",
                es="¿`sentence` usa un contraste 'no solo X sino Y', 'no X sino Y', 'no se trata solo de X, sino de Y', o un fragmento negado al final (..., sin adivinar; ..., sin esfuerzo perdido)?",
                pt="`sentence` usa um contraste 'não só X mas Y', 'não X mas Y', 'não se trata só de X, mas de Y', ou um fragmento negado no final (..., sem adivinhação; ..., sem esforço perdido)?")),
    dict(id="rule_of_three", rule="B10", scope="sentence", type="noul",
         q=dict(en="Does `sentence` list exactly three adjectives, nouns or clauses for rhythm where two would carry the meaning?")),
    dict(id="elegant_variation", rule="B11", scope="paragraph", type="noul",
         q=dict(en="Does `paragraph` cycle through different synonyms for the same thing (protagonist, main character, central figure, hero) instead of reusing one term?")),
    dict(id="false_range", rule="B12", scope="sentence", type="noul",
         q=dict(en="Does `sentence` use 'from X to Y' or 'ranging from A to B' where X and Y are not points on a real scale (from code reviews to team culture)?",
                es="¿`sentence` usa 'desde X hasta Y' o 'que van de A a B' donde X e Y no son puntos de una escala real (desde la revisión de código hasta la cultura del equipo)?",
                pt="`sentence` usa 'de X a Y' ou 'que vão de A a B' onde X e Y não são pontos de uma escala real (da revisão de código à cultura da equipe)?")),
    dict(id="passive_hidden_actor", rule="B13", scope="sentence", type="noul",
         q=dict(en="Does `sentence` use passive voice to hide an actor who matters and is knowable (it was decided that, mistakes were made, the bug was fixed by the team, it is considered)? Passive with an unknown or irrelevant actor does not count.")),

    # ---------------- D. Communication patterns ----------------
    dict(id="chatbot_artifact", rule="D20", scope="sentence", type="noul",
         q=dict(en="Does `sentence` read like a chatbot replying to a user in a conversation (I hope this helps, Certainly!, Of course!, Would you like me to, Let me know if, Here is a summary, Feel free to ask)? Documentation or an email that explains what something does, or tells the reader what to run, is not a chatbot artifact.",
                es="¿`sentence` suena como un chatbot dirigiéndose a un usuario (espero que esto ayude, ¡Claro!, ¡Por supuesto!, ¿Te gustaría que, Avísame si, Aquí tienes, No dudes en)?",
                pt="`sentence` soa como um chatbot falando com um usuário (espero que isso ajude, Claro!, Com certeza!, Gostaria que eu, Me avise se, Aqui está, Fique à vontade para)?")),
    dict(id="knowledge_cutoff", rule="D21", scope="sentence", type="noul",
         q=dict(en="Does `sentence` hedge with a knowledge-cutoff style disclaimer (as of my last update, as of 2024, based on available information, while specific details are limited, it is unclear whether)?")),
    dict(id="sycophancy", rule="D22", scope="sentence", type="noul",
         q=dict(en="Does `sentence` flatter the reader (Great question!, You're absolutely right, That's an excellent point, What a thoughtful observation)?",
                es="¿`sentence` halaga al lector (¡Excelente pregunta!, Tienes toda la razón, Es un punto excelente, Qué observación tan acertada)?",
                pt="`sentence` bajula o leitor (Ótima pergunta!, Você tem toda a razão, É um excelente ponto, Que observação perspicaz)?")),

    # ---------------- E. Filler and hedging ----------------
    dict(id="filler_phrase", rule="E23", scope="sentence", type="noul",
         q=dict(en="Does `sentence` contain wordy filler that a shorter phrase replaces (in order to, due to the fact that, at this point in time, has the ability to, it is important to note that, it is worth mentioning, in terms of)?",
                es="¿`sentence` contiene relleno que una frase más corta reemplaza (con el fin de, debido al hecho de que, en este momento, tiene la capacidad de, es importante señalar que, cabe mencionar, en términos de)?",
                pt="`sentence` contém enchimento que uma frase mais curta substitui (a fim de, devido ao fato de que, neste momento, tem a capacidade de, é importante notar que, vale mencionar, em termos de)?")),
    dict(id="stacked_hedging", rule="E24", scope="sentence", type="noul",
         q=dict(en="Does `sentence` stack qualifiers or hedges (could potentially, might possibly, may perhaps, somewhat, to some extent, arguably, in many cases, it seems that)?",
                es="¿`sentence` acumula matizadores o atenuantes (podría potencialmente, quizás posiblemente, tal vez, en cierta medida, hasta cierto punto, posiblemente, en muchos casos, parece que)?",
                pt="`sentence` acumula qualificadores ou atenuantes (poderia potencialmente, talvez possivelmente, de certa forma, em certa medida, até certo ponto, possivelmente, em muitos casos, parece que)?")),
    dict(id="generic_conclusion", rule="E25", scope="sentence", type="noul",
         q=dict(en="Is `sentence` a generic upbeat conclusion with no concrete fact (the future looks bright, exciting times lie ahead, a step in the right direction, only time will tell, the possibilities are endless)?",
                es="¿`sentence` es una conclusión genérica y optimista sin ningún hecho concreto (el futuro es prometedor, se avecinan tiempos emocionantes, un paso en la dirección correcta, solo el tiempo lo dirá, las posibilidades son infinitas)?",
                pt="`sentence` é uma conclusão genérica e otimista sem nenhum fato concreto (o futuro é promissor, tempos empolgantes estão por vir, um passo na direção certa, só o tempo dirá, as possibilidades são infinitas)?")),
    dict(id="authority_trope", rule="E27", scope="sentence", type="noul",
         q=dict(en="Does `sentence` open or pivot with a persuasive authority trope (the real question is, at its core, in reality, what really matters, fundamentally, the deeper issue, the heart of the matter, at the end of the day)?",
                es="¿`sentence` abre o gira con un recurso de autoridad persuasivo (la verdadera pregunta es, en el fondo, en realidad, lo que realmente importa, fundamentalmente, el problema de fondo, el meollo del asunto, a fin de cuentas)?",
                pt="`sentence` abre ou vira com um recurso de autoridade persuasivo (a verdadeira questão é, em sua essência, na realidade, o que realmente importa, fundamentalmente, o problema mais profundo, o cerne da questão, no fim das contas)?")),
    dict(id="signposting", rule="E28", scope="sentence", type="noul",
         q=dict(en="Does `sentence` announce what comes next instead of saying it (let's dive in, let's explore, let's break this down, here's what you need to know, now let's look at, without further ado, in this article we will)? A plain pointer to another place (see section 4, details in the README) is not signposting.",
                es="¿`sentence` anuncia lo que viene en vez de decirlo (vamos a sumergirnos, exploremos, desglosemos esto, esto es lo que necesitas saber, ahora veamos, sin más preámbulos, en este artículo veremos)?",
                pt="`sentence` anuncia o que vem a seguir em vez de dizer (vamos mergulhar, vamos explorar, vamos destrinchar isso, aqui está o que você precisa saber, agora vejamos, sem mais delongas, neste artigo veremos)?")),

    # ---------------- F. stop-slop additions ----------------
    dict(id="throat_clearing", rule="F1", scope="sentence", type="noul",
         q=dict(en="Does `sentence` start with a throat-clearing opener (here's the thing, here's why, the truth is, let me be clear, it turns out, I'm going to be honest, the uncomfortable truth is, can we talk about, here's the problem though)?",
                es="¿`sentence` empieza con una muletilla introductoria (la cuestión es, esto es lo que pasa, la verdad es que, seamos claros, resulta que, voy a ser honesto, la verdad incómoda es, podemos hablar de, el problema es que)?",
                pt="`sentence` começa com uma muleta introdutória (a questão é, o negócio é o seguinte, a verdade é que, vamos ser claros, acontece que, vou ser honesto, a verdade desconfortável é, podemos falar sobre, o problema é que)?")),
    dict(id="emphasis_crutch", rule="F2", scope="sentence", type="noul",
         q=dict(en="Does `sentence` use an emphasis crutch (Full stop., Period., Let that sink in., Make no mistake, This matters because, Here's why that matters, Read that again)?",
                es="¿`sentence` usa una muleta de énfasis (Punto., Y punto., Piénsalo bien., Que no quepa duda, Esto importa porque, Por eso importa, Léelo otra vez)?",
                pt="`sentence` usa uma muleta de ênfase (Ponto final., E ponto., Pense nisso., Não se engane, Isso importa porque, É por isso que importa, Leia de novo)?")),
    dict(id="business_jargon", rule="F3", scope="sentence", type="noul",
         q=dict(en="Does `sentence` use business jargon (navigate, unpack, lean into, game-changer, double down, deep dive, take a step back, moving forward, circle back, on the same page, synergy, low-hanging fruit)?",
                es="¿`sentence` usa jerga empresarial (navegar, desglosar, apostar por, un antes y un después, redoblar la apuesta, análisis profundo, dar un paso atrás, de cara al futuro, retomar, en la misma página, sinergia, fruta madura)?",
                pt="`sentence` usa jargão empresarial (navegar, destrinchar, apostar em, divisor de águas, dobrar a aposta, mergulho profundo, dar um passo atrás, daqui para frente, retomar, na mesma página, sinergia, frutos fáceis)?")),
    dict(id="meta_commentary", rule="F4", scope="sentence", type="noul",
         q=dict(en="Does `sentence` comment on the text itself instead of making a point (Hint:, Plot twist:, Spoiler:, you already know this but, but that's another post, let me walk you through, in this section we'll, as we'll see, I want to explore)?",
                es="¿`sentence` comenta sobre el propio texto en vez de decir algo (Pista:, Giro inesperado:, Spoiler:, ya lo sabes pero, pero eso es otro tema, déjame guiarte, en esta sección veremos, como veremos, quiero explorar)?",
                pt="`sentence` comenta sobre o próprio texto em vez de dizer algo (Dica:, Reviravolta:, Spoiler:, você já sabe disso mas, mas isso é outro assunto, deixe-me guiá-lo, nesta seção veremos, como veremos, quero explorar)?")),
    dict(id="telling_not_showing", rule="F5", scope="sentence", type="noul",
         q=dict(en="Does `sentence` announce a conclusion instead of showing evidence (this is genuinely hard, this is what leadership actually looks like, this actually matters, this is the part people miss)?")),
    dict(id="vague_declarative", rule="F6", scope="sentence", type="noul",
         q=dict(en="Does `sentence` make a sweeping claim with no specifics (the reasons are structural, the implications are significant, this is the deepest problem, the stakes are high, the consequences are real)?")),
    dict(id="rhetorical_setup", rule="F7", scope="sentence", type="noul",
         q=dict(en="Does `sentence` set up a rhetorical device instead of stating the point (What if, Think about it, Consider this, Imagine, Picture this, Sound familiar?)?",
                es="¿`sentence` plantea un recurso retórico en vez de decir el punto (¿Y si, Piénsalo, Considera esto, Imagina, Imagínate esto, ¿Te suena?)?",
                pt="`sentence` arma um recurso retórico em vez de dizer o ponto (E se, Pense nisso, Considere isto, Imagine, Imagine a cena, Soa familiar?)?")),
    dict(id="dramatic_fragments", rule="F8", scope="paragraph", type="noul",
         q=dict(en="Does `paragraph` use very short sentence fragments for dramatic effect rather than for a clear purpose (Three words. That's it. Done. Every time.)?")),
    dict(id="false_agency", rule="F9", scope="sentence", type="noul",
         q=dict(en="Does `sentence` give an inanimate subject a human act of interpreting (the data tells us, the numbers show, the results suggest, the research reveals, the evidence speaks)?",
                es="¿`sentence` da a un sujeto inanimado un acto humano de interpretar (los datos nos dicen, las cifras muestran, los resultados sugieren, la investigación revela, la evidencia habla)?",
                pt="`sentence` dá a um sujeito inanimado um ato humano de interpretar (os dados nos dizem, os números mostram, os resultados sugerem, a pesquisa revela, as evidências falam)?")),
    dict(id="narrator_distance", rule="F10", scope="paragraph", type="noul",
         q=dict(en="Is `paragraph` written in a detached narrator voice about abstractions and general people, where talking to the reader as 'you' with concrete details would fit better?")),
    dict(id="quotable_line", rule="F12", scope="sentence", type="noul",
         q=dict(en="Does `sentence` read like a pull quote or aphorism, punchy and polished for quoting rather than for informing?")),
    dict(id="redundant_confirmation", rule="F15", scope="sentence", type="noul", context=True,
         q=dict(en="Given the surrounding `paragraph`, does `sentence` add nothing the reader did not already know: an empty confirmation (it is all done, it's all set, just to confirm, as mentioned, as you know), a padding verb of intention (I went ahead and, I just wanted to, I am writing to, I took the liberty of), a restatement of what another line shows, or an announcement of something NOT done (I have not attached, I did not include)?",
                es="Dado el `paragraph` que la rodea, ¿`sentence` no aporta nada que el lector no supiera ya: una confirmación vacía (ya está todo listo, solo para confirmar, como mencioné, como sabes), un verbo de intención de relleno (procedí a, solo quería, le escribo para, me tomé la libertad de), una repetición de lo que otra línea ya muestra, o el anuncio de algo que NO se hizo (no adjunté, no incluí)?",
                pt="Dado o `paragraph` ao redor, `sentence` não acrescenta nada que o leitor já não soubesse: uma confirmação vazia (está tudo pronto, só para confirmar, como mencionei, como você sabe), um verbo de intenção de enchimento (fui lá e, só queria, escrevo para, tomei a liberdade de), uma repetição do que outra linha já mostra, ou o anúncio de algo que NÃO foi feito (não anexei, não incluí)?")),
    dict(id="headless_statement", rule="F16", scope="sentence", type="noul", context=True,
         q=dict(en="Does `sentence` open with a bare noun phrase or a bare count and never say what it is describing, so it reads like a table caption or slide bullet pasted into prose (Six transforms ran over the corpus. Figures are the median of three runs. Present: X, Y. Two things make this a workaround.)?")),

    # ---------------- G. Adverbs ----------------
    dict(id="filler_adverb", rule="G", scope="sentence", type="noul", plain_neg_only=True,
         q=dict(en="Does `sentence` contain an adverb that only adds emphasis or hedging, so the sentence would mean the same without it (really, just, literally, genuinely, honestly, simply, actually, basically, deeply, truly, fundamentally, inherently, completely, essentially, quite, rather, very)? Adverbs that change the technical meaning (lazily, atomically, explicitly, recursively) do not count.",
                es="¿`sentence` contiene un adverbio que solo añade énfasis o atenuación, de modo que la frase significaría lo mismo sin él (realmente, simplemente, literalmente, genuinamente, honestamente, básicamente, profundamente, verdaderamente, fundamentalmente, completamente, esencialmente, bastante, muy)? Los adverbios que cambian el significado técnico (de forma perezosa, atómicamente, explícitamente, recursivamente) no cuentan.",
                pt="`sentence` contém um advérbio que só acrescenta ênfase ou atenuação, de modo que a frase significaria o mesmo sem ele (realmente, simplesmente, literalmente, genuinamente, honestamente, basicamente, profundamente, verdadeiramente, fundamentalmente, completamente, essencialmente, bastante, muito)? Advérbios que mudam o significado técnico (preguiçosamente, atomicamente, explicitamente, recursivamente) não contam.")),

    # ---------------- Overall ----------------
    dict(id="ai_overall", rule="*", scope="sentence", type="score",
         levels=["written by a person", "mixed or unclear", "typical of AI-generated text"],
         q=dict(en="How much does `sentence` read like AI-generated text rather than text written by a person?")),
    dict(id="ai_overall_paragraph", rule="*", scope="paragraph", type="score",
         levels=["written by a person", "mixed or unclear", "typical of AI-generated text"],
         q=dict(en="How much does `paragraph` read like AI-generated text rather than text written by a person?")),
]
