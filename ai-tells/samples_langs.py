"""
Spanish and Portuguese calibration samples for calibrate.py --lang es|pt.

Same shape as samples.py: POS[criterion_id] = texts where the pattern is
present; NEG_SENTENCES / NEG_PARAGRAPHS = plain human writing. Criteria
without positives here are measured only against the negatives' false-positive
rate and marked unreliable by calibrate.py (no TPR), which is the honest
default until someone adds samples.
"""

POS_ES = {
    "undue_significance": [
        "Este lanzamiento marca un hito que definirá el futuro del ecosistema.",
        "Su obra dejó una huella imborrable y refleja cambios más amplios en la industria.",
    ],
    "participle_tail": [
        "El equipo adoptó la herramienta en marzo, reflejando su compromiso con la calidad.",
        "Las ventas subieron un 12 por ciento, destacando la creciente demanda en la región.",
    ],
    "promotional": [
        "Enclavado en el corazón del casco antiguo, el café presume de un ambiente vibrante y una rica herencia culinaria.",
        "Este marco revolucionario ofrece una experiencia impresionante y de clase mundial.",
    ],
    "vague_attribution": [
        "Los expertos afirman que el trabajo remoto mejora la productividad de la mayoría de los equipos.",
        "Informes del sector sugieren que la adopción se duplicará en dos años.",
    ],
    "ai_vocabulary": [
        "Es crucial sumergirse en el intrincado entramado entre rendimiento y mantenibilidad.",
        "Esta guía integral te ayudará a navegar el matizado panorama de las herramientas modernas.",
        "La nueva API fomenta una experiencia fluida y robusta para el desarrollador.",
    ],
    "copula_avoidance": [
        "La función sirve como punto de entrada principal del programa.",
        "El informe constituye un resumen de los resultados del año pasado.",
    ],
    "negative_parallelism": [
        "No se trata solo de un compilador más rápido, sino de una nueva forma de pensar.",
        "No solo pasaron las pruebas, sino que la compilación también fue más rápida.",
    ],
    "false_range": [
        "El taller cubre desde la revisión de código hasta la cultura del equipo.",
        "Nuestros clientes van desde startups hasta hospitales.",
    ],
    "chatbot_artifact": [
        "¡Espero que esto ayude! Avísame si tienes otra pregunta.",
        "¡Claro! Aquí tienes un resumen de los puntos clave que pediste.",
    ],
    "sycophancy": [
        "¡Excelente pregunta! Has tocado algo realmente importante.",
        "Tienes toda la razón, y es un punto excelente.",
    ],
    "filler_phrase": [
        "Con el fin de ejecutar las pruebas, es necesario instalar primero las dependencias.",
        "Debido al hecho de que el servidor estaba caído, perdimos la fecha límite.",
    ],
    "stacked_hedging": [
        "Esto podría potencialmente causar quizás algunos problemas en ciertos casos.",
        "Tal vez sea, en cierta medida, algo beneficioso para algunos usuarios.",
    ],
    "generic_conclusion": [
        "El futuro es prometedor para el proyecto y su creciente comunidad.",
        "Es un paso en la dirección correcta, y se avecinan tiempos emocionantes.",
    ],
    "authority_trope": [
        "En el fondo, esto es una cuestión de confianza.",
        "A fin de cuentas, lo que realmente importa es el usuario.",
    ],
    "signposting": [
        "Vamos a sumergirnos y explorar cómo funciona el planificador.",
        "En este artículo veremos tres formas de guardar resultados en caché.",
    ],
    "throat_clearing": [
        "La cuestión es que la mayoría de los equipos nunca mide sus tiempos de compilación.",
        "La verdad es que nadie lee la documentación.",
    ],
    "emphasis_crutch": [
        "Que no quepa duda, este cambio te va a costar. Y punto.",
        "Las compilaciones son lentas. Piénsalo bien.",
    ],
    "business_jargon": [
        "De cara al futuro, debemos redoblar la apuesta por la plataforma y retomar el tema el próximo trimestre.",
        "Es un antes y un después, así que apostemos por ello y hagamos un análisis profundo.",
    ],
    "rhetorical_setup": [
        "¿Y si tus compilaciones tardaran cinco segundos en vez de cinco minutos?",
        "Piénsalo: cada minuto de espera es un minuto sin programar.",
    ],
    "false_agency": [
        "Los datos nos dicen que los usuarios prefieren el tema oscuro.",
        "Las cifras muestran una clara caída en las cancelaciones desde marzo.",
    ],
    "vague_declarative": [
        "Las razones son estructurales y las implicaciones son significativas.",
        "Hay mucho en juego y las consecuencias son reales.",
    ],
    "filler_adverb": [
        "El código fue completamente refactorizado la semana pasada.",
        "Básicamente así funciona, y es realmente bastante simple.",
    ],
    "challenges_future": [
        "A pesar de su éxito, el proyecto enfrenta desafíos, como la financiación limitada y una base de colaboradores cada vez menor. De cara al futuro, la comunidad sigue siendo optimista.",
    ],
    "dramatic_fragments": [
        "Tres palabras. Eso es todo. Listo. No más reuniones. Nunca.",
    ],
}

