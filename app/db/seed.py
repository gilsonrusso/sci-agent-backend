from sqlmodel import Session, select
from app.models.template import Template, TemplateCreate
from app.db.session import engine

DEFAULT_TEMPLATE_CONTENT = r"""\documentclass[12pt,a4paper]{article}

% --- Pacotes Básicos ---
\usepackage[utf8]{inputenc}    % Codificação de caracteres
\usepackage[T1]{fontenc}       % Codificação da fonte
\usepackage[brazil]{babel}     % Idioma português
\usepackage{indentfirst}       % Indenta o primeiro parágrafo
\usepackage{graphicx}          % Inclusão de figuras
\usepackage{amsmath}           % Fórmulas matemáticas
\usepackage{geometry}          % Margens
\geometry{top=3cm, bottom=2cm, left=3cm, right=2cm}

% --- Informações do Artigo ---
\title{Título do Seu Artigo Científico: Subtítulo se houver}
\author{Nome do Autor 1 \thanks{Email: autor1@exemplo.com} \\ Nome do Autor 2 \thanks{Instituição de Ensino}}
\date{\today}

\begin{document}

\maketitle

\begin{abstract}
Este é o resumo do seu trabalho. Deve conter o objetivo, a metodologia, os principais resultados e a conclusão em um único parágrafo. Geralmente possui entre 100 e 250 palavras.
\par\vspace{0.5em}
\noindent\textbf{Palavras-chave:} LaTeX, Artigo Científico, Template.
\end{abstract}

\section{Introdução}
Aqui você apresenta o tema, o problema de pesquisa e a justificativa do seu trabalho. O LaTeX cuida da numeração automática das seções.

\section{Referencial Teórico}
Nesta parte, você discute trabalhos anteriores. Para citar alguém, você pode usar o comando \texttt{cite}. Exemplo: Segundo o guia do \href{https://pt.overleaf.com}{Overleaf}, LaTeX é excelente para documentos técnicos.

\section{Metodologia}
Descreva como o estudo foi realizado. Se precisar inserir uma lista:
\begin{itemize}
    \item Coleta de dados;
    \item Análise estatística;
    \item Discussão dos resultados.
\end{itemize}

\section{Resultados e Discussão}
Apresente seus dados. Abaixo, um exemplo de como inserir uma equação:
\begin{equation}
    E = mc^2
\end{equation}

\section{Conclusão}
Finalize seu texto recapitulando se os objetivos foram atingidos e sugerindo trabalhos futuros.

% --- Referências ---
\begin{thebibliography}{99}
\bibitem{exemplo1} SOBRENOME, Nome. \textit{Título do Livro}. Cidade: Editora, Ano.
\end{thebibliography}

\end{document}
"""


def seed_db(session: Session):
    # Check if default template exists
    statement = select(Template).where(Template.is_default == True)
    default_template = session.exec(statement).first()

    if not default_template:
        template_in = TemplateCreate(
            title="Artigo Científico Padrão (ABNT)",
            description="Template básico para artigos científicos com formatação ABNT.",
            content=DEFAULT_TEMPLATE_CONTENT,
            is_default=True,
        )
        template = Template.model_validate(template_in)
        session.add(template)
        session.commit()
        session.refresh(template)
        print("Default template created.")
    else:
        print("Default template already exists.")


if __name__ == "__main__":
    with Session(engine) as session:
        seed_db(session)