NEG_ES = [
    "Reservé el hotel como sugeriste y adjunto el recibo.",
    "El vuelo llega a las seis de la tarde del viernes, así que tomaré un taxi al lugar.",
    "¿Me puedes mandar el número de la factura cuando puedas?",
    "La compilación tarda unos cuatro minutos en mi laptop y nueve en el servidor.",
    "Movimos la configuración a un solo archivo para que la gente nueva lo encuentre.",
    "El dueño del apartamento todavía no devuelve el depósito, así que presenté la queja el lunes.",
    "La función devuelve un puntero al primer elemento, o nulo si el vector está vacío.",
    "Gracias por la revisión. Corregí los dos errores y volví a subir el código.",
    "La cena es a las ocho. Trae el vino que mencionaste.",
    "La prueba falla en Windows porque el separador de rutas es distinto.",
    "Leí el artículo dos veces y todavía no entiendo la sección cuatro.",
    "Somos tres personas en Panamá y dos en Brasil.",
    "El carro necesita llantas nuevas antes del viaje, así que reservé el taller para el martes.",
    "El precio subió de 40 a 55 dólares este año.",
    "Necesito el formulario firmado antes del viernes o el banco cierra la solicitud.",
    "La charla dura 45 minutos más 15 de preguntas.",
    "Por favor trae el pasaporte y el boleto impreso.",
    "Lo medí tres veces y obtuve 2,1, 2,3 y 2,2 segundos.",
]

NEG_PARA_ES = [
    "Reservé el hotel como sugeriste. Adjunto el recibo. El vuelo llega a las seis de la tarde del viernes, así que tomaré un taxi y debería estar allí a las ocho.",
    "El analizador lee una línea a la vez. Cuando encuentra un marcador de comentario, salta al final de la línea. Las cadenas se manejan aparte porque pueden contener el marcador.",
    "El dueño todavía no devuelve el depósito. Envié el aviso por escrito el lunes y guardé una copia. Si no sé nada antes del 15, presento la queja en la oficina de vivienda.",
]

POS_PT = {
    "undue_significance": [
        "Este lançamento marca um marco que vai definir o futuro do ecossistema.",
        "O trabalho dela deixou uma marca indelével e reflete mudanças mais amplas no setor.",
    ],
    "participle_tail": [
        "A equipe adotou a ferramenta em março, refletindo seu compromisso com a qualidade.",
        "As vendas subiram 12 por cento, destacando a crescente demanda na região.",
    ],
    "promotional": [
        "Aninhado no coração do centro histórico, o café ostenta um ambiente vibrante e uma rica herança culinária.",
        "Este framework revolucionário entrega uma experiência de tirar o fôlego e de classe mundial.",
    ],
    "vague_attribution": [
        "Especialistas afirmam que o trabalho remoto melhora a produtividade da maioria das equipes.",
        "Relatórios do setor sugerem que a adoção vai dobrar em dois anos.",
    ],
    "ai_vocabulary": [
        "É crucial mergulhar na intrincada tapeçaria entre desempenho e manutenibilidade.",
        "Este guia abrangente vai ajudar você a navegar pelo cenário nuançado das ferramentas modernas.",
        "A nova API fomenta uma experiência fluida e robusta para o desenvolvedor.",
    ],
    "copula_avoidance": [
        "A função serve como ponto de entrada principal do programa.",
        "O relatório constitui um resumo dos resultados do ano passado.",
    ],
    "negative_parallelism": [
        "Não se trata só de um compilador mais rápido, mas de uma nova forma de pensar.",
        "Não só os testes passaram, como o build também ficou mais rápido.",
    ],
    "false_range": [
        "O workshop cobre desde a revisão de código até a cultura da equipe.",
        "Nossos clientes vão de startups a hospitais.",
    ],
    "chatbot_artifact": [
        "Espero que isso ajude! Me avise se tiver outra pergunta.",
        "Claro! Aqui está um resumo dos pontos principais que você pediu.",
    ],
    "sycophancy": [
        "Ótima pergunta! Você tocou em algo realmente importante.",
        "Você tem toda a razão, e esse é um excelente ponto.",
    ],
    "filler_phrase": [
        "A fim de rodar os testes, é preciso instalar as dependências primeiro.",
        "Devido ao fato de que o servidor estava fora do ar, perdemos o prazo.",
    ],
    "stacked_hedging": [
        "Isso poderia potencialmente causar talvez alguns problemas em certos casos.",
        "Talvez seja, em certa medida, um pouco benéfico para alguns usuários.",
    ],
    "generic_conclusion": [
        "O futuro é promissor para o projeto e sua comunidade crescente.",
        "É um passo na direção certa, e tempos empolgantes estão por vir.",
    ],
    "authority_trope": [
        "Em sua essência, isso é uma questão de confiança.",
        "No fim das contas, o que realmente importa é o usuário.",
    ],
    "signposting": [
        "Vamos mergulhar e explorar como o agendador funciona.",
        "Neste artigo veremos três formas de guardar resultados em cache.",
    ],
    "throat_clearing": [
        "O negócio é o seguinte: a maioria das equipes nunca mede o tempo de build.",
        "A verdade é que ninguém lê a documentação.",
    ],
    "emphasis_crutch": [
        "Não se engane, essa mudança vai custar caro. E ponto.",
        "Os builds são lentos. Pense nisso.",
    ],
    "business_jargon": [
        "Daqui para frente, devemos dobrar a aposta na plataforma e retomar o assunto no próximo trimestre.",
        "É um divisor de águas, então vamos apostar nisso e fazer um mergulho profundo.",
    ],
    "rhetorical_setup": [
        "E se seus builds levassem cinco segundos em vez de cinco minutos?",
        "Pense nisso: cada minuto de espera é um minuto sem programar.",
    ],
    "false_agency": [
        "Os dados nos dizem que os usuários preferem o tema escuro.",
        "Os números mostram uma queda clara nos cancelamentos desde março.",
    ],
    "vague_declarative": [
        "As razões são estruturais e as implicações são significativas.",
        "Há muito em jogo e as consequências são reais.",
    ],
    "filler_adverb": [
        "O código foi completamente refatorado na semana passada.",
        "Basicamente é assim que funciona, e é realmente bem simples.",
    ],
    "challenges_future": [
        "Apesar do sucesso, o projeto enfrenta desafios, como financiamento limitado e uma base de colaboradores cada vez menor. Olhando para frente, a comunidade segue otimista.",
    ],
    "dramatic_fragments": [
        "Três palavras. É isso. Pronto. Chega de reuniões. Nunca mais.",
    ],
}

NEG_PT = [
    "Reservei o hotel como você sugeriu e o recibo está anexado.",
    "O voo chega às seis da tarde de sexta, então vou pegar um táxi até o local.",
    "Você pode me mandar o número da nota fiscal quando der?",
    "O build leva uns quatro minutos no meu notebook e nove no servidor.",
    "Movemos a configuração para um único arquivo para que quem chega consiga achar.",
    "O dono do apartamento ainda não devolveu o depósito, então registrei a reclamação na segunda.",
    "A função retorna um ponteiro para o primeiro elemento, ou nulo se o vetor estiver vazio.",
    "Obrigado pela revisão. Corrigi os dois erros e subi o código de novo.",
    "O jantar é às oito. Traz o vinho que você falou.",
    "O teste falha no Windows porque o separador de caminho é diferente.",
    "Li o artigo duas vezes e ainda não entendo a seção quatro.",
    "Somos três pessoas no Panamá e duas no Brasil.",
    "O carro precisa de pneus novos antes da viagem, então marquei a oficina para terça.",
    "O preço subiu de 40 para 55 dólares este ano.",
    "Preciso do formulário assinado até sexta ou o banco fecha o pedido.",
    "A palestra tem 45 minutos mais 15 de perguntas.",
    "Por favor, traga o passaporte e a passagem impressa.",
    "Medi três vezes e deu 2,1, 2,3 e 2,2 segundos.",
]

NEG_PARA_PT = [
    "Reservei o hotel como você sugeriu. O recibo está anexado. O voo chega às seis da tarde de sexta, então vou de táxi e devo chegar lá às oito.",
    "O parser lê uma linha por vez. Quando encontra um marcador de comentário, pula para o fim da linha. Strings são tratadas à parte porque podem conter o marcador.",
    "O dono ainda não devolveu o depósito. Mandei o aviso por escrito na segunda e guardei uma cópia. Se não souber de nada até o dia 15, registro a reclamação no órgão de habitação.",
]

SETS = {
    "es": (POS_ES, NEG_ES, NEG_PARA_ES),
    "pt": (POS_PT, NEG_PT, NEG_PARA_PT),
}
